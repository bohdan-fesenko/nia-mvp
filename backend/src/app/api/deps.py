"""
Dependencies for FastAPI routes.
"""
import logging
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError

from ..config import settings
from ..db.neo4j_client import get_neo4j_client
from ..db.redis_client import get_redis_client
from ..models.user import User, TokenData
from ..repositories.document_repository import DocumentRepository
from ..repositories.document_version_repository import DocumentVersionRepository
from ..repositories.folder_repository import FolderRepository
from ..repositories.project_repository import ProjectRepository
from ..repositories.document_processing_repository import DocumentProcessingRepository
from ..repositories.task_management_repository import TaskManagementRepository
from ..services.document_service import DocumentService, create_document_service
from ..services.folder_service import FolderService, create_folder_service
from ..services.project_service import ProjectService, create_project_service
from ..services.document_processing_service import DocumentProcessingService, create_document_processing_service
from ..services.task_management_service import TaskManagementService, create_task_management_service
from ..services.cache_service import CacheService, create_cache_service
from ..services.pubsub_service import PubSubService, create_pubsub_service
from ..services.session_service import SessionService, create_session_service
from ..services.rate_limit_service import RateLimitService, create_rate_limit_service

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Get the current user from the token.
    
    Args:
        token: JWT token
        
    Returns:
        User object
        
    Raises:
        HTTPException: If the token is invalid or the user is not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except (JWTError, ValidationError):
        raise credentials_exception
    
    # In a real application, you would look up the user in the database
    # For now, we'll just create a mock user
    user = User(
        id="user123",
        username=token_data.username,
        email=f"{token_data.username}@example.com",
        full_name="Test User",
    )
    
    if user is None:
        raise credentials_exception
    
    return user

def get_document_repository() -> DocumentRepository:
    """
    Get the document repository.
    
    Returns:
        DocumentRepository instance
    """
    client = get_neo4j_client()
    return DocumentRepository(client)

def get_document_version_repository() -> DocumentVersionRepository:
    """
    Get the document version repository.
    
    Returns:
        DocumentVersionRepository instance
    """
    client = get_neo4j_client()
    return DocumentVersionRepository(client)

def get_folder_repository() -> FolderRepository:
    """
    Get the folder repository.
    
    Returns:
        FolderRepository instance
    """
    client = get_neo4j_client()
    return FolderRepository(client)

def get_project_repository() -> ProjectRepository:
    """
    Get the project repository.
    
    Returns:
        ProjectRepository instance
    """
    client = get_neo4j_client()
    return ProjectRepository(client)

def get_document_processing_repository() -> DocumentProcessingRepository:
    """
    Get the document processing repository.
    
    Returns:
        DocumentProcessingRepository instance
    """
    client = get_neo4j_client()
    return DocumentProcessingRepository(client)

def get_task_management_repository() -> TaskManagementRepository:
    """
    Get the task management repository.
    
    Returns:
        TaskManagementRepository instance
    """
    client = get_neo4j_client()
    return TaskManagementRepository(client)

def get_document_service(
    document_repo: DocumentRepository = Depends(get_document_repository),
    document_version_repo: DocumentVersionRepository = Depends(get_document_version_repository),
    folder_repo: FolderRepository = Depends(get_folder_repository),
) -> DocumentService:
    """
    Get the document service.
    
    Args:
        document_repo: DocumentRepository instance
        document_version_repo: DocumentVersionRepository instance
        folder_repo: FolderRepository instance
        
    Returns:
        DocumentService instance
    """
    return create_document_service(
        document_repo=document_repo,
        document_version_repo=document_version_repo,
        folder_repo=folder_repo,
    )

def get_folder_service(
    folder_repo: FolderRepository = Depends(get_folder_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
) -> FolderService:
    """
    Get the folder service.
    
    Args:
        folder_repo: FolderRepository instance
        document_repo: DocumentRepository instance
        
    Returns:
        FolderService instance
    """
    return create_folder_service(
        folder_repo=folder_repo,
        document_repo=document_repo,
    )

def get_project_service(
    project_repo: ProjectRepository = Depends(get_project_repository),
    folder_repo: FolderRepository = Depends(get_folder_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
) -> ProjectService:
    """
    Get the project service.
    
    Args:
        project_repo: ProjectRepository instance
        folder_repo: FolderRepository instance
        document_repo: DocumentRepository instance
        
    Returns:
        ProjectService instance
    """
    return create_project_service(
        project_repo=project_repo,
        folder_repo=folder_repo,
        document_repo=document_repo,
    )

def get_document_processing_service(
    document_processing_repo: DocumentProcessingRepository = Depends(get_document_processing_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    document_version_repo: DocumentVersionRepository = Depends(get_document_version_repository),
) -> DocumentProcessingService:
    """
    Get the document processing service.
    
    Args:
        document_processing_repo: DocumentProcessingRepository instance
        document_repo: DocumentRepository instance
        document_version_repo: DocumentVersionRepository instance
        
    Returns:
        DocumentProcessingService instance
    """
    return create_document_processing_service(
        document_processing_repo=document_processing_repo,
        document_repo=document_repo,
        document_version_repo=document_version_repo,
    )

def get_task_management_service(
    task_management_repo: TaskManagementRepository = Depends(get_task_management_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    document_version_repo: DocumentVersionRepository = Depends(get_document_version_repository),
) -> TaskManagementService:
    """
    Get the task management service.
    
    Args:
        task_management_repo: TaskManagementRepository instance
        document_repo: DocumentRepository instance
        document_version_repo: DocumentVersionRepository instance
        
    Returns:
        TaskManagementService instance
    """
    return create_task_management_service(
        task_management_repo=task_management_repo,
        document_repo=document_repo,
        document_version_repo=document_version_repo,
    )

def get_cache_service() -> CacheService:
    """
    Get the cache service.
    
    Returns:
        CacheService instance
    """
    redis_client = get_redis_client()
    return create_cache_service(redis_client)

def get_pubsub_service() -> PubSubService:
    """
    Get the pubsub service.
    
    Returns:
        PubSubService instance
    """
    redis_client = get_redis_client()
    return create_pubsub_service(redis_client)

def get_session_service() -> SessionService:
    """
    Get the session service.
    
    Returns:
        SessionService instance
    """
    redis_client = get_redis_client()
    return create_session_service(redis_client)

def get_rate_limit_service() -> RateLimitService:
    """
    Get the rate limit service.
    
    Returns:
        RateLimitService instance
    """
    redis_client = get_redis_client()
    return create_rate_limit_service(redis_client)