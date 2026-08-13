"""
Seasonal Baseline & Croston Intermittent Demand Models for DemandPilot Layer 4.
Target: Intermittent / sparse demand categories (Zero Ratio > 0.50).
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd


class CrostonBaseline:
    """
    Croston's Method for Intermittent Demand & Seasonal Moving Average Baseline.
    """

    @staticmethod
    def croston_forecast(sales_series: pd.Series, horizon: int = 16, alpha: float = 0.1) -> np.ndarray:
        """
        Decomposes intermittent series into:
          - Non-zero demand size (a_k)
          - Inter-arrival interval between non-zero orders (p_k)
        Forecast y_hat = a_k / p_k
        """
        sales = sales_series.values
        nonzero_indices = np.where(sales > 1e-6)[0]

        if len(nonzero_indices) == 0:
            return np.zeros(horizon)

        if len(nonzero_indices) == 1:
            val = sales[nonzero_indices[0]] / len(sales)
            return np.full(horizon, val)

        # Non-zero demand sizes
        z = sales[nonzero_indices]
        # Inter-arrival times
        p = np.diff(np.insert(nonzero_indices, 0, -1))

        # Exponential smoothing initialization
        a_hat = float(z[0])
        p_hat = float(p[0])

        for i in range(1, len(z)):
            a_hat = alpha * z[i] + (1 - alpha) * a_hat
            p_hat = alpha * p[i] + (1 - alpha) * p_hat

        demand_rate = max(0.0, float(a_hat)) / max(float(p_hat), 1e-3)
        return np.full(horizon, float(max(0.0, demand_rate)))

    @staticmethod
    def seasonal_naive_forecast(sales_series: pd.Series, horizon: int = 16) -> np.ndarray:
        """
        Seasonal Naive / Moving Average Baseline:
        Computes 7-day moving average adjusted by day-of-week factor.
        """
        sales = sales_series.values
        if len(sales) < 7:
            val = float(sales.mean()) if len(sales) > 0 else 0.0
            return np.full(horizon, val)

        recent_7d = sales[-7:]
        avg_7d = float(recent_7d.mean())

        # Extend 7-day pattern over 16-day horizon
        forecasts = np.array([recent_7d[i % 7] for i in range(horizon)])
        return np.clip(forecasts, 0.0, None)
