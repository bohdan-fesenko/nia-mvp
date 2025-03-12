"""
Document routes.
This module provides routes for document management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
import logging
from typing import Dict, List, Optional, Any

from ...db.models import Document, DocumentVersion
from ...repositories.document_repository import DocumentRepository
from ...utils.auth import get_current_active_user, oauth2_scheme, User
from ...config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# No replacement needed - removing this function

# Create a dependency that combines dev mode and regular auth
def get_current_user_or_dev_mode(dev_mode: bool = Query(False, description="Enable development mode authentication bypass")):
    """
    Get the current user, with optional dev mode bypass.
    
    Args:
        dev_mode: Whether to enable development mode
        
    Returns:
        A dependency that returns either a dev user or the current authenticated user
    """
    async def _get_user(token: str = Depends(oauth2_scheme)):
        # Try dev mode first
        if settings.ENVIRONMENT == "development" and settings.DEBUG and dev_mode:
            logger.warning("Using development mode authentication bypass")
            # Return a mock user for development
            return User(
                id="dev-user-id",
                username="dev",
                email="dev@example.com",
                full_name="Development User",
                disabled=False,
                roles=["admin"]
            )
        
        # Fall back to regular auth
        return await get_current_active_user(token=token)
    
    return _get_user
document_repository = DocumentRepository()

@router.get("/documents/{document_id}")
async def get_document(
    document_id: str = Path(..., description="The ID of the document to retrieve"),
    version: Optional[int] = Query(None, description="Optional version number to retrieve"),
    dev_mode: bool = Query(False, description="Enable development mode authentication bypass"),
    current_user: dict = Depends(get_current_user_or_dev_mode)
):
    """
    Get a document by ID with its content.
    
    Args:
        document_id: The ID of the document to retrieve
        version: Optional version number to retrieve (defaults to latest)
        current_user: The current authenticated user
        
    Returns:
        The document with its content
    """
    try:
        # Get document with content
        document = await document_repository.get_document_with_content(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}"
            )
        
        # If specific version requested, get that version
        if version is not None:
            version_obj = await document_repository.get_version(document_id, version)
            if not version_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Version {version} not found for document: {document_id}"
                )
            document["content"] = version_obj.content
            document["version_number"] = version_obj.version_number
        
        return document
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting document: {str(e)}"
        )

@router.get("/projects/{project_id}/documents")
async def get_project_documents(
    project_id: str = Path(..., description="The ID of the project"),
    folder_id: Optional[str] = Query(None, description="Optional folder ID to filter by"),
    dev_mode: bool = Query(False, description="Enable development mode authentication bypass"),
    include_content: bool = Query(False, description="Whether to include document content"),
    current_user: dict = Depends(get_current_user_or_dev_mode)
):
    """
    Get all documents in a project, optionally filtered by folder.
    
    Args:
        project_id: The ID of the project
        folder_id: Optional folder ID to filter by
        include_content: Whether to include document content
        current_user: The current authenticated user
        
    Returns:
        List of documents
    """
    try:
        if folder_id:
            # Get documents in folder
            documents = await document_repository.get_documents_by_folder(folder_id, include_content)
        else:
            # Get all documents in project
            documents = await document_repository.get_documents_by_project(project_id, include_content)
        
        return documents
    except Exception as e:
        logger.error(f"Error getting project documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting project documents: {str(e)}"
        )

@router.post("/projects/{project_id}/documents", status_code=status.HTTP_201_CREATED)
async def create_document(
    project_id: str = Path(..., description="The ID of the project"),
    document_data: Dict[str, Any] = Body(..., description="Document data"),
    dev_mode: bool = Query(False, description="Enable development mode authentication bypass"),
    current_user: dict = Depends(get_current_user_or_dev_mode)
):
    """
    Create a new document.
    
    Args:
        project_id: The ID of the project
        document_data: Document data including name, type, folder_id, and content
        current_user: The current authenticated user
        
    Returns:
        The created document
    """
    try:
        # Extract content from document data
        content = document_data.pop("content", "")
        
        # Add project_id and created_by to document data
        document_data["project_id"] = project_id
        document_data["created_by"] = current_user["id"]
        
        # Create document
        document, version = await document_repository.create_document(document_data, content)
        
        # Return document with content
        result = document.__dict__
        result["content"] = content
        result["version_number"] = version.version_number
        
        return result
    except Exception as e:
        logger.error(f"Error creating document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating document: {str(e)}"
        )

@router.put("/documents/{document_id}")
async def update_document(
    document_id: str = Path(..., description="The ID of the document to update"),
    document_data: Dict[str, Any] = Body(..., description="Document data"),
    dev_mode: bool = Query(False, description="Enable development mode authentication bypass"),
    current_user: dict = Depends(get_current_user_or_dev_mode)
):
    """
    Update a document.
    
    Args:
        document_id: The ID of the document to update
        document_data: Document data to update
        current_user: The current authenticated user
        
    Returns:
        The updated document
    """
    try:
        # Check if document exists
        document = await document_repository.get_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}"
            )
        
        # Extract content from document data
        content = document_data.pop("content", None)
        
        # Update document metadata
        updated_document = await document_repository.update(document_id, document_data)
        
        # Create new version if content provided
        if content is not None:
            version = await document_repository.create_version(
                document_id=document_id,
                content=content,
                user_id=current_user["id"],
                change_summary=document_data.get("change_summary")
            )
            
            # Return document with content
            result = updated_document.__dict__
            result["content"] = content
            result["version_number"] = version.version_number
        else:
            # Get latest version
            version = await document_repository.get_version(document_id)
            
            # Return document with content
            result = updated_document.__dict__
            result["content"] = version.content if version else ""
            result["version_number"] = version.version_number if version else 0
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating document: {str(e)}"
        )

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str = Path(..., description="The ID of the document to delete"),
    dev_mode: bool = Query(False, description="Enable development mode authentication bypass"),
    current_user: dict = Depends(get_current_user_or_dev_mode)
):
    """
    Delete a document.
    
    Args:
        document_id: The ID of the document to delete
        current_user: The current authenticated user
    """
    try:
        # Check if document exists
        document = await document_repository.get_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}"
            )
        
        # Delete document
        success = await document_repository.delete(document_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document: {document_id}"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )

@router.get("/documents/{document_id}/versions")
async def get_document_versions(
    document_id: str = Path(..., description="The ID of the document"),
    dev_mode: bool = Query(False, description="Enable development mode authentication bypass"),
    current_user: dict = Depends(get_current_user_or_dev_mode)
):
    """
    Get all versions of a document.
    
    Args:
        document_id: The ID of the document
        current_user: The current authenticated user
        
    Returns:
        List of document versions
    """
    try:
        # Check if document exists
        document = await document_repository.get_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}"
            )
        
        # Get version history
        versions = await document_repository.get_version_history(document_id)
        
        # Convert to dict for response
        result = []
        for version in versions:
            result.append({
                "id": version.id,
                "document_id": version.document_id,
                "version_number": version.version_number,
                "created_by": version.created_by,
                "created_at": version.created_at,
                "change_summary": version.change_summary
            })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document versions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting document versions: {str(e)}"
        )

@router.post("/documents/{document_id}/restore/{version_number}")
async def restore_document_version(
    document_id: str = Path(..., description="The ID of the document"),
    version_number: int = Path(..., description="The version number to restore"),
    dev_mode: bool = Query(False, description="Enable development mode authentication bypass"),
    current_user: dict = Depends(get_current_user_or_dev_mode)
):
    """
    Restore a document to a previous version.
    
    Args:
        document_id: The ID of the document
        version_number: The version number to restore
        current_user: The current authenticated user
        
    Returns:
        The restored document
    """
    try:
        # Check if document exists
        document = await document_repository.get_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}"
            )
        
        # Restore version
        version = await document_repository.restore_version(
            document_id=document_id,
            version_number=version_number,
            user_id=current_user["id"]
        )
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version_number} not found for document: {document_id}"
            )
        
        # Return document with content
        result = document.__dict__
        result["content"] = version.content
        result["version_number"] = version.version_number
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring document version: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restoring document version: {str(e)}"
        )

@router.post("/documents/{document_id}/pin")
async def pin_document(
    document_id: str = Path(..., description="The ID of the document to pin"),
    dev_mode: bool = Query(False, description="Enable development mode authentication bypass"),
    current_user: dict = Depends(get_current_user_or_dev_mode)
):
    """
    Pin a document to the dashboard.
    
    Args:
        document_id: The ID of the document to pin
        current_user: The current authenticated user
        
    Returns:
        The pinned document
    """
    try:
        # Check if document exists
        document = await document_repository.get_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}"
            )
        
        # Pin document
        pinned_document = await document_repository.pin_document(document_id)
        
        return pinned_document.__dict__
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pinning document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error pinning document: {str(e)}"
        )

@router.post("/documents/{document_id}/unpin")
async def unpin_document(
    document_id: str = Path(..., description="The ID of the document to unpin"),
    dev_mode: bool = Query(False, description="Enable development mode authentication bypass"),
    current_user: dict = Depends(get_current_user_or_dev_mode)
):
    """
    Unpin a document from the dashboard.
    
    Args:
        document_id: The ID of the document to unpin
        current_user: The current authenticated user
        
    Returns:
        The unpinned document
    """
    try:
        # Check if document exists
        document = await document_repository.get_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}"
            )
        
        # Unpin document
        unpinned_document = await document_repository.unpin_document(document_id)
        
        return unpinned_document.__dict__
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unpinning document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error unpinning document: {str(e)}"
        )

@router.post("/documents/{document_id}/move")
async def move_document(
    document_id: str = Path(..., description="The ID of the document to move"),
    folder_id: Optional[str] = Query(None, description="The ID of the folder to move to, or None for root"),
    dev_mode: bool = Query(False, description="Enable development mode authentication bypass"),
    current_user: dict = Depends(get_current_user_or_dev_mode)
):
    """
    Move a document to a different folder or to the root level.
    
    Args:
        document_id: The ID of the document to move
        folder_id: The ID of the folder to move to, or None for root
        current_user: The current authenticated user
        
    Returns:
        The moved document
    """
    try:
        # Check if document exists
        document = await document_repository.get_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}"
            )
        
        # Move document
        moved_document = await document_repository.move_document(document_id, folder_id)
        
        return moved_document.__dict__
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error moving document: {str(e)}"
        )