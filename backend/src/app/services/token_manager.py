"""
Token Manager for the AI Project Assistant.
This module provides functionality for tracking token usage and implementing rate limiting.
"""
from typing import Dict, List, Any, Optional, Union, Tuple
import json
import asyncio
from datetime import datetime, timedelta
import uuid
from loguru import logger
from pydantic import BaseModel, Field

from ..config import settings
from ..models.agent import generate_uuid

# Try to import tiktoken for token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    logger.warning("tiktoken not installed, falling back to approximate token counting")
    TIKTOKEN_AVAILABLE = False


class TokenUsage(BaseModel):
    """Model for token usage tracking."""
    id: str = Field(default_factory=generate_uuid)
    user_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    model: Optional[str] = None
    endpoint: Optional[str] = None


class UserQuota(BaseModel):
    """Model for user token quotas."""
    user_id: str
    max_tokens_per_day: int = 100000
    max_tokens_per_minute: int = 10000
    current_usage_day: int = 0
    current_usage_minute: int = 0
    last_reset_day: datetime = Field(default_factory=datetime.now)
    last_reset_minute: datetime = Field(default_factory=datetime.now)


class TokenManager:
    """Service for tracking token usage and implementing rate limiting."""
    
    def __init__(self):
        """Initialize the token manager."""
        # In-memory storage for token usage
        # In a production environment, this would be stored in a database
        self._token_usage: List[TokenUsage] = []
        
        # In-memory storage for user quotas
        # In a production environment, this would be stored in a database
        self._user_quotas: Dict[str, UserQuota] = {}
        
        # In-memory storage for correlation IDs
        # Maps correlation_id to session_id and user_id
        self._correlation_ids: Dict[str, Dict[str, str]] = {}
        
        # Initialize tokenizer
        if TIKTOKEN_AVAILABLE:
            self._tokenizer = tiktoken.encoding_for_model(settings.DEFAULT_LLM_MODEL)
        else:
            self._tokenizer = None
    
    async def track_usage(
        self,
        user_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> TokenUsage:
        """
        Track token usage for a user.
        
        Args:
            user_id: User ID
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            correlation_id: Optional correlation ID
            session_id: Optional session ID
            model: Optional model name
            endpoint: Optional API endpoint
            
        Returns:
            TokenUsage object
        """
        total_tokens = prompt_tokens + completion_tokens
        
        # Create token usage record
        usage = TokenUsage(
            user_id=user_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            correlation_id=correlation_id,
            session_id=session_id,
            model=model,
            endpoint=endpoint
        )
        
        # Store token usage
        self._token_usage.append(usage)
        
        # Update user quota
        await self._update_user_quota(user_id, total_tokens)
        
        # Log token usage
        logger.debug(f"Token usage: {user_id} - {prompt_tokens} prompt, {completion_tokens} completion, {total_tokens} total")
        
        return usage
    
    async def check_rate_limit(
        self,
        user_id: str,
        estimated_tokens: int
    ) -> bool:
        """
        Check if a user has exceeded their rate limit.
        
        Args:
            user_id: User ID
            estimated_tokens: Estimated number of tokens for the request
            
        Returns:
            True if the user is within their rate limit, False otherwise
        """
        # Get or create user quota
        quota = await self._get_or_create_user_quota(user_id)
        
        # Check if day quota needs to be reset
        now = datetime.now()
        if (now - quota.last_reset_day).days > 0:
            quota.current_usage_day = 0
            quota.last_reset_day = now
        
        # Check if minute quota needs to be reset
        if (now - quota.last_reset_minute).seconds > 60:
            quota.current_usage_minute = 0
            quota.last_reset_minute = now
        
        # Check if user would exceed day quota
        if quota.current_usage_day + estimated_tokens > quota.max_tokens_per_day:
            logger.warning(f"User {user_id} would exceed day quota: {quota.current_usage_day}/{quota.max_tokens_per_day}")
            return False
        
        # Check if user would exceed minute quota
        if quota.current_usage_minute + estimated_tokens > quota.max_tokens_per_minute:
            logger.warning(f"User {user_id} would exceed minute quota: {quota.current_usage_minute}/{quota.max_tokens_per_minute}")
            return False
        
        return True
    
    async def generate_correlation_id(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Generate a correlation ID for tracking message chains.
        
        Args:
            user_id: User ID
            session_id: Optional session ID
            
        Returns:
            Correlation ID
        """
        correlation_id = str(uuid.uuid4())
        
        # Store correlation ID mapping
        self._correlation_ids[correlation_id] = {
            "user_id": user_id,
            "session_id": session_id,
            "created_at": datetime.now().isoformat()
        }
        
        return correlation_id
    
    async def get_usage_stats(
        self,
        user_id: str,
        time_period: Optional[str] = "day"
    ) -> Dict[str, Any]:
        """
        Get token usage statistics for a user.
        
        Args:
            user_id: User ID
            time_period: Time period for statistics (day, week, month, all)
            
        Returns:
            Dictionary of usage statistics
        """
        # Filter usage records by user ID
        user_usage = [u for u in self._token_usage if u.user_id == user_id]
        
        # Filter by time period
        now = datetime.now()
        if time_period == "day":
            start_time = now - timedelta(days=1)
            user_usage = [u for u in user_usage if u.timestamp >= start_time]
        elif time_period == "week":
            start_time = now - timedelta(weeks=1)
            user_usage = [u for u in user_usage if u.timestamp >= start_time]
        elif time_period == "month":
            start_time = now - timedelta(days=30)
            user_usage = [u for u in user_usage if u.timestamp >= start_time]
        
        # Calculate statistics
        total_prompt_tokens = sum(u.prompt_tokens for u in user_usage)
        total_completion_tokens = sum(u.completion_tokens for u in user_usage)
        total_tokens = sum(u.total_tokens for u in user_usage)
        
        # Get quota
        quota = await self._get_or_create_user_quota(user_id)
        
        # Create statistics
        stats = {
            "user_id": user_id,
            "time_period": time_period,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "request_count": len(user_usage),
            "quota_day": {
                "limit": quota.max_tokens_per_day,
                "used": quota.current_usage_day,
                "remaining": quota.max_tokens_per_day - quota.current_usage_day
            },
            "quota_minute": {
                "limit": quota.max_tokens_per_minute,
                "used": quota.current_usage_minute,
                "remaining": quota.max_tokens_per_minute - quota.current_usage_minute
            }
        }
        
        return stats
    
    async def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if TIKTOKEN_AVAILABLE and self._tokenizer:
            # Use tiktoken for accurate token counting
            return len(self._tokenizer.encode(text))
        else:
            # Fallback to approximate token counting
            # This is a very rough approximation
            return len(text) // 4
    
    async def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Count the number of tokens in a list of messages.
        
        Args:
            messages: List of messages
            
        Returns:
            Number of tokens
        """
        if TIKTOKEN_AVAILABLE and self._tokenizer:
            # Use tiktoken for accurate token counting
            token_count = 0
            
            # Count tokens in each message
            for message in messages:
                # Add tokens for message role and content
                token_count += 4  # Every message follows <im_start>{role/name}\n{content}<im_end>\n
                
                for key, value in message.items():
                    token_count += len(self._tokenizer.encode(value))
                    
                    # If the key is "name", add 1 token
                    if key == "name":
                        token_count += 1
            
            # Add tokens for the assistant's reply
            token_count += 2  # Every reply is primed with <im_start>assistant
            
            return token_count
        else:
            # Fallback to approximate token counting
            # This is a very rough approximation
            text = json.dumps(messages)
            return len(text) // 4
    
    async def _update_user_quota(self, user_id: str, tokens: int) -> None:
        """
        Update a user's token quota.
        
        Args:
            user_id: User ID
            tokens: Number of tokens to add to the quota
        """
        # Get or create user quota
        quota = await self._get_or_create_user_quota(user_id)
        
        # Check if day quota needs to be reset
        now = datetime.now()
        if (now - quota.last_reset_day).days > 0:
            quota.current_usage_day = 0
            quota.last_reset_day = now
        
        # Check if minute quota needs to be reset
        if (now - quota.last_reset_minute).seconds > 60:
            quota.current_usage_minute = 0
            quota.last_reset_minute = now
        
        # Update quotas
        quota.current_usage_day += tokens
        quota.current_usage_minute += tokens
        
        # Store updated quota
        self._user_quotas[user_id] = quota
    
    async def _get_or_create_user_quota(self, user_id: str) -> UserQuota:
        """
        Get or create a user's token quota.
        
        Args:
            user_id: User ID
            
        Returns:
            UserQuota object
        """
        if user_id not in self._user_quotas:
            self._user_quotas[user_id] = UserQuota(user_id=user_id)
        
        return self._user_quotas[user_id]


# Create a singleton instance
token_manager = TokenManager()