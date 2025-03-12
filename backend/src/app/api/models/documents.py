"""
Document models.
This module provides Pydantic models for document-related API operations.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Union

class DocumentBase(BaseModel):
    """Base model for document data."""
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., description="Document type (e.g., 'markdown', 'task')")
    project_id: str
    folder_id: Optional[str] = None
    is_task: bool = False
    status: Optional[str] = None
    is_pinned: bool = False

class DocumentCreate(DocumentBase):
    """Model for creating a new document."""
    content: str = ""

class DocumentUpdate(BaseModel):
    """Model for updating a document."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = None
    is_task: Optional[bool] = None
    status: Optional[str] = None
    is_pinned: Optional[bool] = None
    
    model_config = ConfigDict(extra="forbid")

class DocumentContentUpdate(BaseModel):
    """Model for updating document content."""
    content: str
    change_summary: Optional[str] = None
    
    model_config = ConfigDict(extra="forbid")

class DocumentResponse(DocumentBase):
    """Model for document response."""
    id: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class DocumentWithContentResponse(DocumentResponse):
    """Model for document response with content."""
    content: str
    version_number: int

class DocumentListResponse(BaseModel):
    """Model for paginated document list response."""
    items: List[DocumentResponse]
    total: int
    skip: int
    limit: int

class DocumentVersionBase(BaseModel):
    """Base model for document version data."""
    document_id: str
    version_number: int
    content: str
    created_by: Optional[str] = None
    change_summary: Optional[str] = None
    created_at: datetime

class DocumentVersionResponse(DocumentVersionBase):
    """Model for document version response."""
    id: str
    
    model_config = ConfigDict(from_attributes=True)

class DocumentVersionWithCreatorResponse(DocumentVersionResponse):
    """Model for document version response with creator information."""
    creator: Optional[Dict[str, Any]] = None

class DocumentVersionListResponse(BaseModel):
    """Model for document version list response."""
    items: List[DocumentVersionResponse]
    total: int

class DocumentVersionCompareResponse(BaseModel):
    """Model for document version comparison response."""
    version1: DocumentVersionResponse
    version2: DocumentVersionResponse
    diff_stats: Dict[str, int]

class DocumentMoveRequest(BaseModel):
    """Model for moving a document."""
    new_folder_id: Optional[str] = None
    
    model_config = ConfigDict(extra="forbid")

class DocumentStatusUpdateRequest(BaseModel):
    """Model for updating document status."""
    status: str
    comment: Optional[str] = None
    
    model_config = ConfigDict(extra="forbid")

class DocumentStatusUpdate(BaseModel):
    """Model for document status update."""
    id: str
    document_id: str
    previous_status: Optional[str] = None
    new_status: str
    created_by: str
    created_by_name: Optional[str] = None
    created_at: datetime
    comment: Optional[str] = None

class DocumentStatusHistoryResponse(BaseModel):
    """Model for document status history response."""
    items: List[DocumentStatusUpdate]
    total: int