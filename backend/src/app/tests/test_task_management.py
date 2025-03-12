"""
Tests for task management functionality.
"""
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from ..models.task_management import (
    TaskStatus, TaskPriority, TaskRelationshipType,
    TaskStatusUpdate, TaskRelationship, TaskMetadata
)
from ..services.task_management_service import TaskManagementService
from ..db.models import Document, DocumentVersion

@pytest.fixture
def mock_task_management_repo():
    """Create a mock task management repository."""
    repo = AsyncMock()
    
    # Setup detect_task_documents
    repo.detect_task_documents.return_value = [
        {
            "id": str(uuid.uuid4()),
            "name": "TASK_001_test_task.md",
            "task_id": "TASK_001",
            "project_id": str(uuid.uuid4()),
            "folder_id": str(uuid.uuid4()),
            "status": "todo",
            "is_task": False,
            "created_by": str(uuid.uuid4()),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    # Setup save_task_metadata
    repo.save_task_metadata.return_value = str(uuid.uuid4())
    
    # Setup get_task_metadata
    repo.get_task_metadata.return_value = TaskMetadata(
        document_id=str(uuid.uuid4()),
        task_id="TASK_001",
        title="Test Task",
        description="This is a test task",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        assignee="Test User",
        due_date=datetime.utcnow() + timedelta(days=7),
        estimated_effort="2 days",
        completion_percentage=0,
        tags=["test", "example"],
        related_tasks=["TASK_002"],
        custom_fields={"field1": "value1"}
    )
    
    # Setup save_task_status_update
    repo.save_task_status_update.return_value = str(uuid.uuid4())
    
    # Setup get_task_status_history
    repo.get_task_status_history.return_value = [
        TaskStatusUpdate(
            document_id=str(uuid.uuid4()),
            previous_status=None,
            new_status=TaskStatus.TODO,
            comment="Initial status",
            created_by=str(uuid.uuid4())
        ),
        TaskStatusUpdate(
            document_id=str(uuid.uuid4()),
            previous_status=TaskStatus.TODO,
            new_status=TaskStatus.IN_PROGRESS,
            comment="Started working on task",
            created_by=str(uuid.uuid4())
        )
    ]
    
    # Setup save_task_relationship
    repo.save_task_relationship.return_value = str(uuid.uuid4())
    
    # Setup get_task_relationships
    repo.get_task_relationships.return_value = [
        TaskRelationship(
            source_document_id=str(uuid.uuid4()),
            target_document_id=str(uuid.uuid4()),
            relationship_type=TaskRelationshipType.DEPENDS_ON,
            description="Test depends on target",
            created_by=str(uuid.uuid4())
        )
    ]
    
    # Setup get_tasks_by_filter
    repo.get_tasks_by_filter.return_value = ([], 0)
    
    # Setup get_task_statistics
    repo.get_task_statistics.return_value = {
        "total_tasks": 5,
        "by_status": {
            "todo": 2,
            "in_progress": 2,
            "done": 1
        },
        "by_priority": {
            "low": 1,
            "medium": 3,
            "high": 1
        },
        "by_assignee": {
            "User 1": 2,
            "User 2": 3
        },
        "overdue_tasks": 1,
        "completed_tasks_last_week": 1,
        "created_tasks_last_week": 2,
        "average_completion_time_days": 3.5
    }
    
    return repo

@pytest.fixture
def mock_document_repo():
    """Create a mock document repository."""
    repo = AsyncMock()
    
    # Setup get_by_id
    repo.get_by_id.return_value = Document(
        id=str(uuid.uuid4()),
        name="TASK_001_test_task.md",
        project_id=str(uuid.uuid4()),
        folder_id=str(uuid.uuid4()),
        type="markdown",
        is_task=False,
        status=None,
        created_by=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    return repo

@pytest.fixture
def mock_document_version_repo():
    """Create a mock document version repository."""
    repo = AsyncMock()
    
    # Setup get_latest_version
    repo.get_latest_version.return_value = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        version_number=1,
        content="""# Test Task

## Overview
This is a test task for testing the task management functionality.

## Status: todo
## Priority: medium
## Assignee: Test User
## Due Date: 2025-12-31
## Tags: test, example
## Related Tasks: TASK_002

## Custom Fields
field1: value1
""",
        created_by=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        change_summary="Initial version"
    )
    
    return repo

@pytest.fixture
def task_management_service(mock_task_management_repo, mock_document_repo, mock_document_version_repo):
    """Create a task management service with mock repositories."""
    return TaskManagementService(
        task_management_repo=mock_task_management_repo,
        document_repo=mock_document_repo,
        document_version_repo=mock_document_version_repo
    )

@pytest.mark.asyncio
async def test_detect_task_documents(task_management_service, mock_task_management_repo):
    """Test detecting task documents."""
    # Call the service method
    result = await task_management_service.detect_task_documents()
    
    # Verify the repository method was called
    mock_task_management_repo.detect_task_documents.assert_called_once_with(None)
    
    # Verify the result
    assert len(result) == 1
    assert result[0]["name"] == "TASK_001_test_task.md"
    assert result[0]["task_id"] == "TASK_001"

@pytest.mark.asyncio
async def test_extract_and_save_task_metadata(task_management_service, mock_task_management_repo, mock_document_repo, mock_document_version_repo):
    """Test extracting and saving task metadata."""
    document_id = str(uuid.uuid4())
    
    # Call the service method
    result = await task_management_service.extract_and_save_task_metadata(document_id)
    
    # Verify the repository methods were called
    mock_document_repo.get_by_id.assert_called_once_with(document_id)
    mock_document_version_repo.get_latest_version.assert_called_once_with(document_id)
    mock_task_management_repo.save_task_metadata.assert_called_once()
    
    # Verify the result
    assert result is not None
    assert isinstance(result, TaskMetadata)
    assert result.task_id == "TASK_001"
    assert result.title == "Test Task"

@pytest.mark.asyncio
async def test_update_task_status(task_management_service, mock_task_management_repo, mock_document_repo):
    """Test updating task status."""
    document_id = str(uuid.uuid4())
    new_status = TaskStatus.IN_PROGRESS
    comment = "Started working on task"
    user_id = str(uuid.uuid4())
    
    # Setup document with current status
    document = Document(
        id=document_id,
        name="TASK_001_test_task.md",
        project_id=str(uuid.uuid4()),
        folder_id=str(uuid.uuid4()),
        type="markdown",
        is_task=True,
        status=TaskStatus.TODO,
        created_by=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    mock_document_repo.get_by_id.return_value = document
    
    # Call the service method
    result = await task_management_service.update_task_status(document_id, new_status, comment, user_id)
    
    # Verify the repository methods were called
    mock_document_repo.get_by_id.assert_called_once_with(document_id)
    mock_task_management_repo.save_task_status_update.assert_called_once()
    
    # Verify the result
    assert result is not None
    assert isinstance(result, TaskStatusUpdate)
    assert result.document_id == document_id
    assert result.previous_status == TaskStatus.TODO
    assert result.new_status == TaskStatus.IN_PROGRESS
    assert result.comment == comment
    assert result.created_by == user_id

@pytest.mark.asyncio
async def test_get_task_status_history(task_management_service, mock_task_management_repo):
    """Test getting task status history."""
    document_id = str(uuid.uuid4())
    
    # Call the service method
    result = await task_management_service.get_task_status_history(document_id)
    
    # Verify the repository method was called
    mock_task_management_repo.get_task_status_history.assert_called_once_with(document_id)
    
    # Verify the result
    assert len(result) == 2
    assert result[0]["previous_status"] is None
    assert result[0]["new_status"] == TaskStatus.TODO
    assert result[1]["previous_status"] == TaskStatus.TODO
    assert result[1]["new_status"] == TaskStatus.IN_PROGRESS

@pytest.mark.asyncio
async def test_create_task_relationship(task_management_service, mock_task_management_repo, mock_document_repo):
    """Test creating task relationship."""
    source_document_id = str(uuid.uuid4())
    target_document_id = str(uuid.uuid4())
    relationship_type = TaskRelationshipType.DEPENDS_ON
    description = "Test depends on target"
    user_id = str(uuid.uuid4())
    
    # Call the service method
    result = await task_management_service.create_task_relationship(
        source_document_id, target_document_id, relationship_type, description, user_id
    )
    
    # Verify the repository methods were called
    mock_document_repo.get_by_id.assert_any_call(source_document_id)
    mock_document_repo.get_by_id.assert_any_call(target_document_id)
    mock_task_management_repo.save_task_relationship.assert_called_once()
    
    # Verify the result
    assert result is not None
    assert isinstance(result, TaskRelationship)
    assert result.source_document_id == source_document_id
    assert result.target_document_id == target_document_id
    assert result.relationship_type == relationship_type
    assert result.description == description
    assert result.created_by == user_id

@pytest.mark.asyncio
async def test_get_task_relationships(task_management_service, mock_task_management_repo, mock_document_repo):
    """Test getting task relationships."""
    document_id = str(uuid.uuid4())
    
    # Call the service method
    result = await task_management_service.get_task_relationships(document_id)
    
    # Verify the repository method was called
    mock_task_management_repo.get_task_relationships.assert_called_once_with(document_id)
    
    # Verify the result
    assert "outgoing" in result
    assert "incoming" in result
    assert len(result["outgoing"]) + len(result["incoming"]) > 0

@pytest.mark.asyncio
async def test_get_task_metadata(task_management_service, mock_task_management_repo):
    """Test getting task metadata."""
    document_id = str(uuid.uuid4())
    
    # Call the service method
    result = await task_management_service.get_task_metadata(document_id)
    
    # Verify the repository method was called
    mock_task_management_repo.get_task_metadata.assert_called_once_with(document_id)
    
    # Verify the result
    assert result is not None
    assert isinstance(result, TaskMetadata)
    assert result.task_id == "TASK_001"
    assert result.title == "Test Task"