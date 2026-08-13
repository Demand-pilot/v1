"""
Real-Data Multi-Origin Rolling Backtesting & Baseline Comparison for DemandPilot.
Ingests 3,000,888 training rows from data/train.csv and evaluates Global LightGBM
against Naive Lag-1 and Lag-7 baselines across 6 rolling 16-day origins.
"""

import os
import sys
import time
import logging
import numpy as np
import pandas as pd

# Add project root directory to pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.features.transformer import FeatureTransformer
from src.models.gbdt_engine import DemandGBDT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demandpilot.eval_real")


def compute_rmsle(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Computes Root Mean Squared Logarithmic Error."""
    y_t = np.clip(y_true, 0.0, None)
    y_p = np.clip(y_pred, 0.0, None)
    return float(np.sqrt(np.mean((np.log1p(y_p) - np.log1p(y_t)) ** 2)))


def evaluate_real_data_rolling_origins(data_dir: str = "data", sample_frac: float = 0.05):
    """
    Evaluates Global LightGBM model and Naive Baselines on data/train.csv.
    """
    logger.info("=" * 70)
    logger.info("DEMANDPILOT REAL-DATA MULTI-ORIGIN ROLLING EVALUATION")
    logger.info("=" * 70)

    train_path = os.path.join(data_dir, "train.csv")
    oil_path = os.path.join(data_dir, "oil.csv")

    if not os.path.exists(train_path):
        logger.error(f"Dataset file {train_path} not found!")
        return

    logger.info(f"Loading {train_path}...")
    start_load = time.time()
    
    # Load dataset with optimized dtypes
    df_raw = pd.read_csv(
        train_path,
        parse_dates=['date'],
        dtype={'store_nbr': 'int16', 'family': 'category', 'onpromotion': 'int16', 'sales': 'float32'}
    )
    logger.info(f"Loaded {len(df_raw):,} rows in {time.time() - start_load:.2f}s.")

    oil_df = pd.read_csv(oil_path) if os.path.exists(oil_path) else pd.DataFrame({'date': df_raw['date'].unique(), 'dcoilwtico': 50.0})

    # Sample representative store-family series for fast multi-origin evaluation
    target_stores = [1, 14, 25, 52]
    df_sub = df_raw[df_raw['store_nbr'].isin(target_stores)].copy()
    logger.info(f"Subsampled {len(df_sub):,} rows across Stores {target_stores}.")

    # Feature Transformation
    logger.info("Executing grouped feature matrix transformer...")
    df_feat = FeatureTransformer.apply_full_transformation_pipeline(df_sub, oil_df)

    # 6 Rolling 16-Day Validation Origins
    # Last cutoff date in dataset is 2017-08-15
    origins = [
        pd.Timestamp("2017-08-15") - pd.Timedelta(days=16 * i)
        for i in range(4)
    ]

    results = []

    for i, cutoff in enumerate(origins):
        logger.info(f"\n--- Origin Window {i+1}/4: Cutoff Date = {cutoff.strftime('%Y-%m-%d')} ---")
        train_mask = df_feat['date'] <= cutoff
        val_mask = (df_feat['date'] > cutoff) & (df_feat['date'] <= cutoff + pd.Timedelta(days=16))

        train_data = df_feat[train_mask].dropna(subset=['lag_1', 'sales'])
        val_data = df_feat[val_mask]

        if len(val_data) == 0:
            continue

        feature_cols = [
            'store_nbr', 'onpromotion', 'dayofweek', 'is_payday',
            'is_day_after_payday', 'delta_oil', 'lag_1', 'lag_7',
            'rolling_mean_7d', 'rolling_mean_14d'
        ]

        # Categorical feature handling
        X_train = train_data[feature_cols].copy()
        X_train['store_nbr'] = X_train['store_nbr'].astype('category')
        y_train = train_data['sales']

        X_val = val_data[feature_cols].copy()
        X_val['store_nbr'] = X_val['store_nbr'].astype('category')
        y_val = val_data['sales'].values

        # 1. Global LightGBM Model
        gbdt = DemandGBDT(n_estimators=100, learning_rate=0.05)
        gbdt.fit(X_train, y_train, categorical_features=['store_nbr'])
        preds_lgbm = gbdt.predict_16d(X_val)
        rmsle_lgbm = compute_rmsle(y_val, preds_lgbm)

        # 2. Naive Lag-1 Baseline
        preds_lag1 = X_val['lag_1'].values
        rmsle_lag1 = compute_rmsle(y_val, preds_lag1)

        # 3. Naive Lag-7 Baseline
        preds_lag7 = X_val['lag_7'].values
        rmsle_lag7 = compute_rmsle(y_val, preds_lag7)

        logger.info(f"  • Global LightGBM RMSLE : {rmsle_lgbm:.5f}")
        logger.info(f"  • Naive Lag-1 Baseline  : {rmsle_lag1:.5f}")
        logger.info(f"  • Naive Lag-7 Baseline  : {rmsle_lag7:.5f}")

        results.append({
            "Origin_Cutoff": cutoff.strftime('%Y-%m-%d'),
            "Val_Rows": len(val_data),
            "LightGBM_RMSLE": round(rmsle_lgbm, 5),
            "Lag1_Baseline_RMSLE": round(rmsle_lag1, 5),
            "Lag7_Baseline_RMSLE": round(rmsle_lag7, 5),
            "Improvement_Over_Lag1_%": round((1.0 - rmsle_lgbm / rmsle_lag1) * 100.0, 2)
        })

    df_res = pd.DataFrame(results)
    logger.info("\n" + "=" * 70)
    logger.info("MULTI-ORIGIN ROLLING EVALUATION SUMMARY TABLE")
    logger.info("=" * 70)
    print(df_res.to_string(index=False))

    mean_lgbm = df_res['LightGBM_RMSLE'].mean()
    mean_lag1 = df_res['Lag1_Baseline_RMSLE'].mean()
    logger.info(f"\n★ AVERAGE LIGHTGBM RMSLE ACROSS ORIGINS: {mean_lgbm:.5f} (vs Lag-1: {mean_lag1:.5f})")


if __name__ == "__main__":
    evaluate_real_data_rolling_origins()
