"""
Batch training pipeline for DemandPilot.

STATUS: TODO(blocked) — awaiting Phase 3. This script does not train anything yet, and
it refuses to run rather than appearing to.

Why the previous body was deleted rather than repaired:

  * It never read `data/train.csv`. It generated its own series with
    `np.random.uniform(80, 120, n_days)` and `np.random.uniform(10, 30, n_days)`, then
    trained on those.
  * It assigned accuracy by literal: `rmsle = 0.3812` on the LightGBM branch and
    `rmsle = 0.2150` on the LSTM branch. Neither was measured; both were written into the
    Redis cache and served to the UI as "backtest RMSLE".
  * It imported `BacktestEngine` and `MediatorEngine.route_and_ensemble` and called
    neither, while labelling its output "Mediator_Tournament_Hybrid".
  * It fit models in-process and discarded them. Nothing was persisted, so there was no
    inference path — not for a new dataset, and not for the dataset it claimed to be
    trained on.
  * Its forecast window was the string literals "2017-08-16"/"2017-08-31", which are
    Favorita's last observed date + 1 and are meaningless for any other dataset.

Phase 3 replaces this with:

    python -m scripts.train_pipeline \\
        --dataset configs/datasets/favorita.yaml \\
        --cutoff auto \\
        --horizon 16 \\
        --engines lightgbm,lstm,seasonal_naive,croston \\
        --run-id auto

which must: load via the dataset adapter -> profile series -> build horizon-safe features
-> train each engine -> backtest on rolling origins -> actually invoke
`MediatorEngine.route_and_ensemble` -> persist every artifact through
`src/models/registry.py` -> write a `model_runs` row.

Until then, running this exits non-zero. It does not emit a forecast, and it does not
write to the cache or the database.
"""

import sys


def run_batch_training_pipeline(data_dir: str = "data") -> int:
    raise NotImplementedError(
        "TODO(blocked): real training lands in Phase 3.\n"
        "The previous implementation trained on np.random synthetic series and hardcoded "
        "its own RMSLE. It was removed rather than left in place, because a pipeline that "
        "reports fabricated accuracy is worse than one that reports nothing."
    )


if __name__ == "__main__":
    sys.exit(
        "scripts/train_pipeline.py is not implemented yet (Phase 3).\n"
        "No model is trained, no forecast is produced, and nothing is written.\n"
        "See the module docstring for what was removed and why."
    )
