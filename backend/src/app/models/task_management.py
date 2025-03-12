"""
Task management models.
This module defines the models used for task management, including task detection, metadata extraction,
status tracking, and relationship management.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Literal, Union
from pydantic import BaseModel, Field

from ..db.models import AppBaseModel
import uuid


class TaskStatus(str, Enum):
    """Status of a task."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Priority of a task."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskRelationshipType(str, Enum):
    """Types of relationships between tasks."""
    DEPENDS_ON = "depends_on"
    PARENT_OF = "parent_of"
    RELATED_TO = "related_to"
    BLOCKS = "blocks"
    DUPLICATES = "duplicates"


class TaskStatusUpdate(AppBaseModel):
    """Represents a status update for a task."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    previous_status: Optional[TaskStatus] = None
    new_status: TaskStatus
    comment: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskRelationship(AppBaseModel):
    """Represents a relationship between two tasks."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_document_id: str
    target_document_id: str
    relationship_type: TaskRelationshipType
    description: Optional[str] = None
    is_valid: bool = True
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskMetadata(AppBaseModel):
    """Metadata extracted from a task document."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    task_id: str  # The task identifier (e.g., "TASK_001")
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_effort: Optional[str] = None
    completion_percentage: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    related_tasks: List[str] = Field(default_factory=list)  # List of related task IDs
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskFilter(AppBaseModel):
    """Filter criteria for tasks."""
    status: Optional[List[TaskStatus]] = None
    priority: Optional[List[TaskPriority]] = None
    assignee: Optional[List[str]] = None
    due_date_before: Optional[datetime] = None
    due_date_after: Optional[datetime] = None
    tags: Optional[List[str]] = None
    search_query: Optional[str] = None
    related_to_task_id: Optional[str] = None
    project_id: Optional[str] = None
    folder_id: Optional[str] = None


class TaskSummary(AppBaseModel):
    """Summary information about a task."""
    document_id: str
    task_id: str
    title: str
    status: TaskStatus
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None
    completion_percentage: Optional[int] = None
    updated_at: datetime


class TaskDetailResponse(AppBaseModel):
    """Detailed information about a task, including metadata and relationships."""
    document_id: str
    task_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_effort: Optional[str] = None
    completion_percentage: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    related_tasks: List[Dict[str, Any]] = Field(default_factory=list)  # Detailed info about related tasks
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    status_history: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TaskListResponse(AppBaseModel):
    """Response for a list of tasks."""
    tasks: List[TaskSummary] = Field(default_factory=list)
    total_count: int
    page: int = 1
    per_page: int = 20
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class TaskStatusUpdateRequest(AppBaseModel):
    """Request to update a task's status."""
    status: TaskStatus
    comment: Optional[str] = None


class TaskRelationshipRequest(AppBaseModel):
    """Request to create a relationship between tasks."""
    target_task_id: str
    relationship_type: TaskRelationshipType
    description: Optional[str] = None


class TaskStatistics(AppBaseModel):
    """Statistics about tasks in a project."""
    total_tasks: int
    by_status: Dict[TaskStatus, int] = Field(default_factory=dict)
    by_priority: Dict[TaskPriority, int] = Field(default_factory=dict)
    by_assignee: Dict[str, int] = Field(default_factory=dict)
    overdue_tasks: int = 0
    completed_tasks_last_week: int = 0
    created_tasks_last_week: int = 0
    average_completion_time_days: Optional[float] = None