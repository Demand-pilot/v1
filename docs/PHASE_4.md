# Phase 4 — Honest Evaluation

**Status:** not started
**Gate:** GATE 4
**Depends on:** Phase 3 (persisted models, `Predictor`, `model_runs`)

Phase 3 produces forecasts. Phase 4 is what makes any accuracy claim about them
defensible. **Phase 3 results must not be presented without Phase 4.**

---

## 1. Objective

Rewrite `scripts/train_and_evaluate_all_origins.py` so that every number in
`artifacts/evaluation/EVALUATION_REPORT.md` is produced by executing code in this
repository, in the run that wrote the file.

---

## 2. Starting state

`scripts/train_and_evaluate_all_origins.py` is currently a **loud-failing stub**. Phase 1
fixed its two headline defects, then Phase 2 removed the harness body entirely rather than
porting it. What survives is `compute_comprehensive_metrics`, which genuinely measures its
arguments and is reused here.

What was wrong, for the record — this is what the report must explain:

| Defect | Effect |
|---|---|
| `from typing import Dict` at the bottom of the module, after the annotated `def` | `NameError` on import. The script had **never run**, so it did not produce `EVALUATION_REPORT.md` |
| `baseline_lag7` and `baseline_lag1` both assigned `val_df['lag_14']` | The "+27% improvement over best baseline" compared the model against one strawman, twice |
| Features built over the whole frame, then sliced by cutoff | `lag_14` is unknowable at `h > 14`; 2 of 16 horizon days leaked outright, rollings leaked further |
| Only LightGBM evaluated | LSTM, Croston, seasonal naive, and the mediator were never measured |
| Pooled metrics only | Cross-origin variance hidden; single-fold selection noise laundered as signal |

The originals are quarantined in `artifacts/evaluation_UNVERIFIED/` with a README and the
GO/NO-GO table deleted. `tests/test_no_fabrication.py` enforces that they stay there.

---

## 3. Requirements

### 3.1 Per-origin feature rebuild

Features rebuilt **per origin** from `df[df.date <= cutoff]` only. No global
precompute-then-slice. Phase 2's `FeatureBuilder` already enforces the horizon offset;
Phase 4 must additionally ensure the *frame it is handed* is truncated at the cutoff.

### 3.2 Four genuinely distinct baselines

Each implemented separately. The duplicated-column bug must not recur.

1. Seasonal naive — same weekday, previous week
2. Moving average, 28 days
3. Lag-`H` persistence
4. Item-level median

### 3.3 Every engine, plus the mediator as its own arm

LightGBM, LSTM, Croston, seasonal naive, **and the mediator**. The mediator is the product
thesis and has never been measured.

### 3.4 Metrics

Per origin, per horizon-day, per segment: RMSLE, WAPE, MAE, RMSE, signed bias,
under/over-forecast rate.

Report **mean ± std across origins**, not just the pooled figure. A pooled number hides
per-origin variance.

### 3.5 Selection honesty

If the mediator picks per-series winners using backtest RMSLE, that RMSLE is
optimistically biased. **Hold out the most recent origin, use it for reporting only, never
for selection.** Select on origins 1..7, report on origin 8. State this explicitly in the
report.

### 3.6 Resolve the `delta_oil` question

Carried forward from Phase 2 as `TODO(blocked)`. `delta_oil` is currently aligned to the
**target date**, which by the leakage rule is not knowable at the cutoff.

Phase 4 must measure `delta_oil`'s contribution in isolation and decide:

1. shift it by `H` like any other unknown input, or
2. gate target-date alignment behind a per-exogenous `known_in_advance` flag, mirroring
   `promo_known_in_advance`.

Whichever is chosen, `docs/LEAKAGE_POLICY.md` is updated to match the code, and any lift
attributable to `delta_oil` is reported separately so it can be discounted.

---

## 4. The one table that decides whether Layer 5 exists

| Arm | Pooled RMSLE | Mean ± std across origins | Δ vs always-LightGBM |
|---|---|---|---|
| Always-LightGBM | | | — |
| Always-LSTM | | | |
| Best single baseline | | | |
| **Mediator (routed/ensembled)** | | | |

**If the mediator does not beat always-LightGBM by a margin larger than the cross-origin
std, say so in the report and open an ADR proposing its removal.** Do not quietly keep it.

---

## 5. Mediator fixes (from §8 of the master prompt)

The softmax overflow is already fixed — max-subtraction is present. Two issues remain:

1. **Rule 2 fuses two different concepts.** The predicate
   `(second_rmsle - best_rmsle) > 0.05 or promo_elasticity > 0.60` conflates "the models
   are distinguishable" with "this series is promo-elastic". The `or` makes it pick
   whichever model happened to win even when the models are statistically
   indistinguishable. **Split them.**
2. **Blend weights depend on absolute RMSLE scale.** `exp(1 / rmsle)` gives 0.55/0.45 for
   0.30 vs 0.32, but 0.84/0.16 for 0.10 vs 0.12 — the same 0.02 gap. **Replace with
   `softmax(-rmsle / T)` and expose `T`.**

Covered by `tests/test_mediator.py`: rules 1/2/3 fire correctly; softmax stays finite for
RMSLE in `[1e-6, 5.0]`.

---

## 6. Report regeneration

`artifacts/evaluation/EVALUATION_REPORT.md` is written **by the script**, templated, with
`run_id`, git sha, timestamp, and row counts injected programmatically.

- Every artifact listed in the index **must exist on disk**. The old report listed
  `oof_predictions.parquet`, which did not exist.
- No GO/NO-GO table until real numbers back it.
- The report must state the delta versus the old fabricated 0.42393 and explain that the
  old figure came from leakage plus a duplicated strawman baseline.

---

## 7. GATE 4

1. The report regenerates end-to-end from **one command**.
2. Every artifact listed in its index exists on disk.
3. The mediator comparison table is populated with **measured** numbers.
4. `docs/LEAKAGE_POLICY.md` matches the code.

### Blocker

All four items require `data/train.csv`. `data/` is currently empty.

---

## 8. Tests required

| File | Asserts |
|---|---|
| `test_mediator.py` | Rules 1/2/3 fire correctly; softmax finite for RMSLE in `[1e-6, 5.0]`; the split Rule-2 predicates behave independently |

Plus `test_leakage.py` from Phase 3, which is what actually retires the leakage argument.
