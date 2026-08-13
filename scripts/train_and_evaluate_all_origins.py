"""
Multi-origin rolling backtest harness.

STATUS: TODO(blocked) — awaiting Phase 4. The harness body has been removed; only the
metric computation below is real, and Phase 4 reuses it.

Phase 1 fixed the two defects that made the original file inert or actively misleading:

  * `from typing import Dict` sat at the bottom of the module, after the annotated
    `def compute_comprehensive_metrics(...) -> Dict[str, float]`, so importing it raised
    `NameError`. It had therefore never executed, and
    `artifacts/evaluation/EVALUATION_REPORT.md` (RMSLE 0.42393, "APPROVED FOR PRODUCTION
    LAUNCH") was not produced by it.
  * `baseline_lag7` and `baseline_lag1` were both assigned `val_df['lag_14']`, so the
    advertised "+27% improvement over best baseline" compared the model against a single
    strawman counted twice.

Phase 2 then removed the harness body itself rather than porting it, because it depended
on `FeatureTransformer.apply_full_transformation_pipeline` — an Ecuador-specific API that
no longer exists — and because it leaked regardless: it built `lag_14` over the whole
frame and then sliced by cutoff, so horizon days 15 and 16 read target values from after
the cutoff. Porting a harness whose numbers are not reportable is wasted work.

Phase 4 rebuilds it per §6:
  * features rebuilt per origin from `df[df.date <= cutoff]` only,
  * four genuinely distinct baselines (seasonal naive, MA-28, lag-H persistence,
    item-level median),
  * every engine evaluated, including the mediator as its own arm,
  * mean +/- std across origins, not just a pooled figure,
  * selection on origins 1..7, reporting on origin 8.
"""

import sys
from typing import Dict

import numpy as np


def compute_comprehensive_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Computes RMSLE, WAPE, MAE, RMSE, signed bias, and under/over-forecast rates.

    This function is genuine: it measures the arrays it is given. It is retained across
    the Phase 4 rewrite.
    """
    y_t = np.clip(np.asarray(y_true, dtype=float), 0.0, None)
    y_p = np.clip(np.asarray(y_pred, dtype=float), 0.0, None)

    if y_t.shape != y_p.shape:
        raise ValueError(f"Shape mismatch: y_true {y_t.shape} vs y_pred {y_p.shape}")
    if y_t.size == 0:
        raise ValueError("Cannot compute metrics over an empty array.")

    rmsle = float(np.sqrt(np.mean((np.log1p(y_p) - np.log1p(y_t)) ** 2)))
    mae = float(np.mean(np.abs(y_p - y_t)))
    rmse = float(np.sqrt(np.mean((y_p - y_t) ** 2)))

    sum_yt = float(np.sum(y_t))
    wape = float(np.sum(np.abs(y_t - y_p)) / (sum_yt + 1e-6))
    bias = float(np.sum(y_p - y_t) / (sum_yt + 1e-6))

    return {
        "RMSLE": round(rmsle, 5),
        "WAPE": round(wape, 5),
        "MAE": round(mae, 3),
        "RMSE": round(rmse, 3),
        "Signed_Bias_%": round(bias * 100.0, 2),
        "Underforecast_Rate_%": round(float(np.mean(y_p < y_t)) * 100.0, 2),
        "Overforecast_Rate_%": round(float(np.mean(y_p > y_t)) * 100.0, 2),
    }


def run_full_multi_origin_evaluation(data_dir: str = "data"):
    raise NotImplementedError(
        "TODO(blocked): the leakage-safe multi-origin harness lands in Phase 4.\n"
        "The previous body built lag_14 over the full frame before slicing by cutoff, so "
        "horizon days 15 and 16 leaked. Its numbers were not reportable and it was removed "
        "rather than ported."
    )


if __name__ == "__main__":
    sys.exit(
        "scripts/train_and_evaluate_all_origins.py is not implemented yet (Phase 4).\n"
        "No metrics are produced and no artifacts are written.\n"
        "See the module docstring for what was removed and why."
    )
