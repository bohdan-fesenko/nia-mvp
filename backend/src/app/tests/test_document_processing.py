"""
Tests for the document processing functionality.
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from ..models.document_processing import (
    MarkdownElement, MarkdownElementType, HeadingElement, 
    DocumentReference, ExtractedMetadata, ConsistencyIssue, ConsistencyReport
)
from ..services.document_processing_service import DocumentProcessingService
from ..services.diff_service import DiffService


@pytest.fixture
def mock_document_processing_repo():
    """Create a mock document processing repository."""
    repo = AsyncMock()
    repo.save_extracted_metadata = AsyncMock(return_value=str(uuid.uuid4()))
    repo.save_consistency_report = AsyncMock(return_value=str(uuid.uuid4()))
    repo.save_document_diff = AsyncMock(return_value=str(uuid.uuid4()))
    return repo


@pytest.fixture
def mock_document_repo():
    """Create a mock document repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=MagicMock(
        id=str(uuid.uuid4()),
        name="Test Document",
        type="markdown",
        is_task=False,
        status=None,
        is_pinned=False,
        project_id=str(uuid.uuid4()),
        folder_id=None,
        created_by=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    ))
    return repo


@pytest.fixture
def mock_document_version_repo():
    """Create a mock document version repository."""
    repo = AsyncMock()
    repo.get_latest_version = AsyncMock(return_value=MagicMock(
        id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        version_number=1,
        content="# Test Document\n\nThis is a test document.",
        created_by=str(uuid.uuid4()),
        change_summary=None,
        created_at=datetime.utcnow()
    ))
    repo.get_by_id = AsyncMock(return_value=MagicMock(
        id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        version_number=1,
        content="# Test Document\n\nThis is a test document.",
        created_by=str(uuid.uuid4()),
        change_summary=None,
        created_at=datetime.utcnow()
    ))
    return repo


@pytest.fixture
def document_processing_service(
    mock_document_processing_repo, mock_document_repo, mock_document_version_repo
):
    """Create a document processing service with mock repositories."""
    return DocumentProcessingService(
        document_processing_repo=mock_document_processing_repo,
        document_repo=mock_document_repo,
        document_version_repo=mock_document_version_repo
    )


@pytest.mark.asyncio
async def test_parse_markdown(document_processing_service):
    """Test parsing Markdown content."""
    content = "# Test Heading\n\nThis is a paragraph.\n\n```python\nprint('Hello, world!')\n```"
    
    html_content, elements = await document_processing_service.parse_markdown(content)
    
    assert html_content is not None
    assert "<h1>Test Heading</h1>" in html_content
    assert len(elements) > 0
    
    # Check that we extracted the heading
    heading_elements = [e for e in elements if e.type == MarkdownElementType.HEADING]
    assert len(heading_elements) == 1
    assert heading_elements[0].text == "Test Heading"
    assert heading_elements[0].level == 1


@pytest.mark.asyncio
async def test_extract_metadata(document_processing_service):
    """Test extracting metadata from document content."""
    document_id = str(uuid.uuid4())
    content = """# Test Document
    
This is a test document.

- [x] Task 1
- [ ] Task 2

[Link to another document](other-doc.md)
"""
    
    # Parse Markdown first to get elements
    _, elements = await document_processing_service.parse_markdown(content)
    
    # Extract metadata
    metadata = await document_processing_service.extract_metadata(document_id, content, elements)
    
    assert metadata.document_id == document_id
    assert metadata.title == "Test Document"
    assert len(metadata.headings) == 1
    assert len(metadata.tasks) > 0
    assert len(metadata.references) > 0


@pytest.mark.asyncio
async def test_check_consistency(document_processing_service):
    """Test checking document consistency."""
    document_id = str(uuid.uuid4())
    
    # Create metadata with a broken link
    metadata = ExtractedMetadata(
        document_id=document_id,
        title="Test Document",
        headings=[{"level": 1, "text": "Test Document", "position": {}}],
        references=[
            DocumentReference(
                source_document_id=document_id,
                target_document_id="non-existent-id",
                reference_type="link",
                context="[Link](non-existent.md)",
                is_valid=False
            )
        ],
        tasks=[],
        entities={}
    )
    
    # Check consistency
    report = await document_processing_service.check_consistency(document_id, metadata)
    
    assert report.document_id == document_id
    assert len(report.issues) > 0
    assert any(issue.issue_type == "broken_link" for issue in report.issues)


@pytest.mark.asyncio
async def test_process_document(document_processing_service):
    """Test processing a document."""
    document_id = str(uuid.uuid4())
    
    # Process document
    result = await document_processing_service.process_document(document_id)
    
    assert result["document_id"] == document_id
    assert "html_content" in result
    assert "metadata" in result
    assert "consistency_report" in result
    assert "chunks" in result


@pytest.mark.asyncio
async def test_generate_document_diff(document_processing_service):
    """Test generating a document diff."""
    document_id = str(uuid.uuid4())
    old_version_id = str(uuid.uuid4())
    new_version_id = str(uuid.uuid4())
    
    # Mock the diff service
    with patch("app.services.diff_service.diff_service") as mock_diff_service:
        mock_diff_service.generate_document_diff.return_value = {
            "text_diff": {
                "hunks": [],
                "stats": {"lines_added": 1, "lines_removed": 0, "lines_changed": 0, "total_changes": 1}
            }
        }
        mock_diff_service.create_document_diff.return_value = MagicMock()
        
        # Generate diff
        diff = await document_processing_service.generate_document_diff(
            document_id, old_version_id, new_version_id
        )
        
        assert diff is not None
        document_processing_service.document_processing_repo.save_document_diff.assert_called_once()