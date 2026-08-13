"""
Contract & Unit Verification Tests for Layer 2 Orchestration & AI Agent Layer.
Verifies API Endpoints, Pydantic Schemas, Intent Router, and Grounded Verification Gate.
"""

import pytest
from fastapi.testclient import TestClient

from src.orchestration.main import app
from src.orchestration.schemas import ForecastGridResponse, AgentChatResponse
from src.orchestration.agent.tools import (
    get_forecast_logs,
    search_store_knowledge,
    get_promo_elasticity,
    calculate_inventory_rop
)
from src.orchestration.agent.verification_gate import VerificationGate

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_forecast_grid_contract():
    """With no trained model, the grid reports an explicit empty state."""
    response = client.get("/api/v1/forecast/grid?store_id=14&family=SCHOOL%20AND%20OFFICE%20SUPPLIES")
    assert response.status_code == 200
    grid_obj = ForecastGridResponse(**response.json())

    # forecast_facts is empty until the Phase 3 inference path runs. The endpoint used to
    # answer this with engine "LightGBM_GBDT", RMSLE 0.3812 and [100.0] * 16.
    assert grid_obj.status == "no_forecast_available"
    assert grid_obj.data == []
    assert grid_obj.horizon_days == 0
    assert grid_obj.start_date is None
    assert grid_obj.end_date is None


def test_agent_chat_contract():
    """Chat about a series with no forecast reports that it has no data."""
    payload = {
        "user_id": "mgr_store_14",
        "user_role": "STORE_MANAGER",
        "query": "Why is School Supplies surging at Store 14 in late August?"
    }
    response = client.post("/api/v1/agent/chat", json=payload)
    assert response.status_code == 200

    chat_obj = AgentChatResponse(**response.json())
    assert chat_obj.status == "success"
    # No forecast on record => not grounded, and the answer says so rather than
    # asserting a +145% surge sourced from a default parameter.
    assert chat_obj.grounded_verified is False
    assert "don't have a forecast" in chat_obj.explanation
    assert "145" not in chat_obj.explanation


