"""Redis client and connection manager for workers."""

import json
import logging
import os
import sys
from typing import Any, Optional

import redis
from redis import ConnectionPool

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from backend.app.core.config import settings
    REDIS_URL = settings.redis_url
    MAX_CONNECTIONS = settings.redis_max_connections
    DECODE_RESPONSES = settings.redis_decode_responses
except ImportError:
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
    DECODE_RESPONSES = os.getenv("REDIS_DECODE_RESPONSES", "true").lower() == "true"

logger = logging.getLogger(__name__)


class RedisConnectionManager:
    """Redis connection pool manager."""

    _instance: Optional["RedisConnectionManager"] = None
    _pool: Optional[ConnectionPool] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls):
        """Singleton pattern for connection pool."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Redis connection pool."""
        if self._pool is None:
            try:
                self._pool = ConnectionPool.from_url(
                    REDIS_URL,
                    max_connections=MAX_CONNECTIONS,
                    decode_responses=DECODE_RESPONSES,
                )
                self._client = redis.Redis(connection_pool=self._pool)
                self._client.ping()
                logger.info("Redis connection pool initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Redis connection pool: {e}")
                raise

    @property
    def client(self) -> redis.Redis:
        """Get Redis client from pool.

        Returns:
            Redis client instance.
        """
        if self._client is None:
            raise RuntimeError("Redis client not initialized")
        return self._client

    def close(self) -> None:
        """Close Redis connection pool."""
        if self._pool:
            self._pool.disconnect()
            logger.info("Redis connection pool closed")


def get_redis_client() -> redis.Redis:
    """Get Redis client instance.

    Returns:
        Redis client from connection pool.
    """
    manager = RedisConnectionManager()
    return manager.client


def set_json(client: redis.Redis, key: str, value: Any, ex: Optional[int] = None) -> bool:
    """Set a JSON value in Redis.

    Args:
        client: Redis client.
        key: Redis key.
        value: Value to store (will be JSON encoded).
        ex: Optional expiration time in seconds.

    Returns:
        True if successful.
    """
    try:
        serialized = json.dumps(value)
        return client.set(key, serialized, ex=ex)
    except Exception as e:
        logger.error(f"Failed to set JSON key {key}: {e}")
        return False


def get_json(client: redis.Redis, key: str) -> Optional[Any]:
    """Get a JSON value from Redis.

    Args:
        client: Redis client.
        key: Redis key.

    Returns:
        Deserialized value or None if not found.
    """
    try:
        value = client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as e:
        logger.error(f"Failed to get JSON key {key}: {e}")
        return None

