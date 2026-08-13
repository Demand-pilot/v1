# DemandPilot Architecture — Layer 6: Latency Analysis & Mitigation Strategies

**System Scope**: End-to-End Performance, Latency SLA Audit & High-Concurrency Optimization  
**SLA Targets**: Initial Dashboard Load $< 100\text{ms}$, Cache Hit Response $< 15\text{ms}$, Streaming LLM Explanation $< 600\text{ms}$

---

## 1. End-to-End System Latency Audit

In high-concurrency retail environments, processing $1,782$ time series simultaneously introduces potential performance bottlenecks. Below is an audit of potential latency risks across the architecture:

```
[ FRONTEND UI ] ──(1)──► [ FASTAPI ROUTER ] ──(2)──► [ REDIS CACHE ] ──(3)──► [ MODEL INFERENCE ] ──(4)──► [ LLM AGENT ]
  (RSC Hydration)         (Python Async)              (< 15ms Hit)             (1,782 Batch Tensor)      (Streaming SSE)
```

### Potential Latency Bottlenecks Identified

| Pipeline Step | Latency Risk Factor | Raw Unoptimized Time | Optimized SLA Target | Mitigation Technique |
|:---|:---|:---:|:---:|:---|
| **1. Frontend Rendering** | Large JavaScript bundle & client-side data fetching | $1,200\text{ms}$ | **$< 100\text{ms}$** | Next.js 14 React Server Components (RSC) + Selective Client Hydration. |
| **2. API & Routing** | Synchronous Python thread blocking | $350\text{ms}$ | **$< 10\text{ms}$** | FastAPI `async/await` non-blocking endpoints with Uvicorn worker pool. |
| **3. Database Querying** | Scanning 3.0M+ historical transaction rows | $850\text{ms}$ | **$< 15\text{ms}$** | TimescaleDB hypertable index + Redis 7 pre-computed 16-day forecast caching. |
| **4. Parallel Inference** | Running sequential loops for 1,782 models | $4,500\text{ms}$ | **$< 80\text{ms}$** | Batch PyTorch GPU tensor evaluation + C++ LightGBM multi-threading (`num_threads=8`). |
| **5. AI Agent Q&A** | Unbounded LLM prompt generation & network latency | $2,500\text{ms}$ | **$< 600\text{ms}$** | Selective LLM Routing Policy + Server-Sent Events (SSE) streaming token output. |

---

## 2. Technical Mitigation Strategies

### Mitigation 1: Pre-Computed Forecast & Redis 7 Caching Protocol
Rather than computing 1,782 model inferences on the fly whenever a user visits the dashboard, DemandPilot executes batch inference during off-peak hours and writes the 16-day forecast grid directly to **Redis 7**:

```python
# Redis Key Schema: demandpilot:forecast:{store_nbr}:{family}
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0)

def get_forecast(store_nbr: int, family: str):
    cache_key = f"demandpilot:forecast:{store_nbr}:{family}"
    cached_data = r.get(cache_key)
    
    if cached_data:
        # Cache Hit (< 15ms latency)
        return json.loads(cached_data)
    
    # Cache Miss: Fall back to PostgreSQL database query
    forecast_record = fetch_from_db(store_nbr, family)
    r.setex(cache_key, 86400, json.dumps(forecast_record)) # 24-hour TTL
    return forecast_record
```

### Mitigation 2: Batched PyTorch & Multi-Threaded GBDT Inference
* **PyTorch LSTM Batching**: Combines all 1,782 series into a single tensor batch of shape `(1782, 60, num_features)` and runs one single GPU forward pass (`model(batch_x)`), reducing deep learning inference time from $4.5\text{s}$ to **$45\text{ms}$**.
* **LightGBM Multi-Threading**: Invokes LightGBM C++ core binaries compiled with OpenMP support, executing decision tree traversals across 8 parallel CPU cores.

### Mitigation 3: Selective LLM Bypass Architecture
As documented in Layer 2, DemandPilot enforces a strict intent router:
* Request for forecast tables / charts $\rightarrow$ **0% LLM Involvement** (Serviced instantly by Redis cache in $< 15\text{ms}$).
* Request for plain-English explanation $\rightarrow$ **Streaming SSE LLM Output** (First token delivered in $< 350\text{ms}$).

### Mitigation 4: pgvector Index Optimization (HNSW)
To keep vector search latency under $20\text{ms}$ across store knowledge embeddings, DemandPilot uses **Hierarchical Navigable Small World (HNSW)** indexing in PostgreSQL:
```sql
CREATE INDEX ON store_knowledge_vectors 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
```

---

## 3. Latency & Performance SLA Matrix

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                DEMANDPILOT LATENCY SLA MATRIX                             │
├──────────────────────────────┬──────────────────────────────┬─────────────────────────────┤
│ OPERATION                    │ TARGET RESPONSE TIME         │ BOTTLENECK MITIGATION       │
├──────────────────────────────┼──────────────────────────────┼─────────────────────────────┤
│ Dashboard Page Hydration     │ < 100 ms                     │ RSC Server Edge Rendering   │
│ Forecast Grid API Query      │ < 15 ms                      │ Redis 7 In-Memory Cache     │
│ 1,782 Batch Model Inference  │ < 80 ms                      │ Batched GPU PyTorch Tensors │
│ Conversational AI Q&A        │ < 600 ms (First Token <350ms)│ SSE Streaming + Grounded RAG│
│ Vector Knowledge Search      │ < 20 ms                      │ HNSW Cosine Index           │
└──────────────────────────────┴──────────────────────────────┴─────────────────────────────┘
```
