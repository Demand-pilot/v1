"""
GATE 2: the pipeline must handle a dataset that has nothing but the required columns.

The fixture is 3 entities x 2 items x 400 days with no promo, no price, no oil, no
holidays, no entity metadata, and no closures. It is deliberately austere: anything the
feature builder needs beyond entity/item/date/target is a dependency on Favorita's shape,
and would mean the system is not dataset-agnostic.

The data is generated deterministically from a fixed seed. Seeding is the one legitimate
use of randomness (see tests/test_no_fabrication.py) — these are test inputs, not model
outputs presented as measurements.
"""

import os

import numpy as np
import pandas as pd
import pytest
import yaml

from src.features.transformer import (
    UNKNOWN_CATEGORY_CODE,
    CoreFeatureBuilder,
    FeatureBuilder,
)
from src.ingest import schema
from src.ingest.adapter import DatasetAdapter, DatasetConfigError, parse_config

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "configs", "datasets", "synthetic_minimal.yaml")

N_ENTITIES = 3
N_ITEMS = 2
N_DAYS = 400
HORIZON = 16

# Terms that would betray a Favorita-specific dependency leaking into generic code.
FAVORITA_SPECIFIC_TOKENS = [
    "oil", "earthquake", "payday", "sierra", "coast", "ecuador",
    "store_nbr", "family", "onpromotion", "sales", "dcoilwtico",
    "christmas", "holiday", "quito", "guayaquil",
]


