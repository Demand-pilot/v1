"""
Numerical Grounding Check for DemandPilot Layer 2.

Cross-checks numeric claims in a generated answer against the facts actually retrieved.

Naming: this is deliberately NOT called a "Zero Hallucination Guarantee". Comparing
digits against retrieved rows cannot detect a wrong causal attribution, a wrong
aggregation, or a confidently wrong claim that contains no numbers at all. It checks one
specific failure mode, and it is named for that failure mode.

Phase 1 scope (this file): the gate can now return False, no default parameter supplies a
business fact, and an unsupported answer is WITHHELD rather than rewritten. Phase 5
replaces the tuple return with the structured `VerificationResult` described in §7.1.

What was here before:
  * Three `return` statements, all returning True. The gate could not fail.
  * On a numeric mismatch it discarded the model's answer and substituted a template
    string asserting a "+145% demand surge" — a figure that came from this module's own
    default parameters (`surge_percentage`, 145.0), not from any retrieval. A mismatch
    therefore produced a *more* confident fabricated claim than the answer it replaced.
  * Defaults `store_nbr=14`, `family="SCHOOL AND OFFICE SUPPLIES"`, `surge=145.0`,
    `rmsle=0.3812` meant an empty `retrieved_facts` still yielded a fully-populated
    "verified" answer.
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("demandpilot.verification")

# Retrieval confidence floor. Below this, retrieved documents are not treated as support.
SIMILARITY_THRESHOLD = 0.75

# Relative tolerance when matching a claimed number against a retrieved one.
RELATIVE_TOLERANCE = 0.01


class VerificationGate:
    """Numerical grounding check over generated answers."""

    # Calendar and structural tokens are not quantitative claims about the data. Left in,
    # "On Aug 8 with an 8-day window" contributes an 8 that either falsely matches a
    # supported 8.0% surge or falsely fails the check. Both outcomes are wrong, so these
    # spans are removed before numeric extraction.
    _NON_CLAIM_PATTERNS = [
        r'\b\d{4}-\d{2}-\d{2}\b',                                   # ISO dates
        r'\b(?:19|20)\d{2}\b',                                      # years
        r'\b\d{1,2}(?:st|nd|rd|th)\b',                              # ordinals: 15th, 30th
        r'\b\d+[-\s]?(?:day|days|week|weeks|month|months|hour|hours)\b',
        r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b',
        r'\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b',
        r'\bstore\s+\d+\b',                                         # entity identifiers
        r'\bh\s*=\s*\d+\b',
    ]

    @classmethod
    def _strip_non_claims(cls, text: str) -> str:
        cleaned = text or ""
        for pattern in cls._NON_CLAIM_PATTERNS:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
        return cleaned

    @classmethod
    def extract_numbers(cls, text: str) -> List[float]:
        """
        Extracts numeric literals that represent quantitative claims.

        Calendar references, ordinals, durations and entity identifiers are stripped
        first, so this returns the numbers an answer actually asserts about the data.
        """
        return [
            float(m)
            for m in re.findall(r'[+-]?\d+(?:\.\d+)?', cls._strip_non_claims(text))
        ]

    @staticmethod
    def extract_percentages(text: str) -> List[float]:
        """Extracts numbers explicitly qualified as percentages, avoiding date collisions."""
        matches = re.findall(
            r'([+-]?\d+(?:\.\d+)?)\s*(?:%|percent)', text or "", re.IGNORECASE
        )
        return [float(m) for m in matches]

    @staticmethod
    def _supported_values(retrieved_facts: Dict[str, Any]) -> List[float]:
        """
        Flattens retrieved facts into the set of numbers an answer may legitimately cite.

        Only values actually present in `retrieved_facts` are included. Absent keys
        contribute nothing — there is no default.
        """
        supported: List[float] = []

        def add(value: Any) -> None:
            if isinstance(value, bool):
                return
            if isinstance(value, (int, float)):
                supported.append(float(value))
            elif isinstance(value, (list, tuple)):
                for item in value:
                    add(item)

        for key, value in (retrieved_facts or {}).items():
            add(value)
            # Fractions are commonly rendered as percentages in prose.
            if isinstance(value, float) and 0.0 <= value <= 1.0:
                supported.append(round(value * 100.0, 4))

        return supported

    @classmethod
    def _is_supported(cls, claimed: float, supported: List[float]) -> bool:
        """True if `claimed` matches any supported value within tolerance."""
        for value in supported:
            tolerance = max(abs(value) * RELATIVE_TOLERANCE, 1e-6)
            if abs(claimed - value) <= tolerance:
                return True
            # Accept a rounded rendering of the same quantity.
            if round(claimed) == round(value):
                return True
        return False

    @classmethod
    def verify_response(
        cls,
        llm_response: str,
        retrieved_facts: Dict[str, Any],
        knowledge_matches: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Verifies an answer against retrieved facts.

        Returns (is_verified, answer_or_none, sources_used).

        `answer_or_none` is None whenever verification fails. The caller must surface the
        failure, not a substitute answer. Every failure path returns False.
        """
        sources_used = cls._sources_for(retrieved_facts, knowledge_matches)

        # 1. No facts retrieved => nothing to ground against.
        if not retrieved_facts:
            logger.info("Grounding check: NO_DATA (no facts retrieved).")
            return False, None, sources_used

        # 2. Retrieval confidence floor.
        similarities = [
            k.get("similarity_score", 0.0) for k in (knowledge_matches or [])
        ]
        max_similarity = max(similarities, default=0.0)

        # 3. Numeric cross-check across every number the answer asserts.
        supported = cls._supported_values(retrieved_facts)
        claimed = cls.extract_percentages(llm_response) + cls.extract_numbers(llm_response)
        unsupported = [c for c in claimed if not cls._is_supported(c, supported)]

        if unsupported:
            logger.warning(
                "Grounding check: UNSUPPORTED_CLAIM. Withholding answer. "
                "Unsupported values=%s", unsupported[:10]
            )
            return False, None, sources_used

        # An answer with no numeric claims is not thereby verified: if retrieval was weak,
        # there is no basis to assert it. This branch is now reachable, because
        # search_store_knowledge() no longer injects a 0.80-similarity placeholder doc.
        if max_similarity < SIMILARITY_THRESHOLD:
            logger.info(
                "Grounding check: LOW_CONFIDENCE (max similarity %.3f < %.2f).",
                max_similarity, SIMILARITY_THRESHOLD
            )
            return False, None, sources_used

        return True, llm_response, sources_used

    @staticmethod
    def _sources_for(
        retrieved_facts: Dict[str, Any],
        knowledge_matches: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Reports the tools that actually returned something.

        Previously this was a fixed list of three tool names returned regardless of
        whether any of them ran or produced data, so the citation trail was decorative.
        """
        sources: List[str] = []
        if retrieved_facts:
            sources.append("get_forecast_logs")
        if knowledge_matches:
            sources.append("search_store_knowledge")
        return sources
