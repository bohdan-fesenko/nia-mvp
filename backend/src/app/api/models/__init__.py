"""
API models package.
This package provides Pydantic models for API operations.
"""
from .auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest
)
from .projects import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectUserResponse
)
from .folders import (
    FolderCreate,
    FolderUpdate,
    FolderResponse,
    FolderListResponse,
    FolderHierarchyResponse,
    FolderMoveRequest
)
from .documents import (
    DocumentCreate,
    DocumentUpdate,
    DocumentContentUpdate,
    DocumentResponse,
    DocumentWithContentResponse,
    DocumentListResponse,
    DocumentVersionResponse,
    DocumentVersionWithCreatorResponse,
    DocumentVersionListResponse,
    DocumentVersionCompareResponse,
    DocumentMoveRequest,
    DocumentStatusUpdateRequest,
    DocumentStatusUpdate,
    DocumentStatusHistoryResponse
)

__all__ = [
    # Auth models
    'UserCreate',
    'UserLogin',
    'UserResponse',
    'TokenResponse',
    'RefreshTokenRequest',
    
    # Project models
    'ProjectCreate',
    'ProjectUpdate',
    'ProjectResponse',
    'ProjectListResponse',
    'ProjectUserResponse',
    
    # Folder models
    'FolderCreate',
    'FolderUpdate',
    'FolderResponse',
    'FolderListResponse',
    'FolderHierarchyResponse',
    'FolderMoveRequest',
    
    # Document models
    'DocumentCreate',
    'DocumentUpdate',
    'DocumentContentUpdate',
    'DocumentResponse',
    'DocumentWithContentResponse',
    'DocumentListResponse',
    'DocumentVersionResponse',
    'DocumentVersionWithCreatorResponse',
    'DocumentVersionListResponse',
    'DocumentVersionCompareResponse',
    'DocumentMoveRequest',
    'DocumentStatusUpdateRequest',
    'DocumentStatusUpdate',
    'DocumentStatusHistoryResponse'
]