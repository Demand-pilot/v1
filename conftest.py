"""
Pytest configuration: PYTHONPATH root registration and an isolated test database.

The database path is set BEFORE any `src.*` import, because
`src.orchestration.db.database` reads `SQLITE_DB_PATH` at module import time and
`src.orchestration.main` constructs a `DatabaseRepository` at import time. Tests
therefore run against a throwaway database seeded with genuine reference metadata
(stores, category economics, SEED_EXAMPLE knowledge docs) and, deliberately, an empty
`forecast_facts` table — because no model has been trained yet.

Tests assert the empty-state behaviour that follows from that. They must not be made to
pass by seeding fake forecasts.
"""

import os
import sys
import tempfile

# Register workspace root in sys.path
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Isolate the test database from any developer database in the working directory.
_test_db_dir = tempfile.mkdtemp(prefix="demandpilot_test_")
os.environ["SQLITE_DB_PATH"] = os.path.join(_test_db_dir, "demandpilot_test.db")

# Keep Redis off in tests: the client is opt-in, and an accidental connect attempt to a
# dead port cost ~48s per construction on Windows.
os.environ.setdefault("REDIS_ENABLED", "false")


import pytest


@pytest.fixture(autouse=True)
def _clear_forecast_cache():
    """
    Clears the process-wide forecast cache between tests.

    `_in_memory_fallback_cache` is module-level state. Without this, a test that primes
    the cache (e.g. the latency SLA test) makes a later test see a cache hit for a series
    that has no persisted forecast, so an empty-state assertion silently passes as
    "success" on stale data.
    """
    from src.orchestration.cache.redis_client import _in_memory_fallback_cache
    _in_memory_fallback_cache.clear()
    yield
    _in_memory_fallback_cache.clear()


def pytest_configure(config):
    """Seeds reference metadata into the isolated test database once, before collection."""
    from scripts.generate_future_horizon_forecasts import (
        initialize_database,
        seed_store_metadata,
        seed_category_economics,
        seed_store_knowledge_docs,
    )
    import scripts.generate_future_horizon_forecasts as seeder

    seeder.DB_PATH = os.environ["SQLITE_DB_PATH"]
    initialize_database()
    seed_store_metadata()
    seed_category_economics()
    seed_store_knowledge_docs()
