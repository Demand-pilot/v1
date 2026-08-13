"""
Hybrid retriever with Reciprocal Rank Fusion (RRF) for DemandPilot Layer 2.

RRF(d) = sum over rank lists m of 1 / (k + rank_m(d)).

The fusion algorithm here is real and is kept. What was removed is the corpus: both
`lexical_search` and `vector_search` previously ranked a hardcoded in-module list of
three or four documents whose text asserted "+145%" surges and "backtest RMSLE of
0.3812", and `vector_search` attached invented `cosine_similarity` values (0.9421,
0.8850, 0.8120) that were never computed from any embedding. Those documents were then
returned to the agent as retrieved evidence and cross-checked by the verification gate,
which is how invented figures acquired the appearance of provenance.

This retriever now ranks a corpus supplied by the caller (in practice, rows from
`store_knowledge_docs`). With no corpus, it returns [] — which is the correct answer to
"what do we know about this?" when the answer is "nothing".
"""

import logging
import re
from typing import List, Dict, Any, Optional, Sequence

logger = logging.getLogger("demandpilot.rag_retriever")

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


class HybridRRFRetriever:
    """
    Ranks a document corpus by fusing lexical and (when available) vector rank lists.

    Args:
        k_rrf: RRF smoothing constant.
        corpus: documents to search. Each is a dict with at least `id` and `text`, and
            optionally `store_nbr`, `family`, `embedding`, `source`. When None, the
            retriever has nothing to search and every query returns [].
        embedder: callable mapping text -> vector, used for genuine similarity search.
            When None, no vector arm runs. Nothing is simulated in its absence.
    """

    def __init__(
        self,
        k_rrf: int = 60,
        corpus: Optional[Sequence[Dict[str, Any]]] = None,
        embedder=None,
    ):
        self.k_rrf = k_rrf
        self.corpus: List[Dict[str, Any]] = list(corpus) if corpus else []
        self.embedder = embedder

    def _candidates(self, store_nbr: Optional[int]) -> List[Dict[str, Any]]:
        """
        Documents visible for a store: those scoped to it plus global docs.

        The previous filter was `doc["store_nbr"] == store_nbr or doc["store_nbr"] == 14`,
        which leaked store 14's notes into every other store's results.
        """
        if store_nbr is None:
            return list(self.corpus)
        return [
            d for d in self.corpus
            if d.get("store_nbr") in (store_nbr, 0, None)
        ]

    def lexical_search(
        self, query: str, store_nbr: Optional[int] = None, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Token-overlap ranking over the corpus. Returns [] when nothing overlaps."""
        query_terms = set(_tokenize(query))
        if not query_terms:
            return []

        scored = []
        for doc in self._candidates(store_nbr):
            haystack = set(_tokenize(doc.get("text", doc.get("content", ""))))
            haystack.update(_tokenize(" ".join(doc.get("keywords", []))))
            overlap = len(query_terms & haystack)
            if overlap > 0:
                scored.append((overlap, doc))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def vector_search(
        self, query: str, store_nbr: Optional[int] = None, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Embedding similarity search.

        Returns [] when no embedder is configured or no document carries an embedding.
        It does not fabricate cosine similarities, because a fabricated similarity above
        the confidence threshold silently disables the low-confidence branch downstream.
        """
        if self.embedder is None:
            return []

        query_vec = self.embedder(query)
        if query_vec is None:
            return []

        scored = []
        for doc in self._candidates(store_nbr):
            emb = doc.get("embedding")
            if emb is None:
                continue
            sim = self._cosine(query_vec, emb)
            if sim is None:
                continue
            enriched = dict(doc)
            enriched["cosine_similarity"] = sim
            scored.append((sim, enriched))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    @staticmethod
    def _cosine(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
        if a is None or b is None or len(a) != len(b):
            return None
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        if na == 0.0 or nb == 0.0:
            return None
        return dot / (na * nb)

    def combine_rrf(
        self,
        lexical_docs: List[Dict[str, Any]],
        vector_docs: List[Dict[str, Any]],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion over the two rank lists.
        RRF(d) = sum(1 / (k_rrf + rank_m(d))).
        """
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, Any]] = {}

        for rank_list in (lexical_docs, vector_docs):
            for rank, doc in enumerate(rank_list, start=1):
                doc_id = doc["id"]
                if doc_id not in doc_map:
                    doc_map[doc_id] = doc
                elif "cosine_similarity" in doc:
                    doc_map[doc_id] = {**doc_map[doc_id], **doc}
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (self.k_rrf + rank))

        sorted_doc_ids = sorted(rrf_scores, key=lambda did: rrf_scores[did], reverse=True)

        ranked_results = []
        for did in sorted_doc_ids[:top_k]:
            item = dict(doc_map[did])
            item["content"] = item.get("content") or item.get("text", "")
            item["rrf_score"] = round(rrf_scores[did], 6)
            ranked_results.append(item)

        return ranked_results

    def retrieve(self, query: str, store_nbr: Optional[int] = None) -> List[Dict[str, Any]]:
        """Runs hybrid retrieval with RRF ranking. Returns [] on an empty corpus."""
        if not self.corpus:
            logger.info("HybridRRFRetriever has no corpus configured; returning [].")
            return []
        lexical_res = self.lexical_search(query, store_nbr)
        vector_res = self.vector_search(query, store_nbr)
        return self.combine_rrf(lexical_res, vector_res)
