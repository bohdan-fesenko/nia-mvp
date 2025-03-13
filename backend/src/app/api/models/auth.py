"""
Authentication models.
This module provides models for authentication.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

from ...db.models import AppBaseModel, UserResponse


class UserCreate(AppBaseModel):
    """
    Model for user registration
    """
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)
    image: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "password": "securepassword123",
                "image": "https://example.com/avatar.jpg"
            }
        }
    )


class UserLogin(AppBaseModel):
    """
    Model for user login
    """
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }
    )


class TokenResponse(AppBaseModel):
    """
    Model for token response
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "name": "John Doe",
                    "image": "https://example.com/avatar.jpg",
                    "created_at": "2023-01-01T00:00:00",
                    "updated_at": "2023-01-01T00:00:00"
                }
            }
        }
    )


class RefreshTokenRequest(AppBaseModel):
    """
    Model for refresh token request
    """
    refresh_token: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )


class OAuthUserData(AppBaseModel):
    """
    Model for OAuth user data
    """
    provider: str
    provider_user_id: str
    email: EmailStr
    name: str
    image: Optional[str] = None
    access_token: str
    email_verified: Optional[bool] = None
    locale: Optional[str] = None
    # Keeping provider_data for backward compatibility but will be phased out
    provider_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider": "google",
                "provider_user_id": "123456789",
                "email": "user@example.com",
                "name": "John Doe",
                "image": "https://example.com/avatar.jpg",
                "access_token": "ya29.a0AfB_...",
                "email_verified": True,
                "locale": "en"
            }
        }
    )