"""
Feature Engineering Matrix Transformer for DemandPilot Layer 3.
Transforms raw transaction data into temporal, promotional, and empirical shock features.
"""

from typing import List, Dict, Any
import numpy as np
import pandas as pd


class FeatureTransformer:
    """
    Transforms raw retail dataframe into unified feature matrix.
    """

    @staticmethod
    def transform_oil_data(oil_df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes oil price dataset:
        1. Imputes weekday NaNs via linear interpolation, then ffill/bfill for weekends.
        2. Applies first differencing (delta_oil) to eliminate macro trend drift while preserving shocks.
        """
        df = oil_df.copy()
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')

        # Support real competition oil column `dcoilwtico` or fallback `dwtruck_price`
        oil_col = 'dcoilwtico' if 'dcoilwtico' in df.columns else ('dwtruck_price' if 'dwtruck_price' in df.columns else None)
        if oil_col:
            df['oil_price'] = df[oil_col].interpolate(method='linear').ffill().bfill()
        else:
            df['oil_price'] = 50.0

        # First differencing to eliminate spurious macro trend correlation
        df['delta_oil'] = df['oil_price'].diff().fillna(0.0)
        df['delta_oil_3d_rolling'] = df['delta_oil'].rolling(3, min_periods=1).mean().fillna(0.0)
        return df

    @staticmethod
    def add_payday_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates bi-weekly payday features:
        - is_payday: 15th, 30th, 31st
        - is_day_after_payday: 16th, 1st (peak shopping surge +8.0%)
        - payday_weekday_interaction: (is_day_after_payday) * (weekday < 5)
        """
        df['day'] = pd.to_datetime(df['date']).dt.day
        df['dayofweek'] = pd.to_datetime(df['date']).dt.dayofweek

        df['is_payday'] = df['day'].isin([15, 30, 31]).astype(int)
        df['is_day_after_payday'] = df['day'].isin([16, 1]).astype(int)
        df['payday_weekday_interaction'] = (
            df['is_day_after_payday'] * (df['dayofweek'] < 5).astype(int)
        )
        return df

    @staticmethod
    def add_earthquake_decay_feature(df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates exponential decay feature over 30 days post April 16, 2016 Magnitude 7.8 Earthquake.
        Formula: exp(-days / 10.0) for 0 <= days <= 30 else 0.0
        """
        dates = pd.to_datetime(df['date'])
        eq_date = pd.Timestamp('2016-04-16')
        days_since = (dates - eq_date).dt.days

        df['earthquake_decay'] = np.where(
            (days_since >= 0) & (days_since <= 30),
            np.exp(-days_since / 10.0),
            0.0
        )
        return df

    @classmethod
    def generate_lags_and_rolling(cls, df: pd.DataFrame, target_col: str = "sales") -> pd.DataFrame:
        """
        Generates temporal lags (1, 7, 14, 28) and rolling statistics (7d, 14d, 30d)
        strictly grouped by (store_nbr, family) to prevent cross-series data leakage.
        """
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        has_groups = ('store_nbr' in df.columns) and ('family' in df.columns)
        if has_groups:
            df = df.sort_values(['store_nbr', 'family', 'date']).reset_index(drop=True)
            group_cols = ['store_nbr', 'family']
        else:
            df = df.sort_values('date').reset_index(drop=True)
            group_cols = None

        if target_col in df.columns:
            for lag in [1, 7, 14, 28]:
                if group_cols:
                    df[f'lag_{lag}'] = df.groupby(group_cols)[target_col].shift(lag).fillna(0.0)
                else:
                    df[f'lag_{lag}'] = df[target_col].shift(lag).fillna(0.0)

            for window in [7, 14, 30]:
                if group_cols:
                    df[f'rolling_mean_{window}d'] = (
                        df.groupby(group_cols)[target_col]
                        .transform(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
                        .fillna(0.0)
                    )
                else:
                    df[f'rolling_mean_{window}d'] = (
                        df[target_col].shift(1).rolling(window, min_periods=1).mean().fillna(0.0)
                    )

        if 'onpromotion' in df.columns:
            if group_cols:
                df['promo_lag_1'] = df.groupby(group_cols)['onpromotion'].shift(1).fillna(0.0)
                df['promo_lag_7'] = df.groupby(group_cols)['onpromotion'].shift(7).fillna(0.0)
                df['promo_rolling_mean_7d'] = (
                    df.groupby(group_cols)['onpromotion']
                    .transform(lambda s: s.rolling(7, min_periods=1).mean())
                    .fillna(0.0)
                )
            else:
                df['promo_lag_1'] = df['onpromotion'].shift(1).fillna(0.0)
                df['promo_lag_7'] = df['onpromotion'].shift(7).fillna(0.0)
                df['promo_rolling_mean_7d'] = (
                    df['onpromotion'].rolling(7, min_periods=1).mean().fillna(0.0)
                )

        return df

    @classmethod
    def apply_full_transformation_pipeline(
        cls,
        sales_df: pd.DataFrame,
        oil_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Executes full Layer 3 feature transformation pipeline.
        """
        df = sales_df.copy()
        df['date'] = pd.to_datetime(df['date'])

        # 1. Transform & Merge Oil Data
        oil_clean = cls.transform_oil_data(oil_df)
        df = df.merge(oil_clean[['date', 'delta_oil', 'delta_oil_3d_rolling']], on='date', how='left')
        df['delta_oil'] = df['delta_oil'].fillna(0.0)
        df['delta_oil_3d_rolling'] = df['delta_oil_3d_rolling'].fillna(0.0)

        # 2. Add Payday & Earthquake Features
        df = cls.add_payday_features(df)
        df = cls.add_earthquake_decay_feature(df)

        # 3. Add Grouped Lags and Rolling Statistics
        df = cls.generate_lags_and_rolling(df, target_col='sales')

        # 4. Dec 25 / Jan 1 Calendar Flags
        df['month_day'] = df['date'].dt.strftime('%m-%d')
        df['is_christmas_dec25'] = (df['month_day'] == '12-25').astype(int)
        df['is_new_year_jan1'] = (df['month_day'] == '01-01').astype(int)

        return df
