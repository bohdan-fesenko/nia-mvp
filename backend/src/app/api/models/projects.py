"""
Project models.
This module provides Pydantic models for project-related API operations.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any

class ProjectBase(BaseModel):
    """Base model for project data."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    """Model for creating a new project."""
    pass

class ProjectUpdate(BaseModel):
    """Model for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_archived: Optional[bool] = None
    
    model_config = ConfigDict(extra="forbid")

class ProjectResponse(ProjectBase):
    """Model for project response."""
    id: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ProjectListResponse(BaseModel):
    """Model for paginated project list response."""
    items: List[ProjectResponse]
    total: int
    skip: int
    limit: int

class UserInfo(BaseModel):
    """Model for user information."""
    id: str
    name: str
    email: str
    image: Optional[str] = None

class ProjectUserResponse(BaseModel):
    """Model for project user response."""
    user: UserInfo
    role: str