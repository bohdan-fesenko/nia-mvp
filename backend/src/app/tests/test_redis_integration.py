"""
Tests for Redis integration components.
This module contains tests for the Redis client, cache service, pubsub service, 
session service, and rate limit service.
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
import pytest
from unittest.mock import patch, MagicMock

from ..db.redis_client import redis_client
from ..services.cache_service import cache_service
from ..services.pubsub_service import pubsub_service
from ..services.session_service import session_service
from ..services.rate_limit_service import rate_limit_service
from ..config import settings


@pytest.fixture
async def setup_redis():
    """
    Setup Redis connection for testing.
    """
    # Connect to Redis
    await redis_client.connect_async()
    
    # Clear test data
    test_keys = await redis_client.keys("test:*")
    if test_keys:
        await redis_client.delete(*test_keys)
    
    yield
    
    # Clean up after tests
    test_keys = await redis_client.keys("test:*")
    if test_keys:
        await redis_client.delete(*test_keys)
    
    # Close Redis connection
    await redis_client.close_async()


class TestRedisClient:
    """
    Tests for the Redis client.
    """
    
    @pytest.mark.asyncio
    async def test_connection(self, setup_redis):
        """Test Redis connection."""
        # Test ping
        result = await redis_client.ping()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_basic_operations(self, setup_redis):
        """Test basic Redis operations."""
        # Test set and get
        await redis_client.set("test:key", "value")
        value = await redis_client.get("test:key")
        assert value == "value"
        
        # Test delete
        await redis_client.delete("test:key")
        value = await redis_client.get("test:key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_hash_operations(self, setup_redis):
        """Test Redis hash operations."""
        # Test hash set and get
        await redis_client.hset("test:hash", "field1", "value1")
        await redis_client.hset("test:hash", "field2", "value2")
        
        value = await redis_client.hget("test:hash", "field1")
        assert value == "value1"
        
        all_values = await redis_client.hgetall("test:hash")
        assert all_values == {"field1": "value1", "field2": "value2"}
    
    @pytest.mark.asyncio
    async def test_list_operations(self, setup_redis):
        """Test Redis list operations."""
        # Test list operations
        await redis_client.lpush("test:list", "item1")
        await redis_client.lpush("test:list", "item2")
        
        items = await redis_client.lrange("test:list", 0, -1)
        assert items == ["item2", "item1"]
    
    @pytest.mark.asyncio
    async def test_expiration(self, setup_redis):
        """Test key expiration."""
        # Set key with expiration
        await redis_client.set("test:expiring", "value", ex=1)
        
        # Key should exist initially
        value = await redis_client.get("test:expiring")
        assert value == "value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Key should be gone
        value = await redis_client.get("test:expiring")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_increment(self, setup_redis):
        """Test increment operations."""
        # Test increment
        await redis_client.set("test:counter", "10")
        value = await redis_client.incr("test:counter")
        assert value == 11
        
        value = await redis_client.get("test:counter")
        assert value == "11"


class TestCacheService:
    """
    Tests for the cache service.
    """
    
    @pytest.mark.asyncio
    async def test_get_set_delete(self, setup_redis):
        """Test basic cache operations."""
        # Test set and get
        await cache_service.set("test:cache:key", "value")
        value = await cache_service.get("test:cache:key")
        assert value == "value"
        
        # Test delete
        await cache_service.delete("test:cache:key")
        value = await cache_service.get("test:cache:key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_get_or_set(self, setup_redis):
        """Test get_or_set functionality."""
        # Define a function that returns a value
        async def get_value():
            return "computed_value"
        
        # First call should compute the value
        value = await cache_service.get_or_set("test:cache:computed", get_value, ttl=10)
        assert value == "computed_value"
        
        # Second call should return cached value without calling the function again
        with patch("asyncio.iscoroutinefunction", return_value=True) as mock_is_coro:
            with patch("asyncio.create_task") as mock_create_task:
                value = await cache_service.get_or_set("test:cache:computed", get_value, ttl=10)
                assert value == "computed_value"
                mock_create_task.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_ttl(self, setup_redis):
        """Test TTL functionality."""
        # Set cache with TTL
        await cache_service.set("test:cache:ttl", "value", ttl=1)
        
        # Value should exist initially
        value = await cache_service.get("test:cache:ttl")
        assert value == "value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Value should be gone
        value = await cache_service.get("test:cache:ttl")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_json_serialization(self, setup_redis):
        """Test JSON serialization for complex objects."""
        # Create a complex object
        data = {
            "name": "Test",
            "values": [1, 2, 3],
            "nested": {
                "key": "value"
            }
        }
        
        # Cache the object
        await cache_service.set("test:cache:json", data)
        
        # Retrieve the object
        retrieved = await cache_service.get("test:cache:json")
        assert retrieved == data
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, setup_redis):
        """Test cache invalidation by pattern."""
        # Set multiple cache keys
        await cache_service.set("test:cache:user:1", "user1")
        await cache_service.set("test:cache:user:2", "user2")
        await cache_service.set("test:cache:post:1", "post1")
        
        # Invalidate user cache
        await cache_service.invalidate_by_pattern("test:cache:user:*")
        
        # User cache should be gone
        assert await cache_service.get("test:cache:user:1") is None
        assert await cache_service.get("test:cache:user:2") is None
        
        # Post cache should still exist
        assert await cache_service.get("test:cache:post:1") == "post1"


class TestPubSubService:
    """
    Tests for the pub/sub service.
    """
    
    @pytest.mark.asyncio
    async def test_publish_subscribe(self, setup_redis):
        """Test basic publish/subscribe functionality."""
        # Start the pubsub service
        await pubsub_service.start()
        
        # Create a message handler
        received_messages = []
        
        async def message_handler(channel, message):
            received_messages.append((channel, message))
        
        # Subscribe to a channel
        await pubsub_service.subscribe("test:channel", message_handler)
        
        # Wait for subscription to be active
        await asyncio.sleep(0.1)
        
        # Publish a message
        await pubsub_service.publish("test:channel", "Hello, world!")
        
        # Wait for message to be processed
        await asyncio.sleep(0.1)
        
        # Stop the pubsub service
        await pubsub_service.stop()
        
        # Check that the message was received
        assert len(received_messages) == 1
        assert received_messages[0][0] == "test:channel"
        assert received_messages[0][1] == "Hello, world!"
    
    @pytest.mark.asyncio
    async def test_pattern_subscribe(self, setup_redis):
        """Test pattern-based subscription."""
        # Start the pubsub service
        await pubsub_service.start()
        
        # Create a message handler
        received_messages = []
        
        async def message_handler(channel, message):
            received_messages.append((channel, message))
        
        # Subscribe to a pattern
        await pubsub_service.psubscribe("test:channel:*", message_handler)
        
        # Wait for subscription to be active
        await asyncio.sleep(0.1)
        
        # Publish messages to different channels
        await pubsub_service.publish("test:channel:1", "Message 1")
        await pubsub_service.publish("test:channel:2", "Message 2")
        await pubsub_service.publish("test:other", "Should not receive")
        
        # Wait for messages to be processed
        await asyncio.sleep(0.1)
        
        # Stop the pubsub service
        await pubsub_service.stop()
        
        # Check that the correct messages were received
        assert len(received_messages) == 2
        channels = [msg[0] for msg in received_messages]
        messages = [msg[1] for msg in received_messages]
        
        assert "test:channel:1" in channels
        assert "test:channel:2" in channels
        assert "Message 1" in messages
        assert "Message 2" in messages
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, setup_redis):
        """Test unsubscribe functionality."""
        # Start the pubsub service
        await pubsub_service.start()
        
        # Create a message handler
        received_messages = []
        
        async def message_handler(channel, message):
            received_messages.append((channel, message))
        
        # Subscribe to a channel
        await pubsub_service.subscribe("test:channel", message_handler)
        
        # Wait for subscription to be active
        await asyncio.sleep(0.1)
        
        # Publish a message
        await pubsub_service.publish("test:channel", "Message 1")
        
        # Wait for message to be processed
        await asyncio.sleep(0.1)
        
        # Unsubscribe from the channel
        await pubsub_service.unsubscribe("test:channel")
        
        # Wait for unsubscribe to take effect
        await asyncio.sleep(0.1)
        
        # Publish another message
        await pubsub_service.publish("test:channel", "Message 2")
        
        # Wait for potential message processing
        await asyncio.sleep(0.1)
        
        # Stop the pubsub service
        await pubsub_service.stop()
        
        # Check that only the first message was received
        assert len(received_messages) == 1
        assert received_messages[0][1] == "Message 1"
    
    @pytest.mark.asyncio
    async def test_json_serialization(self, setup_redis):
        """Test JSON serialization for complex messages."""
        # Start the pubsub service
        await pubsub_service.start()
        
        # Create a message handler
        received_messages = []
        
        async def message_handler(channel, message):
            received_messages.append((channel, message))
        
        # Subscribe to a channel
        await pubsub_service.subscribe("test:channel", message_handler)
        
        # Wait for subscription to be active
        await asyncio.sleep(0.1)
        
        # Create a complex object
        data = {
            "name": "Test",
            "values": [1, 2, 3],
            "nested": {
                "key": "value"
            }
        }
        
        # Publish the object
        await pubsub_service.publish("test:channel", data)
        
        # Wait for message to be processed
        await asyncio.sleep(0.1)
        
        # Stop the pubsub service
        await pubsub_service.stop()
        
        # Check that the message was received and deserialized correctly
        assert len(received_messages) == 1
        assert received_messages[0][1] == data


class TestSessionService:
    """
    Tests for the session service.
    """
    
    @pytest.mark.asyncio
    async def test_create_get_session(self, setup_redis):
        """Test session creation and retrieval."""
        # Create a session
        user_id = str(uuid.uuid4())
        session_data = {
            "user_id": user_id,
            "username": "testuser",
            "email": "test@example.com"
        }
        
        session_id = await session_service.create_session(user_id, session_data)
        
        # Get the session
        session = await session_service.get_session(session_id)
        
        # Check session data
        assert session is not None
        assert session["user_id"] == user_id
        assert session["username"] == "testuser"
        assert session["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_update_session(self, setup_redis):
        """Test session update."""
        # Create a session
        user_id = str(uuid.uuid4())
        session_data = {
            "user_id": user_id,
            "username": "testuser",
            "email": "test@example.com"
        }
        
        session_id = await session_service.create_session(user_id, session_data)
        
        # Update the session
        updated_data = {
            "user_id": user_id,
            "username": "updateduser",
            "email": "updated@example.com"
        }
        
        success = await session_service.update_session(session_id, updated_data)
        assert success is True
        
        # Get the updated session
        session = await session_service.get_session(session_id)
        
        # Check updated session data
        assert session is not None
        assert session["username"] == "updateduser"
        assert session["email"] == "updated@example.com"
    
    @pytest.mark.asyncio
    async def test_delete_session(self, setup_redis):
        """Test session deletion."""
        # Create a session
        user_id = str(uuid.uuid4())
        session_data = {
            "user_id": user_id,
            "username": "testuser"
        }
        
        session_id = await session_service.create_session(user_id, session_data)
        
        # Delete the session
        success = await session_service.delete_session(session_id)
        assert success is True
        
        # Try to get the deleted session
        session = await session_service.get_session(session_id)
        assert session is None
    
    @pytest.mark.asyncio
    async def test_session_expiration(self, setup_redis):
        """Test session expiration."""
        # Create a session with short TTL
        user_id = str(uuid.uuid4())
        session_data = {
            "user_id": user_id,
            "username": "testuser"
        }
        
        # Override the TTL for testing
        with patch.object(session_service, '_session_ttl', 1):
            session_id = await session_service.create_session(user_id, session_data)
            
            # Session should exist initially
            session = await session_service.get_session(session_id)
            assert session is not None
            
            # Wait for expiration
            await asyncio.sleep(1.1)
            
            # Session should be gone
            session = await session_service.get_session(session_id)
            assert session is None
    
    @pytest.mark.asyncio
    async def test_get_user_sessions(self, setup_redis):
        """Test retrieving all sessions for a user."""
        # Create multiple sessions for the same user
        user_id = str(uuid.uuid4())
        
        session_id1 = await session_service.create_session(user_id, {"user_id": user_id, "device": "mobile"})
        session_id2 = await session_service.create_session(user_id, {"user_id": user_id, "device": "desktop"})
        
        # Get all sessions for the user
        sessions = await session_service.get_user_sessions(user_id)
        
        # Check that both sessions are returned
        assert len(sessions) == 2
        session_ids = [session["session_id"] for session in sessions]
        assert session_id1 in session_ids
        assert session_id2 in session_ids
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, setup_redis):
        """Test cleanup of expired sessions."""
        # Create sessions with different expiration times
        user_id = str(uuid.uuid4())
        
        # Create an expired session (by directly manipulating Redis)
        expired_session_id = str(uuid.uuid4())
        expired_data = {
            "user_id": user_id,
            "session_id": expired_session_id,
            "created_at": (datetime.now() - timedelta(days=2)).isoformat()
        }
        
        # Set the session with a very short TTL
        await redis_client.set(
            f"{session_service._prefix}{expired_session_id}",
            json.dumps(expired_data),
            ex=1
        )
        
        # Add to user sessions index
        await redis_client.sadd(
            f"{session_service._user_prefix}{user_id}",
            expired_session_id
        )
        
        # Create a valid session
        valid_session_id = await session_service.create_session(
            user_id, 
            {"user_id": user_id, "valid": True}
        )
        
        # Wait for the expired session to expire
        await asyncio.sleep(1.1)
        
        # Run cleanup
        await session_service.cleanup_expired_sessions()
        
        # Check that only the valid session remains in the user's sessions
        sessions = await session_service.get_user_sessions(user_id)
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == valid_session_id


class TestRateLimitService:
    """
    Tests for the rate limit service.
    """
    
    @pytest.mark.asyncio
    async def test_check_rate_limit(self, setup_redis):
        """Test rate limit checking."""
        # Check rate limit with high limit
        allowed, count, ttl = await rate_limit_service.check_rate_limit(
            "test", "test_user", limit=100, window=10
        )
        
        # Should be allowed
        assert allowed is True
        assert count == 1
        assert ttl > 0
    
    @pytest.mark.asyncio
    async def test_increment_rate_limit(self, setup_redis):
        """Test rate limit incrementation."""
        # Set a low limit
        limit = 3
        window = 10
        
        # First request should be allowed
        allowed, count, ttl = await rate_limit_service.increment_rate_limit(
            "test", "test_user", limit=limit, window=window
        )
        assert allowed is True
        assert count == 1
        
        # Second request should be allowed
        allowed, count, ttl = await rate_limit_service.increment_rate_limit(
            "test", "test_user", limit=limit, window=window
        )
        assert allowed is True
        assert count == 2
        
        # Third request should be allowed
        allowed, count, ttl = await rate_limit_service.increment_rate_limit(
            "test", "test_user", limit=limit, window=window
        )
        assert allowed is True
        assert count == 3
        
        # Fourth request should be denied
        allowed, count, ttl = await rate_limit_service.increment_rate_limit(
            "test", "test_user", limit=limit, window=window
        )
        assert allowed is False
        assert count == 4
    
    @pytest.mark.asyncio
    async def test_get_rate_limit(self, setup_redis):
        """Test getting current rate limit count."""
        # Increment the rate limit
        await rate_limit_service.increment_rate_limit(
            "test", "test_user", limit=10, window=10
        )
        
        # Get the current count
        count, ttl = await rate_limit_service.get_rate_limit("test", "test_user")
        
        # Check the count
        assert count == 1
        assert ttl > 0
    
    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, setup_redis):
        """Test resetting rate limit."""
        # Increment the rate limit multiple times
        for _ in range(5):
            await rate_limit_service.increment_rate_limit(
                "test", "test_user", limit=10, window=10
            )
        
        # Get the current count
        count, _ = await rate_limit_service.get_rate_limit("test", "test_user")
        assert count == 5
        
        # Reset the rate limit
        success = await rate_limit_service.reset_rate_limit("test", "test_user")
        assert success is True
        
        # Check that the count is reset
        count, _ = await rate_limit_service.get_rate_limit("test", "test_user")
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_is_rate_limited(self, setup_redis):
        """Test checking if rate limited without incrementing."""
        # Set a low limit
        limit = 3
        window = 10
        
        # Increment the rate limit to just below the limit
        for _ in range(2):
            await rate_limit_service.increment_rate_limit(
                "test", "test_user", limit=limit, window=window
            )
        
        # Check if rate limited (should not be)
        is_limited = await rate_limit_service.is_rate_limited(
            "test", "test_user", limit=limit, window=window
        )
        assert is_limited is False
        
        # Increment one more time to reach the limit
        await rate_limit_service.increment_rate_limit(
            "test", "test_user", limit=limit, window=window
        )
        
        # Check if rate limited (should be)
        is_limited = await rate_limit_service.is_rate_limited(
            "test", "test_user", limit=limit, window=window
        )
        assert is_limited is True
    
    @pytest.mark.asyncio
    async def test_different_limit_types(self, setup_redis):
        """Test different limit types have separate counters."""
        # Increment rate limits for different types
        await rate_limit_service.increment_rate_limit("api", "test_user", limit=10)
        await rate_limit_service.increment_rate_limit("auth", "test_user", limit=10)
        
        # Get counts for each type
        api_count, _ = await rate_limit_service.get_rate_limit("api", "test_user")
        auth_count, _ = await rate_limit_service.get_rate_limit("auth", "test_user")
        
        # Each type should have its own counter
        assert api_count == 1
        assert auth_count == 1
    
    @pytest.mark.asyncio
    async def test_different_identifiers(self, setup_redis):
        """Test different identifiers have separate counters."""
        # Increment rate limits for different users
        await rate_limit_service.increment_rate_limit("api", "user1", limit=10)
        await rate_limit_service.increment_rate_limit("api", "user2", limit=10)
        
        # Get counts for each user
        user1_count, _ = await rate_limit_service.get_rate_limit("api", "user1")
        user2_count, _ = await rate_limit_service.get_rate_limit("api", "user2")
        
        # Each user should have their own counter
        assert user1_count == 1
        assert user2_count == 1