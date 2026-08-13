"""
Unit and Contract Verification Tests for Layer 4 (Parallel Models) & Layer 5 (Mediator Engine).
Verifies PyTorch LSTM, LightGBM GBDT, Croston Baseline, Backtesting, and Mediator Engine.
"""

import numpy as np
import pandas as pd
import pytest
import torch

from src.models.lstm_engine import DemandLSTM, RMSLELoss, DemandLSTMTrainer
from src.models.gbdt_engine import DemandGBDT
from src.models.baseline_engine import CrostonBaseline
from src.mediator.backtest import BacktestEngine
from src.mediator.mediator import MediatorEngine


def test_lstm_forward_pass_and_rmsle_loss():
    """Verify PyTorch LSTM tensor input (B, 60, F) -> output (B, 16) and RMSLE loss."""
    model = DemandLSTM(input_dim=5, hidden_dim=32, num_layers=1, forecast_horizon=16)
    x = torch.randn(8, 60, 5)  # Batch of 8, 60 time steps, 5 features
    out = model(x)

    assert out.shape == (8, 16)

    # Test RMSLE loss calculation
    criterion = RMSLELoss()
    y_true = torch.ones(8, 16) * 100.0
    loss = criterion(out, y_true)
    assert loss.item() >= 0.0


def test_lstm_trainer_fit_and_predict():
    """Verify PyTorch DemandLSTMTrainer fitting and 16-day prediction output."""
    X_seq = np.random.uniform(10, 50, (100, 5))
    y_seq = np.random.uniform(10, 50, 100)

    trainer = DemandLSTMTrainer(input_dim=5, hidden_dim=16)
    loss = trainer.fit(X_seq, y_seq, epochs=1, batch_size=16)
    assert loss >= 0.0

    # Test 16-day forecast prediction
    x_test = np.random.uniform(10, 50, (60, 5))
    pred_16d = trainer.predict_16d(x_test)
    assert len(pred_16d) == 16
    assert np.all(pred_16d >= 0.0)


def test_gbdt_engine_fit_and_predict():
    """Verify LightGBM/GBDT model training and 16-day forecast generation."""
    X_train = pd.DataFrame({
        'dayofweek': np.random.randint(0, 7, 100),
        'onpromotion': np.random.randint(0, 2, 100),
        'lag_1': np.random.uniform(10, 100, 100)
    })
    y_train = pd.Series(np.random.uniform(10, 100, 100))

    gbdt = DemandGBDT(n_estimators=10)
    gbdt.fit(X_train, y_train)

    X_test_16d = X_train.iloc[:16].copy()
    preds_16d = gbdt.predict_16d(X_test_16d)

    assert len(preds_16d) == 16
    assert np.all(preds_16d >= 0.0)


def test_croston_baseline_forecast():
    """Verify Croston's method for intermittent demand."""
    sparse_sales = pd.Series([0, 0, 50, 0, 0, 0, 40, 0, 0, 60] * 5)
    croston_preds = CrostonBaseline.croston_forecast(sparse_sales, horizon=16)

    assert len(croston_preds) == 16
    assert np.all(croston_preds >= 0.0)

    # Test seasonal naive
    naive_preds = CrostonBaseline.seasonal_naive_forecast(sparse_sales, horizon=16)
    assert len(naive_preds) == 16


def test_backtest_engine_rmsle():
    """Verify BacktestEngine RMSLE calculation."""
    y_true = np.array([100.0] * 16)
    y_pred_good = np.array([105.0] * 16)
    y_pred_bad = np.array([200.0] * 16)

    rmsle_good = BacktestEngine.calculate_rmsle(y_true, y_pred_good)
    rmsle_bad = BacktestEngine.calculate_rmsle(y_true, y_pred_bad)

    assert rmsle_good < rmsle_bad


def test_mediator_rule_1_zero_bypass():
    """Verify Mediator Rule 1 forces hardcoded zero forecast for 53 permanent zero series."""
    profile = {"is_permanent_zero": True}
    errors = {"PyTorch_LSTM": 0.50, "LightGBM_GBDT": 0.60}
    candidates = {
        "PyTorch_LSTM": np.full(16, 10.0),
        "LightGBM_GBDT": np.full(16, 12.0)
    }

    res = MediatorEngine.route_and_ensemble(profile, errors, candidates)
    assert res["strategy"] == "ZERO_MASK"
    assert np.all(res["raw_forecast"] == 0.0)


def test_mediator_rule_2_single_selector():
    """Verify Mediator Rule 2 picks single winner when clear RMSLE dominance exists."""
    profile = {"is_permanent_zero": False, "promo_elasticity": 0.70}  # High promo elasticity
    errors = {"LightGBM_GBDT": 0.38, "PyTorch_LSTM": 0.55}
    candidates = {
        "LightGBM_GBDT": np.full(16, 150.0),
        "PyTorch_LSTM": np.full(16, 100.0)
    }

    res = MediatorEngine.route_and_ensemble(profile, errors, candidates)
    assert res["strategy"] == "SINGLE_SELECTOR"
    assert res["selected_model"] == "LightGBM_GBDT"
    assert np.array_equal(res["raw_forecast"], candidates["LightGBM_GBDT"])


def test_mediator_rule_3_soft_max_ensemble():
    """Verify Mediator Rule 3 blends predictions via inverse-RMSLE soft-max weights."""
    profile = {"is_permanent_zero": False, "promo_elasticity": 0.20}
    errors = {"PyTorch_LSTM": 0.21, "LightGBM_GBDT": 0.22}  # Close RMSLE scores (< 0.05 diff)
    candidates = {
        "PyTorch_LSTM": np.full(16, 100.0),
        "LightGBM_GBDT": np.full(16, 110.0)
    }

    res = MediatorEngine.route_and_ensemble(profile, errors, candidates)
    assert res["strategy"] == "WEIGHTED_ENSEMBLE"
    assert "PyTorch_LSTM" in res["weights"]
    assert "LightGBM_GBDT" in res["weights"]
    # Blended forecast should lie strictly between 100 and 110
    assert 100.0 < res["raw_forecast"][0] < 110.0


def test_mediator_post_processing_calendar_masks():
    """Verify Christmas Day (Dec 25) zero mask and New Year (Jan 1) Store 25 exemption."""
    raw_forecast = np.full(16, 100.0)
    dates_xmas = ["2017-12-24", "2017-12-25", "2017-12-26"] + ["2017-12-27"] * 13

    # Dec 25 must be zeroed for Store 14
    proc_xmas = MediatorEngine.apply_post_processing(raw_forecast, dates_xmas, store_nbr=14)
    assert proc_xmas[1] == 0.0  # Dec 25 zeroed out

    # Jan 1 must be zeroed out for Store 14, but KEPT for Store 25
    dates_ny = ["2018-01-01"] * 16
    proc_ny_14 = MediatorEngine.apply_post_processing(raw_forecast, dates_ny, store_nbr=14)
    assert proc_ny_14[0] == 0.0

    proc_ny_25 = MediatorEngine.apply_post_processing(raw_forecast, dates_ny, store_nbr=25)
    assert proc_ny_25[0] == 100.0  # Store 25 is open on Jan 1
