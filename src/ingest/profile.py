"""
Dataset and per-series profiles.

A `DatasetProfile` is the answer to "what is actually in this data?", computed from the
data itself. Downstream code gates features on it rather than assuming: promo features
are emitted only if `has_promo`, oil features only if the config declared an oil series
and the file was found.

Every field here is measured. None is defaulted, and none is copied from a spec sheet.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.ingest.schema import (
    ENTITY_ID,
    ITEM_ID,
    DATE,
    TARGET,
    PROMO,
    SERIES_KEY,
    present_optional_columns,
)


@dataclass(frozen=True)
class SeriesProfile:
    """Measured statistics for a single (entity, item) series."""

    entity_id: str
    item_id: str
    n_observations: int
    history_days: int
    date_min: pd.Timestamp
    date_max: pd.Timestamp
    target_sum: float
    target_mean: float
    zero_ratio: float
    cv: Optional[float]
    promo_elasticity: Optional[float]
    is_permanent_zero: bool

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["date_min"] = str(self.date_min.date())
        d["date_max"] = str(self.date_max.date())
        return d


@dataclass
class DatasetProfile:
    """
    Measured description of a loaded dataset.

    `available_exogenous` lists exogenous features that were declared in the config AND
    successfully materialised. A feature declared but whose source file is missing does
    not appear here, so downstream code cannot request it.
    """

    dataset_name: str
    grain: str
    n_rows: int
    n_entities: int
    n_items: int
    n_series: int
    date_min: pd.Timestamp
    date_max: pd.Timestamp
    n_days_spanned: int
    optional_columns: List[str] = field(default_factory=list)
    available_exogenous: List[str] = field(default_factory=list)
    declared_exogenous: List[str] = field(default_factory=list)
    series: List[SeriesProfile] = field(default_factory=list)
    permanent_zero_series: List[tuple] = field(default_factory=list)
    promo_known_in_advance: bool = False
    closures: List[Dict[str, Any]] = field(default_factory=list)

    # --- convenience predicates used to gate optional features -------------------

    @property
    def has_promo(self) -> bool:
        return PROMO in self.optional_columns

    @property
    def has_price(self) -> bool:
        return "price" in self.optional_columns

    def has_exogenous(self, name: str) -> bool:
        return name in self.available_exogenous

    @property
    def entity_vocabulary(self) -> List[str]:
        return sorted({s.entity_id for s in self.series})

    @property
    def item_vocabulary(self) -> List[str]:
        return sorted({s.item_id for s in self.series})

    @property
    def min_history_days(self) -> int:
        return min((s.history_days for s in self.series), default=0)

    @property
    def median_zero_ratio(self) -> float:
        return float(np.median([s.zero_ratio for s in self.series])) if self.series else 0.0

    def summary(self) -> Dict[str, Any]:
        """Compact, JSON-serialisable summary suitable for an API response or a report."""
        return {
            "dataset_name": self.dataset_name,
            "grain": self.grain,
            "n_rows": self.n_rows,
            "n_entities": self.n_entities,
            "n_items": self.n_items,
            "n_series": self.n_series,
            "date_min": str(self.date_min.date()),
            "date_max": str(self.date_max.date()),
            "n_days_spanned": self.n_days_spanned,
            "optional_columns": list(self.optional_columns),
            "declared_exogenous": list(self.declared_exogenous),
            "available_exogenous": list(self.available_exogenous),
            "promo_known_in_advance": self.promo_known_in_advance,
            "n_permanent_zero_series": len(self.permanent_zero_series),
            "min_history_days": self.min_history_days,
            "median_zero_ratio": round(self.median_zero_ratio, 4),
        }


def _coefficient_of_variation(values: np.ndarray) -> Optional[float]:
    """CV = std / mean. None when the mean is zero, because the ratio is undefined."""
    mean = float(np.mean(values))
    if abs(mean) <= 1e-9:
        return None
    return float(np.std(values) / mean)


def _promo_elasticity(target: np.ndarray, promo: np.ndarray) -> Optional[float]:
    """
    Pearson correlation between target and promo intensity.

    Returns None when either series is constant — the correlation is undefined there, and
    the previous implementation returned 0.0, which reads as "measured no relationship"
    rather than "could not be measured".
    """
    if len(target) < 3:
        return None
    if float(np.std(target)) <= 1e-9 or float(np.std(promo)) <= 1e-9:
        return None
    corr = float(np.corrcoef(target, promo)[0, 1])
    return None if np.isnan(corr) else corr


def profile_series(
    df: pd.DataFrame,
    *,
    permanent_zero_min_history: int,
) -> List[SeriesProfile]:
    """
    Computes a SeriesProfile per (entity, item).

    `is_permanent_zero` is derived: total target == 0 over a history long enough for the
    claim to be meaningful. It is never a hardcoded list of item names.
    """
    has_promo = PROMO in df.columns
    profiles: List[SeriesProfile] = []

    for (entity, item), group in df.groupby(SERIES_KEY, observed=True, sort=True):
        target = group[TARGET].to_numpy(dtype=float)
        dates = group[DATE]
        date_min, date_max = dates.min(), dates.max()
        history_days = int((date_max - date_min).days) + 1
        target_sum = float(target.sum())

        promo_elasticity = None
        if has_promo:
            promo_values = group[PROMO].to_numpy(dtype=float)
            promo_elasticity = _promo_elasticity(target, promo_values)

        profiles.append(
            SeriesProfile(
                entity_id=str(entity),
                item_id=str(item),
                n_observations=int(len(group)),
                history_days=history_days,
                date_min=date_min,
                date_max=date_max,
                target_sum=target_sum,
                target_mean=float(target.mean()),
                zero_ratio=float(np.mean(target <= 1e-9)),
                cv=_coefficient_of_variation(target),
                promo_elasticity=promo_elasticity,
                is_permanent_zero=(
                    target_sum == 0.0 and history_days >= permanent_zero_min_history
                ),
            )
        )

    return profiles


def build_dataset_profile(
    df: pd.DataFrame,
    *,
    dataset_name: str,
    grain: str,
    declared_exogenous: List[str],
    available_exogenous: List[str],
    promo_known_in_advance: bool,
    closures: List[Dict[str, Any]],
    permanent_zero_min_history: int,
) -> DatasetProfile:
    """Measures a loaded canonical frame and returns its DatasetProfile."""
    series = profile_series(df, permanent_zero_min_history=permanent_zero_min_history)

    date_min, date_max = df[DATE].min(), df[DATE].max()

    return DatasetProfile(
        dataset_name=dataset_name,
        grain=grain,
        n_rows=int(len(df)),
        n_entities=int(df[ENTITY_ID].nunique()),
        n_items=int(df[ITEM_ID].nunique()),
        n_series=len(series),
        date_min=date_min,
        date_max=date_max,
        n_days_spanned=int((date_max - date_min).days) + 1,
        optional_columns=present_optional_columns(df),
        declared_exogenous=list(declared_exogenous),
        available_exogenous=list(available_exogenous),
        series=series,
        permanent_zero_series=[
            (s.entity_id, s.item_id) for s in series if s.is_permanent_zero
        ],
        promo_known_in_advance=promo_known_in_advance,
        closures=list(closures),
    )
