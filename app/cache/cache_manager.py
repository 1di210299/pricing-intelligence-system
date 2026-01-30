"""Cache manager for market pricing data."""
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """
    Simple in-memory cache for market pricing data.
    
    Falls back to Redis if configured, otherwise uses dict.
    """
    
    def __init__(self):
        """Initialize cache manager."""
        self.use_redis = settings.use_redis
        self.ttl = settings.cache_ttl
        self.redis_client = None
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        
        if self.use_redis:
            try:
                import redis
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.warning(
                    f"Failed to connect to Redis: {str(e)}. "
                    "Falling back to memory cache."
                )
                self.use_redis = False
                self.redis_client = None
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if self.use_redis and self.redis_client:
            return self._get_from_redis(key)
        else:
            return self._get_from_memory(key)
    
    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        cache_ttl = ttl or self.ttl
        
        if self.use_redis and self.redis_client:
            self._set_in_redis(key, value, cache_ttl)
        else:
            self._set_in_memory(key, value, cache_ttl)
    
    def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
        """
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Error deleting from Redis: {str(e)}")
        else:
            self._memory_cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached values."""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.flushdb()
                logger.info("Cleared Redis cache")
            except Exception as e:
                logger.error(f"Error clearing Redis: {str(e)}")
        else:
            self._memory_cache.clear()
            logger.info("Cleared memory cache")
    
    def _get_from_redis(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from Redis."""
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting from Redis: {str(e)}")
            return None
    
    def _set_in_redis(self, key: str, value: Dict[str, Any], ttl: int) -> None:
        """Set value in Redis."""
        try:
            serialized = json.dumps(value, default=str)
            self.redis_client.setex(key, ttl, serialized)
        except Exception as e:
            logger.error(f"Error setting in Redis: {str(e)}")
    
    def _get_from_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from memory cache."""
        if key not in self._memory_cache:
            return None
        
        cached = self._memory_cache[key]
        expires_at = cached.get("expires_at")
        
        # Check expiration
        if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
            # Expired, remove it
            del self._memory_cache[key]
            return None
        
        return cached.get("value")
    
    def _set_in_memory(self, key: str, value: Dict[str, Any], ttl: int) -> None:
        """Set value in memory cache."""
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        self._memory_cache[key] = {
            "value": value,
            "expires_at": expires_at.isoformat()
        }
    
    def get_cache_key(self, prefix: str, identifier: str) -> str:
        """
        Generate a cache key.
        
        Args:
            prefix: Key prefix (e.g., 'market_data')
            identifier: Unique identifier (e.g., UPC)
            
        Returns:
            Cache key string
        """
        return f"{prefix}:{identifier}"


# Global cache instance
cache = CacheManager()
