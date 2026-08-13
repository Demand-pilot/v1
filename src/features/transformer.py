"""
Feature construction, split into CORE and OPTIONAL.

CORE features are computable from the canonical schema alone: calendar arithmetic on the
date, lags and rolling statistics of the target, and categorical codes for the entity and
item. Nothing in CORE may reference oil, earthquakes, paydays, Ecuador, or a specific
store number. A dataset with four columns and nothing else gets a full CORE matrix.

OPTIONAL features are emitted only when the DatasetProfile says their input exists:
promo, price, config-declared exogenous series, config-declared calendar flags, and
config-declared event decays. A dataset without promo simply has no promo columns — it
does not have promo columns full of zeros, which a model cannot distinguish from "never
on promotion".

Horizon safety
--------------
Every target-derived feature takes `min_lag_offset`, which callers set to the forecast
horizon H. A lag of H or more, and a rolling window shifted by H, are knowable at the
cutoff for every h in 1..H. The previous implementation built `lag_1` and
`rolling_mean_7d` over the whole frame and then sliced by cutoff, so a 16-day forecast
was reading values from up to 15 days after the cutoff. See docs/LEAKAGE_POLICY.md.

Calendar features are computed for the TARGET date, which is legitimate: the day of week
of a date three weeks out is known today.
"""

import logging
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from src.ingest import schema
from src.ingest.adapter import DatasetConfig, DatasetAdapter, ExogenousSpec
from src.ingest.profile import DatasetProfile

logger = logging.getLogger("demandpilot.features")

# Sentinel code for an entity or item absent from the training vocabulary. Inference must
# detect this and route to the cold-start policy rather than letting the model bin an
# unseen category alongside a seen one.
UNKNOWN_CATEGORY_CODE = -1


