"""
Folder models.
This module provides Pydantic models for folder-related API operations.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any

class FolderBase(BaseModel):
    """Base model for folder data."""
    name: str = Field(..., min_length=1, max_length=100)
    project_id: str
    parent_folder_id: Optional[str] = None

class FolderCreate(FolderBase):
    """Model for creating a new folder."""
    pass

class FolderUpdate(BaseModel):
    """Model for updating a folder."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    
    model_config = ConfigDict(extra="forbid")

class FolderResponse(FolderBase):
    """Model for folder response."""
    id: str
    path: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class FolderListResponse(BaseModel):
    """Model for paginated folder list response."""
    items: List[FolderResponse]
    total: int
    skip: int
    limit: int

class FolderHierarchyItem(BaseModel):
    """Model for folder hierarchy item."""
    id: str
    name: str
    type: str = "folder"
    children: Dict[str, Any] = {}
    documents: List[Dict[str, Any]] = []

class FolderHierarchyResponse(BaseModel):
    """Model for folder hierarchy response."""
    id: str
    type: str = "project"
    children: Dict[str, FolderHierarchyItem]

class FolderMoveRequest(BaseModel):
    """Model for moving a folder."""
    new_parent_id: Optional[str] = None
    
    model_config = ConfigDict(extra="forbid")