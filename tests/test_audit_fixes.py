"""
DemandPilot Multi-Domain Audit Fixes Verification Tests.
Verifies all 7 domains: Auth security, VerificationGate contextual parsing,
Pagination bounds, Croston safety, Mediator date handling, and RRF SQL search.
"""

import os
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from fastapi import HTTPException

from src.orchestration.main import app
from src.orchestration.auth import decode_supabase_jwt
from src.orchestration.agent.verification_gate import VerificationGate
from src.orchestration.agent.tools import search_store_knowledge
from src.models.baseline_engine import CrostonBaseline
from src.mediator.mediator import MediatorEngine

client = TestClient(app)


def test_auth_production_enforcement(monkeypatch):
    """Domain 1.1: Verify production rejects default/missing JWT secret and bypasses."""
    # 1. Simulate production environment with default secret
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr("src.orchestration.auth.IS_PRODUCTION", True)
    monkeypatch.setattr("src.orchestration.auth.SUPABASE_JWT_SECRET", "demandpilot_dev_jwt_secret_change_in_prod")

    with pytest.raises(HTTPException) as exc_info:
        decode_supabase_jwt("demo-token-store_manager")
    assert exc_info.value.status_code == 500
    assert "Production JWT secret required" in exc_info.value.detail

    # 2. In dev mode, demo token should succeed
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setattr("src.orchestration.auth.IS_PRODUCTION", False)
    payload = decode_supabase_jwt("demo-token-store_manager")
    assert payload["role"] == "STORE_MANAGER"
    assert payload["sub"] == "user_store_manager"


def test_purchase_orders_pagination_bounds():
    """Domain 1.2: Verify GET /api/v1/purchase-orders pagination limit and offset."""
    response = client.get("/api/v1/purchase-orders?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "purchase_orders" in data
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert len(data["purchase_orders"]) <= 10


def test_verification_gate_contextual_percentage_collision_prevention():
    """Calendar tokens must not be read as quantitative claims about the data."""
    retrieved_facts = {
        "store_nbr": 1,
        "family": "BEVERAGES",
        "surge_percentage": 8.0,
        "selected_engine": "PyTorch_LSTM",
        "backtest_rmsle": 0.2080,
        "promo_density_train": 0.15,
        "promo_density_test": 0.30
    }
    knowledge = [{"similarity_score": 0.88, "text": "Payday note"}]

    # Case A: calendar references only, no quantitative claim. Passes through UNCHANGED.
    # The gate no longer rewrites answers to inject "+8%" that the model never said.
    text_without_pct = "On Aug 8 with an 8-day window, sales are steady."
    is_verified, output_text, _ = VerificationGate.verify_response(
        text_without_pct, retrieved_facts, knowledge
    )
    assert is_verified is True
    assert output_text == text_without_pct

    # Case B: a percentage that matches a retrieved fact passes through unchanged.
    text_with_pct = "Beverages at Store 1 experience a +8.0% surge during payday promotions."
    is_verified, output_text, _ = VerificationGate.verify_response(
        text_with_pct, retrieved_facts, knowledge
    )
    assert is_verified is True
    assert output_text == text_with_pct


def test_verification_gate_withholds_unsupported_number():
    """An unsupported figure fails the gate and the answer is withheld, not rewritten."""
    retrieved_facts = {"surge_percentage": 8.0, "backtest_rmsle": 0.2080}
    knowledge = [{"similarity_score": 0.88}]

    is_verified, output_text, _ = VerificationGate.verify_response(
        "Beverages are surging by 500% at store 1.", retrieved_facts, knowledge
    )
    assert is_verified is False
    # Withheld. Critically, NOT replaced by a differently-worded confident claim.
    assert output_text is None


def test_verification_gate_reports_no_data():
    """With no retrieved facts the gate fails; it cannot verify against nothing."""
    is_verified, output_text, sources = VerificationGate.verify_response(
        "Demand will rise 12%.", {}, []
    )
    assert is_verified is False
    assert output_text is None
    assert sources == []


def test_verification_gate_low_confidence_is_reachable():
    """
    Weak retrieval fails the gate.

    This branch was unreachable while search_store_knowledge() injected a placeholder
    document scored 0.80, above the 0.75 threshold.
    """
    is_verified, output_text, _ = VerificationGate.verify_response(
        "Stock levels look stable.",
        {"selected_engine": "LightGBM_GBDT"},
        [{"similarity_score": 0.10}],
    )
    assert is_verified is False
    assert output_text is None


def test_croston_zero_division_and_non_negative_safety():
    """Domain 7.2: Verify Croston forecast handles zero-sales series and edge cases safely."""
    # All zeros
    zeros_series = pd.Series([0.0] * 30)
    fc_zeros = CrostonBaseline.croston_forecast(zeros_series, horizon=16)
    assert len(fc_zeros) == 16
    assert np.all(fc_zeros == 0.0)

    # Intermittent with high gap
    sparse_series = pd.Series([0.0, 0.0, 10.0, 0.0, 0.0, 0.0, 15.0])
    fc_sparse = CrostonBaseline.croston_forecast(sparse_series, horizon=16)
    assert len(fc_sparse) == 16
    assert np.all(fc_sparse >= 0.0)
    assert not np.isnan(fc_sparse).any()


def test_mediator_date_normalization_post_processing():
    """Domain 7.3: Verify short date strings and ISO date strings are masked correctly."""
    fc = np.array([100.0, 100.0, 100.0])
    # Dec 25 must be zeroed out
    dates = ["2017-12-24", "12-25", "2017-12-26"]
    processed = MediatorEngine.apply_post_processing(fc, dates, store_nbr=14)
    assert processed[0] == 100.0
    assert processed[1] == 0.0  # Dec 25 Christmas closure
    assert processed[2] == 100.0


def test_search_store_knowledge_sql_integration():
    """Knowledge search returns structured documents carrying a real match score."""
    results = search_store_knowledge(
        store_nbr=14, query_text="academic campaign restock logistics"
    )
    assert len(results) > 0
    first = results[0]
    assert "doc_id" in first
    assert "content" in first
    assert "similarity_score" in first
    # A genuine match ratio in [0, 1], not a floor of 0.70 applied to everything.
    assert 0.0 < first["similarity_score"] <= 1.0
    # Seeded fixtures must be identifiable as such, so the agent can decline to cite them.
    assert first["source"] == "SEED_EXAMPLE"


def test_search_store_knowledge_returns_empty_on_no_match():
    """No matching document => [], never a synthesised placeholder above the gate."""
    results = search_store_knowledge(
        store_nbr=14, query_text="zzzqqq nonexistent terminology xyzzy"
    )
    assert results == []
