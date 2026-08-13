"""
Automated Demand Profiler for DemandPilot Layer 3.
Profiles 1,782 time series by CV, Zero Ratio, and Promo Elasticity,
segmenting series into 4 candidate sub-domains.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd


class DemandProfiler:
    """
    Evaluates series statistics (CV, Zero Ratio, Promo Elasticity)
    and routes them to target model sub-domains.
    """

    @staticmethod
    def compute_cv(sales_series: pd.Series) -> float:
        """Coefficient of Variation (CV = std / mean)."""
        mean_val = sales_series.mean()
        if mean_val <= 1e-6:
            return 0.0
        return float(sales_series.std() / mean_val)

    @staticmethod
    def compute_zero_ratio(sales_series: pd.Series) -> float:
        """Ratio of 0.0 sales days to total days."""
        if len(sales_series) == 0:
            return 0.0
        zero_count = (sales_series <= 1e-6).sum()
        return float(zero_count / len(sales_series))

    @staticmethod
    def compute_promo_elasticity(sales_series: pd.Series, promo_series: pd.Series) -> float:
        """Pearson correlation between daily sales units and active promotion count."""
        if len(sales_series) == 0 or len(promo_series) == 0:
            return 0.0
        if sales_series.std() == 0.0 or promo_series.std() == 0.0:
            return 0.0
        corr = sales_series.corr(promo_series)
        return float(corr) if not np.isnan(corr) else 0.0

    @classmethod
    def profile_series(
        cls,
        store_nbr: int,
        family: str,
        sales_series: pd.Series,
        promo_series: Optional_Promo = None
    ) -> Dict[str, Any]:
        """
        Profiles one series and returns sub-domain segmentation & target candidate engine.
        """
        cv = cls.compute_cv(sales_series)
        zero_ratio = cls.compute_zero_ratio(sales_series)
        promo_elasticity = (
            cls.compute_promo_elasticity(sales_series, promo_series)
            if promo_series is not None
            else 0.0
        )

        # Rule 1: Permanent Zero Series (53 series)
        if zero_ratio >= 0.99 and len(sales_series) > 500:
            return {
                "store_nbr": store_nbr,
                "family": family,
                "sub_domain": "PERMANENT_ZERO",
                "target_engine": "HARDCODED_ZERO_MASK",
                "cv": cv,
                "zero_ratio": zero_ratio,
                "promo_elasticity": promo_elasticity,
                "is_permanent_zero": True
            }

        # Rule 2: Intermittent / Sparse Series
        if zero_ratio > 0.50:
            return {
                "store_nbr": store_nbr,
                "family": family,
                "sub_domain": "INTERMITTENT_SPARSE",
                "target_engine": "CROSTON_BASELINE",
                "cv": cv,
                "zero_ratio": zero_ratio,
                "promo_elasticity": promo_elasticity,
                "is_permanent_zero": False
            }

        # Rule 3: Promo-Elastic Surge Items (e.g. School Supplies)
        if promo_elasticity > 0.50 or ("SCHOOL" in family.upper() and cv > 1.0):
            return {
                "store_nbr": store_nbr,
                "family": family,
                "sub_domain": "PROMO_ELASTIC_SURGE",
                "target_engine": "LIGHTGBM_GBDT",
                "cv": cv,
                "zero_ratio": zero_ratio,
                "promo_elasticity": promo_elasticity,
                "is_permanent_zero": False
            }

        # Rule 4: Smooth High-Volume Staples (e.g. Grocery I, Beverages)
        return {
            "store_nbr": store_nbr,
            "family": family,
            "sub_domain": "SMOOTH_HIGH_VOLUME_STAPLE",
            "target_engine": "PYTORCH_LSTM",
            "cv": cv,
            "zero_ratio": zero_ratio,
            "promo_elasticity": promo_elasticity,
            "is_permanent_zero": False
        }


# Type alias for Optional promo series
from typing import Optional as Optional_Promo
