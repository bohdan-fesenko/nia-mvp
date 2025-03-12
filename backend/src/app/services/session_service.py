"""
Session management service for the application.
This module provides a service for managing user sessions using Redis.
"""
import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

from ..config import settings
from ..db.redis_client import redis_client

logger = logging.getLogger(__name__)


class SessionService:
    """
    Session management service for the application.
    """
    def __init__(self):
        """
        Initialize the session service.
        """
        self._client = redis_client
        self._session_ttl = settings.SESSION_TTL
        self._session_renewal_threshold = settings.SESSION_RENEWAL_THRESHOLD
        self._session_prefix = "session:"
        self._user_sessions_prefix = "user_sessions:"

    async def create_session(self, user_id: str, data: Dict[str, Any] = None) -> str:
        """
        Create a new session.
        
        Args:
            user_id: The ID of the user.
            data: Additional session data.
            
        Returns:
            The session ID.
        """
        # Generate a session ID
        session_id = str(uuid.uuid4())
        
        # Create session data
        session_data = {
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'last_accessed': datetime.utcnow().isoformat(),
            'data': data or {}
        }
        
        # Store the session in Redis
        key = f"{self._session_prefix}{session_id}"
        success = await self._client.set_object_async(key, session_data, ttl=self._session_ttl)
        
        if success:
            # Add the session ID to the user's sessions set
            user_sessions_key = f"{self._user_sessions_prefix}{user_id}"
            await self._client._async_client.sadd(user_sessions_key, session_id)
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return session_id
        else:
            logger.error(f"Failed to create session for user {user_id}")
            return ""

    async def get_session(self, session_id: str, renew: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get a session.
        
        Args:
            session_id: The ID of the session.
            renew: Whether to renew the session if it's close to expiration.
            
        Returns:
            The session data, or None if not found.
        """
        key = f"{self._session_prefix}{session_id}"
        
        # Get the session data
        session_data = await self._client.get_object_async(key)
        
        if session_data is None:
            return None
        
        # Update last accessed time
        session_data['last_accessed'] = datetime.utcnow().isoformat()
        
        # Check if the session needs renewal
        if renew:
            # Get the TTL
            ttl = await self._client.ttl_async(key)
            
            # If the TTL is less than the renewal threshold, renew the session
            if ttl > 0 and ttl < self._session_renewal_threshold:
                await self._client.set_object_async(key, session_data, ttl=self._session_ttl)
                logger.debug(f"Renewed session {session_id}")
            else:
                # Just update the last accessed time
                await self._client.set_object_async(key, session_data, ttl=ttl)
        
        return session_data

    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a session.
        
        Args:
            session_id: The ID of the session.
            data: The data to update.
            
        Returns:
            True if the session was updated, False otherwise.
        """
        key = f"{self._session_prefix}{session_id}"
        
        # Get the session data
        session_data = await self._client.get_object_async(key)
        
        if session_data is None:
            logger.error(f"Session {session_id} not found")
            return False
        
        # Update the session data
        session_data['data'].update(data)
        session_data['last_accessed'] = datetime.utcnow().isoformat()
        
        # Get the TTL
        ttl = await self._client.ttl_async(key)
        
        # If the TTL is less than the renewal threshold, renew the session
        if ttl > 0 and ttl < self._session_renewal_threshold:
            ttl = self._session_ttl
        
        # Update the session in Redis
        success = await self._client.set_object_async(key, session_data, ttl=ttl)
        
        if success:
            logger.debug(f"Updated session {session_id}")
            return True
        else:
            logger.error(f"Failed to update session {session_id}")
            return False

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The ID of the session.
            
        Returns:
            True if the session was deleted, False otherwise.
        """
        key = f"{self._session_prefix}{session_id}"
        
        # Get the session data to find the user ID
        session_data = await self._client.get_object_async(key)
        
        if session_data is None:
            logger.error(f"Session {session_id} not found")
            return False
        
        # Delete the session
        success = await self._client.delete_async(key)
        
        if success:
            # Remove the session ID from the user's sessions set
            user_id = session_data.get('user_id')
            if user_id:
                user_sessions_key = f"{self._user_sessions_prefix}{user_id}"
                await self._client._async_client.srem(user_sessions_key, session_id)
            
            logger.info(f"Deleted session {session_id}")
            return True
        else:
            logger.error(f"Failed to delete session {session_id}")
            return False

    async def get_user_sessions(self, user_id: str) -> List[str]:
        """
        Get all session IDs for a user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            A list of session IDs.
        """
        user_sessions_key = f"{self._user_sessions_prefix}{user_id}"
        
        # Get the session IDs
        session_ids = await self._client._async_client.smembers(user_sessions_key)
        
        # Convert bytes to strings
        return [s.decode('utf-8') if isinstance(s, bytes) else s for s in session_ids]

    async def delete_user_sessions(self, user_id: str) -> int:
        """
        Delete all sessions for a user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            The number of sessions deleted.
        """
        # Get all session IDs for the user
        session_ids = await self.get_user_sessions(user_id)
        
        # Delete each session
        count = 0
        for session_id in session_ids:
            if await self.delete_session(session_id):
                count += 1
        
        # Delete the user's sessions set
        user_sessions_key = f"{self._user_sessions_prefix}{user_id}"
        await self._client.delete_async(user_sessions_key)
        
        logger.info(f"Deleted {count} sessions for user {user_id}")
        return count

    async def get_session_count(self) -> int:
        """
        Get the total number of active sessions.
        
        Returns:
            The number of active sessions.
        """
        await self._client.connect_async()
        
        try:
            # Use the SCAN command to count keys matching the session prefix
            cursor = 0
            count = 0
            
            while True:
                cursor, keys = await self._client._async_client.scan(cursor, match=f"{self._session_prefix}*", count=100)
                count += len(keys)
                
                # If the cursor is 0, we've scanned all keys
                if cursor == 0:
                    break
            
            return count
        except Exception as e:
            logger.error(f"Error counting sessions: {str(e)}")
            return 0

    async def get_user_session_count(self, user_id: str) -> int:
        """
        Get the number of active sessions for a user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            The number of active sessions for the user.
        """
        user_sessions_key = f"{self._user_sessions_prefix}{user_id}"
        
        try:
            # Get the count of session IDs in the user's sessions set
            return await self._client._async_client.scard(user_sessions_key)
        except Exception as e:
            logger.error(f"Error counting sessions for user {user_id}: {str(e)}")
            return 0

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        This is a maintenance operation that should be run periodically.
        
        Returns:
            The number of expired sessions cleaned up.
        """
        # Redis automatically removes expired keys, so we don't need to do anything
        # However, we should clean up any session IDs in user session sets that don't have corresponding sessions
        
        await self._client.connect_async()
        
        try:
            # Get all user session sets
            cursor = 0
            count = 0
            
            while True:
                cursor, keys = await self._client._async_client.scan(cursor, match=f"{self._user_sessions_prefix}*", count=100)
                
                for key in keys:
                    # Get all session IDs in the set
                    user_key = key.decode('utf-8') if isinstance(key, bytes) else key
                    session_ids = await self._client._async_client.smembers(user_key)
                    
                    # Check each session ID
                    for session_id in session_ids:
                        session_id_str = session_id.decode('utf-8') if isinstance(session_id, bytes) else session_id
                        session_key = f"{self._session_prefix}{session_id_str}"
                        
                        # If the session doesn't exist, remove it from the set
                        if not await self._client.exists_async(session_key):
                            await self._client._async_client.srem(user_key, session_id)
                            count += 1
                
                # If the cursor is 0, we've scanned all keys
                if cursor == 0:
                    break
            
            logger.info(f"Cleaned up {count} expired sessions")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return 0


# Create a singleton instance
session_service = SessionService()