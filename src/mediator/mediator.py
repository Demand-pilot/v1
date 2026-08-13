"""
Multi-Model Mediator & Decision Engine for DemandPilot Layer 5.
Dynamically routes series predictions, applies soft-max ensembling,
and enforces post-processing zero masks & calendar overrides.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd


class MediatorEngine:
    """
    Mediator Engine evaluating series profile and backtest errors
    to select single winning model, calculate soft-max ensemble weights,
    and enforce post-processing calendar zero masks.
    """

    @classmethod
    def route_and_ensemble(
        cls,
        series_profile: Dict[str, Any],
        model_backtest_errors: Dict[str, float],
        candidate_forecasts: Dict[str, np.ndarray]
    ) -> Dict[str, Any]:
        """
        Executes Rule 1 (Zero Mask), Rule 2 (Single Selector), and Rule 3 (Soft-Max Ensemble).
        """
        # Rule 1: Permanent Zero Series Bypass (53 Series)
        if series_profile.get("is_permanent_zero", False):
            return {
                "strategy": "HARDCODED_ZERO_MASK",
                "selected_model": "HARDCODED_ZERO",
                "weights": {"HARDCODED_ZERO": 1.0},
                "raw_forecast": np.zeros(16),
                "rmsle": 0.0
            }

        # Sort candidate models by backtest RMSLE (ascending, lower is better)
        sorted_models = sorted(model_backtest_errors.items(), key=lambda x: x[1])
        best_model, best_rmsle = sorted_models[0]
        second_model, second_rmsle = sorted_models[1] if len(sorted_models) > 1 else (best_model, best_rmsle)

        promo_elasticity = series_profile.get("promo_elasticity", 0.0)

        # Rule 2: Single Model Selector (Clear Dominance or High Promo Elasticity)
        if (second_rmsle - best_rmsle) > 0.05 or promo_elasticity > 0.60:
            return {
                "strategy": "SINGLE_SELECTOR",
                "selected_model": best_model,
                "weights": {best_model: 1.0},
                "raw_forecast": candidate_forecasts[best_model],
                "rmsle": best_rmsle
            }

        # Rule 3: Inverse RMSLE Soft-Max Weighted Ensemble
        rmsle_vals = np.array([err for _, err in sorted_models])
        inv_rmsle = 1.0 / (rmsle_vals + 1e-4)
        exp_inv = np.exp(inv_rmsle - np.max(inv_rmsle))
        ensemble_weights = exp_inv / np.sum(exp_inv)

        blended_forecast = np.zeros(16)
        weight_dict = {}
        for i, (name, _) in enumerate(sorted_models):
            w = float(ensemble_weights[i])
            blended_forecast += w * candidate_forecasts[name]
            weight_dict[name] = round(w, 4)

        return {
            "strategy": "WEIGHTED_ENSEMBLE",
            "selected_model": f"ENSEMBLE_{best_model}_{second_model}",
            "weights": weight_dict,
            "raw_forecast": blended_forecast,
            "rmsle": best_rmsle
        }

    @classmethod
    def apply_post_processing(
        cls,
        forecast_16d: np.ndarray,
        dates_16d: List[str],
        store_nbr: int
    ) -> np.ndarray:
        """
        Post-Processing Verification Layer:
        1. Christmas Day Mask (Dec 25 = 0.0)
        2. New Year Day Mask (Jan 1 = 0.0 except Store 25)
        3. Non-negative truncation max(0.0, y_hat)
        """
        final_forecast = forecast_16d.copy()

        for i, date_str in enumerate(dates_16d):
            clean_str = str(date_str).strip()
            if len(clean_str) <= 6 and not clean_str.startswith("201"):
                dt = pd.to_datetime(f"2017 {clean_str}")
            else:
                dt = pd.to_datetime(clean_str)
            month_day = dt.strftime('%m-%d')

            # 1. Christmas Day closure
            if month_day == '12-25':
                final_forecast[i] = 0.0
            # 2. New Year Day closure (except Store 25)
            elif month_day == '01-01' and store_nbr != 25:
                final_forecast[i] = 0.0

        # 3. Non-negative sales truncation
        return np.clip(final_forecast, 0.0, None)
