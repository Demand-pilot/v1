# Leakage Policy

## The rule

> **A feature is legal at horizon _h_ if and only if its value is fully determined by
> information available at the cutoff.**

Everything below follows from that one sentence.

## Why this document exists

The original pipeline built lag and rolling features over the entire dataframe and *then*
split it by cutoff:

```python
df_feat = FeatureTransformer.apply_full_transformation_pipeline(df_raw, oil_df)  # lag_1 ... lag_28
train_df = df_feat[df_feat['date'] <= cutoff]
val_df   = df_feat[(df_feat['date'] > cutoff) & (df_feat['date'] <= cutoff + 16 days)]
```

At forecast time you stand at `cutoff` and predict `cutoff+1 … cutoff+16`. The row for
`cutoff+16` carried a `lag_14` computed from `cutoff+2` — a value that will not exist for
another fortnight. Two of sixteen horizon days leaked outright through `lag_14` alone, and
the rolling windows (`shift(1).rolling(7)`) leaked across nearly the whole horizon.

That is the mechanism behind the reported "+27% improvement over best baseline". The
model was partly reading the answer.

## What is legal

Let `H` be the forecast horizon (16 for the Favorita config).

### Target-derived features — legal only at offset ≥ H

| Feature | Legal? | Why |
|---|---|---|
| `lag_16`, `lag_21`, `lag_28`, `lag_35` | Yes | For `h = 16`, `lag_16` is the value at the cutoff itself. |
| `rolling_mean_16d/28d/56d` (shifted by `H`) | Yes | Window ends at or before the cutoff. |
| `rolling_std_28d`, `zero_ratio_56d` (shifted by `H`) | Yes | Same. |
| `lag_1`, `lag_7`, `rolling_mean_7d` | **No** | Unknown for every `h > 1`, `h > 7` respectively. |

The rule is enforced in code, not by convention:
`CoreFeatureBuilder.lag_and_rolling(..., min_lag_offset=H)` raises `ValueError` if asked
for a lag shorter than `H`.

Note the asymmetry this creates: `lag_16` is genuinely stale for `h = 1`, where a `lag_1`
would be available and far more informative. A single direct model must use the most
conservative lag across the whole horizon, so short-horizon accuracy is sacrificed. See
*Known cost* below.

### Calendar features — legal for the target date

`dayofweek`, `day`, `month`, `weekofyear`, `is_month_start`, `is_month_end` are computed
for `cutoff + h`, not for the cutoff. This is legitimate: the day of the week three weeks
out is a fact about the calendar, fully determined today.

The same applies to config-declared `calendar_flag` and `event_decay` exogenous features.

### Promo — legal for the target date **only when declared**

Promo features for `cutoff + h` are legal if and only if the dataset config sets:

```yaml
promo_known_in_advance: true
```

Favorita's `onpromotion` is a published promotional schedule, so a retailer genuinely
knows it in advance. That is a property of *that dataset*, not a general truth: for a
dataset where promotional activity is only recorded after the fact, using it at horizon
`h` is leakage. The flag must be set deliberately; it defaults to `false`.

When `false`, only `promo_lag_{H}` and shifted promo rollings are emitted.

### Price — lagged only

Treated as unknown in advance. Only `price_lag_{H}` is emitted. If a dataset can supply a
committed forward price schedule, that warrants a config flag mirroring
`promo_known_in_advance`; none exists yet.

### Global exogenous series — depends on the transform

A `global_series` such as differenced oil is aligned to the **target date**. This is the
one genuinely arguable case in this document, and it is flagged rather than hidden:
`delta_oil` at `cutoff + 16` is *not* knowable at the cutoff. It is currently emitted for
the target date because the original design treated macro series as exogenous regressors
in the classical sense, where future values are assumed given.

**`TODO(blocked)`: this is unresolved.** Two honest options, to be decided in Phase 4 when
the feature can actually be measured:

1. Shift global series by `H` like any other unknown input (safe, and probably correct).
2. Keep target-date alignment but only for series with a published forward curve, gated
   behind a per-exogenous `known_in_advance` flag like promo.

Until then, Phase 4 must report `delta_oil`'s contribution separately so that any lift it
provides can be discounted if it turns out to be leakage.

## Missing values are not zeros

Lag and rolling features are left as `NaN` where history is insufficient. The previous
implementation called `.fillna(0.0)` on every one of them, which teaches the model that
every series begins with a run of genuine zero-demand days.

Rows with incomplete features are **dropped** before fitting
(`FeatureBuilder.drop_rows_without_history`), not imputed. A series with too little
history to produce features has too little history to train on; at inference it routes to
the cold-start policy instead.

## Test enforcement

| Test | Enforces |
|---|---|
| `test_adapter_generalization.py::test_all_target_features_respect_the_horizon` | Every emitted lag ≥ H |
| `test_adapter_generalization.py::test_shorter_lags_than_horizon_are_rejected` | Requesting `lag_1` at H=16 raises |
| `test_production_pipeline.py::test_feature_grouped_isolation_no_cross_series_leakage` | Lags never cross a series boundary; absent history is `NaN`, not `0.0` |
| `test_leakage.py` *(Phase 3)* | Property test: shuffling post-cutoff target values must leave predictions **bit-identical** |

That last one is the definitive check. Everything above is an argument; that test is
evidence. It is `TODO(blocked)` until the Phase 3 inference path exists.

## Known cost

Applying this policy will make measured RMSLE **worse** than the previously reported
0.42393. That figure was produced by a script that had never run, using a duplicated
strawman baseline, over leaked features. The new number will be the first honest one, and
a higher honest number is the correct outcome.

## Recorded upgrade path (not built)

Sixteen direct per-horizon models (`model_h`, one per `h ∈ 1..16`) would let each model
use the tightest lag legal for *its* horizon — `lag_1` for `h = 1`, `lag_16` for
`h = 16` — instead of forcing every horizon onto the most conservative offset. This
typically buys 3–8% RMSLE. The single global model with `horizon_day` as a feature ships
first; this is noted in the ADR, not built.
