# Phase 5 — Grounded Chat That Can Say "I Don't Know"

**Status:** not started
**Gate:** GATE 5
**Depends on:** Phase 3 (`run_id`, real forecasts), Phase 4 (measured metrics to cite)

---

## 1. Objective

The agent answers questions about **any** loaded dataset using that dataset's real
forecasts, and withholds an answer it cannot support.

---

## 2. Starting state

Phase 1 already did the emergency work. Phase 5 completes the design.

**Already fixed:**

- The gate could not return `False` — all three `return` statements returned `True`. It
  now has four failure paths and withholds rather than rewrites.
- On mismatch it substituted a template asserting a "+145% demand surge" built from its
  own default parameters, turning a *detected error* into a more confident fabrication.
  Removed.
- Defaults `store_nbr=14`, `family="SCHOOL AND OFFICE SUPPLIES"`, `surge=145.0`,
  `rmsle=0.3812` deleted — an empty `retrieved_facts` no longer yields a populated answer.
- `search_store_knowledge` returned a synthetic doc scored `0.80`, above the `0.75` gate,
  making the low-confidence branch unreachable. Now returns `[]`.
- `hybrid_search_knowledge` scored every doc `0.70 + n*0.08`, floating all of them over
  the threshold including zero-overlap docs. Now a real match ratio, non-matching
  excluded.
- Calendar tokens ("Aug 8", "8-day window", years, ordinals) are stripped before numeric
  extraction, so dates neither falsely satisfy nor falsely fail the check.
- `get_forecast_logs` returns `Optional`; the agent answers *"I don't have a forecast on
  record for …"* with `grounded_verified: false`.

**Still to do:** the structured return type, dataset-agnostic keying, the ROP magic
constant, the runtime vocabulary, and the rename.

---

## 3. Requirements

### 3.1 Structured verification result

Replace the `(bool, str|None, list[str])` tuple with:

```python
@dataclass
class VerificationResult:
    status: Literal["VERIFIED", "UNSUPPORTED_CLAIM", "NO_DATA", "LOW_CONFIDENCE"]
    answer: str | None
    unsupported_values: list[float]
    sources: list[SourceRef]     # table + row keys + run_id actually queried
```

Rules — all four statuses must be reachable, and all four are already exercised by tests
added in Phase 1:

- Every numeric claim must match a value in `retrieved_facts` within tolerance.
  Non-matching → `UNSUPPORTED_CLAIM`, and the answer is **withheld, not rewritten**.
- `retrieved_facts` empty → `NO_DATA`, answer:
  *"I don't have a forecast for {entity}/{item} in run {run_id}."*
- Retrieval similarity below threshold → `LOW_CONFIDENCE`, naming which part is
  unsupported.
- **No default parameter may supply a business fact.**

`SourceRef` must carry the `run_id` actually queried, so a cited number is traceable to
the model artifact that produced it.

### 3.2 Rename the guarantee

**"Zero Hallucination Guarantee" → "Numerical Grounding Check"** — in code, docs, the
deck, and the UI.

Numeric cross-checking cannot prevent wrong causal attribution, wrong aggregation, or a
confidently wrong claim containing no digits. Do not promise what the mechanism cannot
deliver. (`verification_gate.py` already carries this reasoning in its module docstring;
the rename must propagate outward to `presentation/`, `architecture/`, and the frontend.)

### 3.3 Dataset-agnostic tools

`src/orchestration/agent/tools.py` currently keys on `(store_nbr, family)` — Favorita's
schema. Re-key on `(dataset_id, run_id, entity_id, item_id)`:

```python
get_forecast(dataset_id, run_id, entity_id, item_id) -> Optional[ForecastFact]
get_series_profile(dataset_id, entity_id, item_id)   -> Optional[SeriesProfile]
compare_to_baseline(dataset_id, run_id, entity_id, item_id) -> Optional[Comparison]
calculate_inventory_rop(forecast_avg, lead_time, service_factor, demand_std) -> ROP
search_knowledge(dataset_id, entity_id, query) -> list[Doc]   # [] when empty
```

`SeriesProfile` already exists from Phase 2 (`src/ingest/profile.py`) — reuse it rather
than defining a second one.

### 3.4 Kill the safety-stock magic constant

`calculate_inventory_rop` defaults `std_dev_daily=35.0`. That constant silently sizes
safety stock for every series, in units nobody chose. **Compute demand std from the
series' actual history and make the parameter required.**

### 3.5 Runtime vocabulary

`intent_router.extract_entities_from_query` hardcodes the 33 Favorita families as a class
constant (`PRODUCT_FAMILIES`). **Load the entity/item vocabulary from the
`DatasetProfile` at runtime.**

Phase 2 already exposes `DatasetProfile.entity_vocabulary` and `.item_vocabulary`. The
hardcoded list survives today only as a *test fixture* in
`tests/test_production_pipeline.py`, which is legitimate — it describes that dataset.

Also remove the Ecuador defaults still in the request path: `store_id: int = 14` and
`family: str = "SCHOOL AND OFFICE SUPPLIES"` in `intent_router` and `main.py`, and the
"Corporación Favorita, Ecuador's largest grocery retailer" framing in the agent's system
prompt.

---

## 4. GATE 5

1. Ask about a series that does not exist → it says it has no data.
2. Ask about the synthetic dataset from GATE 2 → it answers using **that dataset's** real
   forecasts.
3. Ask a question whose answer is not in the retrieved facts → `UNSUPPORTED_CLAIM`, answer
   withheld.
4. The string `145` appears nowhere in `src/`.

### Note on item 4

`145` currently appears in `src/` only inside module docstrings that document what was
removed — `test_no_fabrication.py` uses token-level parsing to exempt comments and
strings, so it passes today. If GATE 5 is read strictly as "nowhere at all, including
comments", the audit-trail comments must be relocated to these phase docs. **That is a
presentation choice, not a correctness one** — flag it and let the reviewer decide rather
than silently deleting the record of what was fixed.

### Blocker

Item 2 requires Phase 3's inference path. Item 1 and 3 work today.

---

## 5. Tests required

| File | Asserts |
|---|---|
| `test_verification_gate.py` | Each of the 4 statuses is reachable; unsupported numbers are **withheld, not rewritten** |

Phase 1 already added four of these against the tuple API
(`test_verification_gate_withholds_unsupported_number`, `..._reports_no_data`,
`..._low_confidence_is_reachable`, `..._withholds_instead_of_reanchoring`). Phase 5 ports
them to `VerificationResult` and consolidates them into `test_verification_gate.py`.
