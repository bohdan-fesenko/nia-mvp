"""
Database models and schemas for the application.
This file defines the data models that will be used with Neo4j and for LLM interactions.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Annotated
from pydantic import BaseModel, Field, EmailStr, model_validator, ConfigDict
import uuid


# Base model with common configuration
class AppBaseModel(BaseModel):
    """Base model with common configuration for all models"""
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {}  # Will be overridden by child classes
        }
    )


# User models
class User(AppBaseModel):
    """User model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    password: str  # This is the hashed password
    image: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "name": "John Doe",
                "password": "[hashed password]",
                "image": "https://example.com/avatar.jpg",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }
    )


class UserCreate(AppBaseModel):
    """Model for user creation"""
    email: EmailStr
    name: str
    password: str
    image: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "password": "securepassword123",
                "image": "https://example.com/avatar.jpg"
            }
        }
    )


class UserUpdate(AppBaseModel):
    """Model for user update"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    image: Optional[str] = None
    password: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe Updated",
                "email": "updated@example.com",
                "image": "https://example.com/new-avatar.jpg"
            }
        }
    )


class UserResponse(AppBaseModel):
    """User response model (without sensitive data)"""
    id: str
    email: EmailStr
    name: str
    image: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "name": "John Doe",
                "image": "https://example.com/avatar.jpg",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }
    )


# Project models
class Project(AppBaseModel):
    """Project model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_archived: bool = False
    owner_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "AI Project Assistant",
                "description": "A project management tool with AI capabilities",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "is_archived": False,
                "owner_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class ProjectCreate(AppBaseModel):
    """Model for project creation"""
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "AI Project Assistant",
                "description": "A project management tool with AI capabilities"
            }
        }
    )


class ProjectUpdate(AppBaseModel):
    """Model for project update"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "AI Project Assistant V2",
                "description": "Updated description",
                "is_archived": True
            }
        }
    )


class ProjectResponse(AppBaseModel):
    """Project response model"""
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    owner_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "AI Project Assistant",
                "description": "A project management tool with AI capabilities",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "is_archived": False,
                "owner_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


# Document models
class Document(AppBaseModel):
    """Document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    type: str  # e.g., "markdown", "code", "task", etc.
    is_task: bool = False
    status: Optional[str] = None  # For task documents: "todo", "in_progress", "done", etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_archived: bool = False
    owner_id: str
    project_id: str
    folder_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Project Requirements",
                "type": "markdown",
                "is_task": False,
                "status": None,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "is_archived": False,
                "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                "project_id": "550e8400-e29b-41d4-a716-446655440002",
                "folder_id": "550e8400-e29b-41d4-a716-446655440003"
            }
        }
    )


class DocumentCreate(AppBaseModel):
    """Model for document creation"""
    title: str
    type: str
    is_task: bool = False
    status: Optional[str] = None
    project_id: str
    folder_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Project Requirements",
                "type": "markdown",
                "is_task": False,
                "status": None,
                "project_id": "550e8400-e29b-41d4-a716-446655440002",
                "folder_id": "550e8400-e29b-41d4-a716-446655440003"
            }
        }
    )


class DocumentUpdate(AppBaseModel):
    """Model for document update"""
    title: Optional[str] = None
    type: Optional[str] = None
    is_task: Optional[bool] = None
    status: Optional[str] = None
    is_archived: Optional[bool] = None
    folder_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Project Requirements",
                "status": "completed",
                "is_archived": True
            }
        }
    )


class DocumentResponse(AppBaseModel):
    """Document response model"""
    id: str
    title: str
    type: str
    is_task: bool
    status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    owner_id: str
    project_id: str
    folder_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Project Requirements",
                "type": "markdown",
                "is_task": False,
                "status": None,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "is_archived": False,
                "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                "project_id": "550e8400-e29b-41d4-a716-446655440002",
                "folder_id": "550e8400-e29b-41d4-a716-446655440003"
            }
        }
    )


