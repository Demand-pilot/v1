"""
Unit and Contract Verification Tests for Layer 3 Feature Engineering & Selection Pipeline.
Verifies DemandProfiler and the CORE/OPTIONAL feature builders.
"""

import numpy as np
import pandas as pd
import pytest

from src.features.demand_profiler import DemandProfiler
from src.features.transformer import CoreFeatureBuilder, OptionalFeatureBuilder


def test_demand_profiler_smooth_staple():
    """Verify smooth staple (low CV, low zero ratio) is assigned to PyTorch LSTM."""
    # Steady sales around 100
    sales = pd.Series([100.0, 102.0, 98.0, 101.0, 99.0] * 100)
    profile = DemandProfiler.profile_series(store_nbr=1, family="GROCERY I", sales_series=sales)

    assert profile["sub_domain"] == "SMOOTH_HIGH_VOLUME_STAPLE"
    assert profile["target_engine"] == "PYTORCH_LSTM"
    assert profile["cv"] < 0.6
    assert profile["zero_ratio"] < 0.05


def test_demand_profiler_permanent_zero():
    """Verify permanent zero series (1000+ zero sales days) is routed to Hardcoded Zero Mask."""
    sales = pd.Series([0.0] * 1600)
    profile = DemandProfiler.profile_series(store_nbr=14, family="BOOKS", sales_series=sales)

    assert profile["sub_domain"] == "PERMANENT_ZERO"
    assert profile["target_engine"] == "ZERO_MASK"
    assert profile["is_permanent_zero"] is True
    assert profile["zero_ratio"] == 1.0


def test_demand_profiler_promo_surge():
    """Verify promo surge item (high promo elasticity) is assigned to LightGBM."""
    sales = pd.Series([10.0, 200.0, 15.0, 250.0] * 50)
    promos = pd.Series([0, 1, 0, 1] * 50)
    profile = DemandProfiler.profile_series(
        store_nbr=14, family="SCHOOL AND OFFICE SUPPLIES", sales_series=sales, promo_series=promos
    )

    assert profile["sub_domain"] == "PROMO_ELASTIC_SURGE"
    assert profile["target_engine"] == "LIGHTGBM_GBDT"
    assert profile["promo_elasticity"] > 0.5


def test_core_calendar_features_are_dataset_agnostic():
    """CORE calendar features depend only on the date."""
    dates = pd.to_datetime(["2017-08-15", "2017-08-31", "2017-09-01"])
    cal = CoreFeatureBuilder.calendar(dates)

    assert list(cal.columns) == CoreFeatureBuilder.CALENDAR_FEATURES
    assert cal["day"].tolist() == [15, 31, 1]
    assert cal["month"].tolist() == [8, 8, 9]
    assert cal["is_month_end"].tolist() == [0, 1, 0]
    assert cal["is_month_start"].tolist() == [0, 0, 1]
    assert cal.isna().sum().sum() == 0


def test_configured_calendar_flag_replaces_hardcoded_payday():
    """
    Payday flags come from the dataset config, not from a literal in the feature code.

    `days_of_month` was previously the hardcoded list [15, 30, 31] inside
    FeatureTransformer.add_payday_features.
    """
    from src.ingest.adapter import ExogenousSpec

    spec = ExogenousSpec(kind="calendar_flag", name="is_payday", days_of_month=[15, 30, 31])
    dates = pd.to_datetime(["2017-08-15", "2017-08-16", "2017-08-30", "2017-08-20"])
    flags = OptionalFeatureBuilder.calendar_flag(dates, spec)

    assert flags.name == "is_payday"
    assert flags.tolist() == [1, 0, 1, 0]

    # A different dataset declares different paydays, with no code change.
    other = ExogenousSpec(kind="calendar_flag", name="is_payday", days_of_month=[1])
    assert OptionalFeatureBuilder.calendar_flag(dates, other).tolist() == [0, 0, 0, 0]
