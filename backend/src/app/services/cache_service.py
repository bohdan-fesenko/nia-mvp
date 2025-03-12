"""
Caching service for the application.
This module provides a service for caching data using Redis.
"""
import logging
import json
import hashlib
import inspect
import asyncio
from typing import Dict, List, Any, Optional, Union, TypeVar, Generic, Type, Callable, Tuple
from datetime import datetime, timedelta
import time

from ..config import settings
from ..db.redis_client import redis_client

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheService:
    """
    Caching service for the application.
    """
    def __init__(self):
        """
        Initialize the caching service.
        """
        self._client = redis_client
        self._enabled = settings.CACHE_ENABLED
        self._default_ttl = settings.CACHE_TTL_DEFAULT
        self._ttl_mapping = {
            'document': settings.CACHE_TTL_DOCUMENT,
            'project': settings.CACHE_TTL_PROJECT,
            'user': settings.CACHE_TTL_USER,
            'mermaid': settings.CACHE_TTL_MERMAID,
        }
        self._stampede_protection_window = settings.CACHE_STAMPEDE_PROTECTION_WINDOW

    def _get_ttl(self, data_type: str) -> int:
        """
        Get the TTL for a data type.
        
        Args:
            data_type: The type of data.
            
        Returns:
            The TTL in seconds.
        """
        return self._ttl_mapping.get(data_type, self._default_ttl)

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate a cache key.
        
        Args:
            prefix: The prefix for the key.
            *args: Positional arguments to include in the key.
            **kwargs: Keyword arguments to include in the key.
            
        Returns:
            The cache key.
        """
        # Convert args and kwargs to a string representation
        key_parts = [prefix]
        
        # Add args to key parts
        for arg in args:
            if arg is not None:
                key_parts.append(str(arg))
        
        # Add sorted kwargs to key parts
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}={v}")
        
        # Join key parts with a colon
        key = ":".join(key_parts)
        
        # If the key is too long, hash it
        if len(key) > 200:
            # Keep the prefix for readability but hash the rest
            prefix_part = prefix
            hash_part = hashlib.md5(key.encode()).hexdigest()
            key = f"{prefix_part}:{hash_part}"
        
        return key

    async def get(self, key: str) -> Optional[str]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key.
            
        Returns:
            The cached value, or None if not found.
        """
        if not self._enabled:
            return None
        
        return await self._client.get_async(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Time-to-live in seconds. If None, the default TTL will be used.
            
        Returns:
            True if the value was cached, False otherwise.
        """
        if not self._enabled:
            return False
        
        return await self._client.set_async(key, value, ttl=ttl or self._default_ttl)

    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: The cache key.
            
        Returns:
            True if the value was deleted, False otherwise.
        """
        if not self._enabled:
            return False
        
        return await self._client.delete_async(key)

    async def get_object(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Get an object from the cache.
        
        Args:
            key: The cache key.
            default: The default value to return if not found.
            
        Returns:
            The cached object, or default if not found.
        """
        if not self._enabled:
            return default
        
        return await self._client.get_object_async(key, default=default)

    async def set_object(self, key: str, value: Any, ttl: Optional[int] = None, use_msgpack: bool = False) -> bool:
        """
        Set an object in the cache.
        
        Args:
            key: The cache key.
            value: The object to cache.
            ttl: Time-to-live in seconds. If None, the default TTL will be used.
            use_msgpack: Whether to use msgpack for serialization.
            
        Returns:
            True if the object was cached, False otherwise.
        """
        if not self._enabled:
            return False
        
        return await self._client.set_object_async(key, value, ttl=ttl or self._default_ttl, use_msgpack=use_msgpack)

    async def invalidate(self, key: str) -> bool:
        """
        Invalidate a cached value.
        
        Args:
            key: The cache key.
            
        Returns:
            True if the value was invalidated, False otherwise.
        """
        if not self._enabled:
            return False
        
        return await self._client.delete_async(key)

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cached values matching a pattern.
        
        Args:
            pattern: The pattern to match.
            
        Returns:
            The number of keys invalidated.
        """
        if not self._enabled:
            return 0
        
        await self._client.connect_async()
        
        try:
            # Use the SCAN command to find keys matching the pattern
            cursor = 0
            count = 0
            
            while True:
                cursor, keys = await self._client._async_client.scan(cursor, match=pattern, count=100)
                
                if keys:
                    # Delete the keys
                    await self._client._async_client.delete(*keys)
                    count += len(keys)
                
                # If the cursor is 0, we've scanned all keys
                if cursor == 0:
                    break
            
            return count
        except Exception as e:
            logger.error(f"Error invalidating keys matching pattern {pattern}: {str(e)}")
            return 0

    async def cached(
        self, 
        prefix: str, 
        data_type: str, 
        fetch_func: Callable[..., Any], 
        *args, 
        ttl: Optional[int] = None, 
        use_msgpack: bool = False, 
        **kwargs
    ) -> Any:
        """
        Get a value from cache or fetch it if not cached.
        
        Args:
            prefix: The prefix for the cache key.
            data_type: The type of data (used for TTL).
            fetch_func: Function to fetch the value if not cached.
            *args: Arguments to pass to the fetch function.
            ttl: Time-to-live in seconds. If None, the TTL for the data type will be used.
            use_msgpack: Whether to use msgpack for serialization.
            **kwargs: Keyword arguments to pass to the fetch function.
            
        Returns:
            The cached or freshly fetched value.
        """
        if not self._enabled:
            # If caching is disabled, just call the fetch function
            return await fetch_func(*args, **kwargs) if asyncio.iscoroutinefunction(fetch_func) else fetch_func(*args, **kwargs)
        
        # Generate a cache key
        key = self._generate_key(prefix, *args, **kwargs)
        
        # Get the TTL for the data type
        ttl_value = ttl or self._get_ttl(data_type)
        
        # Try to get the value from cache with stampede protection
        return await self._client.get_with_stampede_protection(
            key,
            lambda: fetch_func(*args, **kwargs),
            ttl=ttl_value,
            stale_ttl=self._stampede_protection_window,
            use_msgpack=use_msgpack
        )

    async def cached_property(
        self, 
        prefix: str, 
        data_type: str, 
        instance: Any, 
        property_name: str, 
        fetch_func: Callable[..., Any], 
        ttl: Optional[int] = None, 
        use_msgpack: bool = False
    ) -> Any:
        """
        Get a property value from cache or fetch it if not cached.
        
        Args:
            prefix: The prefix for the cache key.
            data_type: The type of data (used for TTL).
            instance: The instance to get the property from.
            property_name: The name of the property.
            fetch_func: Function to fetch the value if not cached.
            ttl: Time-to-live in seconds. If None, the TTL for the data type will be used.
            use_msgpack: Whether to use msgpack for serialization.
            
        Returns:
            The cached or freshly fetched property value.
        """
        if not self._enabled:
            # If caching is disabled, just call the fetch function
            return await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
        
        # Generate a cache key
        instance_id = getattr(instance, 'id', str(id(instance)))
        key = self._generate_key(f"{prefix}:{property_name}", instance_id)
        
        # Get the TTL for the data type
        ttl_value = ttl or self._get_ttl(data_type)
        
        # Try to get the value from cache with stampede protection
        return await self._client.get_with_stampede_protection(
            key,
            fetch_func,
            ttl=ttl_value,
            stale_ttl=self._stampede_protection_window,
            use_msgpack=use_msgpack
        )

    async def memoize(
        self, 
        prefix: str, 
        data_type: str, 
        func: Callable[..., Any], 
        *args, 
        ttl: Optional[int] = None, 
        use_msgpack: bool = False, 
        **kwargs
    ) -> Any:
        """
        Memoize a function call.
        
        Args:
            prefix: The prefix for the cache key.
            data_type: The type of data (used for TTL).
            func: The function to memoize.
            *args: Arguments to pass to the function.
            ttl: Time-to-live in seconds. If None, the TTL for the data type will be used.
            use_msgpack: Whether to use msgpack for serialization.
            **kwargs: Keyword arguments to pass to the function.
            
        Returns:
            The cached or freshly computed result.
        """
        if not self._enabled:
            # If caching is disabled, just call the function
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        
        # Generate a cache key
        func_name = func.__name__
        module_name = func.__module__
        key = self._generate_key(f"{prefix}:{module_name}.{func_name}", *args, **kwargs)
        
        # Get the TTL for the data type
        ttl_value = ttl or self._get_ttl(data_type)
        
        # Try to get the value from cache with stampede protection
        return await self._client.get_with_stampede_protection(
            key,
            lambda: func(*args, **kwargs),
            ttl=ttl_value,
            stale_ttl=self._stampede_protection_window,
            use_msgpack=use_msgpack
        )

    # ==================== Specific Caching Strategies ====================

    async def cache_document(self, document_id: str, document_data: Dict[str, Any]) -> bool:
        """
        Cache a document.
        
        Args:
            document_id: The ID of the document.
            document_data: The document data to cache.
            
        Returns:
            True if the document was cached, False otherwise.
        """
        key = f"document:{document_id}"
        return await self.set_object(key, document_data, ttl=self._get_ttl('document'))

    async def get_cached_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached document.
        
        Args:
            document_id: The ID of the document.
            
        Returns:
            The cached document, or None if not found.
        """
        key = f"document:{document_id}"
        return await self.get_object(key)

    async def invalidate_document(self, document_id: str) -> bool:
        """
        Invalidate a cached document.
        
        Args:
            document_id: The ID of the document.
            
        Returns:
            True if the document was invalidated, False otherwise.
        """
        key = f"document:{document_id}"
        return await self.invalidate(key)

    async def cache_project(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """
        Cache a project.
        
        Args:
            project_id: The ID of the project.
            project_data: The project data to cache.
            
        Returns:
            True if the project was cached, False otherwise.
        """
        key = f"project:{project_id}"
        return await self.set_object(key, project_data, ttl=self._get_ttl('project'))

    async def get_cached_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached project.
        
        Args:
            project_id: The ID of the project.
            
        Returns:
            The cached project, or None if not found.
        """
        key = f"project:{project_id}"
        return await self.get_object(key)

    async def invalidate_project(self, project_id: str) -> bool:
        """
        Invalidate a cached project.
        
        Args:
            project_id: The ID of the project.
            
        Returns:
            True if the project was invalidated, False otherwise.
        """
        key = f"project:{project_id}"
        return await self.invalidate(key)

    async def cache_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """
        Cache a user.
        
        Args:
            user_id: The ID of the user.
            user_data: The user data to cache.
            
        Returns:
            True if the user was cached, False otherwise.
        """
        key = f"user:{user_id}"
        return await self.set_object(key, user_data, ttl=self._get_ttl('user'))

    async def get_cached_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            The cached user, or None if not found.
        """
        key = f"user:{user_id}"
        return await self.get_object(key)

    async def invalidate_user(self, user_id: str) -> bool:
        """
        Invalidate a cached user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            True if the user was invalidated, False otherwise.
        """
        key = f"user:{user_id}"
        return await self.invalidate(key)

    async def cache_mermaid(self, diagram_source: str, svg_output: str) -> bool:
        """
        Cache a rendered Mermaid diagram.
        
        Args:
            diagram_source: The source of the Mermaid diagram.
            svg_output: The rendered SVG output.
            
        Returns:
            True if the diagram was cached, False otherwise.
        """
        # Use a hash of the diagram source as the key
        diagram_hash = hashlib.md5(diagram_source.encode()).hexdigest()
        key = f"mermaid:{diagram_hash}"
        return await self.set(key, svg_output, ttl=self._get_ttl('mermaid'))

    async def get_cached_mermaid(self, diagram_source: str) -> Optional[str]:
        """
        Get a cached Mermaid diagram.
        
        Args:
            diagram_source: The source of the Mermaid diagram.
            
        Returns:
            The cached SVG output, or None if not found.
        """
        # Use a hash of the diagram source as the key
        diagram_hash = hashlib.md5(diagram_source.encode()).hexdigest()
        key = f"mermaid:{diagram_hash}"
        return await self.get(key)

    async def invalidate_mermaid(self, diagram_source: str) -> bool:
        """
        Invalidate a cached Mermaid diagram.
        
        Args:
            diagram_source: The source of the Mermaid diagram.
            
        Returns:
            True if the diagram was invalidated, False otherwise.
        """
        # Use a hash of the diagram source as the key
        diagram_hash = hashlib.md5(diagram_source.encode()).hexdigest()
        key = f"mermaid:{diagram_hash}"
        return await self.invalidate(key)

# Create a singleton instance
cache_service = CacheService()

# Create a factory function for the service
def create_cache_service(redis_client) -> CacheService:
    """
    Create a cache service.
    
    Args:
        redis_client: Redis client
        
    Returns:
        A cache service
    """
    # We're using a singleton pattern, so just return the existing instance
    # In a real implementation, you might create a new instance with the provided client
    return cache_service
cache_service = CacheService()