def test_agent_chat_streaming():
    """Verify SSE streaming format for POST /api/v1/agent/chat?stream=true."""
    payload = {
        "user_id": "mgr_store_14",
        "user_role": "STORE_MANAGER",
        "query": "Why is School Supplies surging at Store 14?"
    }
    response = client.post("/api/v1/agent/chat?stream=true", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "data: {" in response.text


def test_macro_analytics_contract():
    """Macro analytics reports zeros and NO_DATA when no financial returns exist."""
    response = client.get("/api/v1/analytics/macro")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    # Previously this branch returned a fabricated national picture: 2,674,850 units,
    # $16,526,470 revenue, $4,703,580 profit, across "54" stores.
    assert data["stores"] == []
    assert data["stores_count"] == 0
    assert data["national_demand_volume"] == 0.0
    assert data["gross_revenue_usd"] == 0.0


def test_inventory_rop_calculation():
    """Verify deterministic Reorder Point & Safety Stock calculation formula."""
    res = calculate_inventory_rop(forecast_avg_daily=100.0, lead_time_days=7.0, service_factor_z=1.65, std_dev_daily=30.0)
    assert res["safety_stock"] > 0
    assert res["reorder_point"] > (100.0 * 7.0)


def test_verification_gate_withholds_instead_of_reanchoring():
    """
    An unsupported number causes the answer to be withheld.

    The gate used to respond to a mismatch by discarding the answer and substituting a
    template asserting a "+145% demand surge" built from its own default parameters,
    turning a detected error into a more confident fabrication.
    """
    raw_llm = "School supplies are surging by 500% at store 14."
    db_facts = {"surge_percentage": 145.0, "selected_engine": "LightGBM_GBDT", "backtest_rmsle": 0.3812}
    knowledge = [{"similarity_score": 0.90}]

    is_verified, explanation, _ = VerificationGate.verify_response(raw_llm, db_facts, knowledge)
    assert is_verified is False
    assert explanation is None


def test_store_financial_returns_empty_without_a_run():
    """Financial returns are empty until a real forecast run writes them."""
    from src.orchestration.db.database import DatabaseRepository
    db = DatabaseRepository()
    assert db.get_store_financial_returns() == []


def test_macro_analytics_reports_no_data_status():
    """The macro payload marks itself NO_DATA rather than inventing headline figures."""
    from src.orchestration.db.database import DatabaseRepository
    db = DatabaseRepository()
    data = db.get_macro_analytics()
    assert data["data_status"] == "NO_DATA"
    assert data["avg_net_margin_pct"] is None
    assert data["return_profit_usd"] == 0.0


def test_auth_jwt_validation_and_rbac():
    """Verify JWT decoding and user derivation."""
    from src.orchestration.auth import decode_supabase_jwt
    payload = decode_supabase_jwt("demo-token-store_manager")
    assert payload["role"] == "STORE_MANAGER"
    assert 14 in payload["authorized_stores"]


def test_store_authorization_403():
    """Verify 403 Forbidden is returned when user attempts to access unauthorized store."""
    # Store Manager with access only to store 14 attempts to access store 99
    headers = {"Authorization": "Bearer demo-token-store_manager"}
    response = client.get("/api/v1/store/operations-snapshot?store_id=99", headers=headers)
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_order_plan_crud_and_persistence():
    """Verify Order Plan draft creation and line saving."""
    from src.orchestration.db.database import DatabaseRepository
    db = DatabaseRepository()
    
    plan = db.get_or_create_order_plan(store_nbr=14, user_id="test_user_01")
    assert plan["store_nbr"] == 14
    assert plan["status"] == "DRAFT"
    
    line = db.save_order_plan_line(
        plan_id=plan["id"],
        family="SCHOOL AND OFFICE SUPPLIES",
        adjusted_qty=1200.0,
        recommended_qty=1120.0,
        reason="Test Quantity Adjustment"
    )
    assert line["status"] == "success"
    assert line["adjusted_qty"] == 1200.0


def test_purchase_order_submission_and_audit():
    """Verify Order Plan submission generates persistent PO and writes audit log."""
    from src.orchestration.db.database import DatabaseRepository
    db = DatabaseRepository()
    
    plan = db.get_or_create_order_plan(store_nbr=14, user_id="test_user_01")
    db.save_order_plan_line(plan["id"], "BEVERAGES", 1500.0, 1500.0, "Payday Order")
    
    po = db.submit_purchase_order(plan_id=plan["id"], user_id="test_user_01")
    assert po["status"] == "success"
    assert po["po_number"].startswith("PO-EC-2017-0816-14-")
    assert po["total_units"] >= 1500.0
    assert po["total_cost_usd"] > 0
    assert po["edi_transmission_status"] == "CONFIRMED_ACK"


def test_hybrid_rrf_retrieval_ranking():
    """RRF ranking over persisted documents returns real scores, or [] when nothing matches."""
    from src.orchestration.db.database import DatabaseRepository
    db = DatabaseRepository()

    results = db.hybrid_search_knowledge(
        query_text="academic campaign restock", store_nbr=14, family="SCHOOL AND OFFICE SUPPLIES"
    )
    assert len(results) > 0
    top_doc = results[0]
    assert top_doc["rrf_score"] > 0
    assert 0.0 < top_doc["similarity_score"] <= 1.0
    assert top_doc["source"] == "SEED_EXAMPLE"

    # Zero lexical overlap must yield nothing at all.
    assert db.hybrid_search_knowledge(query_text="zzzqqq xyzzy nonexistent") == []


def test_store_operations_snapshot_reports_missing_data_honestly():
    """The snapshot reports absent forecasts and inventory instead of inventing them."""
    from src.orchestration.db.database import DatabaseRepository
    db = DatabaseRepository()

    snapshot = db.get_store_operations_snapshot(store_nbr=14)
    assert snapshot["store_id"] == 14
    # Store metadata is real (seeded), so the store resolves...
    assert snapshot["city"] == "Quito"
    # ...but there is no forecast run, so there are no categories and no actions.
    assert snapshot["data_status"] == "NO_FORECAST_AVAILABLE"
    assert snapshot["categories"] == []
    assert snapshot["priority_actions"] == []
    assert snapshot["as_of"] is None
    assert snapshot["forecast_run_id"] is None
    assert snapshot["summary_metrics"]["total_on_hand_units"] is None


def test_store_operations_snapshot_unknown_store_returns_none():
    """An unknown store yields None, not metadata guessed from the store number."""
    from src.orchestration.db.database import DatabaseRepository
    db = DatabaseRepository()
    assert db.get_store_operations_snapshot(store_nbr=9999) is None
