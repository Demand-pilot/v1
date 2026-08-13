"""
Historical Rolling 16-Day Backtesting Engine for DemandPilot Layer 5.
Evaluates candidate predictions (LSTM, GBDT, Baselines) against actual historical validation windows.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd


class BacktestEngine:
    """
    Evaluates 16-day backtest forecasts using Root Mean Squared Logarithmic Error (RMSLE).
    """

    @staticmethod
    def calculate_rmsle(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        RMSLE Formula: sqrt( (1/16) * sum( (ln(y_pred + 1) - ln(y_true + 1))^2 ) )
        """
        y_true_clipped = np.clip(y_true, 0.0, None)
        y_pred_clipped = np.clip(y_pred, 0.0, None)
        log_diff = np.log1p(y_pred_clipped) - np.log1p(y_true_clipped)
        return float(np.sqrt(np.mean(log_diff ** 2)))

    @classmethod
    def evaluate_candidates(
        cls,
        actual_16d: np.ndarray,
        candidate_forecasts: Dict[str, np.ndarray]
    ) -> Dict[str, float]:
        """
        Calculates RMSLE for all candidate models across a 16-day validation window.
        Returns dictionary mapping model_name -> RMSLE score.
        """
        rmsle_results = {}
        for name, forecast in candidate_forecasts.items():
            score = cls.calculate_rmsle(actual_16d, forecast)
            rmsle_results[name] = score
        return rmsle_results
