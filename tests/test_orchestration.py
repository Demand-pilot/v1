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
    """Verify GET /api/v1/forecast/grid matches exact Layer 1 contract schema."""
    response = client.get("/api/v1/forecast/grid?store_id=14&family=SCHOOL%20AND%20OFFICE%20SUPPLIES")
    assert response.status_code == 200
    data = response.json()

    # Validate against Pydantic schema
    grid_obj = ForecastGridResponse(**data)
    assert grid_obj.status == "success"
    assert grid_obj.horizon_days == 16
    assert grid_obj.start_date == "2017-08-16"
    assert grid_obj.end_date == "2017-08-31"

    item = grid_obj.data[0]
    assert item.store_nbr == 14
    assert item.family == "SCHOOL AND OFFICE SUPPLIES"
    assert item.selected_engine == "LightGBM_GBDT"
    assert len(item.daily_forecasts) == 16
    assert item.reorder_point > 0
    assert item.safety_stock > 0


def test_agent_chat_contract():
    """Verify POST /api/v1/agent/chat natural language Q&A flow."""
    payload = {
        "user_id": "mgr_store_14",
        "user_role": "STORE_MANAGER",
        "query": "Why is School Supplies surging by +145% at Store 14 in late August?"
    }
    response = client.post("/api/v1/agent/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    chat_obj = AgentChatResponse(**data)
    assert chat_obj.status == "success"
    assert chat_obj.grounded_verified is True
    assert "+145%" in chat_obj.explanation or "145%" in chat_obj.explanation
    assert len(chat_obj.source_tools_used) > 0


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
    """Verify GET /api/v1/analytics/macro executive dashboard endpoint."""
    response = client.get("/api/v1/analytics/macro")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["national_demand_volume"] > 0
    assert len(data["stores"]) > 0


def test_inventory_rop_calculation():
    """Verify deterministic Reorder Point & Safety Stock calculation formula."""
    res = calculate_inventory_rop(forecast_avg_daily=100.0, lead_time_days=7.0, service_factor_z=1.65, std_dev_daily=30.0)
    assert res["safety_stock"] > 0
    assert res["reorder_point"] > (100.0 * 7.0)


def test_verification_gate_reanchoring():
    """Verify Verification Gate corrects/anchors unverified numbers."""
    raw_llm = "School supplies are surging by 500% at store 14."
    db_facts = {"surge_percentage": 145.0, "selected_engine": "LightGBM_GBDT", "backtest_rmsle": 0.3812}
    knowledge = [{"similarity_score": 0.90}]

    is_verified, explanation, _ = VerificationGate.verify_response(raw_llm, db_facts, knowledge)
    assert is_verified is True
    assert "+145%" in explanation  # Corrected to ground truth database surge percentage


def test_store_financial_returns_54_stores():
    """Verify all 54 Ecuador stores have populated financial return records."""
    from src.orchestration.db.database import DatabaseRepository
    db = DatabaseRepository()
    stores = db.get_store_financial_returns()
    assert len(stores) == 54
    for s in stores:
        assert s["gross_revenue_usd"] > 0
        assert s["return_profit_usd"] > 0
        assert 0.15 <= s["net_margin_pct"] <= 0.40
        assert s["region"] in ["Sierra", "Coast", "Oriente"]


def test_macro_analytics_financial_payload():
    """Verify Executive Leadership macro analytics aggregates 54-store financial return profits."""
    response = client.get("/api/v1/analytics/macro")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["stores_count"] == 54
    assert data["gross_revenue_usd"] > 1000000.0
    assert data["return_profit_usd"] > 500000.0
    assert "sierra" in data["regional_summary"]
    assert "coast" in data["regional_summary"]
    assert data["regional_summary"]["sierra"]["count"] > 0


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
    """Verify Reciprocal Rank Fusion formula and document scoring."""
    from src.orchestration.db.database import DatabaseRepository
    db = DatabaseRepository()
    
    results = db.hybrid_search_knowledge(query_text="school supplies spike August", store_nbr=14, family="SCHOOL AND OFFICE SUPPLIES")
    assert len(results) > 0
    top_doc = results[0]
    assert "rrf_score" in top_doc
    assert top_doc["rrf_score"] > 0
    assert "SCHOOL" in top_doc["title"].upper() or "SIERRA" in top_doc["title"].upper()


def test_store_operations_snapshot_zero_numpy_sin():
    """Verify store operations snapshot uses real persisted facts and returns LIVE data status."""
    from src.orchestration.db.database import DatabaseRepository
    db = DatabaseRepository()
    
    snapshot = db.get_store_operations_snapshot(store_nbr=14)
    assert snapshot["store_id"] == 14
    assert snapshot["data_status"] == "LIVE"
    assert snapshot["as_of"] == "2017-08-15T08:00:00Z"
    assert len(snapshot["categories"]) > 0
    assert len(snapshot["priority_actions"]) > 0
    
    school_cat = next(c for c in snapshot["categories"] if "SCHOOL" in c["family"])
    assert school_cat["days_of_cover"] > 0
    assert len(school_cat["actual_history_28d"]) == 28
    assert len(school_cat["actual_history_56d"]) == 56
    assert len(school_cat["forecast_16d"]) == 16
    assert school_cat["audit_details"]["selected_engine"] == "LightGBM_GBDT"


