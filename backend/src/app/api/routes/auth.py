"""
Authentication routes.
This module provides routes for authentication.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import logging
import uuid
from typing import Dict, Any

from ...db.neo4j_client import neo4j_client
from ...utils.auth import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    create_refresh_token,
    decode_token,
    get_current_active_user
)
from ..models.auth import (
    UserCreate, 
    UserLogin, 
    UserResponse, 
    TokenResponse, 
    RefreshTokenRequest
)
from ...config import settings
from ...db.models import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user
    """
    # Check if user already exists
    existing_user_query = """
    MATCH (u:User {email: $email})
    RETURN u
    """
    
    existing_user = await neo4j_client.execute_query_async(
        existing_user_query,
        {"email": user_data.email}
    )
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash the password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user in database
    try:
        user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        create_user_query = """
        CREATE (u:User {
            id: $id,
            email: $email,
            name: $name,
            password: $password,
            image: $image,
            created_at: datetime($created_at),
            updated_at: datetime($updated_at)
        })
        RETURN u
        """
        
        result = await neo4j_client.execute_query_async(
            create_user_query,
            {
                "id": user_id,
                "email": user_data.email,
                "name": user_data.name,
                "password": hashed_password,
                "image": user_data.image,
                "created_at": now,
                "updated_at": now
            }
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        new_user = result[0]["u"]
        
        # Convert to response model
        return UserResponse(
            id=new_user["id"],
            email=new_user["email"],
            name=new_user["name"],
            image=new_user.get("image"),
            created_at=datetime.fromisoformat(new_user["created_at"].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(new_user["updated_at"].replace('Z', '+00:00'))
        )
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.post("/auth/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate a user and return JWT tokens
    """
    # Find user by email
    find_user_query = """
    MATCH (u:User {email: $email})
    RETURN u
    """
    
    result = await neo4j_client.execute_query_async(
        find_user_query,
        {"email": form_data.username}
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = result[0]["u"]
    
    # Check if password is correct
    if not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"]},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user["id"], "email": user["email"]},
        expires_delta=refresh_token_expires
    )
    
    # Return tokens and user data
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            image=user.get("image"),
            created_at=datetime.fromisoformat(user["created_at"].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(user["updated_at"].replace('Z', '+00:00'))
        )
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_request: RefreshTokenRequest):
    """
    Refresh access token using a refresh token
    """
    try:
        # Decode and validate refresh token
        payload = decode_token(refresh_request.refresh_token)
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        find_user_query = """
        MATCH (u:User {id: $id})
        RETURN u
        """
        
        result = await neo4j_client.execute_query_async(
            find_user_query,
            {"id": user_id}
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = result[0]["u"]
        
        # Create new tokens
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={"sub": user["id"], "email": user["email"]},
            expires_delta=access_token_expires
        )
        
        new_refresh_token = create_refresh_token(
            data={"sub": user["id"], "email": user["email"]},
            expires_delta=refresh_token_expires
        )
        
        # Return new tokens and user data
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            user=UserResponse(
                id=user["id"],
                email=user["email"],
                name=user["name"],
                image=user.get("image"),
                created_at=datetime.fromisoformat(user["created_at"].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(user["updated_at"].replace('Z', '+00:00'))
            )
        )
    
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Get current user information
    """
    # Get user from database
    find_user_query = """
    MATCH (u:User {id: $id})
    RETURN u
    """
    
    result = await neo4j_client.execute_query_async(
        find_user_query,
        {"id": current_user["id"]}
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = result[0]["u"]
    
    # Return user data
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        image=user.get("image"),
        created_at=datetime.fromisoformat(user["created_at"].replace('Z', '+00:00')),
        updated_at=datetime.fromisoformat(user["updated_at"].replace('Z', '+00:00'))
    )