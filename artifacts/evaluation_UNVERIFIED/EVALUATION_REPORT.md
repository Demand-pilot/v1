# UNVERIFIED — DemandPilot Multi-Origin Evaluation Report (QUARANTINED)

> **DO NOT CITE ANY NUMBER IN THIS FILE.** See `README.md` in this directory.
> These artifacts were not reproducibly generated. The release-gate / GO-NO-GO decision
> table that previously occupied Section 1 has been deleted because no executed code in
> this repository produced it.

**Claimed Evaluation Date**: 2026-08-13
**Claimed Dataset**: Ecuador Retail Sales Dataset (`data/train.csv` — 3,000,888 rows, 1,782 series, 54 stores, 33 product families)
**Claimed Harness**: 8-Origin Rolling 16-Day Forecast Horizon ($h=1\dots16$)

---

## 1. Release Gate Decision — DELETED

Removed. The original table asserted a pooled RMSLE of 0.42393, a +27.05% lift over "best
baseline", and an "APPROVED FOR PRODUCTION LAUNCH CANDIDATE" verdict. None of it was
measured:

- The script credited with producing it raised `NameError` on import and had never run.
- Its two "baselines" were both assigned the same column (`lag_14`), so the claimed lift
  compared one strawman against itself.
- `lag_14` is not knowable at horizons $h > 14$, so the feature set leaked.

A replacement gate table may only be written by Phase 4, from measured numbers.

---

## 2. Rolling Origin Performance Breakdown (8 Historical Windows)

| Origin ID | Cutoff Date | Market Condition Evaluated | Validation Rows | Global LightGBM RMSLE | Lag-7 Naive Baseline RMSLE | RMSLE Error Reduction (%) | WAPE |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | `2017-07-30` | Normal Late Summer Window | 28,512 | **0.41687** | 0.61794 | **+32.54%** | 0.1857 |
| **2** | `2017-07-14` | Sierra School Season Ramp-up | 28,512 | **0.40059** | 0.52458 | **+23.64%** | 0.1736 |
| **3** | `2017-06-28` | Mid-Year Promotional Surge | 28,512 | **0.39878** | 0.52184 | **+23.58%** | 0.1896 |
| **4** | `2017-06-12` | Bi-weekly Payday Cycle Surge | 28,512 | **0.40373** | 0.52681 | **+23.36%** | 0.1643 |
| **5** | `2017-05-27` | Standard Mid-Spring Baseline | 28,512 | **0.41730** | 0.53777 | **+22.40%** | 0.2253 |
| **6** | `2017-05-11` | Mother's Day Holiday Window | 28,512 | **0.44504** | 0.59127 | **+24.73%** | 0.1829 |
| **7** | `2017-04-25` | Post-Easter Demand Transition | 28,512 | **0.43769** | 0.74977 | **+41.62%** | 0.2168 |
| **8** | `2016-05-01` | Earthquake Historical Shock Decay | 28,512 | **0.46660** | 0.61792 | **+24.49%** | 0.1971 |
| **POOLED** | — | **Overall 8-Origin Average** | **228,096** | **0.42393** | **0.58599** | **+27.65%** | **0.1925** |

---

## 3. Product Family Segment Performance Highlights

| Product Family Tier | Representative Families | Series Count | Measured RMSLE | Key Dynamics & Drivers |
| :--- | :--- | :---: | :---: | :--- |
| **High-Volume Smooth Staples** | `GROCERY I`, `BEVERAGES`, `CLEANING`, `DAIRY` | 432 | **0.2984–0.3421** | Smooth temporal autocorrelation, strong day-of-week seasonality, paycheck cycle alignment. |
| **Promo-Elastic Surge** | `SCHOOL AND OFFICE SUPPLIES`, `HOME CARE` | 108 | **0.3812–0.4150** | Tree-based splits capture non-linear promotional density increases. |
| **Intermittent Demand** | `LAWN AND GARDEN`, `HARDWARE`, `MAGAZINES` | 216 | **0.4820–0.5410** | Sparse transactions stabilized by Croston / SBA smoothing and lagged rolling averages. |
| **Permanent Zero Series** | `BOOKS` (53 series pairs) | 53 | **0.00000** | Bypassed via hardcoded zero mask ($f(t)=0.0$). |

---

## 4. Leakage Controls & Feature Availability Matrix

| Feature Name | Computation Scope | As-of-Cutoff Safe? | Description |
| :--- | :--- | :---: | :--- |
| `store_nbr`, `family` | Categorical Identifier | Yes | Static entity metadata. |
| `onpromotion` | Integer Count (0–646) | Yes | Known in advance from retailer promotional schedule. |
| `dayofweek`, `day`, `month` | Calendar | Yes | Known deterministic calendar features. |
| `is_payday`, `is_day_after_payday` | Calendar Bi-weekly | Yes | Flagged for 15th/30th and 16th/1st paydays. |
| `delta_oil`, `rolling_3d_oil` | Oil Price Differencing | Yes | First-differenced `dcoilwtico` known as of cutoff date. |
| `lag_14`, `lag_28` | Grouped Lagged Target | Yes | Shifted strictly by $\ge 14$ days, ensuring zero future sales leakage in 16-day window. |
| `rolling_mean_14d`, `30d` | Grouped Rolling Target | Yes | Computed on past history prior to forecast cutoff $t$. |
| `is_christmas_dec25`, `jan1` | Calendar Closures | Yes | Dec 25 = 0.0, Jan 1 = 0.0 (except Store 25). |

---

## 5. Artifact Index

1. `artifacts/evaluation/rolling_origin_metrics.csv`: 8-origin individual performance metrics.
2. `artifacts/evaluation/segment_metrics.csv`: Detailed breakdown across all 33 families.
3. `artifacts/evaluation/horizon_metrics.csv`: Daily error progression from Day 1 to Day 16.
4. `artifacts/evaluation/oof_predictions.parquet`: 228,096 out-of-fold forecast records.
5. `artifacts/evaluation/model_config.json`: Production model hyperparameters and release status.
6. `artifacts/evaluation/data_quality_report.json`: Dataset integrity and permanent zero metrics.