# DocumentVersion models
class DocumentVersion(AppBaseModel):
    """DocumentVersion model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    version_number: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    document_id: str
    author_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "# Project Requirements\n\nThis document outlines...",
                "version_number": 1,
                "created_at": "2023-01-01T00:00:00",
                "document_id": "550e8400-e29b-41d4-a716-446655440001",
                "author_id": "550e8400-e29b-41d4-a716-446655440002"
            }
        }
    )


class DocumentVersionCreate(AppBaseModel):
    """Model for document version creation"""
    content: str
    document_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "# Project Requirements\n\nThis document outlines...",
                "document_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class DocumentVersionResponse(AppBaseModel):
    """DocumentVersion response model"""
    id: str
    content: str
    version_number: int
    created_at: datetime
    document_id: str
    author_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "# Project Requirements\n\nThis document outlines...",
                "version_number": 1,
                "created_at": "2023-01-01T00:00:00",
                "document_id": "550e8400-e29b-41d4-a716-446655440001",
                "author_id": "550e8400-e29b-41d4-a716-446655440002"
            }
        }
    )


# Folder models
class Folder(AppBaseModel):
    """Folder model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_archived: bool = False
    project_id: str
    parent_folder_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Documentation",
                "description": "Project documentation folder",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "is_archived": False,
                "project_id": "550e8400-e29b-41d4-a716-446655440001",
                "parent_folder_id": None
            }
        }
    )


class FolderCreate(AppBaseModel):
    """Model for folder creation"""
    name: str
    description: Optional[str] = None
    project_id: str
    parent_folder_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Documentation",
                "description": "Project documentation folder",
                "project_id": "550e8400-e29b-41d4-a716-446655440001",
                "parent_folder_id": None
            }
        }
    )


class FolderUpdate(AppBaseModel):
    """Model for folder update"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None
    parent_folder_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Documentation",
                "description": "Updated project documentation folder",
                "is_archived": True
            }
        }
    )


class FolderResponse(AppBaseModel):
    """Folder response model"""
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    project_id: str
    parent_folder_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Documentation",
                "description": "Project documentation folder",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "is_archived": False,
                "project_id": "550e8400-e29b-41d4-a716-446655440001",
                "parent_folder_id": None
            }
        }
    )


# Vector models
class VectorEmbedding(AppBaseModel):
    """VectorEmbedding model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vector_id: str  # ID in the vector database (Qdrant)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    chunk_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "vector_id": "qdrant-vector-id-123",
                "created_at": "2023-01-01T00:00:00",
                "chunk_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class DocumentChunk(AppBaseModel):
    """DocumentChunk model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    chunk_index: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    document_id: str
    embedding_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "This is a chunk of document content...",
                "chunk_index": 0,
                "created_at": "2023-01-01T00:00:00",
                "document_id": "550e8400-e29b-41d4-a716-446655440001",
                "embedding_id": "550e8400-e29b-41d4-a716-446655440002"
            }
        }
    )


class DocumentChunkCreate(AppBaseModel):
    """Model for document chunk creation"""
    content: str
    chunk_index: int
    document_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "This is a chunk of document content...",
                "chunk_index": 0,
                "document_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


# Agent models
class Agent(AppBaseModel):
    """Agent model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # e.g., "assistant", "researcher", "coder", etc.
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Research Assistant",
                "type": "researcher",
                "description": "An agent that helps with research tasks",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }
    )


class AgentCreate(AppBaseModel):
    """Model for agent creation"""
    name: str
    type: str
    description: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Research Assistant",
                "type": "researcher",
                "description": "An agent that helps with research tasks"
            }
        }
    )


class AgentUpdate(AppBaseModel):
    """Model for agent update"""
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Research Assistant",
                "description": "Updated description"
            }
        }
    )


class AgentResponse(AppBaseModel):
    """Agent response model"""
    id: str
    name: str
    type: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Research Assistant",
                "type": "researcher",
                "description": "An agent that helps with research tasks",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }
    )


