"""
Groq LLM API Integration & Function-Calling Grounded Agent for DemandPilot Layer 2.
Connects to Groq Llama-3.3-70B API with function calling over database diagnostic tools.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv
load_dotenv()

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

        facts_text = (
            f"Store: {store_nbr}, Family: {family}\n"
            f"Selected Engine: {retrieved_facts.get('selected_engine', 'N/A')}\n"
            f"Backtest RMSLE: {retrieved_facts.get('backtest_rmsle', 'N/A')}\n"
            f"16-Day Forecast Sum: {retrieved_facts.get('forecast_16d_sum', 'N/A')} units\n"
            f"Baseline 16-Day Sum: {retrieved_facts.get('baseline_16d_sum', 'N/A')} units\n"
            f"Surge Percentage: +{retrieved_facts.get('surge_percentage', 0):.0f}%\n"
            f"Promo Density (Train): {retrieved_facts.get('promo_density_train', 0)*100:.1f}%\n"
            f"Promo Density (Test): {retrieved_facts.get('promo_density_test', 0)*100:.1f}%"
        )

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

                models_to_try = [self.model]
                if "8b" not in self.model:
                    models_to_try.append("llama-3.1-8b-instant")

                raw_text = None
                last_err = None

                for target_model in models_to_try:
                    try:
                        # Primary attempt with tools
                        try:
                            response = self.client.chat.completions.create(
                                model=target_model,
                                messages=messages,
                                tools=GROQ_TOOLS_SCHEMA,
                                tool_choice="auto"
                            )
                            response_message = response.choices[0].message

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
                                    model=target_model,
                                    messages=messages
                                )
                                raw_text = second_response.choices[0].message.content
                            else:
                                raw_text = response_message.content

                        except Exception as tool_err:
                            # Retry without tools — Llama 3.3/3.1 sometimes emits XML-style function calls
                            logger.info(f"Retrying {target_model} without tools after: {tool_err}")
                            retry_response = self.client.chat.completions.create(
                                model=target_model,
                                messages=messages
                            )
                            raw_text = retry_response.choices[0].message.content

                        if raw_text and raw_text.strip():
                            break  # Successfully generated with target_model

                    except Exception as model_err:
                        last_err = model_err
                        logger.warning(f"Groq {target_model} failed ({model_err}). Trying next fallback model...")

                if raw_text and raw_text.strip():
                    # Verification Gate Pass
                    is_verified, verified_explanation, _ = VerificationGate.verify_response(
                        raw_text, retrieved_facts, knowledge
                    )

                    # Record assistant response in memory
                    memory.add_turn("assistant", verified_explanation)

                    all_tools = list(set(prefetch_tools + groq_called_tools))
                    return verified_explanation, is_verified, all_tools
                else:
                    logger.warning(f"All Groq models failed ({last_err}). Using query-aware grounded RAG synthesis engine.")

            except Exception as err:
                logger.warning(f"Groq API call error: {err}. Falling back to grounded RAG engine.")

        # Intelligent Query-Aware Grounded RAG Fallback
        q_lower = query.lower()
        if any(w in q_lower for w in ["hello", "hi", "hey", "who are you", "what can you do", "help"]):
            raw_draft = (
                f"Hello! I am the DemandPilot Retail AI Assistant for Corporación Favorita. "
                f"I provide data-grounded explanations, forecast analyses, and inventory calculations. "
                f"Currently viewing Store {store_nbr} ({family}). You can ask me about demand surges, "
                f"promotional elasticity, model performance (LightGBM vs PyTorch LSTM), or Reorder Points (ROP)."
            )
        elif any(w in q_lower for w in ["safety stock", "rop", "reorder point", "formula", "inventory"]):
            rop_info = calculate_inventory_rop(forecast_avg_daily=retrieved_facts.get("forecast_16d_sum", 1600.0) / 16.0)
            raw_draft = (
                f"Reorder Point (ROP) and Safety Stock (SS) for Store {store_nbr} ({family}):\n"
                f"- Safety Stock (SS) = Z * std_dev * sqrt(lead_time) = {rop_info['safety_stock']} units\n"
                f"- Reorder Point (ROP) = (Avg Daily Demand * Lead Time) + SS = {rop_info['reorder_point']} units\n"
                f"- Lead Time: {rop_info['lead_time_days']} days (Service Factor Z: {rop_info['service_factor_z']})."
            )
        elif any(w in q_lower for w in ["model", "gbdt", "lstm", "algorithm", "engine", "rmsle"]):
            raw_draft = (
                f"For Store {store_nbr} ({family}), the selected forecasting engine is {retrieved_facts.get('selected_engine', 'LightGBM_GBDT')} "
                f"with a backtest RMSLE of {retrieved_facts.get('backtest_rmsle', 0.3812):.4f}. "
                f"LightGBM GBDT is selected for high promo-elasticity items and tabular shock features, "
                f"while PyTorch LSTM captures smooth sequence trends for high-volume staples."
            )
        else:
            raw_draft = (
                f"Store {store_nbr} ({family}) exhibits a +{retrieved_facts.get('surge_percentage', 0):.0f}% demand surge in late August. "
                f"This surge is driven by seasonal regional demand and active promo density increasing "
                f"from {retrieved_facts.get('promo_density_train', 0.204)*100:.1f}% to {retrieved_facts.get('promo_density_test', 0.441)*100:.1f}%. "
                f"Selected Engine: {retrieved_facts.get('selected_engine', 'LightGBM_GBDT')} (Backtest RMSLE: {retrieved_facts.get('backtest_rmsle', 0.3812)})."
            )

        is_verified, verified_explanation, _ = VerificationGate.verify_response(raw_draft, retrieved_facts, knowledge)
        memory.add_turn("assistant", verified_explanation)
        return verified_explanation, is_verified, prefetch_tools

