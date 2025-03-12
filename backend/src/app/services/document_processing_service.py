"""
Document processing service.
This module provides functionality for processing documents, including Markdown parsing,
Mermaid diagram rendering, content extraction, consistency verification, and indexing.
"""
import logging
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set, Union
import asyncio
import json

import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.footnotes import FootnoteExtension
import bleach
import mermaid as md
from mermaid.graph import Graph

from ..models.document_processing import (
    MarkdownElement, MarkdownElementType, HeadingElement, CodeBlockElement, 
    MermaidDiagramElement, LinkElement, DocumentReference, ExtractedMetadata,
    ConsistencyIssue, ConsistencyReport, DocumentChunk, DiffChangeType,
    DiffLine, DiffHunk, DocumentDiff
)
from ..repositories.document_processing_repository import DocumentProcessingRepository
from ..repositories.document_repository import DocumentRepository
from ..repositories.document_version_repository import DocumentVersionRepository
from .diff_service import diff_service

logger = logging.getLogger(__name__)

class DocumentProcessingService:
    """Service for processing documents."""
    
    def __init__(self, 
                 document_processing_repo: DocumentProcessingRepository,
                 document_repo: DocumentRepository,
                 document_version_repo: DocumentVersionRepository):
        """
        Initialize the document processing service.
        
        Args:
            document_processing_repo: Repository for document processing
            document_repo: Repository for documents
            document_version_repo: Repository for document versions
        """
        self.document_processing_repo = document_processing_repo
        self.document_repo = document_repo
        self.document_version_repo = document_version_repo
        
        # Configure Markdown parser with extensions
        self.markdown_extensions = [
            FencedCodeExtension(),
            TableExtension(),
            FootnoteExtension(),
            'markdown.extensions.attr_list',
            'markdown.extensions.def_list',
            'markdown.extensions.abbr',
            'markdown.extensions.admonition',
            'markdown.extensions.meta',
            'markdown.extensions.sane_lists',
            'markdown.extensions.smarty',
            'markdown.extensions.toc',
            'markdown.extensions.wikilinks'
        ]
        
        # Configure HTML sanitizer
        self.allowed_tags = [
            'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'p',
            'pre', 'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span',
            'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'br', 'img', 'del', 'ins',
            'sup', 'sub', 'dl', 'dt', 'dd', 'details', 'summary', 'figure', 'figcaption'
        ]
        
        self.allowed_attrs = {
            '*': ['id', 'class', 'style'],
            'a': ['href', 'title', 'target', 'rel'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            'td': ['colspan', 'rowspan', 'align'],
            'th': ['colspan', 'rowspan', 'align']
        }
    
    async def process_document(self, document_id: str, version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a document, extracting metadata, rendering Markdown, and checking consistency.
        
        Args:
            document_id: The ID of the document to process
            version_id: Optional version ID to process (defaults to latest version)
            
        Returns:
            A dictionary containing the processing results
        """
        try:
            # Get the document and version
            document = await self.document_repo.get_by_id(document_id)
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            if version_id:
                version = await self.document_version_repo.get_by_id(version_id)
                if not version:
                    raise ValueError(f"Version not found: {version_id}")
            else:
                version = await self.document_version_repo.get_latest_version(document_id)
                if not version:
                    raise ValueError(f"No versions found for document: {document_id}")
            
            # Process the document content
            content = version.content
            
            # Parse Markdown
            html_content, markdown_elements = await self.parse_markdown(content)
            
            # Extract metadata
            metadata = await self.extract_metadata(document_id, content, markdown_elements)
            
            # Save extracted metadata
            metadata_id = await self.document_processing_repo.save_extracted_metadata(metadata)
            
            # Check consistency
            consistency_report = await self.check_consistency(document_id, metadata)
            
            # Save consistency report
            report_id = await self.document_processing_repo.save_consistency_report(consistency_report)
            
            # Create document chunks for indexing
            chunks = await self.create_document_chunks(document_id, version.id, content)
            
            # Return processing results
            return {
                "document_id": document_id,
                "version_id": version.id,
                "html_content": html_content,
                "metadata": metadata.dict(),
                "consistency_report": consistency_report.dict(),
                "chunks": [chunk.dict() for chunk in chunks]
            }
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise
    
    async def parse_markdown(self, content: str) -> Tuple[str, List[MarkdownElement]]:
        """
        Parse Markdown content and extract elements.
        
        Args:
            content: The Markdown content to parse
            
        Returns:
            A tuple containing the HTML content and a list of extracted Markdown elements
        """
        try:
            # Parse Markdown to HTML
            html_content = markdown.markdown(content, extensions=self.markdown_extensions)
            
            # Sanitize HTML
            html_content = bleach.clean(
                html_content,
                tags=self.allowed_tags,
                attributes=self.allowed_attrs,
                strip=True
            )
            
            # Extract Markdown elements
            elements = await self._extract_markdown_elements(content)
            
            return html_content, elements
        except Exception as e:
            logger.error(f"Error parsing Markdown: {str(e)}")
            raise
    
    async def _extract_markdown_elements(self, content: str) -> List[MarkdownElement]:
        """
        Extract elements from Markdown content.
        
        Args:
            content: The Markdown content to extract elements from
            
        Returns:
            A list of extracted Markdown elements
        """
        elements = []
        lines = content.splitlines()
        
        # Extract headings
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        for i, line in enumerate(lines):
            match = heading_pattern.match(line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                
                element = HeadingElement(
                    type=MarkdownElementType.HEADING,
                    content=line,
                    metadata={"level": level},
                    position={"start_line": i + 1, "end_line": i + 1, "start_col": 0, "end_col": len(line)},
                    level=level,
                    text=text
                )
                
                elements.append(element)
        
        # Extract code blocks
        in_code_block = False
        code_block_start = 0
        code_block_content = []
        code_block_language = None
        
        for i, line in enumerate(lines):
            if line.startswith('```'):
                if not in_code_block:
                    # Start of code block
                    in_code_block = True
                    code_block_start = i
                    code_block_language = line[3:].strip()
                    code_block_content = []
                else:
                    # End of code block
                    in_code_block = False
                    
                    # Check if it's a Mermaid diagram
                    is_mermaid = code_block_language.lower() == 'mermaid'
                    
                    if is_mermaid:
                        # Create Mermaid diagram element
                        diagram_code = '\n'.join(code_block_content)
                        diagram_type = self._detect_mermaid_diagram_type(diagram_code)
                        
                        element = MermaidDiagramElement(
                            type=MarkdownElementType.MERMAID,
                            content='\n'.join(lines[code_block_start:i+1]),
                            metadata={"language": "mermaid", "diagram_type": diagram_type},
                            position={"start_line": code_block_start + 1, "end_line": i + 1, "start_col": 0, "end_col": len(line)},
                            diagram_type=diagram_type,
                            diagram_code=diagram_code,
                            svg_output=None  # Will be rendered later
                        )
                    else:
                        # Create regular code block element
                        element = CodeBlockElement(
                            type=MarkdownElementType.CODE_BLOCK,
                            content='\n'.join(lines[code_block_start:i+1]),
                            metadata={"language": code_block_language},
                            position={"start_line": code_block_start + 1, "end_line": i + 1, "start_col": 0, "end_col": len(line)},
                            language=code_block_language,
                            code='\n'.join(code_block_content)
                        )
                    
                    elements.append(element)
            elif in_code_block:
                code_block_content.append(line)
        
        # Extract links
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        for i, line in enumerate(lines):
            for match in link_pattern.finditer(line):
                text = match.group(1)
                url = match.group(2)
                
                # Check if it's an internal link to another document
                is_internal = url.endswith('.md') or url.startswith('#')
                
                element = LinkElement(
                    type=MarkdownElementType.LINK,
                    content=match.group(0),
                    metadata={"is_internal": is_internal},
                    position={"start_line": i + 1, "end_line": i + 1, "start_col": match.start(), "end_col": match.end()},
                    text=text,
                    url=url,
                    is_internal=is_internal
                )
                
                elements.append(element)
        
        return elements
    
    def _detect_mermaid_diagram_type(self, diagram_code: str) -> str:
        """
        Detect the type of Mermaid diagram from its code.
        
        Args:
            diagram_code: The Mermaid diagram code
            
        Returns:
            The detected diagram type
        """
        diagram_code = diagram_code.strip()
        
        if diagram_code.startswith('graph ') or diagram_code.startswith('flowchart '):
            return 'flowchart'
        elif diagram_code.startswith('sequenceDiagram'):
            return 'sequence'
        elif diagram_code.startswith('classDiagram'):
            return 'class'
        elif diagram_code.startswith('stateDiagram'):
            return 'state'
        elif diagram_code.startswith('erDiagram'):
            return 'er'
        elif diagram_code.startswith('gantt'):
            return 'gantt'
        elif diagram_code.startswith('pie'):
            return 'pie'
        elif diagram_code.startswith('journey'):
            return 'journey'
        else:
            return 'unknown'
    
    async def render_mermaid_diagram(self, diagram_code: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Render a Mermaid diagram to SVG.
        
        Args:
            diagram_code: The Mermaid diagram code
            
        Returns:
            A tuple containing the SVG output and any error message
        """
        try:
            # Use mermaid-py to render the diagram
            diagram_type = self._detect_mermaid_diagram_type(diagram_code)
            graph = Graph(f"{diagram_type}-diagram", diagram_code)
            render = md.Mermaid(graph)
            
            # Get the SVG output
            svg_output = render.to_svg()
            
            return svg_output, None
        except Exception as e:
            logger.error(f"Error rendering Mermaid diagram: {str(e)}")
            return None, str(e)
    
    async def extract_metadata(self, document_id: str, content: str, 
                              markdown_elements: List[MarkdownElement]) -> ExtractedMetadata:
        """
        Extract metadata from document content.
        
        Args:
            document_id: The ID of the document
            content: The document content
            markdown_elements: The extracted Markdown elements
            
        Returns:
            The extracted metadata
        """
        # Extract title from first heading
        title = None
        headings = []
        
        for element in markdown_elements:
            if element.type == MarkdownElementType.HEADING:
                heading = element
                
                if heading.level == 1 and title is None:
                    title = heading.text
                
                headings.append({
                    "level": heading.level,
                    "text": heading.text,
                    "position": heading.position
                })
        
        # Extract references to other documents
        references = []
        
        for element in markdown_elements:
            if element.type == MarkdownElementType.LINK and element.is_internal:
                # This is a placeholder - in a real implementation, you would
                # resolve the link to a document ID
                target_document_id = None
                
                if element.url.endswith('.md'):
                    # Extract the document name from the URL
                    doc_name = element.url.split('/')[-1]
                    
                    # TODO: Look up the document ID based on the name
                    # This would require a repository method to find documents by name
                    
                    reference = DocumentReference(
                        source_document_id=document_id,
                        target_document_id=target_document_id or "unknown",
                        reference_type="link",
                        context=element.content,
                        is_valid=target_document_id is not None
                    )
                    
                    references.append(reference)
        
        # Extract tasks
        tasks = []
        task_pattern = re.compile(r'- \[([ xX])\] (.+)$')
        
        for i, line in enumerate(content.splitlines()):
            match = task_pattern.match(line)
            if match:
                is_completed = match.group(1).lower() == 'x'
                task_text = match.group(2).strip()
                
                tasks.append({
                    "text": task_text,
                    "is_completed": is_completed,
                    "position": {"start_line": i + 1, "end_line": i + 1, "start_col": 0, "end_col": len(line)}
                })
        
        # Extract entities (people, projects, technologies)
        entities = {}
        
        # This is a placeholder - in a real implementation, you would use
        # NLP or other techniques to extract entities
        
        # Generate summary
        summary = None
        
        if title:
            # Simple summary: title + first paragraph
            paragraphs = re.split(r'\n\s*\n', content)
            if len(paragraphs) > 1:
                first_para = paragraphs[1].strip()
                summary = f"{title}: {first_para[:100]}..."
        
        # Create metadata object
        metadata = ExtractedMetadata(
            document_id=document_id,
            title=title,
            headings=headings,
            references=references,
            tasks=tasks,
            entities=entities,
            summary=summary
        )
        
        return metadata
    
    async def check_consistency(self, document_id: str, metadata: ExtractedMetadata) -> ConsistencyReport:
        """
        Check document consistency and generate a report.
        
        Args:
            document_id: The ID of the document
            metadata: The extracted metadata
            
        Returns:
            A consistency report
        """
        issues = []
        
        # Check for broken links
        for reference in metadata.references:
            if not reference.is_valid:
                issue = ConsistencyIssue(
                    document_id=document_id,
                    issue_type="broken_link",
                    description=f"Broken link to document: {reference.target_document_id}",
                    location={"context": reference.context},
                    suggested_fix="Update the link to point to an existing document",
                    severity="warning"
                )
                
                issues.append(issue)
        
        # Check for missing title
        if not metadata.title:
            issue = ConsistencyIssue(
                document_id=document_id,
                issue_type="missing_title",
                description="Document is missing a title (H1 heading)",
                location={},
                suggested_fix="Add a level 1 heading (# Title) at the beginning of the document",
                severity="warning"
            )
            
            issues.append(issue)
        
        # Generate summary statistics
        summary = {
            "total_issues": len(issues),
            "broken_links": sum(1 for issue in issues if issue.issue_type == "broken_link"),
            "missing_title": 1 if not metadata.title else 0,
            "warnings": sum(1 for issue in issues if issue.severity == "warning"),
            "errors": sum(1 for issue in issues if issue.severity == "error")
        }
        
        # Create report
        report = ConsistencyReport(
            document_id=document_id,
            issues=issues,
            summary=summary
        )
        
        return report
    
    async def create_document_chunks(self, document_id: str, version_id: str, content: str) -> List[DocumentChunk]:
        """
        Create document chunks for indexing.
        
        Args:
            document_id: The ID of the document
            version_id: The ID of the document version
            content: The document content
            
        Returns:
            A list of document chunks
        """
        chunks = []
        
        # Split content into paragraphs
        paragraphs = re.split(r'\n\s*\n', content)
        
        # Create chunks (one per paragraph for simplicity)
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
            
            chunk = DocumentChunk(
                document_id=document_id,
                document_version_id=version_id,
                chunk_index=i,
                content=paragraph.strip(),
                metadata={
                    "paragraph_index": i,
                    "char_count": len(paragraph),
                    "word_count": len(paragraph.split())
                }
            )
            
            chunks.append(chunk)
        
        return chunks
    
    async def generate_document_diff(self, document_id: str, old_version_id: str, new_version_id: str) -> DocumentDiff:
        """
        Generate a diff between two document versions.
        
        Args:
            document_id: The ID of the document
            old_version_id: The ID of the old version
            new_version_id: The ID of the new version
            
        Returns:
            A DocumentDiff object
        """
        try:
            # Get the versions
            old_version = await self.document_version_repo.get_by_id(old_version_id)
            if not old_version:
                raise ValueError(f"Old version not found: {old_version_id}")
            
            new_version = await self.document_version_repo.get_by_id(new_version_id)
            if not new_version:
                raise ValueError(f"New version not found: {new_version_id}")
            
            # Convert versions to dictionaries
            old_version_dict = old_version.__dict__
            new_version_dict = new_version.__dict__
            
            # Generate diff using diff service
            diff_result = diff_service.generate_document_diff(old_version_dict, new_version_dict)
            
            # Create DocumentDiff object
            diff = diff_service.create_document_diff(
                document_id=document_id,
                old_version_id=old_version_id,
                new_version_id=new_version_id,
                old_version_number=old_version.version_number,
                new_version_number=new_version.version_number,
                hunks=diff_result["text_diff"]["hunks"],
                stats=diff_result["text_diff"]["stats"],
                created_by=new_version.created_by
            )
            
            # Save diff to database
            await self.document_processing_repo.save_document_diff(diff)
            
            return diff
        except Exception as e:
            logger.error(f"Error generating document diff: {str(e)}")
            raise
    
    async def get_document_diff(self, diff_id: str) -> Optional[DocumentDiff]:
        """
        Get a document diff by ID.
        
        Args:
            diff_id: The ID of the diff to get
            
        Returns:
            The document diff if found, None otherwise
        """
        return await self.document_processing_repo.get_document_diff(diff_id)
    
    async def get_document_diffs(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all diffs for a document.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            A list of document diffs
        """
        return await self.document_processing_repo.get_document_diffs(document_id)
    
    async def get_extracted_metadata(self, document_id: str) -> Optional[ExtractedMetadata]:
        """
        Get extracted metadata for a document.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            The extracted metadata if found, None otherwise
        """
        return await self.document_processing_repo.get_extracted_metadata(document_id)
    
    async def get_consistency_report(self, report_id: str) -> Optional[ConsistencyReport]:
        """
        Get a consistency report by ID.
        
        Args:
            report_id: The ID of the report to get
            
        Returns:
            The consistency report if found, None otherwise
        """
        return await self.document_processing_repo.get_consistency_report(report_id)
    
    async def get_document_consistency_issues(self, document_id: str) -> List[ConsistencyIssue]:
        """
        Get all consistency issues for a document.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            A list of consistency issues
        """
        return await self.document_processing_repo.get_document_consistency_issues(document_id)

# Create a factory function for the service
def create_document_processing_service(
    document_processing_repo: DocumentProcessingRepository,
    document_repo: DocumentRepository,
    document_version_repo: DocumentVersionRepository
) -> DocumentProcessingService:
    """
    Create a document processing service.
    
    Args:
        document_processing_repo: Repository for document processing
        document_repo: Repository for documents
        document_version_repo: Repository for document versions
        
    Returns:
        A document processing service
    """
    return DocumentProcessingService(
        document_processing_repo=document_processing_repo,
        document_repo=document_repo,
        document_version_repo=document_version_repo
    )