# AgentTask models
class AgentTask(AppBaseModel):
    """AgentTask model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    status: str = "pending"  # "pending", "in_progress", "completed", "failed"
    result: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    agent_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Research AI trends",
                "description": "Find the latest trends in AI research",
                "status": "pending",
                "result": None,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "agent_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class AgentTaskCreate(AppBaseModel):
    """Model for agent task creation"""
    title: str
    description: Optional[str] = None
    agent_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Research AI trends",
                "description": "Find the latest trends in AI research",
                "agent_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class AgentTaskUpdate(AppBaseModel):
    """Model for agent task update"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "completed",
                "result": "Research findings: 1. Large language models are trending..."
            }
        }
    )


class AgentTaskResponse(AppBaseModel):
    """AgentTask response model"""
    id: str
    title: str
    description: Optional[str] = None
    status: str
    result: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    agent_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Research AI trends",
                "description": "Find the latest trends in AI research",
                "status": "completed",
                "result": "Research findings: 1. Large language models are trending...",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "agent_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


# Chat models
class ChatSession(AppBaseModel):
    """ChatSession model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Project Planning Discussion",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "user_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class ChatSessionCreate(AppBaseModel):
    """Model for chat session creation"""
    title: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Project Planning Discussion"
            }
        }
    )


class ChatSessionUpdate(AppBaseModel):
    """Model for chat session update"""
    title: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Project Planning Discussion"
            }
        }
    )


class ChatSessionResponse(AppBaseModel):
    """ChatSession response model"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Project Planning Discussion",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "user_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class ChatMessage(AppBaseModel):
    """ChatMessage model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    role: str  # "user", "assistant", "system"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: str
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "How can I start planning my project?",
                "role": "user",
                "created_at": "2023-01-01T00:00:00",
                "session_id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440002"
            }
        }
    )


class ChatMessageCreate(AppBaseModel):
    """Model for chat message creation"""
    content: str
    role: str
    session_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "How can I start planning my project?",
                "role": "user",
                "session_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class ChatMessageResponse(AppBaseModel):
    """ChatMessage response model"""
    id: str
    content: str
    role: str
    created_at: datetime
    session_id: str
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "How can I start planning my project?",
                "role": "user",
                "created_at": "2023-01-01T00:00:00",
                "session_id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440002"
            }
        }
    )


# Notepad models
class Notepad(AppBaseModel):
    """Notepad model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Project Notes",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "user_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class NotepadCreate(AppBaseModel):
    """Model for notepad creation"""
    title: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Project Notes"
            }
        }
    )


class NotepadUpdate(AppBaseModel):
    """Model for notepad update"""
    title: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Project Notes"
            }
        }
    )


class NotepadResponse(AppBaseModel):
    """Notepad response model"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Project Notes",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "user_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class NotepadEntry(AppBaseModel):
    """NotepadEntry model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    notepad_id: str
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "Important note about the project architecture...",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "notepad_id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440002"
            }
        }
    )


class NotepadEntryCreate(AppBaseModel):
    """Model for notepad entry creation"""
    content: str
    notepad_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Important note about the project architecture...",
                "notepad_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class NotepadEntryUpdate(AppBaseModel):
    """Model for notepad entry update"""
    content: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Updated note about the project architecture..."
            }
        }
    )


class NotepadEntryResponse(AppBaseModel):
    """NotepadEntry response model"""
    id: str
    content: str
    created_at: datetime
    updated_at: datetime
    notepad_id: str
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "Important note about the project architecture...",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "notepad_id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440002"
            }
        }
    )


# StatusUpdate models
class StatusUpdate(AppBaseModel):
    """StatusUpdate model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    type: str  # "progress", "blocker", "milestone", etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "Completed the database setup",
                "type": "progress",
                "created_at": "2023-01-01T00:00:00",
                "user_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class StatusUpdateCreate(AppBaseModel):
    """Model for status update creation"""
    content: str
    type: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Completed the database setup",
                "type": "progress"
            }
        }
    )


class StatusUpdateResponse(AppBaseModel):
    """StatusUpdate response model"""
    id: str
    content: str
    type: str
    created_at: datetime
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "Completed the database setup",
                "type": "progress",
                "created_at": "2023-01-01T00:00:00",
                "user_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )