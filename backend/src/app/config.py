"""
Configuration settings for the application.
"""
import os
import json
from typing import List, Optional, Union, Any, Dict
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.
    """
    # General settings
    DEBUG: bool = Field(default=True)
    ENVIRONMENT: str = Field(default="development")
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    # CORS settings
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    # JWT settings
    JWT_SECRET: str = Field(default="your-secret-key-change-in-production")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    
    # Neo4j settings
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USERNAME: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="password")
    NEO4J_DATABASE: str = Field(default="neo4j")
    
    # Qdrant settings
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: Optional[str] = Field(default=None)
    QDRANT_COLLECTION: str = Field(default="ai-project-assistant")
    
    # Redis settings
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_DB: int = Field(default=0)
    REDIS_SSL: bool = Field(default=False)
    REDIS_CONNECTION_POOL_SIZE: int = Field(default=10)
    REDIS_SOCKET_TIMEOUT: int = Field(default=5)  # seconds
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(default=5)  # seconds
    REDIS_RETRY_ON_TIMEOUT: bool = Field(default=True)
    REDIS_MAX_CONNECTIONS: int = Field(default=50)
    
    # Caching settings
    CACHE_ENABLED: bool = Field(default=True)
    CACHE_STAMPEDE_PROTECTION_WINDOW: int = Field(default=30)  # seconds
    CACHE_STAMPEDE_LOCK_TIMEOUT: int = Field(default=5)  # seconds
    
    # Cache TTLs for different types of data
    CACHE_TTL_DEFAULT: int = Field(default=300)  # 5 minutes in seconds
    CACHE_TTL_DOCUMENT: int = Field(default=600)  # 10 minutes
    CACHE_TTL_PROJECT: int = Field(default=1800)  # 30 minutes
    CACHE_TTL_USER: int = Field(default=3600)  # 1 hour
    CACHE_TTL_MERMAID: int = Field(default=86400)  # 24 hours
    CACHE_TTL_EMBEDDING: int = Field(default=604800)  # 7 days
    CACHE_TTL_LLM: int = Field(default=3600)  # 1 hour
    CACHE_TTL_SESSION: int = Field(default=86400)  # 24 hours
    CACHE_TTL_SEARCH: int = Field(default=300)  # 5 minutes
    
    # Pub/Sub settings
    PUBSUB_CHANNELS: Dict[str, str] = Field(default={
        "document_updates": "channel:document_updates",
        "project_updates": "channel:project_updates",
        "agent_tasks": "channel:agent_tasks",
        "notifications": "channel:notifications",
        "system_events": "channel:system_events"
    })
    
    # Session management
    SESSION_TTL: int = Field(default=86400)  # 24 hours in seconds
    SESSION_RENEWAL_THRESHOLD: int = Field(default=3600)  # 1 hour in seconds
    SESSION_COOKIE_NAME: str = Field(default="session_id")
    SESSION_COOKIE_SECURE: bool = Field(default=False)  # Set to True in production
    SESSION_COOKIE_HTTPONLY: bool = Field(default=True)
    SESSION_MAX_PER_USER: int = Field(default=5)  # Maximum sessions per user
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_DEFAULT: int = Field(default=100)  # requests per minute
    RATE_LIMIT_WINDOW_DEFAULT: int = Field(default=60)  # 1 minute in seconds
    
    # Rate limits for different types of operations
    RATE_LIMIT_API: int = Field(default=100)  # General API requests per minute
    RATE_LIMIT_AUTH: int = Field(default=10)  # Auth requests per minute
    RATE_LIMIT_USER: int = Field(default=60)  # User-specific requests per minute
    RATE_LIMIT_ADMIN: int = Field(default=30)  # Admin requests per minute
    RATE_LIMIT_LLM: int = Field(default=20)  # LLM requests per minute
    
    # Rate limit windows for different types of operations
    RATE_LIMIT_WINDOW_API: int = Field(default=60)  # 1 minute in seconds
    RATE_LIMIT_WINDOW_AUTH: int = Field(default=300)  # 5 minutes in seconds
    RATE_LIMIT_WINDOW_USER: int = Field(default=60)  # 1 minute in seconds
    RATE_LIMIT_WINDOW_ADMIN: int = Field(default=60)  # 1 minute in seconds
    RATE_LIMIT_WINDOW_LLM: int = Field(default=60)  # 1 minute in seconds
    
    RATE_LIMIT_BY_USER: bool = Field(default=True)
    RATE_LIMIT_BY_IP: bool = Field(default=True)
    RATE_LIMIT_ENDPOINTS: Dict[str, int] = Field(default={
        "/api/v1/ai/chat": 30,  # 30 requests per minute
        "/api/v1/documents": 60,  # 60 requests per minute
        "/api/v1/projects": 60,  # 60 requests per minute
    })
    
    # LLM settings
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    DEFAULT_LLM_MODEL: str = Field(default="gpt-4o")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    EMBEDDING_DIMENSION: int = Field(default=1536)
    
    # File storage settings
    UPLOAD_DIR: str = Field(default="uploads")
    MAX_UPLOAD_SIZE: int = Field(default=10 * 1024 * 1024)  # 10 MB
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO")
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """
        Parse CORS_ORIGINS from string to list if needed.
        """
        if isinstance(v, str):
            # If the string is empty, return default value
            if not v.strip():
                return ["http://localhost:3000", "http://127.0.0.1:3000"]
                
            try:
                # Try to parse as JSON
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                else:
                    # If parsed but not a list, wrap in a list
                    return [str(parsed)]
            except json.JSONDecodeError:
                # If not valid JSON, split by comma
                return [origin.strip() for origin in v.split(',') if origin.strip()]
        
        # If already a list or other iterable, convert all items to strings
        if isinstance(v, (list, tuple, set)):
            return [str(item) for item in v]
            
        # If none of the above, return default value
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    @field_validator('PUBSUB_CHANNELS', mode='before')
    @classmethod
    def parse_pubsub_channels(cls, v: Any) -> Dict[str, str]:
        """
        Parse PUBSUB_CHANNELS from string to dict if needed.
        """
        default_channels = {
            "document_updates": "channel:document_updates",
            "project_updates": "channel:project_updates",
            "agent_tasks": "channel:agent_tasks",
            "notifications": "channel:notifications",
            "system_events": "channel:system_events"
        }
        
        if isinstance(v, str):
            # If the string is empty, return default value
            if not v.strip():
                return default_channels
                
            try:
                # Try to parse as JSON
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    return default_channels
            except json.JSONDecodeError:
                return default_channels
        
        # If already a dict, return it
        if isinstance(v, dict):
            return v
            
        # If none of the above, return default value
        return default_channels
    
    @field_validator('RATE_LIMIT_ENDPOINTS', mode='before')
    @classmethod
    def parse_rate_limit_endpoints(cls, v: Any) -> Dict[str, int]:
        """
        Parse RATE_LIMIT_ENDPOINTS from string to dict if needed.
        """
        default_endpoints = {
            "/api/v1/ai/chat": 30,
            "/api/v1/documents": 60,
            "/api/v1/projects": 60,
        }
        
        if isinstance(v, str):
            # If the string is empty, return default value
            if not v.strip():
                return default_endpoints
                
            try:
                # Try to parse as JSON
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    return default_endpoints
            except json.JSONDecodeError:
                return default_endpoints
        
        # If already a dict, return it
        if isinstance(v, dict):
            return v
            
        # If none of the above, return default value
        return default_endpoints
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Create a singleton instance
settings = Settings()