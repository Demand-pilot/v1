"""
Dataset adapter: YAML config -> canonical frame + measured DatasetProfile.

This is the boundary that makes the rest of the system dataset-agnostic. Everything
Ecuador-specific — the `store_nbr`/`family`/`sales` column names, the WTI oil series, the
15th/30th payday calendar, the April 2016 earthquake, the Dec 25 / Jan 1 closures and
store 25's exemption — lives in `configs/datasets/favorita.yaml` and nowhere else.

Adding a new dataset means adding a YAML file, not editing Python.

Loud failure is the rule: a config that names a missing file, an unmappable column, or a
malformed exogenous block raises with an actionable message. Nothing is silently skipped,
with one deliberate exception — an exogenous source whose file is absent is dropped from
`available_exogenous` and logged, so the feature builder simply never emits it rather
than emitting a column of imputed zeros.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

from src.ingest import schema
from src.ingest.profile import DatasetProfile, build_dataset_profile

logger = logging.getLogger("demandpilot.adapter")

# A series must be observed at least this long before "permanently zero" is a claim about
# the world rather than about a short sample. Overridable per dataset.
DEFAULT_PERMANENT_ZERO_MIN_HISTORY = 365

SUPPORTED_EXOGENOUS_KINDS = {"global_series", "calendar_flag", "event_decay"}
SUPPORTED_TRANSFORMS = {"none", "first_difference", "log", "pct_change"}


class DatasetConfigError(ValueError):
    """Raised when a dataset config is missing, malformed, or self-inconsistent."""


@dataclass
class ExogenousSpec:
    """One declared exogenous feature."""

    kind: str
    name: str
    # global_series
    path: Optional[str] = None
    date_col: Optional[str] = None
    value_col: Optional[str] = None
    transform: str = "none"
    # calendar_flag
    days_of_month: List[int] = field(default_factory=list)
    # event_decay
    event_date: Optional[str] = None
    decay_days: Optional[int] = None
    half_life: Optional[float] = None


@dataclass
class DatasetConfig:
    """Parsed dataset config. Mirrors configs/datasets/*.yaml."""

    name: str
    grain: str
    main_path: str
    column_map: Dict[str, str]
    config_dir: str
    entity_meta: Optional[Dict[str, Any]] = None
    exogenous: List[ExogenousSpec] = field(default_factory=list)
    closures: List[Dict[str, Any]] = field(default_factory=list)
    promo_known_in_advance: bool = False
    permanent_zero_min_history: int = DEFAULT_PERMANENT_ZERO_MIN_HISTORY

    def resolve(self, path: str) -> str:
        """Resolves a config-relative path against the repository root."""
        if os.path.isabs(path):
            return path
        return os.path.normpath(os.path.join(self.config_dir, path))


def _require(mapping: Dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise DatasetConfigError(f"{context}: missing required key '{key}'.")
    return mapping[key]


def parse_config(config_path: str) -> DatasetConfig:
    """Parses and validates a dataset YAML config."""
    if not os.path.exists(config_path):
        raise DatasetConfigError(f"Dataset config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise DatasetConfigError(f"{config_path}: top level must be a mapping.")

    # Config paths are relative to the repository root (two levels above configs/datasets).
    config_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(config_path))))

    files = _require(raw, "files", config_path)
    main = _require(files, "main", f"{config_path}:files")

    column_map = {}
    for canonical, source_key in (
        (schema.ENTITY_ID, "entity_id"),
        (schema.ITEM_ID, "item_id"),
        (schema.DATE, "date"),
        (schema.TARGET, "target"),
    ):
        column_map[canonical] = _require(main, source_key, f"{config_path}:files.main")

    for canonical, source_key in ((schema.PROMO, "promo"), (schema.PRICE, "price")):
        if source_key in main and main[source_key]:
            column_map[canonical] = main[source_key]

    exogenous = [
        _parse_exogenous(spec, config_path) for spec in (raw.get("exogenous") or [])
    ]

    names = [e.name for e in exogenous]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        raise DatasetConfigError(f"{config_path}: duplicate exogenous feature name(s): {sorted(duplicates)}")

    return DatasetConfig(
        name=_require(raw, "name", config_path),
        grain=raw.get("grain", "daily"),
        main_path=_require(main, "path", f"{config_path}:files.main"),
        column_map=column_map,
        config_dir=config_dir,
        entity_meta=files.get("entity_meta"),
        exogenous=exogenous,
        closures=list(raw.get("closures") or []),
        promo_known_in_advance=bool(raw.get("promo_known_in_advance", False)),
        permanent_zero_min_history=int(
            raw.get("permanent_zero_min_history", DEFAULT_PERMANENT_ZERO_MIN_HISTORY)
        ),
    )


def _parse_exogenous(spec: Dict[str, Any], config_path: str) -> ExogenousSpec:
    context = f"{config_path}:exogenous"
    kind = _require(spec, "kind", context)
    name = _require(spec, "name", context)

    if kind not in SUPPORTED_EXOGENOUS_KINDS:
        raise DatasetConfigError(
            f"{context}[{name}]: unsupported kind {kind!r}. "
            f"Supported: {sorted(SUPPORTED_EXOGENOUS_KINDS)}"
        )

    if kind == "global_series":
        transform = spec.get("transform", "none")
        if transform not in SUPPORTED_TRANSFORMS:
            raise DatasetConfigError(
                f"{context}[{name}]: unsupported transform {transform!r}. "
                f"Supported: {sorted(SUPPORTED_TRANSFORMS)}"
            )
        return ExogenousSpec(
            kind=kind,
            name=name,
            path=_require(spec, "path", f"{context}[{name}]"),
            date_col=_require(spec, "date_col", f"{context}[{name}]"),
            value_col=_require(spec, "value_col", f"{context}[{name}]"),
            transform=transform,
        )

    if kind == "calendar_flag":
        days = _require(spec, "days_of_month", f"{context}[{name}]")
        if not isinstance(days, list) or not days:
            raise DatasetConfigError(f"{context}[{name}]: days_of_month must be a non-empty list.")
        invalid = [d for d in days if not isinstance(d, int) or not 1 <= d <= 31]
        if invalid:
            raise DatasetConfigError(f"{context}[{name}]: invalid days_of_month entries: {invalid}")
        return ExogenousSpec(kind=kind, name=name, days_of_month=list(days))

    # event_decay
    half_life = float(_require(spec, "half_life", f"{context}[{name}]"))
    if half_life <= 0:
        raise DatasetConfigError(f"{context}[{name}]: half_life must be positive.")
    return ExogenousSpec(
        kind=kind,
        name=name,
        event_date=str(_require(spec, "event_date", f"{context}[{name}]")),
        decay_days=int(_require(spec, "decay_days", f"{context}[{name}]")),
        half_life=half_life,
    )


class DatasetAdapter:
    """Loads a dataset described by a YAML config into the canonical schema."""

    @staticmethod
    def load(config_path: str) -> Tuple[pd.DataFrame, DatasetProfile]:
        """
        Loads and normalises a dataset.

        Returns (canonical_frame, profile). The frame carries exactly the canonical
        columns plus any entity metadata columns declared in the config; exogenous
        features are NOT merged here — they are computed per target date by the feature
        builder, because their legality depends on the forecast horizon.
        """
        config = parse_config(config_path)
        df = DatasetAdapter._load_main(config)
        df = DatasetAdapter._attach_entity_meta(df, config)

        schema.validate_canonical(df, dataset_name=config.name)

        available_exog = DatasetAdapter.available_exogenous(config)

        profile = build_dataset_profile(
            df,
            dataset_name=config.name,
            grain=config.grain,
            declared_exogenous=[e.name for e in config.exogenous],
            available_exogenous=available_exog,
            promo_known_in_advance=config.promo_known_in_advance,
            closures=config.closures,
            permanent_zero_min_history=config.permanent_zero_min_history,
        )

        logger.info(
            "Loaded %s: %s rows, %s series (%s entities x %s items), %s..%s. "
            "Optional columns: %s. Exogenous available: %s. Permanent-zero series: %s.",
            config.name, f"{profile.n_rows:,}", profile.n_series, profile.n_entities,
            profile.n_items, profile.date_min.date(), profile.date_max.date(),
            profile.optional_columns or "none", available_exog or "none",
            len(profile.permanent_zero_series),
        )

        return df, profile

    # --- loading -----------------------------------------------------------------

    @staticmethod
    def _load_main(config: DatasetConfig) -> pd.DataFrame:
        path = config.resolve(config.main_path)
        if not os.path.exists(path):
            raise DatasetConfigError(
                f"[{config.name}] main data file not found: {path}\n"
                f"Declared as files.main.path = {config.main_path!r}. "
                f"Large CSVs are gitignored; place the file before loading."
            )

        source_to_canonical = {src: canon for canon, src in config.column_map.items()}
        raw = pd.read_csv(path, usecols=list(source_to_canonical.keys()))

        missing = [c for c in source_to_canonical if c not in raw.columns]
        if missing:
            raise DatasetConfigError(
                f"[{config.name}] {path} lacks column(s) named in the config: {missing}. "
                f"Found: {sorted(raw.columns)}"
            )

        df = raw.rename(columns=source_to_canonical)
        df[schema.DATE] = pd.to_datetime(df[schema.DATE], errors="raise")
        df[schema.TARGET] = pd.to_numeric(df[schema.TARGET], errors="raise").astype("float64")

        for optional in (schema.PROMO, schema.PRICE):
            if optional in df.columns:
                df[optional] = pd.to_numeric(df[optional], errors="coerce").astype("float64")

        df = schema.coerce_identifier_columns(df)
        return df.sort_values(schema.SERIES_KEY + [schema.DATE]).reset_index(drop=True)

    @staticmethod
    def _attach_entity_meta(df: pd.DataFrame, config: DatasetConfig) -> pd.DataFrame:
        """
        Merges optional entity metadata (city, cluster, type, ...) if declared.

        These become ordinary categorical features. Nothing downstream may hardcode their
        values — 'Sierra' is a value in a column, not a branch in the code.
        """
        meta = config.entity_meta
        if not meta:
            return df

        path = config.resolve(_require(meta, "path", f"[{config.name}] files.entity_meta"))
        if not os.path.exists(path):
            logger.warning(
                "[%s] entity_meta file not found (%s); continuing without entity metadata.",
                config.name, path
            )
            return df

        join_on = _require(meta, "join_on", f"[{config.name}] files.entity_meta")
        columns = list(meta.get("columns") or [])

        meta_df = pd.read_csv(path, usecols=[join_on] + columns)
        meta_df[join_on] = meta_df[join_on].astype(str)
        meta_df = meta_df.rename(columns={join_on: schema.ENTITY_ID})

        # Namespace metadata columns so they can never collide with canonical names.
        meta_df = meta_df.rename(columns={c: f"entity_{c}" for c in columns})

        return df.merge(meta_df, on=schema.ENTITY_ID, how="left")

    # --- exogenous ---------------------------------------------------------------

    @staticmethod
    def available_exogenous(config: DatasetConfig) -> List[str]:
        """
        Names of declared exogenous features that can actually be materialised.

        Calendar flags and event decays are always available — they are computed from the
        date alone. A global series is available only if its file exists.
        """
        available = []
        for spec in config.exogenous:
            if spec.kind == "global_series":
                path = config.resolve(spec.path)
                if not os.path.exists(path):
                    logger.warning(
                        "[%s] exogenous %r declared but source missing (%s); "
                        "it will not be emitted as a feature.",
                        config.name, spec.name, path
                    )
                    continue
            available.append(spec.name)
        return available

    @staticmethod
    def load_global_series(config: DatasetConfig, spec: ExogenousSpec) -> pd.Series:
        """
        Loads a global (dataset-wide) exogenous series, indexed by date.

        `first_difference` exists because the raw level of a macro series is usually
        spuriously correlated with any trending target. Differencing removes the shared
        trend and keeps the shocks.

        Gaps are forward-filled after interpolation: a market that is closed on Sunday has
        the same price it had on Friday, which is a defensible reading. The value is NOT
        back-filled beyond the first observation into dates that predate the series.
        """
        path = config.resolve(spec.path)
        raw = pd.read_csv(path, usecols=[spec.date_col, spec.value_col])
        raw[spec.date_col] = pd.to_datetime(raw[spec.date_col], errors="raise")
        raw = raw.sort_values(spec.date_col).set_index(spec.date_col)

        values = pd.to_numeric(raw[spec.value_col], errors="coerce")
        values = values.interpolate(method="linear").ffill()

        if spec.transform == "first_difference":
            values = values.diff()
        elif spec.transform == "log":
            values = np.log(values.where(values > 0))
        elif spec.transform == "pct_change":
            values = values.pct_change()

        return values.rename(spec.name)
