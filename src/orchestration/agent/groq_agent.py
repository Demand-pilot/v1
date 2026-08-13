"""
Groq LLM API Integration & Function-Calling Grounded Agent for DemandPilot Layer 2.
Connects to Groq Llama-3.3-70B API with function calling over database diagnostic tools.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from src.orchestration.agent.tools import (
    get_forecast_logs,
    search_store_knowledge,
    get_promo_elasticity,
    calculate_inventory_rop
)
from src.orchestration.agent.verification_gate import VerificationGate
from src.orchestration.agent.memory import ConversationMemoryManager

logger = logging.getLogger("demandpilot.groq_agent")

GROQ_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_forecast_logs",
            "description": "Retrieves pre-computed predictions, backtest RMSLE, and selected model engine from PostgreSQL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_nbr": {"type": "integer", "description": "Store number (1-54)"},
                    "family": {"type": "string", "description": "Product family name"}
                },
                "required": ["store_nbr", "family"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_store_knowledge",
            "description": "Performs vector similarity search over store logs and local events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_nbr": {"type": "integer", "description": "Store number (1-54)"},
                    "query_text": {"type": "string", "description": "Search query text"}
                },
                "required": ["store_nbr", "query_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_promo_elasticity",
            "description": "Fetches promo-to-sales correlation elasticity score for a family.",
            "parameters": {
                "type": "object",
                "properties": {
                    "family": {"type": "string", "description": "Product family category"}
                },
                "required": ["family"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_inventory_rop",
            "description": "Computes deterministic Reorder Point (ROP) and Safety Stock (SS).",
            "parameters": {
                "type": "object",
                "properties": {
                    "forecast_avg_daily": {"type": "number", "description": "Average projected daily units"},
                    "lead_time_days": {"type": "number", "description": "Supplier lead time in days"}
                },
                "required": ["forecast_avg_daily"]
            }
        }
    }
]


class GroqGroundedAgent:
    """
    Grounded AI Agent executing 4-Step Zero-Hallucination Loop via Groq LLM or Grounded Fallback.
    Supports multi-turn conversation memory and data-grounded system prompts.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model
        self.client = None
        self._sessions: Dict[str, ConversationMemoryManager] = {}
        self._init_client()

    def _init_client(self):
        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
                logger.info("Initialized Groq LLM API client successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq API client ({e}). Using grounded RAG fallback.")
                self.client = None
        else:
            logger.info("No GROQ_API_KEY set. Using high-speed grounded RAG synthesis engine.")

    def _get_memory(self, session_id: str) -> ConversationMemoryManager:
        """Returns or creates a per-session memory instance."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationMemoryManager()
        return self._sessions[session_id]

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Executes diagnostic database tool functions."""
        if tool_name == "get_forecast_logs":
            return get_forecast_logs(tool_args.get("store_nbr", 14), tool_args.get("family", "SCHOOL AND OFFICE SUPPLIES"))
        elif tool_name == "search_store_knowledge":
            return search_store_knowledge(tool_args.get("store_nbr", 14), tool_args.get("query_text", ""))
        elif tool_name == "get_promo_elasticity":
            return get_promo_elasticity(tool_args.get("family", "SCHOOL AND OFFICE SUPPLIES"))
        elif tool_name == "calculate_inventory_rop":
            return calculate_inventory_rop(tool_args.get("forecast_avg_daily", 100.0), tool_args.get("lead_time_days", 7.0))
        return {}

    def _build_system_prompt(
        self,
        retrieved_facts: Dict[str, Any],
        knowledge: List[Dict[str, Any]],
        memory: ConversationMemoryManager,
        store_nbr: int,
        family: str
    ) -> str:
        """Builds a data-grounded system prompt with retrieved facts, knowledge, and memory context."""
        knowledge_text = "\n".join([
            f"- [{doc.get('title', 'Note')}] {doc.get('content', doc.get('text', ''))}"
            for doc in knowledge[:3]
        ]) or "No specific store knowledge documents found."

        # Only keys actually present are stated. The previous version printed
        # "Surge Percentage: +0%" and "Promo Density (Train): 0.0%" when those fields were
        # absent, handing the model zeros that read as measurements.
        fact_lines = [f"Store: {store_nbr}, Family: {family}"]
        for label, key, fmt in (
            ("Selected Engine", "selected_engine", None),
            ("Backtest RMSLE", "backtest_rmsle", "{:.4f}"),
            ("Forecast Sum", "forecast_16d_sum", "{:.1f} units"),
            ("Forecast Avg Daily", "forecast_avg_daily", "{:.1f} units/day"),
            ("Reorder Point", "reorder_point", "{:.1f}"),
            ("Safety Stock", "safety_stock", "{:.1f}"),
            ("Surge Percentage", "surge_percentage", "{:+.1f}%"),
            ("Run ID", "run_id", None),
        ):
            value = retrieved_facts.get(key)
            if value is None:
                continue
            fact_lines.append(f"{label}: {fmt.format(value) if fmt else value}")

        facts_text = "\n".join(fact_lines)

        memory_context = memory.get_context_prompt()

        prompt = (
            "You are DemandPilot Retail AI Assistant for Corporación Favorita, Ecuador's largest grocery retailer. "
            "Provide data-grounded explanations for retail store managers and supply chain planners. "
            "Always cite the exact numbers from the database facts below. Never invent statistics.\n\n"
            "## Verified Database Facts\n"
            f"{facts_text}\n\n"
            "## Store Knowledge Documents\n"
            f"{knowledge_text}\n\n"
            "## Available Tools\n"
            "You have access to the following tools:\n"
            "- get_forecast_logs: Retrieve predictions, backtest RMSLE, and model engine from PostgreSQL.\n"
            "- search_store_knowledge: Vector similarity search over store operational notes.\n"
            "- get_promo_elasticity: Fetch promo-to-sales correlation elasticity score.\n"
            "- calculate_inventory_rop: Compute Reorder Point (ROP) and Safety Stock (SS).\n\n"
            "Use these tools when the user asks about a different store or family than the one already provided, "
            "or when you need additional data not covered by the facts above.\n\n"
            "If you do not have enough information to answer accurately, say so explicitly.\n"
        )

        if memory_context:
            prompt += f"\n## Conversation History\n{memory_context}\n"

        return prompt

    def ask(
        self,
        query: str,
        store_nbr: int = 14,
        family: str = "SCHOOL AND OFFICE SUPPLIES",
        session_id: str = "default"
    ) -> Tuple[str, bool, List[str]]:
        """
        Executes 4-Step Execution Loop:
        1. Intent Parsing & Pre-Fetch
        2. DB & Vector Retrieval (via Groq Tool Calling or Direct Retrieval)
        3. Verification Gate Cross-Check
        4. Verified Synthesis
        """
        # Step 1: Pre-fetch grounding data
        retrieved_facts = get_forecast_logs(store_nbr, family)
        knowledge = search_store_knowledge(store_nbr, query)
        prefetch_tools = ["get_forecast_logs", "search_store_knowledge"]
        groq_called_tools: List[str] = []

        # No facts => say so. There is nothing to ground an answer in, and the model must
        # not be asked to write one. get_forecast_logs() now returns None on a miss
        # instead of a fabricated record, so this branch is reachable.
        if not retrieved_facts:
            memory = self._get_memory(session_id)
            memory.add_turn("user", query)
            no_data = (
                f"I don't have a forecast on record for store {store_nbr} / {family!r}, "
                f"so I can't answer that. Run the forecast pipeline for this series first."
            )
            memory.add_turn("assistant", no_data)
            logger.info("No retrieved facts for store=%s family=%r; answering NO_DATA.",
                        store_nbr, family)
            return no_data, False, prefetch_tools

        # Get conversation memory
        memory = self._get_memory(session_id)
        memory.add_turn("user", query)

        if self.client:
            try:
                system_prompt = self._build_system_prompt(
                    retrieved_facts, knowledge, memory, store_nbr, family
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ]

                raw_text = None
                try:
                    # Primary call with tools available
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=GROQ_TOOLS_SCHEMA,
                        tool_choice="auto"
                    )
                    response_message = response.choices[0].message

                    # Handle tool calling if the LLM decided it needs additional data
                    if response_message.tool_calls:
                        messages.append(response_message)
                        for tool_call in response_message.tool_calls:
                            func_name = tool_call.function.name
                            func_args = json.loads(tool_call.function.arguments)
                            tool_result = self._execute_tool(func_name, func_args)
                            groq_called_tools.append(func_name)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": func_name,
                                "content": json.dumps(tool_result)
                            })

                        second_response = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages
                        )
                        raw_text = second_response.choices[0].message.content
                    else:
                        raw_text = response_message.content

                except Exception as tool_err:
                    # Retry without tools — Llama 3.3 sometimes emits XML-style function calls
                    # that cause tool_use_failed. Since all data is in the system prompt, a plain
                    # completion works fine.
                    logger.info(f"Retrying Groq without tools after: {tool_err}")
                    retry_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages
                    )
                    raw_text = retry_response.choices[0].message.content

                # Verification Gate Pass
                is_verified, verified_explanation, _ = VerificationGate.verify_response(
                    raw_text, retrieved_facts, knowledge
                )

                # A withheld answer is withheld. The gate returns None on failure and the
                # answer is replaced by an explicit refusal, never by a rewritten claim.
                answer = verified_explanation if is_verified else self._withheld_message(
                    store_nbr, family
                )
                memory.add_turn("assistant", answer)

                all_tools = list(set(prefetch_tools + groq_called_tools))
                return answer, is_verified, all_tools
            except Exception as err:
                logger.warning(f"Groq API call error: {err}. Falling back to fact rendering.")

        # No LLM available. Render the retrieved facts literally, with no causal story.
        #
        # The previous fallback asserted "+{surge}% demand surge ... driven by the Sierra
        # academic season and active promo density increasing from X% to Y%" — a causal
        # explanation the system had never tested, built from fields that were themselves
        # fabricated defaults. Facts get restated; causes do not get invented.
        raw_draft = self._render_facts(store_nbr, family, retrieved_facts)
        is_verified, verified_explanation, _ = VerificationGate.verify_response(
            raw_draft, retrieved_facts, knowledge
        )
        answer = verified_explanation if is_verified else raw_draft
        memory.add_turn("assistant", answer)
        return answer, is_verified, prefetch_tools

    @staticmethod
    def _withheld_message(store_nbr: int, family: str) -> str:
        return (
            f"I drafted an answer about store {store_nbr} / {family!r} but it contained "
            f"figures I could not match against the retrieved records, so I'm withholding "
            f"it rather than showing numbers I can't support."
        )

    @staticmethod
    def _render_facts(store_nbr: int, family: str, facts: Dict[str, Any]) -> str:
        """Restates retrieved facts. Only keys actually present are mentioned."""
        parts = [f"Store {store_nbr}, {family}:"]

        engine = facts.get("selected_engine")
        if engine:
            parts.append(f"forecast produced by {engine}")

        rmsle = facts.get("backtest_rmsle")
        if rmsle is not None:
            parts.append(f"backtest RMSLE {float(rmsle):.4f}")

        total = facts.get("forecast_16d_sum")
        if total is not None:
            parts.append(f"forecast total {float(total):.1f} units")

        avg = facts.get("forecast_avg_daily")
        if avg is not None:
            parts.append(f"average {float(avg):.1f} units/day")

        rop = facts.get("reorder_point")
        if rop is not None:
            parts.append(f"reorder point {float(rop):.1f}")

        run_id = facts.get("run_id")
        if run_id:
            parts.append(f"from run {run_id}")

        return " ".join([parts[0], ", ".join(parts[1:]) + "."]) if len(parts) > 1 else parts[0]
