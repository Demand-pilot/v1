"""
Redis 7 caching protocol client for DemandPilot Layer 2.
Ensures forecast grid sub-15ms response SLA.
"""

import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("demandpilot.redis")

# In-memory fallback cache for development/testing when Redis server is offline
_in_memory_fallback_cache: Dict[str, str] = {}


class RedisForecastCache:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self.redis_conn = None
        self._connected = False
        self._init_redis()

    def _init_redis(self):
        try:
            import redis
            self.redis_conn = redis.Redis(
                host=self.host, port=self.port, db=self.db, socket_timeout=1.0
            )
            # Test ping
            self.redis_conn.ping()
            self._connected = True
            logger.info("Connected to Redis 7 server successfully.")
        except Exception as e:
            logger.warning(f"Redis connection unavailable ({e}). Using fast in-memory fallback cache.")
            self._connected = False

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
