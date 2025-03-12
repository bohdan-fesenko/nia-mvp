"""
Rate limiting service for the application.
This module provides a service for rate limiting API requests using Redis.
"""
import logging
import time
import hashlib
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import asyncio

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..config import settings
from ..db.redis_client import redis_client

logger = logging.getLogger(__name__)


class RateLimitService:
    """
    Rate limiting service for the application.
    """
    def __init__(self):
        """
        Initialize the rate limit service.
        """
        self._client = redis_client
        self._enabled = settings.RATE_LIMIT_ENABLED
        self._default_limit = settings.RATE_LIMIT_DEFAULT
        self._default_window = settings.RATE_LIMIT_WINDOW_DEFAULT
        self._limit_mapping = {
            'api': settings.RATE_LIMIT_API,
            'auth': settings.RATE_LIMIT_AUTH,
            'user': settings.RATE_LIMIT_USER,
            'admin': settings.RATE_LIMIT_ADMIN,
            'llm': settings.RATE_LIMIT_LLM,
        }
        self._window_mapping = {
            'api': settings.RATE_LIMIT_WINDOW_API,
            'auth': settings.RATE_LIMIT_WINDOW_AUTH,
            'user': settings.RATE_LIMIT_WINDOW_USER,
            'admin': settings.RATE_LIMIT_WINDOW_ADMIN,
            'llm': settings.RATE_LIMIT_WINDOW_LLM,
        }
        self._prefix = "rate_limit:"

    def _get_limit(self, limit_type: str) -> int:
        """
        Get the rate limit for a limit type.
        
        Args:
            limit_type: The type of rate limit.
            
        Returns:
            The rate limit.
        """
        return self._limit_mapping.get(limit_type, self._default_limit)

    def _get_window(self, limit_type: str) -> int:
        """
        Get the rate limit window for a limit type.
        
        Args:
            limit_type: The type of rate limit.
            
        Returns:
            The rate limit window in seconds.
        """
        return self._window_mapping.get(limit_type, self._default_window)

    def _generate_key(self, limit_type: str, identifier: str) -> str:
        """
        Generate a rate limit key.
        
        Args:
            limit_type: The type of rate limit.
            identifier: The identifier (e.g., IP address, user ID).
            
        Returns:
            The rate limit key.
        """
        return f"{self._prefix}{limit_type}:{identifier}"

    async def check_rate_limit(
        self, 
        limit_type: str, 
        identifier: str, 
        limit: Optional[int] = None, 
        window: Optional[int] = None
    ) -> Tuple[bool, int, int]:
        """
        Check if a rate limit has been exceeded.
        
        Args:
            limit_type: The type of rate limit.
            identifier: The identifier (e.g., IP address, user ID).
            limit: The maximum number of requests allowed in the window.
                  If None, the limit for the limit type will be used.
            window: The time window in seconds.
                   If None, the window for the limit type will be used.
            
        Returns:
            A tuple of (allowed, current_count, ttl) where:
            - allowed is True if the request is allowed, False otherwise.
            - current_count is the current count of requests.
            - ttl is the time-to-live for the rate limit in seconds.
        """
        if not self._enabled:
            return True, 0, 0
        
        # Get the limit and window
        limit_value = limit or self._get_limit(limit_type)
        window_value = window or self._get_window(limit_type)
        
        # Generate the key
        key = self._generate_key(limit_type, identifier)
        
        # Check the rate limit
        return await self._client.increment_rate_limit(key, limit_value, window_value)

    async def increment_rate_limit(
        self, 
        limit_type: str, 
        identifier: str, 
        limit: Optional[int] = None, 
        window: Optional[int] = None
    ) -> Tuple[bool, int, int]:
        """
        Increment a rate limit counter and check if the limit has been exceeded.
        
        Args:
            limit_type: The type of rate limit.
            identifier: The identifier (e.g., IP address, user ID).
            limit: The maximum number of requests allowed in the window.
                  If None, the limit for the limit type will be used.
            window: The time window in seconds.
                   If None, the window for the limit type will be used.
            
        Returns:
            A tuple of (allowed, current_count, ttl) where:
            - allowed is True if the request is allowed, False otherwise.
            - current_count is the current count of requests.
            - ttl is the time-to-live for the rate limit in seconds.
        """
        if not self._enabled:
            return True, 0, 0
        
        # Get the limit and window
        limit_value = limit or self._get_limit(limit_type)
        window_value = window or self._get_window(limit_type)
        
        # Generate the key
        key = self._generate_key(limit_type, identifier)
        
        # Increment the rate limit
        return await self._client.increment_rate_limit(key, limit_value, window_value)

    async def get_rate_limit(self, limit_type: str, identifier: str) -> Tuple[int, int]:
        """
        Get the current rate limit count and TTL.
        
        Args:
            limit_type: The type of rate limit.
            identifier: The identifier (e.g., IP address, user ID).
            
        Returns:
            A tuple of (count, ttl) where:
            - count is the current count of requests.
            - ttl is the time-to-live for the rate limit in seconds.
        """
        if not self._enabled:
            return 0, 0
        
        # Generate the key
        key = self._generate_key(limit_type, identifier)
        
        # Get the rate limit
        return await self._client.get_rate_limit(key)

    async def reset_rate_limit(self, limit_type: str, identifier: str) -> bool:
        """
        Reset a rate limit counter.
        
        Args:
            limit_type: The type of rate limit.
            identifier: The identifier (e.g., IP address, user ID).
            
        Returns:
            True if the rate limit was reset, False otherwise.
        """
        if not self._enabled:
            return True
        
        # Generate the key
        key = self._generate_key(limit_type, identifier)
        
        # Reset the rate limit
        return await self._client.reset_rate_limit(key)

    async def is_rate_limited(
        self, 
        limit_type: str, 
        identifier: str, 
        limit: Optional[int] = None, 
        window: Optional[int] = None
    ) -> bool:
        """
        Check if a rate limit has been exceeded without incrementing the counter.
        
        Args:
            limit_type: The type of rate limit.
            identifier: The identifier (e.g., IP address, user ID).
            limit: The maximum number of requests allowed in the window.
                  If None, the limit for the limit type will be used.
            window: The time window in seconds.
                   If None, the window for the limit type will be used.
            
        Returns:
            True if the rate limit has been exceeded, False otherwise.
        """
        if not self._enabled:
            return False
        
        # Get the limit
        limit_value = limit or self._get_limit(limit_type)
        
        # Get the current count and TTL
        count, _ = await self.get_rate_limit(limit_type, identifier)
        
        # Check if the limit has been exceeded
        return count >= limit_value


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.
    """
    def __init__(
        self, 
        app: ASGIApp, 
        limit_type: str = 'api', 
        get_identifier: Optional[callable] = None,
        exclude_paths: Optional[List[str]] = None,
        bypass_key_header: Optional[str] = None,
        bypass_key_value: Optional[str] = None
    ):
        """
        Initialize the rate limit middleware.
        
        Args:
            app: The ASGI application.
            limit_type: The type of rate limit to use.
            get_identifier: A function that takes a request and returns an identifier.
                          If None, the client IP address will be used.
            exclude_paths: A list of paths to exclude from rate limiting.
            bypass_key_header: The header name for the bypass key.
            bypass_key_value: The value for the bypass key.
        """
        super().__init__(app)
        self._rate_limit_service = rate_limit_service
        self._limit_type = limit_type
        self._get_identifier = get_identifier or self._default_get_identifier
        self._exclude_paths = exclude_paths or []
        self._bypass_key_header = bypass_key_header
        self._bypass_key_value = bypass_key_value

    def _default_get_identifier(self, request: Request) -> str:
        """
        Get the default identifier for a request (client IP address).
        
        Args:
            request: The request.
            
        Returns:
            The identifier.
        """
        # Get the client IP address
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # X-Forwarded-For can be a comma-separated list of IPs
            # The client's IP is the first one
            ip = forwarded_for.split(',')[0].strip()
        else:
            # If no X-Forwarded-For header, use the client's IP
            ip = request.client.host if request.client else 'unknown'
        
        return ip

    async def dispatch(self, request: Request, call_next):
        """
        Dispatch the request with rate limiting.
        
        Args:
            request: The request.
            call_next: The next middleware or route handler.
            
        Returns:
            The response.
        """
        # Check if the path should be excluded
        path = request.url.path
        if any(path.startswith(exclude_path) for exclude_path in self._exclude_paths):
            return await call_next(request)
        
        # Check if the request has a bypass key
        if self._bypass_key_header and self._bypass_key_value:
            bypass_key = request.headers.get(self._bypass_key_header)
            if bypass_key == self._bypass_key_value:
                return await call_next(request)
        
        # Get the identifier
        identifier = self._get_identifier(request)
        
        # Check the rate limit
        allowed, count, ttl = await self._rate_limit_service.increment_rate_limit(self._limit_type, identifier)
        
        # Set rate limit headers
        headers = {
            'X-RateLimit-Limit': str(self._rate_limit_service._get_limit(self._limit_type)),
            'X-RateLimit-Remaining': str(max(0, self._rate_limit_service._get_limit(self._limit_type) - count)),
            'X-RateLimit-Reset': str(ttl)
        }
        
        # If the rate limit has been exceeded, return a 429 response
        if not allowed:
            return HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers=headers
            )
        
        # Otherwise, process the request
        response = await call_next(request)
        
        # Add rate limit headers to the response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# Create a singleton instance
rate_limit_service = RateLimitService()

# Create a factory function for the service
def create_rate_limit_service(redis_client) -> RateLimitService:
    """
    Create a rate limit service.
    
    Args:
        redis_client: Redis client
        
    Returns:
        A rate limit service
    """
    # We're using a singleton pattern, so just return the existing instance
    # In a real implementation, you might create a new instance with the provided client
    return rate_limit_service