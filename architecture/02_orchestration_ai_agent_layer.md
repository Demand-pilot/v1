# DemandPilot Architecture — Layer 2: Orchestration & AI Agent Layer

**System Layer**: API Gateway, Workflow Orchestration & Grounded LLM Agent  
**Technologies**: FastAPI (Python 3.11), Redis 7, LangChain / LlamaIndex, PostgreSQL (pgvector)  
**Protocol Specs**: REST (JSON API), Server-Sent Events (SSE), Vector Embedding Search

---

## 1. FastAPI REST API Protocols & Schemas

The orchestration layer exposes clean RESTful microservices for frontend consumption:

```
[ FRONTEND ] ──► [ FastAPI ROUTER ] ──► [ INTENT CHECKER ] ──┬──► (Non-LLM Path: < 15ms Cache / SQL)
                                                             │
                                                             └──► (LLM Path: Grounded RAG Agent)
```

### Key Endpoint Specifications

#### Endpoint 1: `/api/v1/forecast/grid` (REST GET)
* **Description**: Returns 16-day daily forecast data across selected stores and categories.
* **Query Parameters**: `store_id` (int, optional), `family` (string, optional), `page` (int, default=1)
* **Response Schema**:
```json
{
  "status": "success",
  "horizon_days": 16,
  "start_date": "2017-08-16",
  "end_date": "2017-08-31",
  "data": [
    {
      "store_nbr": 14,
      "family": "SCHOOL AND OFFICE SUPPLIES",
      "selected_engine": "LightGBM_GBDT",
      "backtest_rmsle": 0.3812,
      "daily_forecasts": [124.5, 130.2, 145.8, 160.1, 155.0, 142.3, 138.9, 140.2, 150.1, 165.4, 180.2, 175.6, 160.0, 152.1, 148.3, 140.0],
      "reorder_point": 2480,
      "safety_stock": 420
    }
  ]
}
```

#### Endpoint 2: `/api/v1/agent/chat` (POST / SSE Stream)
* **Description**: Conversational Q&A endpoint for store managers with streaming response tokens.
* **Request Schema**:
```json
{
  "user_id": "mgr_store_14",
  "user_role": "STORE_MANAGER",
  "query": "Why is School Supplies surging by +145% at Store 14 in late August?"
}
```

---

## 2. Selective LLM Routing Protocol (Zero-Latency Overhead)

To optimize operational latency and avoid API compute costs, DemandPilot enforces a **Strict Selective LLM Routing Policy**:

```
                       ┌───────────────────────────────────────────┐
                       │           INCOMING USER REQUEST           │
                       └─────────────────────┬─────────────────────┘
                                             │
                                             ▼
                       ┌───────────────────────────────────────────┐
                       │       FASTAPI INTENT ROUTER CHECK         │
                       └─────────────────────┬─────────────────────┘
                                             │
                      Is this a natural language explanation query?
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      │ YES                                         │ NO
                      ▼                                             ▼
       ┌──────────────────────────────┐              ┌──────────────────────────────┐
       │ DIRECT TO GROUNDED LLM AGENT  │              │ DIRECT TO SQL / REDIS CACHE  │
       │ (LangChain + pgvector RAG)   │              │ (Pre-Computed Predictions)   │
       │ Latency: 400ms - 800ms        │              │ Latency: < 15ms              │
       └──────────────────────────────┘              └──────────────────────────────┘
```

### Selective Routing Rules
1. **Dashboard & Grid Requests**: Direct SQL/Redis lookup (`< 15ms`). **LLM is NEVER invoked** for raw data loading or chart rendering.
2. **Reorder Point & Safety Stock Calculations**: Pure deterministic Python math (`< 2ms`). **LLM is NEVER invoked** for formula evaluation.
3. **Manager Natural Language Q&A**: Routed to LLM Agent (`400ms – 800ms`) with strict database context grounding.

---

## 3. Grounded AI Agent & pgvector RAG Workflow

When a store manager asks a question, the AI Agent executes a **4-Step Zero-Hallucination Execution Loop**:

```
[ 1. INTENT PARSING ] ──► [ 2. DATABASE & VECTOR RETRIEVAL ] ──► [ 3. VERIFICATION GATE ] ──► [ 4. NATURAL SYNTHESIS ]
```

### Agent Tool Registry
The agent is provided with four read-only diagnostic tools:

| Tool Name | Input Arguments | Function Description |
|:---|:---|:---|
| `get_forecast_logs` | `store_nbr`, `family`, `date_range` | Retrieves pre-computed predictions, backtest RMSLE, and selected model name from PostgreSQL. |
| `search_store_knowledge` | `store_nbr`, `query_text` | Performs vector similarity search ($k=3$) over pgvector embeddings of store logs and local events. |
| `get_promo_elasticity` | `family` | Fetches historical promo-to-sales correlation scores (e.g. School Supplies = 0.6698). |
| `calculate_inventory_rop` | `forecast_avg`, `lead_time`, `service_factor` | Computes deterministic Reorder Point (ROP) and Safety Stock (SS). |

### Verification Gate (Zero Hallucination Guarantee)
Before the agent returns any natural language answer:
1. **Numerical Cross-Check**: The output generator verifies that every number in the LLM response matches the database query result exactly.
2. **Fallback Enforcement**: If the vector search returns low confidence ($< 0.75$ cosine similarity), the agent states: *"Forecast increase verified in SQL logs (+145%), but no local event notes found in store knowledge base."*
