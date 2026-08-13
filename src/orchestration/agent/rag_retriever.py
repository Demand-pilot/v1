"""
Hybrid Lexical + Vector RAG Retriever with Reciprocal Rank Fusion (RRF) for DemandPilot Layer 2.
Combines PostgreSQL tsvector full-text search with pgvector similarity search,
ranked via RRF formula: RRF(d) = sum(1 / (60 + rank_m(d))).
"""

import math
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("demandpilot.rag_retriever")


class HybridRRFRetriever:
    """
    Hybrid Retriever executing Reciprocal Rank Fusion (RRF) over Lexical and Vector search results.
    """

    def __init__(self, k_rrf: int = 60):
        self.k_rrf = k_rrf

    def lexical_search(self, query: str, store_nbr: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Simulates PostgreSQL tsvector full-text search over store operational notes and promo events.
        """
        knowledge_db = [
            {
                "id": "doc_101",
                "store_nbr": 14,
                "family": "SCHOOL AND OFFICE SUPPLIES",
                "text": "Sierra academic year begins mid-August. Store 14 historical sales surge by +145% due to back-to-school promotional campaign.",
                "keywords": ["sierra", "academic", "august", "surge", "school", "promotion"]
            },
            {
                "id": "doc_102",
                "store_nbr": 14,
                "family": "ALL",
                "text": "Store 14 inventory reorder lead time is 7 days. Buffer safety stock required for high-velocity families during August.",
                "keywords": ["inventory", "reorder", "lead time", "safety stock", "august"]
            },
            {
                "id": "doc_103",
                "store_nbr": 1,
                "family": "GROCERY I",
                "text": "Store 1 Grocery I maintains steady volume with 1st and 16th bi-weekly payday surges of +8.0%.",
                "keywords": ["grocery", "payday", "surges", "bi-weekly"]
            }
        ]

        query_terms = [t.lower() for t in query.split()]
        matches = []
        for doc in knowledge_db:
            if doc["store_nbr"] == store_nbr or doc["store_nbr"] == 14:
                overlap = sum(1 for term in query_terms if term in doc["keywords"] or term in doc["text"].lower())
                if overlap > 0:
                    matches.append({"doc": doc, "score": overlap})

        matches = sorted(matches, key=lambda x: x["score"], reverse=True)
        return [m["doc"] for m in matches[:top_k]]

    def vector_search(self, query: str, store_nbr: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Simulates pgvector HNSW embedding similarity search.
        """
        vector_db = [
            {
                "id": "doc_101",
                "store_nbr": 14,
                "text": "Sierra academic year begins mid-August. Store 14 historical sales surge by +145% due to back-to-school promotional campaign.",
                "cosine_similarity": 0.9421
            },
            {
                "id": "doc_104",
                "store_nbr": 14,
                "text": "LightGBM GBDT engine selected with backtest RMSLE of 0.3812 for promo-elastic surge handling.",
                "cosine_similarity": 0.8850
            },
            {
                "id": "doc_102",
                "store_nbr": 14,
                "text": "Store 14 inventory reorder lead time is 7 days. Buffer safety stock required for high-velocity families during August.",
                "cosine_similarity": 0.8120
            }
        ]

        matches = [d for d in vector_db if d["store_nbr"] == store_nbr or store_nbr == 14]
        matches = sorted(matches, key=lambda x: x["cosine_similarity"], reverse=True)
        return matches[:top_k]

    def combine_rrf(
        self,
        lexical_docs: List[Dict[str, Any]],
        vector_docs: List[Dict[str, Any]],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) algorithm:
        RRF(d) = sum(1 / (k_rrf + rank_m(d))) across lexical and vector rank lists.
        """
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, Any]] = {}

        # 1. Rank Lexical Results
        for rank, doc in enumerate(lexical_docs, start=1):
            doc_id = doc["id"]
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (self.k_rrf + rank))

        # 2. Rank Vector Results
        for rank, doc in enumerate(vector_docs, start=1):
            doc_id = doc["id"]
            if doc_id not in doc_map:
                doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (self.k_rrf + rank))

        # 3. Sort by aggregated RRF score
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda did: rrf_scores[did], reverse=True)

        ranked_results = []
        for did in sorted_doc_ids[:top_k]:
            item = doc_map[did].copy()
            item["content"] = item.get("text", "")
            item["rrf_score"] = round(rrf_scores[did], 6)
            ranked_results.append(item)

        return ranked_results

    def retrieve(self, query: str, store_nbr: int = 14) -> List[Dict[str, Any]]:
        """
        Runs hybrid lexical + vector retrieval with RRF ranking.
        """
        lexical_res = self.lexical_search(query, store_nbr)
        vector_res = self.vector_search(query, store_nbr)
        return self.combine_rrf(lexical_res, vector_res)
