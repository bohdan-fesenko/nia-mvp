"""
Agent models for the AI Project Assistant.
This module defines the data models for agents, tasks, chat sessions, and related entities.
"""
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from datetime import datetime
import uuid
from pydantic import BaseModel, Field


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class AgentType(str, Enum):
    """Agent types."""
    CONVERSATION = "conversation_agent"
    DOCUMENT = "document_agent"
    TASK = "task_agent"
    ANALYSIS = "analysis_agent"


class AgentTaskType(str, Enum):
    """Agent task types."""
    DOCUMENT_CREATION = "document_creation"
    DOCUMENT_MODIFICATION = "document_modification"
    DOCUMENT_ANALYSIS = "document_analysis"
    TASK_CREATION = "task_creation"
    TASK_ANALYSIS = "task_analysis"
    PROJECT_ANALYSIS = "project_analysis"
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"


class AgentTaskStatus(str, Enum):
    """Agent task statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageSenderType(str, Enum):
    """Message sender types."""
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class QuestionType(str, Enum):
    """Question types."""
    YES_NO = "yes_no"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"


class ApprovalStatus(str, Enum):
    """Approval statuses."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class NotificationType(str, Enum):
    """Notification types."""
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_MODIFIED = "document_modified"
    QUESTION = "question"
    APPROVAL_REQUEST = "approval_request"
    SYSTEM = "system"


class NotificationPriority(str, Enum):
    """Notification priorities."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentActivityType(str, Enum):
    """Agent activity types."""
    SESSION_CREATED = "session_created"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_DELEGATED = "task_delegated"
    TASK_INTERRUPTED = "task_interrupted"
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_MODIFIED = "document_modified"
    DOCUMENT_ANALYZED = "document_analyzed"
    QUESTION_ASKED = "question_asked"
    QUESTION_ANSWERED = "question_answered"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESPONSE = "approval_response"


class Agent(BaseModel):
    """Agent model."""
    id: str = Field(default_factory=generate_uuid)
    name: str
    type: AgentType
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class AgentTask(BaseModel):
    """Agent task model."""
    id: str = Field(default_factory=generate_uuid)
    agent_id: str
    requested_by: str
    parent_task_id: Optional[str] = None
    session_id: Optional[str] = None
    description: str
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    task_type: AgentTaskType
    priority: int = 3  # 1-5, where 1 is highest
    context: Dict[str, Any] = Field(default_factory=dict)
    result_document_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskExecutionStep(BaseModel):
    """Task execution step model."""
    id: str = Field(default_factory=generate_uuid)
    task_id: str
    step_number: int
    description: str
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    details: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class TaskStatusUpdate(BaseModel):
    """Task status update model."""
    id: str = Field(default_factory=generate_uuid)
    task_id: str
    previous_status: Optional[AgentTaskStatus] = None
    new_status: AgentTaskStatus
    progress_percentage: Optional[int] = None
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ChatSession(BaseModel):
    """Chat session model."""
    id: str = Field(default_factory=generate_uuid)
    user_id: str
    title: str
    context: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ChatMessage(BaseModel):
    """Chat message model."""
    id: str = Field(default_factory=generate_uuid)
    session_id: str
    content: str
    sender_type: MessageSenderType
    sender_id: str
    document_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)


class AgentQuestion(BaseModel):
    """Agent question model."""
    id: str = Field(default_factory=generate_uuid)
    session_id: str
    agent_id: str
    question: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    answer: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None  # seconds
    created_at: datetime = Field(default_factory=datetime.now)
    answered_at: Optional[datetime] = None


class AgentApprovalRequest(BaseModel):
    """Agent approval request model."""
    id: str = Field(default_factory=generate_uuid)
    session_id: str
    agent_id: str
    action: str
    details: Dict[str, Any]
    approved: Optional[bool] = None
    response: Optional[str] = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    context: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None  # seconds
    created_at: datetime = Field(default_factory=datetime.now)
    responded_at: Optional[datetime] = None


class Notification(BaseModel):
    """Notification model."""
    id: str = Field(default_factory=generate_uuid)
    user_id: str
    title: str
    content: str
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    related_id: Optional[str] = None
    related_type: Optional[str] = None
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    read_at: Optional[datetime] = None


class AgentActivityLog(BaseModel):
    """Agent activity log model."""
    id: str = Field(default_factory=generate_uuid)
    agent_id: str
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    document_id: Optional[str] = None
    activity_type: AgentActivityType
    description: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)


class DocumentDiff(BaseModel):
    """Document diff model."""
    id: str = Field(default_factory=generate_uuid)
    document_id: str
    before_content: str
    after_content: str
    changes: List[Dict[str, Any]]
    created_by: str
    task_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)