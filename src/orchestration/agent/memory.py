"""
3-Layer Stateful Conversation Memory System for DemandPilot Layer 2.
Layer 1: Short-term chat turns (last 6-10 turns)
Layer 2: Rolling conversation summary
Layer 3: Durable user preferences & RBAC permissions
"""

from typing import List, Dict, Any, Optional
import time


class ConversationMemoryManager:
    """
    Manages stateful multi-layered memory per user and tenant.
    """

    def __init__(self, max_short_term_turns: int = 10):
        self.max_short_term_turns = max_short_term_turns
        self.short_term_history: List[Dict[str, str]] = []
        self.conversation_summary: str = ""
        self.durable_preferences: Dict[str, Any] = {
            "authorized_stores": [1, 14, 25, 52],
            "default_family": "SCHOOL AND OFFICE SUPPLIES",
            "preferred_unit": "units"
        }

    def add_turn(self, role: str, message: str):
        """Adds a short-term chat turn."""
        self.short_term_history.append({
            "role": role,
            "message": message,
            "timestamp": str(time.time())
        })

        # Trim short-term memory if budget exceeded
        if len(self.short_term_history) > self.max_short_term_turns:
            self._update_conversation_summary()
            self.short_term_history = self.short_term_history[-self.max_short_term_turns:]

    def _update_conversation_summary(self):
        """Updates rolling conversation summary from older turns."""
        turns_text = " ".join([t["message"] for t in self.short_term_history[:4]])
        self.conversation_summary += f" Summary update: {turns_text[:150]}..."

    def get_context_prompt(self) -> str:
        """Constructs memory context string for LLM system prompt."""
        context = []
        if self.conversation_summary:
            context.append(f"Conversation Summary: {self.conversation_summary}")

        if self.short_term_history:
            recent = "\n".join([f"{t['role'].upper()}: {t['message']}" for t in self.short_term_history[-6:]])
            context.append(f"Recent Messages:\n{recent}")

        return "\n\n".join(context)

    def is_store_authorized(self, store_nbr: int) -> bool:
        """Enforces RBAC store authorization policy."""
        return store_nbr in self.durable_preferences.get("authorized_stores", [])
