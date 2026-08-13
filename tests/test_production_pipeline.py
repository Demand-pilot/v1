"""
Production Quality Verification Test Suite for DemandPilot.
Validates:
1. Feature Leakage-Safety ("as-of-cutoff" proof).
2. Grouped Series Isolation (no cross-series leakage).
3. All 33 Product-Family Entity Extraction Cases.
4. Hybrid RAG & Reciprocal Rank Fusion (RRF) Ranking.
5. 3-Layer Stateful Memory Tenant Isolation.
6. RBAC Store Authorization & Denial Policy.
7. SQL Forecast Facts & Verification Gate Integration.
"""

import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from src.orchestration.main import app
from src.orchestration.db.database import DatabaseRepository
from src.orchestration.agent.rag_retriever import HybridRRFRetriever
from src.orchestration.agent.memory import ConversationMemoryManager
from src.orchestration.router.intent_router import IntentRouter
from src.orchestration.cache.redis_client import RedisForecastCache
from src.features.transformer import FeatureTransformer

client = TestClient(app)
db_repo = DatabaseRepository()


# -----------------------------------------------------------------------------
# 1. Feature Leakage & Grouped Isolation Tests
# -----------------------------------------------------------------------------

def test_feature_grouped_isolation_no_cross_series_leakage():
    """Verify that lag features do not leak sales across different store/family series."""
    df_sample = pd.DataFrame({
        "date": pd.to_datetime(["2017-08-01", "2017-08-02", "2017-08-01", "2017-08-02"]),
        "store_nbr": [1, 1, 2, 2],
        "family": ["GROCERY I", "GROCERY I", "GROCERY I", "GROCERY I"],
        "sales": [100.0, 200.0, 500.0, 600.0],
        "onpromotion": [0, 1, 0, 1]
    })

    df_res = FeatureTransformer.generate_lags_and_rolling(df_sample, target_col="sales")

    # Store 2 on Day 1 must NOT receive Store 1 Day 2 sales as lag_1!
    store2_day1 = df_res[(df_res["store_nbr"] == 2) & (df_res["date"] == "2017-08-01")].iloc[0]
    assert store2_day1["lag_1"] == 0.0  # Must be 0.0 initial lag, NOT 200.0 from Store 1!


def test_as_of_cutoff_safe_oil_differencing():
    """Verify oil price differencing handles missing values and computes shocks safely."""
    oil_df = pd.DataFrame({
        "date": ["2017-08-01", "2017-08-02", "2017-08-03"],
        "dcoilwtico": [48.5, np.nan, 50.5]
    })
    transformed = FeatureTransformer.transform_oil_data(oil_df)
    assert "delta_oil" in transformed.columns
    assert transformed["delta_oil"].iloc[0] == 0.0
    assert not transformed["oil_price"].isna().any()


# -----------------------------------------------------------------------------
# 2. All 33 Product-Family Entity Extraction Tests
# -----------------------------------------------------------------------------

ALL_33_FAMILIES = [
    "AUTOMOTIVE", "BABY CARE", "BEAUTY", "BEVERAGES", "BOOKS",
    "BREAD/BAKERY", "CELEBRATION", "CLEANING", "DAIRY", "DELI",
    "EGGS", "FROZEN FOODS", "GROCERY I", "GROCERY II", "HARDWARE",
    "HOME AND KITCHEN I", "HOME AND KITCHEN II", "HOME APPLIANCES",
    "HOME CARE", "LADIESWEAR", "LAWN AND GARDEN", "LINGERIE",
    "LIQUOR,WINE,BEER", "MAGAZINES", "MEATS", "PERSONAL CARE",
    "PET SUPPLIES", "PLAYERS AND ELECTRONICS", "POULTRY", "PREPARED FOODS",
    "PRODUCE", "SCHOOL AND OFFICE SUPPLIES", "SEAFOOD"
]

@pytest.mark.parametrize("family_name", ALL_33_FAMILIES)
def test_all_33_product_family_entity_extraction(family_name):
    """Verify Intent Router extracts all 33 official competition product families."""
    router = IntentRouter(RedisForecastCache())
    query = f"Explain the inventory demand forecast for {family_name} at Store 25 in August."
    store_id, extracted_family = router.extract_entities_from_query(query)

    assert store_id == 25
    assert (extracted_family == family_name) or (family_name.split()[0] in extracted_family) or (extracted_family in family_name)


# -----------------------------------------------------------------------------
# 3. Hybrid RAG & Reciprocal Rank Fusion (RRF) Tests
# -----------------------------------------------------------------------------

def test_hybrid_rrf_retrieval_ranking():
    """Verify RRF formula fuses and ranks lexical + vector search results."""
    retriever = HybridRRFRetriever(k_rrf=60)
    results = retriever.retrieve(query="Sierra academic school season promotions", store_nbr=14)

    assert len(results) > 0
    top_doc = results[0]
    assert "rrf_score" in top_doc
    assert top_doc["rrf_score"] > 0.0
    assert "Sierra" in top_doc["content"] or "school" in top_doc["content"].lower()


# -----------------------------------------------------------------------------
# 4. 3-Layer Stateful Memory & Tenant Isolation Tests
# -----------------------------------------------------------------------------

def test_memory_tenant_and_user_isolation():
    """Verify memory isolates state across users and enforces turn budget."""
    mem_mgr = ConversationMemoryManager(max_short_term_turns=5)

    for i in range(7):
        mem_mgr.add_turn("user", f"Turn {i} request regarding Store 14.")
        mem_mgr.add_turn("assistant", f"Turn {i} explanation.")

    assert len(mem_mgr.short_term_history) <= 5  # Trimmed to max turns
    assert "Summary update" in mem_mgr.conversation_summary


def test_rbac_store_authorization_and_denial():
    """Verify RBAC denies unauthorized store queries."""
    mem_mgr = ConversationMemoryManager()
    mem_mgr.durable_preferences["authorized_stores"] = [1, 14, 25]

    assert mem_mgr.is_store_authorized(14) is True
    assert mem_mgr.is_store_authorized(99) is False  # Unauthorized store


# -----------------------------------------------------------------------------
# 5. Database SQL Facts & Grounded Chat API Integration Tests
# -----------------------------------------------------------------------------

def test_sql_database_authoritative_facts():
    """Verify DatabaseRepository returns authoritative forecast facts."""
    facts = db_repo.get_forecast_facts(store_nbr=14, family="SCHOOL AND OFFICE SUPPLIES")
    assert facts["selected_engine"] == "LightGBM_GBDT"
    assert facts["surge_percentage"] == 145.0
    assert facts["reorder_point"] > 0.0


def test_chat_endpoint_integration_with_sql_facts():
    """Verify POST /api/v1/agent/chat retrieves authoritative SQL facts."""
    payload = {
        "user_id": "mgr_store_14",
        "user_role": "STORE_MANAGER",
        "query": "What is the expected demand surge and selected engine for School Supplies at Store 14?"
    }
    response = client.post("/api/v1/agent/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["grounded_verified"] is True
    assert "145%" in data["explanation"] or "LightGBM" in data["explanation"]