class CoreFeatureBuilder:
    """Features computable from (entity_id, item_id, date, target) alone."""

    CALENDAR_FEATURES: List[str] = [
        "dayofweek",
        "day",
        "month",
        "weekofyear",
        "is_month_start",
        "is_month_end",
    ]

    @staticmethod
    def calendar(dates: pd.Series) -> pd.DataFrame:
        """
        Calendar features for the given dates.

        Computed for the target date, not the cutoff. These are deterministic properties
        of the calendar and are known arbitrarily far in advance.
        """
        d = pd.to_datetime(pd.Series(dates).reset_index(drop=True))
        return pd.DataFrame({
            "dayofweek": d.dt.dayofweek.astype("int16"),
            "day": d.dt.day.astype("int16"),
            "month": d.dt.month.astype("int16"),
            "weekofyear": d.dt.isocalendar().week.astype("int16"),
            "is_month_start": d.dt.is_month_start.astype("int8"),
            "is_month_end": d.dt.is_month_end.astype("int8"),
        })

    @staticmethod
    def lag_and_rolling(
        df: pd.DataFrame,
        *,
        min_lag_offset: int,
        lags: Optional[Sequence[int]] = None,
        windows: Optional[Sequence[int]] = None,
        target_col: str = schema.TARGET,
    ) -> pd.DataFrame:
        """
        Lags and rolling statistics of the target, all offset by at least `min_lag_offset`.

        Returns a frame aligned to `df`'s index, containing only the new columns.

        NaNs are left in place. A missing lag means "this series has no observation that
        far back", which is not zero demand. The previous implementation called
        `.fillna(0.0)` on every lag and rolling column, teaching the model that every
        series begins with a run of zero-demand days.
        """
        if min_lag_offset < 1:
            raise ValueError(f"min_lag_offset must be >= 1, got {min_lag_offset}")

        lags = list(lags) if lags is not None else [
            min_lag_offset,
            min_lag_offset + 5,
            min_lag_offset + 12,
            min_lag_offset + 19,
        ]
        windows = list(windows) if windows is not None else [min_lag_offset, 28, 56]

        illegal = [lag for lag in lags if lag < min_lag_offset]
        if illegal:
            raise ValueError(
                f"Lags {illegal} are shorter than the horizon offset {min_lag_offset}; "
                f"they are not knowable at the cutoff for every horizon day. "
                f"See docs/LEAKAGE_POLICY.md."
            )

        ordered = df.sort_values(schema.SERIES_KEY + [schema.DATE])
        grouped = ordered.groupby(schema.SERIES_KEY, observed=True)[target_col]

        out = pd.DataFrame(index=ordered.index)

        for lag in lags:
            out[f"lag_{lag}"] = grouped.shift(lag)

        for window in windows:
            shifted = grouped.shift(min_lag_offset)
            by_series = shifted.groupby(
                [ordered[schema.ENTITY_ID], ordered[schema.ITEM_ID]], observed=True
            )
            out[f"rolling_mean_{window}d"] = by_series.transform(
                lambda s, w=window: s.rolling(w, min_periods=max(2, w // 4)).mean()
            )
            if window >= 28:
                out[f"rolling_std_{window}d"] = by_series.transform(
                    lambda s, w=window: s.rolling(w, min_periods=max(2, w // 4)).std()
                )

        # Zero ratio over a shifted window: how intermittent this series has been.
        shifted = grouped.shift(min_lag_offset)
        is_zero = (shifted <= 1e-9).astype("float64").where(shifted.notna())
        out["zero_ratio_56d"] = is_zero.groupby(
            [ordered[schema.ENTITY_ID], ordered[schema.ITEM_ID]], observed=True
        ).transform(lambda s: s.rolling(56, min_periods=14).mean())

        return out.reindex(df.index)

    @staticmethod
    def identifiers(
        df: pd.DataFrame,
        *,
        entity_vocabulary: Sequence[str],
        item_vocabulary: Sequence[str],
    ) -> pd.DataFrame:
        """
        Integer codes for entity and item, against a FIXED vocabulary.

        The vocabulary is captured at training time and reused at inference. The previous
        engine called `.cat.codes` independently in `fit()` and in `predict()`, so the
        code assigned to a given store depended on which rows happened to be in the frame
        — training and inference could disagree about which store was which, silently.

        Unseen categories get UNKNOWN_CATEGORY_CODE so the caller can detect them.
        """
        entity_index = {value: idx for idx, value in enumerate(entity_vocabulary)}
        item_index = {value: idx for idx, value in enumerate(item_vocabulary)}

        return pd.DataFrame({
            "entity_code": df[schema.ENTITY_ID].map(entity_index)
                .fillna(UNKNOWN_CATEGORY_CODE).astype("int32").to_numpy(),
            "item_code": df[schema.ITEM_ID].map(item_index)
                .fillna(UNKNOWN_CATEGORY_CODE).astype("int32").to_numpy(),
        }, index=df.index)

    @staticmethod
    def horizon_day(values: Sequence[int], index: pd.Index) -> pd.DataFrame:
        """Explicit horizon-day feature (1..H) for a direct multi-horizon model."""
        return pd.DataFrame({"horizon_day": np.asarray(values, dtype="int16")}, index=index)


class OptionalFeatureBuilder:
    """Features emitted only when the DatasetProfile confirms their input exists."""

    @staticmethod
    def promo(
        df: pd.DataFrame,
        *,
        min_lag_offset: int,
        known_in_advance: bool,
    ) -> pd.DataFrame:
        """
        Promotional features.

        When the dataset config declares `promo_known_in_advance: true`, the promo value
        for the target date is legal, because it comes from a published schedule. When it
        does not, only lagged promo is legal — the same horizon rule as the target.
        """
        ordered = df.sort_values(schema.SERIES_KEY + [schema.DATE])
        grouped = ordered.groupby(schema.SERIES_KEY, observed=True)[schema.PROMO]

        out = pd.DataFrame(index=ordered.index)

        if known_in_advance:
            out["promo"] = ordered[schema.PROMO]

        out[f"promo_lag_{min_lag_offset}"] = grouped.shift(min_lag_offset)
        out["promo_rolling_mean_28d"] = grouped.shift(min_lag_offset).groupby(
            [ordered[schema.ENTITY_ID], ordered[schema.ITEM_ID]], observed=True
        ).transform(lambda s: s.rolling(28, min_periods=7).mean())

        return out.reindex(df.index)

    @staticmethod
    def price(df: pd.DataFrame, *, min_lag_offset: int) -> pd.DataFrame:
        """
        Price features.

        Price is treated as unknown in advance unless a dataset later declares otherwise,
        so only lagged price is emitted.
        """
        ordered = df.sort_values(schema.SERIES_KEY + [schema.DATE])
        grouped = ordered.groupby(schema.SERIES_KEY, observed=True)[schema.PRICE]
        out = pd.DataFrame(index=ordered.index)
        out[f"price_lag_{min_lag_offset}"] = grouped.shift(min_lag_offset)
        return out.reindex(df.index)

    @staticmethod
    def calendar_flag(dates: pd.Series, spec: ExogenousSpec) -> pd.Series:
        """A 0/1 flag for configured days of the month. Days come from config, not code."""
        d = pd.to_datetime(pd.Series(dates).reset_index(drop=True))
        return pd.Series(
            d.dt.day.isin(spec.days_of_month).astype("int8").to_numpy(),
            name=spec.name,
        )

    @staticmethod
    def event_decay(dates: pd.Series, spec: ExogenousSpec) -> pd.Series:
        """
        Exponential decay following a one-off event, truncated at `decay_days`.

        `half_life` is a genuine half-life: the multiplier is 0.5 ** (days / half_life),
        so it equals 0.5 exactly at `half_life` days. The previous hardcoded version
        computed exp(-days / 10.0) and described the 10 as a half-life; that expression's
        actual half-life is 10 * ln(2) ~= 6.93 days, so the feature decayed noticeably
        faster than the code claimed.
        """
        d = pd.to_datetime(pd.Series(dates).reset_index(drop=True))
        days_since = (d - pd.Timestamp(spec.event_date)).dt.days

        decay = np.where(
            (days_since >= 0) & (days_since <= spec.decay_days),
            np.power(0.5, days_since / spec.half_life),
            0.0,
        )
        return pd.Series(decay.astype("float64"), name=spec.name)

    @staticmethod
    def global_series(
        dates: pd.Series,
        series: pd.Series,
        name: str,
    ) -> pd.Series:
        """
        Aligns a dataset-wide exogenous series onto the given dates.

        Dates with no value in the source get NaN, not 0.0. Zero is a meaningful value for
        a differenced price series ("no change"), so imputing it would assert something
        false.
        """
        d = pd.to_datetime(pd.Series(dates).reset_index(drop=True))
        aligned = d.map(series)
        return pd.Series(aligned.to_numpy(dtype="float64"), name=name)


class FeatureBuilder:
    """
    Assembles CORE + OPTIONAL features for a dataset, gated on its profile.

    Usage:
        builder = FeatureBuilder(config, profile, horizon=16)
        features = builder.build(df)
    """

    def __init__(
        self,
        config: DatasetConfig,
        profile: DatasetProfile,
        *,
        horizon: int,
    ):
        self.config = config
        self.profile = profile
        self.horizon = int(horizon)
        if self.horizon < 1:
            raise ValueError(f"horizon must be >= 1, got {horizon}")

        self._global_series_cache: Dict[str, pd.Series] = {}

    # --- public ------------------------------------------------------------------

    def build(
        self,
        df: pd.DataFrame,
        *,
        target_dates: Optional[pd.Series] = None,
        horizon_days: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """
        Builds the feature matrix.

        Args:
            df: canonical frame carrying the history used for lags.
            target_dates: dates the features describe. Defaults to `df[date]`, which is
                the training-matrix case. At inference these are the future dates.
            horizon_days: horizon index per row, emitted as an explicit feature.

        Returns a frame aligned to `df.index`. NaNs are preserved; call
        `drop_rows_without_history` before fitting.
        """
        dates = pd.Series(target_dates if target_dates is not None else df[schema.DATE])
        dates.index = df.index

        blocks: List[pd.DataFrame] = []

        calendar = CoreFeatureBuilder.calendar(dates)
        calendar.index = df.index
        blocks.append(calendar)

        blocks.append(
            CoreFeatureBuilder.lag_and_rolling(df, min_lag_offset=self.horizon)
        )
        blocks.append(
            CoreFeatureBuilder.identifiers(
                df,
                entity_vocabulary=self.profile.entity_vocabulary,
                item_vocabulary=self.profile.item_vocabulary,
            )
        )

        if horizon_days is not None:
            blocks.append(CoreFeatureBuilder.horizon_day(horizon_days, df.index))

        blocks.extend(self._optional_blocks(df, dates))

        features = pd.concat(blocks, axis=1)
        return features

    def feature_names(self) -> List[str]:
        """Ordered feature names this builder will emit, for schema capture."""
        names = list(CoreFeatureBuilder.CALENDAR_FEATURES)
        probe = CoreFeatureBuilder.lag_and_rolling(
            self._probe_frame(), min_lag_offset=self.horizon
        )
        names.extend(probe.columns)
        names.extend(["entity_code", "item_code"])
        return names

    @staticmethod
    def drop_rows_without_history(
        features: pd.DataFrame,
        *others: pd.Series,
    ):
        """
        Drops rows whose features are incomplete, instead of imputing them.

        Returns (features, *others) filtered to the same rows. A row lacking a lag has no
        usable history; training on an imputed zero teaches the model a fact about the
        data that is not true.
        """
        keep = features.notna().all(axis=1)
        filtered_others = tuple(other[keep.to_numpy()] for other in others)
        return (features[keep], *filtered_others) if filtered_others else features[keep]

    # --- internals ---------------------------------------------------------------

    def _optional_blocks(self, df: pd.DataFrame, dates: pd.Series) -> List[pd.DataFrame]:
        blocks: List[pd.DataFrame] = []

        if self.profile.has_promo:
            blocks.append(
                OptionalFeatureBuilder.promo(
                    df,
                    min_lag_offset=self.horizon,
                    known_in_advance=self.profile.promo_known_in_advance,
                )
            )

        if self.profile.has_price:
            blocks.append(OptionalFeatureBuilder.price(df, min_lag_offset=self.horizon))

        for spec in self.config.exogenous:
            if not self.profile.has_exogenous(spec.name):
                continue

            if spec.kind == "calendar_flag":
                series = OptionalFeatureBuilder.calendar_flag(dates, spec)
            elif spec.kind == "event_decay":
                series = OptionalFeatureBuilder.event_decay(dates, spec)
            elif spec.kind == "global_series":
                series = OptionalFeatureBuilder.global_series(
                    dates, self._global_series(spec), spec.name
                )
            else:
                continue

            series.index = df.index
            blocks.append(series.to_frame())

        return blocks

    def _global_series(self, spec: ExogenousSpec) -> pd.Series:
        if spec.name not in self._global_series_cache:
            self._global_series_cache[spec.name] = DatasetAdapter.load_global_series(
                self.config, spec
            )
        return self._global_series_cache[spec.name]

    def _probe_frame(self) -> pd.DataFrame:
        """Tiny frame used to enumerate generated lag/rolling column names."""
        return pd.DataFrame({
            schema.ENTITY_ID: ["a"],
            schema.ITEM_ID: ["b"],
            schema.DATE: [pd.Timestamp("2000-01-01")],
            schema.TARGET: [0.0],
        })
