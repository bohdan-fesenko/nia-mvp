"""
Task management API routes.
This module provides API endpoints for task management functionality.
"""
import logging
from typing import Dict, List, Optional, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status

from ...models.task_management import (
    TaskStatus, TaskPriority, TaskRelationshipType,
    TaskStatusUpdateRequest, TaskRelationshipRequest,
    TaskDetailResponse, TaskListResponse, TaskStatistics
)
from ...services.task_management_service import TaskManagementService
from ...api.deps import get_current_user, get_task_management_service

router = APIRouter(prefix="/tasks", tags=["tasks"])

logger = logging.getLogger(__name__)

@router.get("/detect", response_model=List[Dict[str, Any]])
async def detect_task_documents(
    project_id: Optional[str] = Query(None, description="Optional project ID to filter by"),
    current_user = Depends(get_current_user),
    task_management_service: TaskManagementService = Depends(get_task_management_service)
):
    """
    Detect documents that follow the task naming convention.
    """
    try:
        return await task_management_service.detect_task_documents(project_id)
    except Exception as e:
        logger.error(f"Error detecting task documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error detecting task documents: {str(e)}"
        )

@router.get("", response_model=TaskListResponse)
async def get_tasks(
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    priority: Optional[List[str]] = Query(None, description="Filter by priority"),
    assignee: Optional[List[str]] = Query(None, description="Filter by assignee"),
    due_date_before: Optional[str] = Query(None, description="Filter by due date before (YYYY-MM-DD)"),
    due_date_after: Optional[str] = Query(None, description="Filter by due date after (YYYY-MM-DD)"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    search_query: Optional[str] = Query(None, description="Search in title and description"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    folder_id: Optional[str] = Query(None, description="Filter by folder ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user = Depends(get_current_user),
    task_management_service: TaskManagementService = Depends(get_task_management_service)
):
    """
    Get a list of tasks based on filter criteria.
    """
    try:
        # Build filter criteria from query parameters
        filter_criteria = {}
        
        if status:
            filter_criteria["status"] = status
        
        if priority:
            filter_criteria["priority"] = priority
        
        if assignee:
            filter_criteria["assignee"] = assignee
        
        if due_date_before:
            filter_criteria["due_date_before"] = due_date_before
        
        if due_date_after:
            filter_criteria["due_date_after"] = due_date_after
        
        if tags:
            filter_criteria["tags"] = tags
        
        if search_query:
            filter_criteria["search_query"] = search_query
        
        if project_id:
            filter_criteria["project_id"] = project_id
        
        if folder_id:
            filter_criteria["folder_id"] = folder_id
        
        return await task_management_service.get_tasks(filter_criteria, page, per_page)
    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting tasks: {str(e)}"
        )

@router.get("/statistics", response_model=TaskStatistics)
async def get_task_statistics(
    project_id: Optional[str] = Query(None, description="Optional project ID to filter by"),
    current_user = Depends(get_current_user),
    task_management_service: TaskManagementService = Depends(get_task_management_service)
):
    """
    Get statistics about tasks.
    """
    try:
        return await task_management_service.get_task_statistics(project_id)
    except Exception as e:
        logger.error(f"Error getting task statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting task statistics: {str(e)}"
        )

@router.get("/{document_id}", response_model=TaskDetailResponse)
async def get_task_details(
    document_id: str = Path(..., description="The ID of the document"),
    current_user = Depends(get_current_user),
    task_management_service: TaskManagementService = Depends(get_task_management_service)
):
    """
    Get detailed information about a task.
    """
    try:
        task_details = await task_management_service.get_task_details(document_id)
        if not task_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found: {document_id}"
            )
        return task_details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting task details: {str(e)}"
        )

@router.post("/{document_id}/status", response_model=Dict[str, Any])
async def update_task_status(
    document_id: str = Path(..., description="The ID of the document"),
    status_update: TaskStatusUpdateRequest = Body(..., description="Status update request"),
    current_user = Depends(get_current_user),
    task_management_service: TaskManagementService = Depends(get_task_management_service)
):
    """
    Update the status of a task.
    """
    try:
        status_update_result = await task_management_service.update_task_status(
            document_id, 
            status_update.status, 
            status_update.comment, 
            current_user.id
        )
        
        if not status_update_result:
            return {"message": "Status unchanged", "status": status_update.status}
        
        return {
            "message": "Status updated successfully",
            "previous_status": status_update_result.previous_status,
            "new_status": status_update_result.new_status,
            "updated_at": status_update_result.created_at
        }
    except Exception as e:
        logger.error(f"Error updating task status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating task status: {str(e)}"
        )

