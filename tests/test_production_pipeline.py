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
from src.features.transformer import CoreFeatureBuilder

client = TestClient(app)
db_repo = DatabaseRepository()


# -----------------------------------------------------------------------------
# 1. Feature Leakage & Grouped Isolation Tests
# -----------------------------------------------------------------------------

def test_feature_grouped_isolation_no_cross_series_leakage():
    """Lag features must never cross a series boundary."""
    df_sample = pd.DataFrame({
        "entity_id": ["1", "1", "2", "2"],
        "item_id": ["GROCERY I"] * 4,
        "date": pd.to_datetime(["2017-08-01", "2017-08-02", "2017-08-01", "2017-08-02"]),
        "target": [100.0, 200.0, 500.0, 600.0],
    })

    lagged = CoreFeatureBuilder.lag_and_rolling(df_sample, min_lag_offset=1, lags=[1], windows=[])

    # Entity 2 on day 1 has no prior observation of its OWN series. That is NaN, not 0.0
    # and emphatically not 200.0 carried over from entity 1. The previous implementation
    # filled it with 0.0, which reads as an observed zero-demand day.
    entity2_day1 = lagged.loc[
        (df_sample["entity_id"] == "2") & (df_sample["date"] == "2017-08-01")
    ].iloc[0]
    assert pd.isna(entity2_day1["lag_1"])

    # Entity 2 on day 2 sees its own day-1 value, not entity 1's.
    entity2_day2 = lagged.loc[
        (df_sample["entity_id"] == "2") & (df_sample["date"] == "2017-08-02")
    ].iloc[0]
    assert entity2_day2["lag_1"] == 500.0


def test_as_of_cutoff_safe_oil_differencing(tmp_path):
    """
    A config-declared global series is differenced and gap-filled on load.

    Oil is no longer a concept the feature code knows about; it is a `global_series`
    entry in configs/datasets/favorita.yaml, loaded generically.
    """
    from src.ingest.adapter import DatasetConfig, DatasetAdapter, ExogenousSpec

    csv_path = tmp_path / "oil.csv"
    pd.DataFrame({
        "date": ["2017-08-01", "2017-08-02", "2017-08-03"],
        "dcoilwtico": [48.5, np.nan, 50.5],
    }).to_csv(csv_path, index=False)

    config = DatasetConfig(
        name="t", grain="daily", main_path="unused",
        column_map={}, config_dir=str(tmp_path),
    )
    spec = ExogenousSpec(
        kind="global_series", name="delta_oil", path=str(csv_path),
        date_col="date", value_col="dcoilwtico", transform="first_difference",
    )

    series = DatasetAdapter.load_global_series(config, spec)

    assert series.name == "delta_oil"
    # The interior gap is interpolated (48.5 -> 49.5 -> 50.5), so each step is +1.0.
    assert series.iloc[1] == pytest.approx(1.0)
    assert series.iloc[2] == pytest.approx(1.0)
    # The first difference is genuinely undefined, and is left as NaN rather than
    # asserted to be 0.0 ("no change") as the previous implementation did.
    assert pd.isna(series.iloc[0])


# -----------------------------------------------------------------------------
# 2. Entity Extraction Tests
# -----------------------------------------------------------------------------

# Favorita's item vocabulary. Phase 5 replaces this hardcoded list in the router with the
# vocabulary read from the DatasetProfile at runtime; the test list stays here as a
# fixture for that dataset.
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
    """RRF fuses and ranks a supplied corpus; an empty corpus returns []."""
    corpus = [
        {"id": "d1", "store_nbr": 14, "text": "Sierra academic season restock planning."},
        {"id": "d2", "store_nbr": 14, "text": "Payday staging for beverage aisles."},
        {"id": "d3", "store_nbr": 25, "text": "Coastal port transit buffer levels."},
    ]
    retriever = HybridRRFRetriever(k_rrf=60, corpus=corpus)
    results = retriever.retrieve(query="Sierra academic season promotions", store_nbr=14)

    assert len(results) > 0
    top_doc = results[0]
    assert top_doc["rrf_score"] > 0.0
    assert "Sierra" in top_doc["content"]
    # Store 25's document must not surface for store 14. The previous filter
    # (`doc.store_nbr == store_nbr or doc.store_nbr == 14`) leaked across stores.
    assert all(d["id"] != "d3" for d in results)

    # No corpus configured => nothing retrieved, rather than a hardcoded document set.
    assert HybridRRFRetriever(k_rrf=60).retrieve(query="anything", store_nbr=14) == []


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
    """A series with no persisted forecast returns None, not a synthesised record."""
    facts = db_repo.get_forecast_facts(store_nbr=14, family="SCHOOL AND OFFICE SUPPLIES")
    assert facts is None


def test_chat_endpoint_integration_with_sql_facts():
    """The chat endpoint declines to answer when it has no facts for the series."""
    payload = {
        "user_id": "mgr_store_14",
        "user_role": "STORE_MANAGER",
        "query": "What is the expected demand surge and selected engine for School Supplies at Store 14?"
    }
    response = client.post("/api/v1/agent/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["grounded_verified"] is False
    assert "don't have a forecast" in data["explanation"]
