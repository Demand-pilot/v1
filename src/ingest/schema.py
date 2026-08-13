"""
Canonical demand-forecasting schema.

Every dataset — Favorita included — is normalised to these column names before any
feature, model, or serving code sees it. Favorita is one dataset among many, not the
shape of the world: nothing downstream may refer to `store_nbr`, `family`, `sales`,
`onpromotion`, oil, earthquakes, or Ecuadorian paydays.

Required
    entity_id : str      store / location / warehouse
    item_id   : str      product / family / SKU
    date      : datetime daily grain
    target    : float    units sold, the forecast target

Optional (presence is recorded in DatasetProfile; features are gated on it)
    promo     : float    promotional intensity or count
    price     : float

Entity and item identifiers are strings by design. They are labels, not quantities:
Favorita's integer `store_nbr` supports no arithmetic that means anything, and keeping it
numeric invites a model to treat store 52 as "twice" store 26.
"""

from typing import Dict, List, Optional

import pandas as pd

ENTITY_ID = "entity_id"
ITEM_ID = "item_id"
DATE = "date"
TARGET = "target"

PROMO = "promo"
PRICE = "price"

REQUIRED_COLUMNS: List[str] = [ENTITY_ID, ITEM_ID, DATE, TARGET]
OPTIONAL_COLUMNS: List[str] = [PROMO, PRICE]

# The key identifying one time series.
SERIES_KEY: List[str] = [ENTITY_ID, ITEM_ID]


class SchemaValidationError(ValueError):
    """
    Raised when a frame does not conform to the canonical schema.

    Validation failures are loud. A frame that is silently coerced into shape produces a
    model that trains on something other than what the operator believes it trained on.
    """


def validate_canonical(df: pd.DataFrame, *, dataset_name: str = "<unnamed>") -> None:
    """
    Validates a canonical frame, raising SchemaValidationError with an actionable message.

    Checks, in order: required columns present, dtypes usable, target numeric and
    non-negative, no duplicate (entity, item, date), no null keys.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaValidationError(
            f"[{dataset_name}] missing required canonical column(s): {missing}. "
            f"Present: {sorted(df.columns)}. "
            f"Map them in the dataset config under files.main."
        )

    if df.empty:
        raise SchemaValidationError(f"[{dataset_name}] contains no rows.")

    if not pd.api.types.is_datetime64_any_dtype(df[DATE]):
        raise SchemaValidationError(
            f"[{dataset_name}] '{DATE}' must be datetime64, got {df[DATE].dtype}."
        )

    if not pd.api.types.is_numeric_dtype(df[TARGET]):
        raise SchemaValidationError(
            f"[{dataset_name}] '{TARGET}' must be numeric, got {df[TARGET].dtype}."
        )

    for key in (ENTITY_ID, ITEM_ID, DATE):
        n_null = int(df[key].isna().sum())
        if n_null:
            raise SchemaValidationError(
                f"[{dataset_name}] '{key}' has {n_null:,} null value(s); keys must be complete."
            )

    n_null_target = int(df[TARGET].isna().sum())
    if n_null_target:
        raise SchemaValidationError(
            f"[{dataset_name}] '{TARGET}' has {n_null_target:,} null value(s). "
            f"A missing observation is not a zero sale; resolve it in the source data or "
            f"declare the gap policy in the dataset config."
        )

    n_negative = int((df[TARGET] < 0).sum())
    if n_negative:
        raise SchemaValidationError(
            f"[{dataset_name}] '{TARGET}' has {n_negative:,} negative value(s). "
            f"Unit demand cannot be negative; check the column mapping."
        )

    duplicated = df.duplicated(subset=[ENTITY_ID, ITEM_ID, DATE])
    n_dupes = int(duplicated.sum())
    if n_dupes:
        sample = df.loc[duplicated, [ENTITY_ID, ITEM_ID, DATE]].head(3).to_dict("records")
        raise SchemaValidationError(
            f"[{dataset_name}] has {n_dupes:,} duplicate (entity_id, item_id, date) row(s). "
            f"The grain must be one row per series per day. Examples: {sample}"
        )


def present_optional_columns(df: pd.DataFrame) -> List[str]:
    """Returns the optional canonical columns actually present and non-null in `df`."""
    present = []
    for col in OPTIONAL_COLUMNS:
        if col in df.columns and not df[col].isna().all():
            present.append(col)
    return present


def coerce_identifier_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Casts entity/item identifiers to string, preserving them as labels."""
    out = df.copy()
    for key in (ENTITY_ID, ITEM_ID):
        if key in out.columns:
            out[key] = out[key].astype(str)
    return out