@router.get("/{document_id}/status-history", response_model=List[Dict[str, Any]])
async def get_task_status_history(
    document_id: str = Path(..., description="The ID of the document"),
    current_user = Depends(get_current_user),
    task_management_service: TaskManagementService = Depends(get_task_management_service)
):
    """
    Get the status history for a task.
    """
    try:
        return await task_management_service.get_task_status_history(document_id)
    except Exception as e:
        logger.error(f"Error getting task status history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting task status history: {str(e)}"
        )

@router.post("/{document_id}/relationships", response_model=Dict[str, Any])
async def create_task_relationship(
    document_id: str = Path(..., description="The ID of the source document"),
    relationship: TaskRelationshipRequest = Body(..., description="Relationship request"),
    current_user = Depends(get_current_user),
    task_management_service: TaskManagementService = Depends(get_task_management_service)
):
    """
    Create a relationship between two tasks.
    """
    try:
        relationship_result = await task_management_service.create_task_relationship(
            document_id,
            relationship.target_task_id,
            relationship.relationship_type,
            relationship.description,
            current_user.id
        )
        
        return {
            "message": "Relationship created successfully",
            "relationship_id": relationship_result.id,
            "source_document_id": relationship_result.source_document_id,
            "target_document_id": relationship_result.target_document_id,
            "relationship_type": relationship_result.relationship_type,
            "created_at": relationship_result.created_at
        }
    except Exception as e:
        logger.error(f"Error creating task relationship: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task relationship: {str(e)}"
        )

@router.get("/{document_id}/relationships", response_model=Dict[str, List[Dict[str, Any]]])
async def get_task_relationships(
    document_id: str = Path(..., description="The ID of the document"),
    current_user = Depends(get_current_user),
    task_management_service: TaskManagementService = Depends(get_task_management_service)
):
    """
    Get all relationships for a task.
    """
    try:
        return await task_management_service.get_task_relationships(document_id)
    except Exception as e:
        logger.error(f"Error getting task relationships: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting task relationships: {str(e)}"
        )

@router.post("/detect-relationships", response_model=Dict[str, Any])
async def detect_task_relationships(
    document_id: Optional[str] = Query(None, description="Optional document ID to analyze"),
    project_id: Optional[str] = Query(None, description="Optional project ID to analyze all tasks within"),
    current_user = Depends(get_current_user),
    task_management_service: TaskManagementService = Depends(get_task_management_service)
):
    """
    Detect relationships between tasks based on content analysis.
    """
    try:
        if not document_id and not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either document_id or project_id must be provided"
            )
        
        relationships = await task_management_service.detect_task_relationships(document_id, project_id)
        
        return {
            "message": "Relationship detection completed",
            "relationships_detected": len(relationships),
            "relationships": [rel.dict() for rel in relationships]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting task relationships: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error detecting task relationships: {str(e)}"
        )

@router.post("/{document_id}/extract-metadata", response_model=Dict[str, Any])
async def extract_task_metadata(
    document_id: str = Path(..., description="The ID of the document"),
    current_user = Depends(get_current_user),
    task_management_service: TaskManagementService = Depends(get_task_management_service)
):
    """
    Extract metadata from a task document.
    """
    try:
        metadata = await task_management_service.extract_and_save_task_metadata(document_id)
        
        return {
            "message": "Metadata extraction completed",
            "metadata_id": metadata.id,
            "task_id": metadata.task_id,
            "title": metadata.title,
            "status": metadata.status,
            "priority": metadata.priority,
            "assignee": metadata.assignee,
            "due_date": metadata.due_date,
            "tags": metadata.tags,
            "related_tasks": metadata.related_tasks
        }
    except Exception as e:
        logger.error(f"Error extracting task metadata: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting task metadata: {str(e)}"
        )