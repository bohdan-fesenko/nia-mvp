"""
User models for authentication and authorization.
"""
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class TokenData(BaseModel):
    """
    Token data model.
    """
    username: Optional[str] = None
    exp: Optional[int] = None


class User(BaseModel):
    """
    User model.
    """
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    roles: List[str] = []


class UserCreate(BaseModel):
    """
    User creation model.
    """
    username: str
    email: str
    password: str
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    """
    User update model.
    """
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    disabled: Optional[bool] = None
    roles: Optional[List[str]] = None


class UserInDB(User):
    """
    User model with hashed password.
    """
    hashed_password: str


class Token(BaseModel):
    """
    Token model.
    """
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None