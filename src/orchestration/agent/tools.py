"""
Agent tool surface for DemandPilot.

Every function here answers a question about real data. When the data is absent, the
answer is `None` or `[]` — never a stand-in. The previous implementations returned
fabricated facts on a database miss (RMSLE 0.3812, a +145% surge, a 2480-unit forecast),
which the agent then presented as retrieved ground truth.
"""

import logging
import math
from typing import Dict, Any, List, Optional

from src.orchestration.db.database import DatabaseRepository
from src.orchestration.agent.rag_retriever import HybridRRFRetriever

logger = logging.getLogger("demandpilot.tools")

db_repo = DatabaseRepository()
rag_retriever = HybridRRFRetriever()


def get_forecast_logs(store_nbr: int, family: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves persisted forecast facts for a series.

    Returns None when no forecast exists for (store_nbr, family). A None here means
    "this system has not forecast that series", which is a true and useful answer.
    Callers must not substitute a number.
    """
    facts = db_repo.get_forecast_facts(store_nbr, family)
    if facts:
        return facts

    logger.info(
        "No forecast_facts row for store=%s family=%r; returning None.", store_nbr, family
    )
    return None


def search_store_knowledge(store_nbr: int, query_text: str) -> List[Dict[str, Any]]:
    """
    Hybrid lexical + vector search (RRF) over store operational knowledge.

    Returns [] when nothing matches. The previous implementation returned a synthetic
    document with `similarity_score: 0.80` — above the 0.75 confidence gate — which made
    the gate's low-confidence branch unreachable and guaranteed every query "found"
    supporting evidence.
    """
    try:
        sql_docs = db_repo.hybrid_search_knowledge(query_text, store_nbr=store_nbr)
        if sql_docs:
            return sql_docs
    except Exception as err:
        logger.warning("Knowledge search against SQL failed: %s", err)

    ranked_docs = rag_retriever.retrieve(query_text, store_nbr)
    results = []
    for doc in ranked_docs:
        # No similarity default: a document with no computed score cannot be scored, and
        # inventing 0.85 would silently clear the confidence gate.
        score = doc.get("cosine_similarity")
        results.append({
            "doc_id": doc.get("id", "doc_unknown"),
            "store_nbr": doc.get("store_nbr", store_nbr),
            "title": doc.get("title", f"Store {store_nbr} Notes"),
            "content": doc.get("content", doc.get("text", "")),
            "similarity_score": float(score) if score is not None else 0.0,
            "rrf_score": doc.get("rrf_score", 0.0),
            "source": doc.get("source", "UNKNOWN"),
        })
    return results


def get_promo_elasticity(family: str) -> Optional[float]:
    """
    Fetches the measured promo-to-sales elasticity for a family.

    Returns None when the family has no elasticity record. The previous `0.2500` default
    was a business constant presented as a measurement.
    """
    elasticity_record = db_repo.get_promo_elasticity(family)
    if not elasticity_record:
        logger.info("No promo_elasticity row for family=%r; returning None.", family)
        return None

    score = elasticity_record.get("elasticity_score")
    if score is None:
        return None
    return float(score)


def calculate_inventory_rop(forecast_avg_daily: float, lead_time_days: float = 7.0, service_factor_z: float = 1.65, std_dev_daily: float = 35.0) -> Dict[str, float]:
    """
    Computes deterministic Reorder Point (ROP) and Safety Stock (SS).
    Formula:
      Safety Stock (SS) = Z * std_dev * sqrt(lead_time)
      Reorder Point (ROP) = (forecast_avg_daily * lead_time) + SS
    """
    safety_stock = service_factor_z * std_dev_daily * math.sqrt(lead_time_days)
    reorder_point = (forecast_avg_daily * lead_time_days) + safety_stock
    return {
        "safety_stock": round(safety_stock, 2),
        "reorder_point": round(reorder_point, 2),
        "lead_time_days": lead_time_days,
        "service_factor_z": service_factor_z
    }

