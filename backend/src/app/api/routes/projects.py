"""
Project routes.
This module provides routes for project management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
import logging
from typing import List, Optional

from ...db.models import Project
from ...repositories import ProjectRepository
from ...utils.auth import get_current_active_user
from ..models.projects import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectListResponse,
    ProjectUserResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)
project_repository = ProjectRepository()

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Create a new project
    """
    try:
        # Add user ID as creator
        project_data_dict = project_data.dict()
        project_data_dict["created_by"] = current_user["id"]
        
        # Create project
        project = await project_repository.create(project_data_dict)
        
        # Add user as owner
        await project_repository.add_user_to_project(
            project_id=project.id,
            user_id=current_user["id"],
            role="owner"
        )
        
        return project
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )

@router.get("/projects", response_model=ProjectListResponse)
async def get_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    include_archived: bool = Query(False),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get all projects for the current user
    """
    try:
        projects = await project_repository.get_projects_by_user(
            user_id=current_user["id"],
            include_archived=include_archived
        )
        
        # Apply pagination
        paginated_projects = projects[skip:skip + limit]
        
        return {
            "items": paginated_projects,
            "total": len(projects),
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get projects"
        )

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get a specific project
    """
    try:
        project = await project_repository.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if user has access to this project
        user_projects = await project_repository.get_projects_by_user(current_user["id"], True)
        if project.id not in [p.id for p in user_projects]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        return project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project"
        )

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update a project
    """
    try:
        # Check if project exists
        project = await project_repository.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if user has access to this project
        project_users = await project_repository.get_project_users(project_id)
        user_role = None
        
        for user in project_users:
            if user["user"]["id"] == current_user["id"]:
                user_role = user["role"]
                break
        
        if not user_role or user_role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this project"
            )
        
        # Update project
        updated_project = await project_repository.update(
            project_id,
            project_data.dict(exclude_unset=True)
        )
        
        if not updated_project:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update project"
            )
        
        return updated_project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )

@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Delete a project
    """
    try:
        # Check if project exists
        project = await project_repository.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if user is the owner
        project_users = await project_repository.get_project_users(project_id)
        is_owner = False
        
        for user in project_users:
            if user["user"]["id"] == current_user["id"] and user["role"] == "owner":
                is_owner = True
                break
        
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can delete a project"
            )
        
        # Delete project
        success = await project_repository.delete(project_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete project"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )

@router.post("/projects/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Archive a project
    """
    try:
        # Check if project exists
        project = await project_repository.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if user has access to this project
        project_users = await project_repository.get_project_users(project_id)
        user_role = None
        
        for user in project_users:
            if user["user"]["id"] == current_user["id"]:
                user_role = user["role"]
                break
        
        if not user_role or user_role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to archive this project"
            )
        
        # Archive project
        archived_project = await project_repository.archive_project(project_id)
        
        if not archived_project:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to archive project"
            )
        
        return archived_project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive project"
        )

@router.post("/projects/{project_id}/unarchive", response_model=ProjectResponse)
async def unarchive_project(
    project_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Unarchive a project
    """
    try:
        # Check if project exists
        project = await project_repository.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if user has access to this project
        project_users = await project_repository.get_project_users(project_id)
        user_role = None
        
        for user in project_users:
            if user["user"]["id"] == current_user["id"]:
                user_role = user["role"]
                break
        
        if not user_role or user_role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to unarchive this project"
            )
        
        # Unarchive project
        unarchived_project = await project_repository.unarchive_project(project_id)
        
        if not unarchived_project:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to unarchive project"
            )
        
        return unarchived_project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unarchiving project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unarchive project"
        )

@router.get("/projects/{project_id}/users", response_model=List[ProjectUserResponse])
async def get_project_users(
    project_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get all users in a project
    """
    try:
        # Check if project exists
        project = await project_repository.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if user has access to this project
        user_projects = await project_repository.get_projects_by_user(current_user["id"], True)
        if project.id not in [p.id for p in user_projects]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get project users
        project_users = await project_repository.get_project_users(project_id)
        
        return project_users
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project users"
        )

@router.post("/projects/{project_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_user_to_project(
    project_id: str,
    user_id: str,
    role: str = Query(..., regex="^(owner|admin|editor|viewer)$"),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Add a user to a project
    """
    try:
        # Check if project exists
        project = await project_repository.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if current user is owner or admin
        project_users = await project_repository.get_project_users(project_id)
        current_user_role = None
        
        for user in project_users:
            if user["user"]["id"] == current_user["id"]:
                current_user_role = user["role"]
                break
        
        if not current_user_role or current_user_role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to add users to this project"
            )
        
        # Only owners can add other owners
        if role == "owner" and current_user_role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can add other owners"
            )
        
        # Add user to project
        success = await project_repository.add_user_to_project(
            project_id=project_id,
            user_id=user_id,
            role=role
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add user to project"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding user to project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add user to project"
        )

@router.delete("/projects/{project_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_project(
    project_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Remove a user from a project
    """
    try:
        # Check if project exists
        project = await project_repository.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if current user is owner or admin
        project_users = await project_repository.get_project_users(project_id)
        current_user_role = None
        user_to_remove_role = None
        
        for user in project_users:
            if user["user"]["id"] == current_user["id"]:
                current_user_role = user["role"]
            if user["user"]["id"] == user_id:
                user_to_remove_role = user["role"]
        
        if not current_user_role or current_user_role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to remove users from this project"
            )
        
        # Only owners can remove other owners
        if user_to_remove_role == "owner" and current_user_role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can remove other owners"
            )
        
        # Cannot remove the last owner
        if user_to_remove_role == "owner":
            owner_count = sum(1 for user in project_users if user["role"] == "owner")
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last owner of a project"
                )
        
        # Remove user from project
        success = await project_repository.remove_user_from_project(
            project_id=project_id,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove user from project"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing user from project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove user from project"
        )

@router.put("/projects/{project_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_role(
    project_id: str,
    user_id: str,
    role: str = Query(..., regex="^(owner|admin|editor|viewer)$"),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update a user's role in a project
    """
    try:
        # Check if project exists
        project = await project_repository.get_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if current user is owner or admin
        project_users = await project_repository.get_project_users(project_id)
        current_user_role = None
        user_to_update_role = None
        
        for user in project_users:
            if user["user"]["id"] == current_user["id"]:
                current_user_role = user["role"]
            if user["user"]["id"] == user_id:
                user_to_update_role = user["role"]
        
        if not current_user_role or current_user_role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update user roles in this project"
            )
        
        # Only owners can change owner status
        if (role == "owner" or user_to_update_role == "owner") and current_user_role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can change owner status"
            )
        
        # Cannot remove the last owner
        if user_to_update_role == "owner" and role != "owner":
            owner_count = sum(1 for user in project_users if user["role"] == "owner")
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last owner of a project"
                )
        
        # Update user role
        success = await project_repository.update_user_role(
            project_id=project_id,
            user_id=user_id,
            role=role
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user role"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )