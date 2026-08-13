"""
Redis caching client for DemandPilot Layer 2, with an in-memory fallback.

Connection behaviour:

`socket_timeout` bounds socket *reads*, not the TCP connect. With no
`socket_connect_timeout` set, constructing this class against a host where nothing is
listening blocked for ~48 seconds per instance on Windows. Because the API module, the
router, and 33 parametrized tests each construct one, the test suite never finished —
it was not hanging on a deadlock, it was serially waiting out connect timeouts.

Redis is therefore opt-in (`REDIS_ENABLED`), the connect timeout is bounded, and a failed
connection is attempted once and then remembered, so the penalty is paid at most once per
process rather than once per instantiation.
"""

import json
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger("demandpilot.redis")

# In-memory fallback cache for development/testing when Redis is disabled or offline.
_in_memory_fallback_cache: Dict[str, str] = {}

# Process-wide latch: once a connection attempt has failed, later instances skip it.
_redis_unavailable = False


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class RedisForecastCache:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: int = 0,
        connect_timeout: float = 0.25,
    ):
        self.host = host or os.environ.get("REDIS_HOST", "localhost")
        self.port = int(port or os.environ.get("REDIS_PORT", 6379))
        self.db = db
        self.connect_timeout = float(
            os.environ.get("REDIS_CONNECT_TIMEOUT", connect_timeout)
        )
        self.redis_conn = None
        self._connected = False
        self._init_redis()

    def _init_redis(self):
        global _redis_unavailable

        if not _env_flag("REDIS_ENABLED", False):
            logger.debug("REDIS_ENABLED is not set; using in-memory cache.")
            return

        if _redis_unavailable:
            logger.debug("Redis already known unavailable in this process; skipping connect.")
            return

        try:
            import redis
            self.redis_conn = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                socket_timeout=1.0,
                socket_connect_timeout=self.connect_timeout,
            )
            self.redis_conn.ping()
            self._connected = True
            logger.info("Connected to Redis at %s:%s.", self.host, self.port)
        except Exception as e:
            _redis_unavailable = True
            self.redis_conn = None
            logger.warning(
                "Redis unavailable at %s:%s (%s). Using in-memory cache for this process.",
                self.host, self.port, e
            )

    def get_forecast(self, store_nbr: int, family: str) -> Optional[Dict[str, Any]]:
        """Retrieve pre-computed 16-day forecast record. Response SLA < 15ms."""
        cache_key = f"demandpilot:forecast:{store_nbr}:{family}"
        try:
            if self._connected and self.redis_conn:
                cached_data = self.redis_conn.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            elif cache_key in _in_memory_fallback_cache:
                return json.loads(_in_memory_fallback_cache[cache_key])
        except Exception as err:
            logger.error(f"Error reading from cache: {err}")
        return None

    def set_forecast(self, store_nbr: int, family: str, record: Dict[str, Any], ttl_seconds: int = 86400) -> bool:
        """Cache pre-computed 16-day forecast record with 24h TTL."""
        cache_key = f"demandpilot:forecast:{store_nbr}:{family}"
        serialized = json.dumps(record)
        try:
            if self._connected and self.redis_conn:
                self.redis_conn.setex(cache_key, ttl_seconds, serialized)
                return True
            else:
                _in_memory_fallback_cache[cache_key] = serialized
                return True
        except Exception as err:
            logger.error(f"Error writing to cache: {err}")
            return False

    def clear(self):
        """Clear cache."""
        if self._connected and self.redis_conn:
            self.redis_conn.flushdb()
        _in_memory_fallback_cache.clear()