@pytest.fixture(scope="module")
def synthetic_csv():
    """Writes the minimal CSV declared by configs/datasets/synthetic_minimal.yaml."""
    config = parse_config(CONFIG_PATH)
    path = config.resolve(config.main_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    rng = np.random.default_rng(20260814)
    dates = pd.date_range("2023-01-01", periods=N_DAYS, freq="D")

    rows = []
    for entity in range(N_ENTITIES):
        for item in range(N_ITEMS):
            level = 40.0 + 25.0 * entity + 10.0 * item
            weekly = 1.0 + 0.20 * np.sin(np.arange(N_DAYS) * 2 * np.pi / 7.0)
            noise = rng.normal(0.0, 3.0, N_DAYS)
            units = np.clip(level * weekly + noise, 0.0, None).round(2)

            rows.append(pd.DataFrame({
                "location": f"L{entity}",
                "sku": f"S{item}",
                "day": dates,
                "units": units,
            }))

    pd.concat(rows, ignore_index=True).to_csv(path, index=False)
    yield path

    if os.path.exists(path):
        os.remove(path)


def test_minimal_dataset_loads_through_adapter(synthetic_csv):
    """A four-column CSV loads to the canonical schema with a measured profile."""
    df, profile = DatasetAdapter.load(CONFIG_PATH)

    assert list(schema.REQUIRED_COLUMNS) == [c for c in schema.REQUIRED_COLUMNS if c in df.columns]
    assert len(df) == N_ENTITIES * N_ITEMS * N_DAYS
    assert profile.n_entities == N_ENTITIES
    assert profile.n_items == N_ITEMS
    assert profile.n_series == N_ENTITIES * N_ITEMS
    assert profile.n_days_spanned == N_DAYS

    # Nothing optional is present, and nothing is invented to fill the gap.
    assert profile.optional_columns == []
    assert profile.available_exogenous == []
    assert profile.declared_exogenous == []
    assert profile.has_promo is False
    assert profile.promo_known_in_advance is False
    assert profile.closures == []

    # Identifiers are labels, not numbers.
    assert df[schema.ENTITY_ID].dtype == object
    assert set(profile.entity_vocabulary) == {"L0", "L1", "L2"}


def test_feature_matrix_has_no_nans_and_no_dataset_specific_columns(synthetic_csv):
    """GATE 2: zero NaNs after dropping unusable rows, and zero Favorita-specific columns."""
    df, profile = DatasetAdapter.load(CONFIG_PATH)
    config = parse_config(CONFIG_PATH)

    builder = FeatureBuilder(config, profile, horizon=HORIZON)
    features = builder.build(df)

    features = FeatureBuilder.drop_rows_without_history(features)

    assert len(features) > 0, "Dropping incomplete rows must not empty the matrix."
    assert int(features.isna().sum().sum()) == 0, (
        "Feature matrix still contains NaNs:\n"
        f"{features.isna().sum()[features.isna().sum() > 0]}"
    )

    lowered = [c.lower() for c in features.columns]
    offenders = [
        col for col in lowered
        if any(token in col for token in FAVORITA_SPECIFIC_TOKENS)
    ]
    assert offenders == [], f"Dataset-specific columns leaked into CORE features: {offenders}"

    # CORE must actually be present, not merely free of contamination.
    for expected in CoreFeatureBuilder.CALENDAR_FEATURES + ["entity_code", "item_code"]:
        assert expected in features.columns


def test_all_target_features_respect_the_horizon(synthetic_csv):
    """Every emitted lag/rolling column is offset by at least the horizon."""
    df, profile = DatasetAdapter.load(CONFIG_PATH)
    config = parse_config(CONFIG_PATH)

    features = FeatureBuilder(config, profile, horizon=HORIZON).build(df)

    lag_columns = [c for c in features.columns if c.startswith("lag_")]
    assert lag_columns, "Expected lag features."
    for col in lag_columns:
        assert int(col.split("_")[1]) >= HORIZON, (
            f"{col} is shorter than the {HORIZON}-day horizon and is not knowable at cutoff."
        )


def test_shorter_lags_than_horizon_are_rejected(synthetic_csv):
    """Requesting a lag inside the horizon is an error, not a silent leak."""
    df, _ = DatasetAdapter.load(CONFIG_PATH)

    with pytest.raises(ValueError, match="shorter than the horizon offset"):
        CoreFeatureBuilder.lag_and_rolling(df, min_lag_offset=HORIZON, lags=[1, 7])


def test_unseen_categories_are_flagged_not_silently_binned(synthetic_csv):
    """An entity outside the training vocabulary gets the unknown code."""
    df, profile = DatasetAdapter.load(CONFIG_PATH)

    unseen = df.head(3).copy()
    unseen[schema.ENTITY_ID] = "L_NEVER_SEEN"

    codes = CoreFeatureBuilder.identifiers(
        unseen,
        entity_vocabulary=profile.entity_vocabulary,
        item_vocabulary=profile.item_vocabulary,
    )
    assert (codes["entity_code"] == UNKNOWN_CATEGORY_CODE).all()
    # A known item alongside an unknown entity still resolves correctly.
    assert (codes["item_code"] >= 0).all()


def test_categorical_codes_are_stable_across_frames(synthetic_csv):
    """
    The same entity maps to the same code regardless of which rows are present.

    This is the defect that made the old GBDT engine silently wrong: it called
    `.cat.codes` separately in fit() and predict(), so codes depended on frame contents.
    """
    df, profile = DatasetAdapter.load(CONFIG_PATH)

    full = CoreFeatureBuilder.identifiers(
        df, entity_vocabulary=profile.entity_vocabulary,
        item_vocabulary=profile.item_vocabulary,
    )
    subset_rows = df[df[schema.ENTITY_ID].isin(["L2"])]
    subset = CoreFeatureBuilder.identifiers(
        subset_rows, entity_vocabulary=profile.entity_vocabulary,
        item_vocabulary=profile.item_vocabulary,
    )

    expected = full.loc[subset_rows.index, "entity_code"].unique()
    assert set(subset["entity_code"].unique()) == set(expected)


def test_missing_data_file_fails_loudly(tmp_path):
    """A config naming an absent file raises, rather than yielding an empty frame."""
    config_dir = tmp_path / "configs" / "datasets"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "absent.yaml"
    config_file.write_text(yaml.safe_dump({
        "name": "absent_dataset",
        "grain": "daily",
        "files": {
            "main": {
                "path": "data/definitely_not_here.csv",
                "entity_id": "location",
                "item_id": "sku",
                "date": "day",
                "target": "units",
            }
        },
    }), encoding="utf-8")

    with pytest.raises(DatasetConfigError, match="main data file not found"):
        DatasetAdapter.load(str(config_file))


def test_duplicate_grain_is_rejected(tmp_path):
    """Two rows for the same (entity, item, date) is a schema error."""
    df = pd.DataFrame({
        schema.ENTITY_ID: ["a", "a"],
        schema.ITEM_ID: ["x", "x"],
        schema.DATE: pd.to_datetime(["2023-01-01", "2023-01-01"]),
        schema.TARGET: [1.0, 2.0],
    })
    with pytest.raises(schema.SchemaValidationError, match="duplicate"):
        schema.validate_canonical(df, dataset_name="dupes")


def test_negative_target_is_rejected():
    """Negative unit demand indicates a bad column mapping and must not pass silently."""
    df = pd.DataFrame({
        schema.ENTITY_ID: ["a"],
        schema.ITEM_ID: ["x"],
        schema.DATE: pd.to_datetime(["2023-01-01"]),
        schema.TARGET: [-5.0],
    })
    with pytest.raises(schema.SchemaValidationError, match="negative"):
        schema.validate_canonical(df, dataset_name="negatives")


def test_favorita_config_parses_and_isolates_ecuador():
    """
    The Favorita config parses, and every Ecuador-specific constant lives in it.

    This is the structural claim of Phase 2: Favorita is one config, not the universe.
    """
    config = parse_config(os.path.join(REPO_ROOT, "configs", "datasets", "favorita.yaml"))

    assert config.name == "favorita_ecuador"
    assert config.column_map[schema.TARGET] == "sales"
    assert config.column_map[schema.ENTITY_ID] == "store_nbr"
    assert config.promo_known_in_advance is True

    by_name = {e.name: e for e in config.exogenous}
    assert by_name["delta_oil"].transform == "first_difference"
    assert by_name["is_payday"].days_of_month == [15, 30, 31]
    assert by_name["earthquake_decay"].event_date == "2016-04-16"
    assert by_name["earthquake_decay"].half_life == 10

    # Store 25's New Year exemption is config, not an `if store_nbr == 25` in code.
    new_year = next(c for c in config.closures if c["month_day"] == "01-01")
    assert new_year["except"] == ["25"]


def test_event_decay_half_life_is_a_real_half_life():
    """
    At exactly `half_life` days the multiplier is 0.5.

    The previous hardcoded feature used exp(-days / 10.0) while calling the 10 a
    half-life; that expression is at 0.5 only at ~6.93 days.
    """
    from src.features.transformer import OptionalFeatureBuilder
    from src.ingest.adapter import ExogenousSpec

    spec = ExogenousSpec(
        kind="event_decay", name="quake_decay",
        event_date="2016-04-16", decay_days=30, half_life=10,
    )
    dates = pd.to_datetime(["2016-04-16", "2016-04-26", "2016-05-20"])
    decay = OptionalFeatureBuilder.event_decay(dates, spec)

    assert decay.iloc[0] == pytest.approx(1.0)
    assert decay.iloc[1] == pytest.approx(0.5)      # exactly one half-life
    assert decay.iloc[2] == 0.0                     # beyond decay_days
