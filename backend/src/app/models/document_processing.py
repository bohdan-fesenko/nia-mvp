"""
Document processing models.
This module defines the models used for document processing, including content extraction and analysis.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Literal
from pydantic import BaseModel, Field

from ..db.models import AppBaseModel
import uuid


class MarkdownElementType(str, Enum):
    """Types of Markdown elements that can be extracted from a document."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    CODE_BLOCK = "code_block"
    BLOCKQUOTE = "blockquote"
    TABLE = "table"
    MERMAID = "mermaid"
    IMAGE = "image"
    LINK = "link"
    TASK_LIST = "task_list"
    HORIZONTAL_RULE = "horizontal_rule"
    FOOTNOTE = "footnote"


class MarkdownElement(AppBaseModel):
    """Represents a parsed Markdown element."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MarkdownElementType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    position: Dict[str, int] = Field(default_factory=dict)  # start_line, end_line, start_col, end_col


class HeadingElement(MarkdownElement):
    """Represents a heading in Markdown."""
    level: int
    text: str


class CodeBlockElement(MarkdownElement):
    """Represents a code block in Markdown."""
    language: Optional[str] = None
    code: str


class MermaidDiagramElement(MarkdownElement):
    """Represents a Mermaid diagram in Markdown."""
    diagram_type: str  # flowchart, sequence, class, etc.
    diagram_code: str
    svg_output: Optional[str] = None
    render_error: Optional[str] = None


class LinkElement(MarkdownElement):
    """Represents a link in Markdown."""
    text: str
    url: str
    is_internal: bool = False
    target_document_id: Optional[str] = None


class DocumentReference(AppBaseModel):
    """Represents a reference to another document."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_document_id: str
    target_document_id: str
    reference_type: str  # "link", "dependency", "mention", etc.
    context: str  # The text surrounding the reference
    is_valid: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExtractedMetadata(AppBaseModel):
    """Metadata extracted from a document."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    title: Optional[str] = None
    headings: List[Dict[str, Any]] = Field(default_factory=list)
    references: List[DocumentReference] = Field(default_factory=list)
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    entities: Dict[str, List[str]] = Field(default_factory=dict)  # Entity type -> list of entities
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentChunk(AppBaseModel):
    """A chunk of document content for indexing."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    document_version_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DiffChangeType(str, Enum):
    """Types of changes in a diff."""
    ADDED = "added"
    REMOVED = "removed"
    UNCHANGED = "unchanged"
    MODIFIED = "modified"  # For line-level changes that have both additions and removals


class DiffLine(AppBaseModel):
    """Represents a single line in a diff."""
    line_number_old: Optional[int] = None  # Line number in old version (None for added lines)
    line_number_new: Optional[int] = None  # Line number in new version (None for removed lines)
    content: str  # The content of the line
    change_type: DiffChangeType  # Type of change
    inline_changes: Optional[List[Dict[str, Any]]] = None  # For character-level changes within a line


class DiffHunk(AppBaseModel):
    """Represents a hunk in a diff (a group of changed lines)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    old_start: int  # Starting line in old version
    old_count: int  # Number of lines in old version
    new_start: int  # Starting line in new version
    new_count: int  # Number of lines in new version
    header: str  # The hunk header (e.g., "@@ -1,7 +1,9 @@")
    lines: List[DiffLine] = Field(default_factory=list)  # The lines in this hunk


class DocumentDiff(AppBaseModel):
    """Represents a diff between two document versions."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    old_version_id: str
    new_version_id: str
    old_version_number: int
    new_version_number: int
    hunks: List[DiffHunk] = Field(default_factory=list)
    stats: Dict[str, int] = Field(default_factory=dict)  # Stats about the diff (lines added, removed, etc.)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


class ConsistencyIssue(AppBaseModel):
    """Represents a consistency issue in a document."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    issue_type: str  # "broken_link", "missing_reference", "inconsistent_data", etc.
    description: str
    location: Dict[str, Any] = Field(default_factory=dict)  # Information about where the issue is located
    suggested_fix: Optional[str] = None
    severity: str = "warning"  # "info", "warning", "error"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConsistencyReport(AppBaseModel):
    """A report of consistency issues in a document or project."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: Optional[str] = None
    project_id: Optional[str] = None
    issues: List[ConsistencyIssue] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    summary: Dict[str, int] = Field(default_factory=dict)  # Counts by issue type and severity


class SearchQuery(AppBaseModel):
    """A search query for documents."""
    query: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[str] = None
    limit: int = 10
    offset: int = 0


class SearchResult(AppBaseModel):
    """A search result item."""
    document_id: str
    document_title: str
    document_type: str
    snippet: str
    score: float
    highlights: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(AppBaseModel):
    """Response for a search query."""
    results: List[SearchResult] = Field(default_factory=list)
    total_count: int
    query: str
    execution_time_ms: int