"""
Unit and Contract Verification Tests for Layer 3 Feature Engineering & Selection Pipeline.
Verifies DemandProfiler, FeatureTransformer, and FeatureAblationHarness.
"""

import numpy as np
import pandas as pd
import pytest

from src.features.demand_profiler import DemandProfiler
from src.features.transformer import FeatureTransformer
from src.features.ablation_experiment import FeatureAblationHarness, FEATURE_SETS


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
    assert profile["target_engine"] == "HARDCODED_ZERO_MASK"
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


def test_transformer_oil_differencing():
    """Verify oil price first-differencing (delta_oil) removes trend while preserving shocks."""
    dates = pd.date_range('2017-01-01', periods=5, freq='D')
    oil_raw = pd.DataFrame({
        'date': dates,
        'dwtruck_price': [50.0, 52.0, 51.0, np.nan, 55.0]
    })

    oil_transformed = FeatureTransformer.transform_oil_data(oil_raw)
    assert 'delta_oil' in oil_transformed.columns
    assert 'delta_oil_3d_rolling' in oil_transformed.columns
    assert oil_transformed['delta_oil'].iloc[1] == 2.0  # 52.0 - 50.0


def test_transformer_payday_features():
    """Verify is_day_after_payday and payday_weekday_interaction flags."""
    df = pd.DataFrame({
        'date': pd.to_datetime(['2017-08-15', '2017-08-16', '2017-09-01'])
    })
    transformed = FeatureTransformer.add_payday_features(df)

    assert transformed['is_payday'].iloc[0] == 1  # 15th is payday
    assert transformed['is_day_after_payday'].iloc[1] == 1  # 16th is day after
    assert transformed['is_day_after_payday'].iloc[2] == 1  # 1st is day after


def test_transformer_earthquake_decay():
    """Verify 30-day post-earthquake exponential decay feature."""
    df = pd.DataFrame({
        'date': pd.to_datetime(['2016-04-16', '2016-04-26', '2016-05-20'])
    })
    transformed = FeatureTransformer.add_earthquake_decay_feature(df)

    assert transformed['earthquake_decay'].iloc[0] == 1.0  # Day 0 = exp(0) = 1.0
    assert 0.0 < transformed['earthquake_decay'].iloc[1] < 1.0  # Day 10 decay
    assert transformed['earthquake_decay'].iloc[2] == 0.0  # > 30 days = 0.0


def test_ablation_harness_best_combination_selection():
    """Verify feature ablation selects Set B/C for LightGBM and Set A for LSTM."""
    val_df = pd.DataFrame({
        'sales': np.random.uniform(50, 150, 100)
    })

    # LightGBM on Promo Surge should pick Set B or C (Promo features reduce RMSLE)
    lgbm_winner = FeatureAblationHarness.select_best_feature_combination(
        sub_domain="PROMO_ELASTIC_SURGE",
        target_model="LIGHTGBM_GBDT",
        val_df=val_df
    )
    assert lgbm_winner["feature_set"] in ["SET_B_PROMO_PAYDAY", "SET_C_FULL_CONTEXT_SHOCKS"]
    assert lgbm_winner["backtest_rmsle"] < 0.40

    # LSTM on Smooth Staples should pick Set A (Clean temporal sequence without noise)
    lstm_winner = FeatureAblationHarness.select_best_feature_combination(
        sub_domain="SMOOTH_HIGH_VOLUME_STAPLE",
        target_model="PYTORCH_LSTM",
        val_df=val_df
    )
    assert lstm_winner["feature_set"] == "SET_A_TEMPORAL_BASE"
    assert lstm_winner["backtest_rmsle"] < 0.22
