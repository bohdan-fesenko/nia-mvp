"""
Redis client for caching, pub/sub, and session management.
This module provides a client for interacting with Redis.
"""
import logging
import json
import asyncio
import time
from typing import Dict, List, Any, Optional, Union, TypeVar, Generic, Type, Callable, Tuple
from datetime import datetime, timedelta
import uuid
import msgpack

import redis
import aioredis
from redis.exceptions import RedisError
from redis.asyncio.client import Redis as AsyncRedis
from redis.asyncio.connection import ConnectionPool as AsyncConnectionPool

from ..config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RedisClient:
    """
    Redis client for caching, pub/sub, and session management.
    """
    def __init__(self):
        """
        Initialize the Redis client.
        """
        self._client = None
        self._async_client = None
        self._connection_pool = None
        self._async_connection_pool = None
        self._pubsub = None
        self._async_pubsub = None
        self._host = settings.REDIS_HOST
        self._port = settings.REDIS_PORT
        self._password = settings.REDIS_PASSWORD
        self._db = settings.REDIS_DB
        self._ssl = settings.REDIS_SSL
        self._max_connections = settings.REDIS_MAX_CONNECTIONS
        self._socket_timeout = settings.REDIS_SOCKET_TIMEOUT
        self._socket_connect_timeout = settings.REDIS_SOCKET_CONNECT_TIMEOUT
        self._retry_on_timeout = settings.REDIS_RETRY_ON_TIMEOUT
        self._connection_pool_size = settings.REDIS_CONNECTION_POOL_SIZE
        self._subscribers = {}  # Store active subscribers

    def connect(self):
        """
        Connect to Redis.
        """
        if self._client is None:
            try:
                # Create a connection pool
                self._connection_pool = redis.ConnectionPool(
                    host=self._host,
                    port=self._port,
                    password=self._password,
                    db=self._db,
                    ssl=self._ssl,
                    max_connections=self._max_connections,
                    socket_timeout=self._socket_timeout,
                    socket_connect_timeout=self._socket_connect_timeout,
                    retry_on_timeout=self._retry_on_timeout,
                    decode_responses=True  # Automatically decode responses to strings
                )
                
                # Create a Redis client using the connection pool
                self._client = redis.Redis(connection_pool=self._connection_pool)
                
                # Test the connection
                self._client.ping()
                
                logger.info("Connected to Redis")
            except RedisError as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error connecting to Redis: {str(e)}")
                raise

    async def connect_async(self):
        """
        Connect to Redis asynchronously.
        """
        if self._async_client is None:
            try:
                # Create an async connection pool
                self._async_connection_pool = AsyncConnectionPool(
                    host=self._host,
                    port=self._port,
                    password=self._password,
                    db=self._db,
                    ssl=self._ssl,
                    max_connections=self._max_connections,
                    socket_timeout=self._socket_timeout,
                    socket_connect_timeout=self._socket_connect_timeout,
                    retry_on_timeout=self._retry_on_timeout,
                    decode_responses=True  # Automatically decode responses to strings
                )
                
                # Create an async Redis client using the connection pool
                self._async_client = AsyncRedis(connection_pool=self._async_connection_pool)
                
                # Test the connection
                await self._async_client.ping()
                
                logger.info("Connected to Redis (async)")
            except RedisError as e:
                logger.error(f"Failed to connect to Redis (async): {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error connecting to Redis (async): {str(e)}")
                raise

    def close(self):
        """
        Close the connection to Redis.
        """
        if self._client is not None:
            try:
                # Close the connection pool
                self._connection_pool.disconnect()
                self._connection_pool = None
                self._client = None
                logger.info("Disconnected from Redis")
            except Exception as e:
                logger.error(f"Error disconnecting from Redis: {str(e)}")

    async def close_async(self):
        """
        Close the async connection to Redis.
        """
        if self._async_client is not None:
            try:
                # Close the async connection pool
                await self._async_connection_pool.disconnect()
                self._async_connection_pool = None
                self._async_client = None
                logger.info("Disconnected from Redis (async)")
            except Exception as e:
                logger.error(f"Error disconnecting from Redis (async): {str(e)}")

    # ==================== Caching Methods ====================

    def get(self, key: str) -> Optional[str]:
        """
        Get a value from Redis.
        
        Args:
            key: The key to get.
            
        Returns:
            The value, or None if not found.
        """
        self.connect()
        
        try:
            return self._client.get(key)
        except RedisError as e:
            logger.error(f"Redis error getting key {key}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error getting key {key}: {str(e)}")
            return None

    async def get_async(self, key: str) -> Optional[str]:
        """
        Get a value from Redis asynchronously.
        
        Args:
            key: The key to get.
            
        Returns:
            The value, or None if not found.
        """
        await self.connect_async()
        
        try:
            return await self._async_client.get(key)
        except RedisError as e:
            logger.error(f"Redis error getting key {key} (async): {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error getting key {key} (async): {str(e)}")
            return None

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Set a value in Redis.
        
        Args:
            key: The key to set.
            value: The value to set.
            ttl: Time-to-live in seconds. If None, the key will not expire.
            
        Returns:
            True if the key was set, False otherwise.
        """
        self.connect()
        
        try:
            return self._client.set(key, value, ex=ttl)
        except RedisError as e:
            logger.error(f"Redis error setting key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error setting key {key}: {str(e)}")
            return False

    async def set_async(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Set a value in Redis asynchronously.
        
        Args:
            key: The key to set.
            value: The value to set.
            ttl: Time-to-live in seconds. If None, the key will not expire.
            
        Returns:
            True if the key was set, False otherwise.
        """
        await self.connect_async()
        
        try:
            return await self._async_client.set(key, value, ex=ttl)
        except RedisError as e:
            logger.error(f"Redis error setting key {key} (async): {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error setting key {key} (async): {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: The key to delete.
            
        Returns:
            True if the key was deleted, False otherwise.
        """
        self.connect()
        
        try:
            return bool(self._client.delete(key))
        except RedisError as e:
            logger.error(f"Redis error deleting key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error deleting key {key}: {str(e)}")
            return False

    async def delete_async(self, key: str) -> bool:
        """
        Delete a key from Redis asynchronously.
        
        Args:
            key: The key to delete.
            
        Returns:
            True if the key was deleted, False otherwise.
        """
        await self.connect_async()
        
        try:
            return bool(await self._async_client.delete(key))
        except RedisError as e:
            logger.error(f"Redis error deleting key {key} (async): {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error deleting key {key} (async): {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: The key to check.
            
        Returns:
            True if the key exists, False otherwise.
        """
        self.connect()
        
        try:
            return bool(self._client.exists(key))
        except RedisError as e:
            logger.error(f"Redis error checking if key {key} exists: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error checking if key {key} exists: {str(e)}")
            return False

    async def exists_async(self, key: str) -> bool:
        """
        Check if a key exists in Redis asynchronously.
        
        Args:
            key: The key to check.
            
        Returns:
            True if the key exists, False otherwise.
        """
        await self.connect_async()
        
        try:
            return bool(await self._async_client.exists(key))
        except RedisError as e:
            logger.error(f"Redis error checking if key {key} exists (async): {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error checking if key {key} exists (async): {str(e)}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """
        Set the expiration time for a key.
        
        Args:
            key: The key to set the expiration for.
            ttl: Time-to-live in seconds.
            
        Returns:
            True if the expiration was set, False otherwise.
        """
        self.connect()
        
        try:
            return bool(self._client.expire(key, ttl))
        except RedisError as e:
            logger.error(f"Redis error setting expiration for key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error setting expiration for key {key}: {str(e)}")
            return False

    async def expire_async(self, key: str, ttl: int) -> bool:
        """
        Set the expiration time for a key asynchronously.
        
        Args:
            key: The key to set the expiration for.
            ttl: Time-to-live in seconds.
            
        Returns:
            True if the expiration was set, False otherwise.
        """
        await self.connect_async()
        
        try:
            return bool(await self._async_client.expire(key, ttl))
        except RedisError as e:
            logger.error(f"Redis error setting expiration for key {key} (async): {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error setting expiration for key {key} (async): {str(e)}")
            return False

    def ttl(self, key: str) -> int:
        """
        Get the time-to-live for a key.
        
        Args:
            key: The key to get the TTL for.
            
        Returns:
            The TTL in seconds, or -1 if the key has no TTL, or -2 if the key does not exist.
        """
        self.connect()
        
        try:
            return self._client.ttl(key)
        except RedisError as e:
            logger.error(f"Redis error getting TTL for key {key}: {str(e)}")
            return -2
        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {str(e)}")
            return -2

    async def ttl_async(self, key: str) -> int:
        """
        Get the time-to-live for a key asynchronously.
        
        Args:
            key: The key to get the TTL for.
            
        Returns:
            The TTL in seconds, or -1 if the key has no TTL, or -2 if the key does not exist.
        """
        await self.connect_async()
        
        try:
            return await self._async_client.ttl(key)
        except RedisError as e:
            logger.error(f"Redis error getting TTL for key {key} (async): {str(e)}")
            return -2
        except Exception as e:
            logger.error(f"Error getting TTL for key {key} (async): {str(e)}")
            return -2

    # ==================== Object Caching Methods ====================

    def get_object(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Get an object from Redis.
        
        Args:
            key: The key to get.
            default: The default value to return if the key is not found.
            
        Returns:
            The object, or default if not found.
        """
        self.connect()
        
        try:
            data = self._client.get(key)
            if data is None:
                return default
            
            try:
                # Try to deserialize as JSON first
                return json.loads(data)
            except json.JSONDecodeError:
                try:
                    # If JSON fails, try msgpack
                    return msgpack.unpackb(data, raw=False)
                except:
                    # If all deserialization fails, return the raw data
                    return data
        except RedisError as e:
            logger.error(f"Redis error getting object {key}: {str(e)}")
            return default
        except Exception as e:
            logger.error(f"Error getting object {key}: {str(e)}")
            return default

    async def get_object_async(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Get an object from Redis asynchronously.
        
        Args:
            key: The key to get.
            default: The default value to return if the key is not found.
            
        Returns:
            The object, or default if not found.
        """
        await self.connect_async()
        
        try:
            data = await self._async_client.get(key)
            if data is None:
                return default
            
            try:
                # Try to deserialize as JSON first
                return json.loads(data)
            except json.JSONDecodeError:
                try:
                    # If JSON fails, try msgpack
                    return msgpack.unpackb(data, raw=False)
                except:
                    # If all deserialization fails, return the raw data
                    return data
        except RedisError as e:
            logger.error(f"Redis error getting object {key} (async): {str(e)}")
            return default
        except Exception as e:
            logger.error(f"Error getting object {key} (async): {str(e)}")
            return default

    def set_object(self, key: str, value: Any, ttl: Optional[int] = None, use_msgpack: bool = False) -> bool:
        """
        Set an object in Redis.
        
        Args:
            key: The key to set.
            value: The object to set.
            ttl: Time-to-live in seconds. If None, the key will not expire.
            use_msgpack: Whether to use msgpack for serialization (more efficient but less readable).
            
        Returns:
            True if the object was set, False otherwise.
        """
        self.connect()
        
        try:
            if use_msgpack:
                # Use msgpack for more efficient serialization
                serialized = msgpack.packb(value, use_bin_type=True)
            else:
                # Use JSON for more readable serialization
                serialized = json.dumps(value)
            
            return self._client.set(key, serialized, ex=ttl)
        except RedisError as e:
            logger.error(f"Redis error setting object {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error setting object {key}: {str(e)}")
            return False

    async def set_object_async(self, key: str, value: Any, ttl: Optional[int] = None, use_msgpack: bool = False) -> bool:
        """
        Set an object in Redis asynchronously.
        
        Args:
            key: The key to set.
            value: The object to set.
            ttl: Time-to-live in seconds. If None, the key will not expire.
            use_msgpack: Whether to use msgpack for serialization (more efficient but less readable).
            
        Returns:
            True if the object was set, False otherwise.
        """
        await self.connect_async()
        
        try:
            if use_msgpack:
                # Use msgpack for more efficient serialization
                serialized = msgpack.packb(value, use_bin_type=True)
            else:
                # Use JSON for more readable serialization
                serialized = json.dumps(value)
            
            return await self._async_client.set(key, serialized, ex=ttl)
        except RedisError as e:
            logger.error(f"Redis error setting object {key} (async): {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error setting object {key} (async): {str(e)}")
            return False

    # ==================== Cache Stampede Protection ====================

    async def get_with_stampede_protection(
        self, 
        key: str, 
        fetch_func: Callable[[], Any], 
        ttl: int = 300,
        stale_ttl: int = 30,
        use_msgpack: bool = False
    ) -> Any:
        """
        Get a value from cache with protection against cache stampede.
        If the value is not in cache, only one process will execute the fetch function.
        
        Args:
            key: The cache key.
            fetch_func: Function to fetch the value if not in cache.
            ttl: Time-to-live for the cached value in seconds.
            stale_ttl: Additional time the value remains valid while being refreshed.
            use_msgpack: Whether to use msgpack for serialization.
            
        Returns:
            The cached or freshly fetched value.
        """
        await self.connect_async()
        
        # Try to get the value from cache
        cached_data = await self.get_object_async(key)
        
        # If we have cached data, check if it's still fresh
        if cached_data is not None and isinstance(cached_data, dict) and 'value' in cached_data:
            expires_at = cached_data.get('expires_at', 0)
            refresh_at = expires_at - stale_ttl
            
            # If the value is still fresh, return it
            if time.time() < refresh_at:
                return cached_data['value']
            
            # If the value is stale but not expired, try to refresh it in the background
            # but still return the stale value
            if time.time() < expires_at:
                # Try to acquire a lock to refresh the value
                lock_key = f"{key}:lock"
                if await self._async_client.set(lock_key, "1", ex=stale_ttl, nx=True):
                    # We got the lock, refresh the value in the background
                    asyncio.create_task(self._refresh_cached_value(key, fetch_func, ttl, use_msgpack))
                
                # Return the stale value while it's being refreshed
                return cached_data['value']
        
        # If we don't have cached data or it's expired, we need to fetch it
        # First, try to acquire a lock to prevent multiple processes from fetching
        lock_key = f"{key}:lock"
        if await self._async_client.set(lock_key, "1", ex=stale_ttl, nx=True):
            # We got the lock, fetch the value
            try:
                value = await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
                
                # Cache the value with expiration
                expires_at = time.time() + ttl
                await self.set_object_async(
                    key, 
                    {'value': value, 'expires_at': expires_at}, 
                    ttl=ttl + stale_ttl,
                    use_msgpack=use_msgpack
                )
                
                # Release the lock
                await self._async_client.delete(lock_key)
                
                return value
            except Exception as e:
                # If fetching fails, release the lock and re-raise
                await self._async_client.delete(lock_key)
                logger.error(f"Error fetching value for key {key}: {str(e)}")
                raise
        else:
            # We didn't get the lock, someone else is fetching
            # Wait a bit and try to get the value from cache again
            for _ in range(10):  # Try up to 10 times
                await asyncio.sleep(0.1)
                cached_data = await self.get_object_async(key)
                if cached_data is not None and isinstance(cached_data, dict) and 'value' in cached_data:
                    return cached_data['value']
            
            # If we still don't have the value, fetch it directly (without caching)
            return await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()

    async def _refresh_cached_value(self, key: str, fetch_func: Callable[[], Any], ttl: int, use_msgpack: bool):
        """
        Refresh a cached value in the background.
        
        Args:
            key: The cache key.
            fetch_func: Function to fetch the value.
            ttl: Time-to-live for the cached value in seconds.
            use_msgpack: Whether to use msgpack for serialization.
        """
        try:
            # Fetch the new value
            value = await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
            
            # Cache the value with expiration
            expires_at = time.time() + ttl
            await self.set_object_async(
                key, 
                {'value': value, 'expires_at': expires_at}, 
                ttl=ttl + settings.CACHE_STAMPEDE_PROTECTION_WINDOW,
                use_msgpack=use_msgpack
            )
            
            # Release the lock
            lock_key = f"{key}:lock"
            await self._async_client.delete(lock_key)
        except Exception as e:
            # If refreshing fails, release the lock and log the error
            lock_key = f"{key}:lock"
            await self._async_client.delete(lock_key)
            logger.error(f"Error refreshing cached value for key {key}: {str(e)}")

    # ==================== Pub/Sub Methods ====================

    def publish(self, channel: str, message: str) -> int:
        """
        Publish a message to a channel.
        
        Args:
            channel: The channel to publish to.
            message: The message to publish.
            
        Returns:
            The number of clients that received the message.
        """
        self.connect()
        
        try:
            return self._client.publish(channel, message)
        except RedisError as e:
            logger.error(f"Redis error publishing to channel {channel}: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Error publishing to channel {channel}: {str(e)}")
            return 0

    async def publish_async(self, channel: str, message: str) -> int:
        """
        Publish a message to a channel asynchronously.
        
        Args:
            channel: The channel to publish to.
            message: The message to publish.
            
        Returns:
            The number of clients that received the message.
        """
        await self.connect_async()
        
        try:
            return await self._async_client.publish(channel, message)
        except RedisError as e:
            logger.error(f"Redis error publishing to channel {channel} (async): {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Error publishing to channel {channel} (async): {str(e)}")
            return 0

    def publish_json(self, channel: str, data: Any) -> int:
        """
        Publish a JSON message to a channel.
        
        Args:
            channel: The channel to publish to.
            data: The data to publish (will be serialized to JSON).
            
        Returns:
            The number of clients that received the message.
        """
        try:
            message = json.dumps(data)
            return self.publish(channel, message)
        except Exception as e:
            logger.error(f"Error publishing JSON to channel {channel}: {str(e)}")
            return 0

    async def publish_json_async(self, channel: str, data: Any) -> int:
        """
        Publish a JSON message to a channel asynchronously.
        
        Args:
            channel: The channel to publish to.
            data: The data to publish (will be serialized to JSON).
            
        Returns:
            The number of clients that received the message.
        """
        try:
            message = json.dumps(data)
            return await self.publish_async(channel, message)
        except Exception as e:
            logger.error(f"Error publishing JSON to channel {channel} (async): {str(e)}")
            return 0

    def subscribe(self, channel: str, callback: Callable[[str, str], None]) -> bool:
        """
        Subscribe to a channel.
        Note: This is a blocking operation and should be run in a separate thread.
        
        Args:
            channel: The channel to subscribe to.
            callback: The callback function to call when a message is received.
                     The callback takes two arguments: channel and message.
            
        Returns:
            True if the subscription was successful, False otherwise.
        """
        self.connect()
        
        try:
            if self._pubsub is None:
                self._pubsub = self._client.pubsub()
            
            # Subscribe to the channel
            self._pubsub.subscribe(**{channel: lambda message: callback(channel, message['data'])})
            
            # Start listening for messages in a separate thread
            self._pubsub.run_in_thread(sleep_time=0.001)
            
            # Store the subscription
            self._subscribers[channel] = callback
            
            return True
        except RedisError as e:
            logger.error(f"Redis error subscribing to channel {channel}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error subscribing to channel {channel}: {str(e)}")
            return False

    async def subscribe_async(self, channel: str) -> Optional[aioredis.client.PubSub]:
        """
        Subscribe to a channel asynchronously.
        
        Args:
            channel: The channel to subscribe to.
            
        Returns:
            A PubSub object that can be used to listen for messages, or None if the subscription failed.
        """
        await self.connect_async()
        
        try:
            if self._async_pubsub is None:
                self._async_pubsub = self._async_client.pubsub()
            
            # Subscribe to the channel
            await self._async_pubsub.subscribe(channel)
            
            return self._async_pubsub
        except RedisError as e:
            logger.error(f"Redis error subscribing to channel {channel} (async): {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error subscribing to channel {channel} (async): {str(e)}")
            return None

    def unsubscribe(self, channel: str) -> bool:
        """
        Unsubscribe from a channel.
        
        Args:
            channel: The channel to unsubscribe from.
            
        Returns:
            True if the unsubscription was successful, False otherwise.
        """
        if self._pubsub is None:
            return True
        
        try:
            # Unsubscribe from the channel
            self._pubsub.unsubscribe(channel)
            
            # Remove the subscription
            if channel in self._subscribers:
                del self._subscribers[channel]
            
            return True
        except RedisError as e:
            logger.error(f"Redis error unsubscribing from channel {channel}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error unsubscribing from channel {channel}: {str(e)}")
            return False

    async def unsubscribe_async(self, channel: str) -> bool:
        """
        Unsubscribe from a channel asynchronously.
        
        Args:
            channel: The channel to unsubscribe from.
            
        Returns:
            True if the unsubscription was successful, False otherwise.
        """
        if self._async_pubsub is None:
            return True
        
        try:
            # Unsubscribe from the channel
            await self._async_pubsub.unsubscribe(channel)
            
            return True
        except RedisError as e:
            logger.error(f"Redis error unsubscribing from channel {channel} (async): {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error unsubscribing from channel {channel} (async): {str(e)}")
            return False

    # ==================== Session Management Methods ====================

    def create_session(self, user_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> str:
        """
        Create a new session.
        
        Args:
            user_id: The ID of the user.
            data: The session data.
            ttl: Time-to-live in seconds. If None, the default session TTL will be used.
            
        Returns:
            The session ID.
        """
        self.connect()
        
        # Generate a session ID
        session_id = str(uuid.uuid4())
        
        # Add user ID and creation timestamp to the session data
        session_data = {
            **data,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Set the session in Redis
        key = f"session:{session_id}"
        if self.set_object(key, session_data, ttl=ttl or settings.SESSION_TTL):
            # Also store the session ID in a user-specific set for lookup
            user_sessions_key = f"user:{user_id}:sessions"
            self._client.sadd(user_sessions_key, session_id)
            
            return session_id
        else:
            logger.error(f"Failed to create session for user {user_id}")
            return ""

    async def create_session_async(self, user_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> str:
        """
        Create a new session asynchronously.
        
        Args:
            user_id: The ID of the user.
            data: The session data.
            ttl: Time-to-live in seconds. If None, the default session TTL will be used.
            
        Returns:
            The session ID.
        """
        await self.connect_async()
        
        # Generate a session ID
        session_id = str(uuid.uuid4())
        
        # Add user ID and creation timestamp to the session data
        session_data = {
            **data,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Set the session in Redis
        key = f"session:{session_id}"
        if await self.set_object_async(key, session_data, ttl=ttl or settings.SESSION_TTL):
            # Also store the session ID in a user-specific set for lookup
            user_sessions_key = f"user:{user_id}:sessions"
            await self._async_client.sadd(user_sessions_key, session_id)
            
            return session_id
        else:
            logger.error(f"Failed to create session for user {user_id}")
            return ""

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a session.
        
        Args:
            session_id: The ID of the session.
            
        Returns:
            The session data, or None if not found.
        """
        self.connect()
        
        key = f"session:{session_id}"
        return self.get_object(key)

    async def get_session_async(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a session asynchronously.
        
        Args:
            session_id: The ID of the session.
            
        Returns:
            The session data, or None if not found.
        """
        await self.connect_async()
        
        key = f"session:{session_id}"
        return await self.get_object_async(key)

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a session.
        
        Args:
            session_id: The ID of the session.
            data: The new session data.
            
        Returns:
            True if the session was updated, False otherwise.
        """
        self.connect()
        
        key = f"session:{session_id}"
        
        # Get the current session data
        current_data = self.get_object(key)
        if current_data is None:
            logger.error(f"Session {session_id} not found")
            return False
        
        # Update the session data
        updated_data = {**current_data, **data, 'updated_at': datetime.utcnow().isoformat()}
        
        # Get the current TTL
        ttl = self.ttl(key)
        if ttl < 0:
            ttl = settings.SESSION_TTL
        
        # Set the updated session data
        return self.set_object(key, updated_data, ttl=ttl)

    async def update_session_async(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a session asynchronously.
        
        Args:
            session_id: The ID of the session.
            data: The new session data.
            
        Returns:
            True if the session was updated, False otherwise.
        """
        await self.connect_async()
        
        key = f"session:{session_id}"
        
        # Get the current session data
        current_data = await self.get_object_async(key)
        if current_data is None:
            logger.error(f"Session {session_id} not found")
            return False
        
        # Update the session data
        updated_data = {**current_data, **data, 'updated_at': datetime.utcnow().isoformat()}
        
        # Get the current TTL
        ttl = await self.ttl_async(key)
        if ttl < 0:
            ttl = settings.SESSION_TTL
        
        # Set the updated session data
        return await self.set_object_async(key, updated_data, ttl=ttl)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The ID of the session.
            
        Returns:
            True if the session was deleted, False otherwise.
        """
        self.connect()
        
        key = f"session:{session_id}"
        
        # Get the session data to find the user ID
        session_data = self.get_object(key)
        if session_data is None:
            return False
        
        user_id = session_data.get('user_id')
        if user_id:
            # Remove the session ID from the user's sessions set
            user_sessions_key = f"user:{user_id}:sessions"
            self._client.srem(user_sessions_key, session_id)
        
        # Delete the session
        return self.delete(key)

    async def delete_session_async(self, session_id: str) -> bool:
        """
        Delete a session asynchronously.
        
        Args:
            session_id: The ID of the session.
            
        Returns:
            True if the session was deleted, False otherwise.
        """
        await self.connect_async()
        
        key = f"session:{session_id}"
        
        # Get the session data to find the user ID
        session_data = await self.get_object_async(key)
        if session_data is None:
            return False
        
        user_id = session_data.get('user_id')
        if user_id:
            # Remove the session ID from the user's sessions set
            user_sessions_key = f"user:{user_id}:sessions"
            await self._async_client.srem(user_sessions_key, session_id)
        
        # Delete the session
        return await self.delete_async(key)

    def get_user_sessions(self, user_id: str) -> List[str]:
        """
        Get all session IDs for a user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            A list of session IDs.
        """
        self.connect()
        
        user_sessions_key = f"user:{user_id}:sessions"
        return [s.decode('utf-8') if isinstance(s, bytes) else s for s in self._client.smembers(user_sessions_key)]

    async def get_user_sessions_async(self, user_id: str) -> List[str]:
        """
        Get all session IDs for a user asynchronously.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            A list of session IDs.
        """
        await self.connect_async()
        
        user_sessions_key = f"user:{user_id}:sessions"
        sessions = await self._async_client.smembers(user_sessions_key)
        return [s.decode('utf-8') if isinstance(s, bytes) else s for s in sessions]

    def delete_user_sessions(self, user_id: str) -> int:
        """
        Delete all sessions for a user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            The number of sessions deleted.
        """
        self.connect()
        
        # Get all session IDs for the user
        session_ids = self.get_user_sessions(user_id)
        
        # Delete each session
        count = 0
        for session_id in session_ids:
            if self.delete_session(session_id):
                count += 1
        
        return count

    async def delete_user_sessions_async(self, user_id: str) -> int:
        """
        Delete all sessions for a user asynchronously.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            The number of sessions deleted.
        """
        await self.connect_async()
        
        # Get all session IDs for the user
        session_ids = await self.get_user_sessions_async(user_id)
        
        # Delete each session
        count = 0
        for session_id in session_ids:
            if await self.delete_session_async(session_id):
                count += 1
        
        return count

    # ==================== Rate Limiting Methods ====================

    async def increment_rate_limit(
        self, 
        key: str, 
        limit: int = 100, 
        window: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Increment a rate limit counter and check if the limit has been exceeded.
        
        Args:
            key: The rate limit key.
            limit: The maximum number of requests allowed in the window.
            window: The time window in seconds.
            
        Returns:
            A tuple of (allowed, current_count, ttl) where:
            - allowed is True if the request is allowed, False otherwise.
            - current_count is the current count of requests.
            - ttl is the time-to-live for the rate limit in seconds.
        """
        await self.connect_async()
        
        try:
            # Increment the counter
            count = await self._async_client.incr(key)
            
            # If this is the first request, set the expiration
            if count == 1:
                await self._async_client.expire(key, window)
            
            # Get the TTL
            ttl = await self._async_client.ttl(key)
            
            # Check if the limit has been exceeded
            allowed = count <= limit
            
            return allowed, count, ttl
        except RedisError as e:
            logger.error(f"Redis error incrementing rate limit for key {key}: {str(e)}")
            # In case of error, allow the request
            return True, 0, 0
        except Exception as e:
            logger.error(f"Error incrementing rate limit for key {key}: {str(e)}")
            # In case of error, allow the request
            return True, 0, 0

    async def get_rate_limit(self, key: str) -> Tuple[int, int]:
        """
        Get the current rate limit count and TTL.
        
        Args:
            key: The rate limit key.
            
        Returns:
            A tuple of (count, ttl) where:
            - count is the current count of requests.
            - ttl is the time-to-live for the rate limit in seconds.
        """
        await self.connect_async()
        
        try:
            # Get the current count
            count_str = await self._async_client.get(key)
            count = int(count_str) if count_str is not None else 0
            
            # Get the TTL
            ttl = await self._async_client.ttl(key)
            
            return count, ttl
        except RedisError as e:
            logger.error(f"Redis error getting rate limit for key {key}: {str(e)}")
            return 0, 0
        except Exception as e:
            logger.error(f"Error getting rate limit for key {key}: {str(e)}")
            return 0, 0

    async def reset_rate_limit(self, key: str) -> bool:
        """
        Reset a rate limit counter.
        
        Args:
            key: The rate limit key.
            
        Returns:
            True if the rate limit was reset, False otherwise.
        """
        await self.connect_async()
        
        try:
            # Delete the key
            return bool(await self._async_client.delete(key))
        except RedisError as e:
            logger.error(f"Redis error resetting rate limit for key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error resetting rate limit for key {key}: {str(e)}")
            return False


# Create a singleton instance
redis_client = RedisClient()