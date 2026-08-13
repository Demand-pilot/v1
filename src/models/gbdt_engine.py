"""
LightGBM / XGBoost GBDT Engine for DemandPilot Layer 4.
Target: Promo-elastic surge items (Sierra School Supplies, Home Care) and tabular interaction features.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from src.models.exceptions import ModelNotFittedError


class DemandGBDT:
    """
    Gradient Boosted Decision Tree (GBDT) engine wrapper.
    Leverages categorical tree splits and tabular lag/lead features.
    """

    def __init__(self, n_estimators: int = 100, learning_rate: float = 0.03, max_depth: int = 8):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.model = None
        self.is_fitted = False

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        categorical_features: Optional[List[str]] = None
    ) -> "DemandGBDT":
        """
        Fits LightGBM (or scikit-learn GradientBoosting fallback) model.
        """
        X_clean = X_train.copy()
        for col in X_clean.select_dtypes(include=['category', 'object']).columns:
            X_clean[col] = X_clean[col].astype('category').cat.codes
        X_clean = X_clean.fillna(0.0)

        log_y = np.log1p(np.clip(y_train, 0, None))

        try:
            import lightgbm as lgb
            params = {
                'objective': 'regression',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'n_estimators': self.n_estimators,
                'learning_rate': self.learning_rate,
                'max_depth': self.max_depth,
                'verbose': -1,
                'random_state': 42
            }
            train_data = lgb.Dataset(X_clean, label=log_y)
            self.model = lgb.train(params, train_data)
            self.is_fitted = True
        except ImportError:
            from sklearn.ensemble import GradientBoostingRegressor
            gb = GradientBoostingRegressor(
                n_estimators=min(self.n_estimators, 50),
                learning_rate=self.learning_rate,
                max_depth=min(self.max_depth, 5),
                random_state=42
            )
            gb.fit(X_clean, log_y)
            self.model = gb
            self.is_fitted = True

        return self

    def predict_16d(self, X_test_16d: pd.DataFrame) -> np.ndarray:
        """
        Predicts 16 future days of unit sales from 16-day feature rows.
        Applies inverse log transformation expm1(y_pred).
        """
        if not self.is_fitted or self.model is None:
            raise ModelNotFittedError(
                "DemandGBDT.predict_16d() called before fit(). "
                "This previously returned np.ones(n) * 100.0, which the API served to the "
                "dashboard as a forecast. Fit the model, or handle this exception by "
                "surfacing an empty state."
            )

        X_clean = X_test_16d.copy()
        for col in X_clean.select_dtypes(include=['category', 'object']).columns:
            X_clean[col] = X_clean[col].astype('category').cat.codes
        X_clean = X_clean.fillna(0.0)

        if not hasattr(self.model, 'predict'):
            raise ModelNotFittedError(
                f"Fitted model object of type {type(self.model).__name__} exposes no "
                f"predict(). Previously this silently returned zeros."
            )
        log_preds = self.model.predict(X_clean)

        preds = np.expm1(log_preds)
        return np.clip(preds, 0.0, None)
