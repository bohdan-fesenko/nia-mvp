"""
API routes for document processing.
This module provides API endpoints for document processing operations.
"""
import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body

from ...models.document_processing import (
    DocumentDiff, ExtractedMetadata, ConsistencyReport, ConsistencyIssue
)
from ...services.document_processing_service import DocumentProcessingService
from ...repositories.document_processing_repository import DocumentProcessingRepository
from ...repositories.document_repository import DocumentRepository
from ...repositories.document_version_repository import DocumentVersionRepository
from ...db.neo4j_client import get_neo4j_client

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/document-processing",
    tags=["document-processing"],
    responses={404: {"description": "Not found"}},
)

async def get_document_processing_service():
    """
    Dependency to get the document processing service.
    
    Returns:
        A document processing service
    """
    client = await get_neo4j_client()
    document_processing_repo = DocumentProcessingRepository(client)
    document_repo = DocumentRepository(client)
    document_version_repo = DocumentVersionRepository(client)
    
    return DocumentProcessingService(
        document_processing_repo=document_processing_repo,
        document_repo=document_repo,
        document_version_repo=document_version_repo
    )

@router.post("/process/{document_id}")
async def process_document(
    document_id: str = Path(..., description="The ID of the document to process"),
    version_id: Optional[str] = Query(None, description="Optional version ID to process (defaults to latest)"),
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> Dict[str, Any]:
    """
    Process a document, extracting metadata, rendering Markdown, and checking consistency.
    
    Args:
        document_id: The ID of the document to process
        version_id: Optional version ID to process (defaults to latest)
        service: The document processing service
        
    Returns:
        A dictionary containing the processing results
    """
    try:
        result = await service.process_document(document_id, version_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@router.post("/diff/{document_id}")
async def generate_document_diff(
    document_id: str = Path(..., description="The ID of the document"),
    old_version_id: str = Query(..., description="The ID of the old version"),
    new_version_id: str = Query(..., description="The ID of the new version"),
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> Dict[str, Any]:
    """
    Generate a diff between two document versions.
    
    Args:
        document_id: The ID of the document
        old_version_id: The ID of the old version
        new_version_id: The ID of the new version
        service: The document processing service
        
    Returns:
        The generated diff
    """
    try:
        diff = await service.generate_document_diff(document_id, old_version_id, new_version_id)
        return diff.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating document diff: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating document diff: {str(e)}")

@router.get("/diff/{diff_id}")
async def get_document_diff(
    diff_id: str = Path(..., description="The ID of the diff to get"),
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> Dict[str, Any]:
    """
    Get a document diff by ID.
    
    Args:
        diff_id: The ID of the diff to get
        service: The document processing service
        
    Returns:
        The document diff
    """
    try:
        diff = await service.get_document_diff(diff_id)
        if not diff:
            raise HTTPException(status_code=404, detail=f"Diff not found: {diff_id}")
        
        return diff.dict()
    except Exception as e:
        logger.error(f"Error getting document diff: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting document diff: {str(e)}")

@router.get("/diffs/{document_id}")
async def get_document_diffs(
    document_id: str = Path(..., description="The ID of the document"),
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> List[Dict[str, Any]]:
    """
    Get all diffs for a document.
    
    Args:
        document_id: The ID of the document
        service: The document processing service
        
    Returns:
        A list of document diffs
    """
    try:
        diffs = await service.get_document_diffs(document_id)
        return diffs
    except Exception as e:
        logger.error(f"Error getting document diffs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting document diffs: {str(e)}")

@router.get("/metadata/{document_id}")
async def get_extracted_metadata(
    document_id: str = Path(..., description="The ID of the document"),
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> Dict[str, Any]:
    """
    Get extracted metadata for a document.
    
    Args:
        document_id: The ID of the document
        service: The document processing service
        
    Returns:
        The extracted metadata
    """
    try:
        metadata = await service.get_extracted_metadata(document_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Metadata not found for document: {document_id}")
        
        return metadata.dict()
    except Exception as e:
        logger.error(f"Error getting extracted metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting extracted metadata: {str(e)}")

@router.get("/consistency-report/{report_id}")
async def get_consistency_report(
    report_id: str = Path(..., description="The ID of the report to get"),
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> Dict[str, Any]:
    """
    Get a consistency report by ID.
    
    Args:
        report_id: The ID of the report to get
        service: The document processing service
        
    Returns:
        The consistency report
    """
    try:
        report = await service.get_consistency_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Consistency report not found: {report_id}")
        
        return report.dict()
    except Exception as e:
        logger.error(f"Error getting consistency report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting consistency report: {str(e)}")

@router.get("/consistency-issues/{document_id}")
async def get_document_consistency_issues(
    document_id: str = Path(..., description="The ID of the document"),
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> List[Dict[str, Any]]:
    """
    Get all consistency issues for a document.
    
    Args:
        document_id: The ID of the document
        service: The document processing service
        
    Returns:
        A list of consistency issues
    """
    try:
        issues = await service.get_document_consistency_issues(document_id)
        return [issue.dict() for issue in issues]
    except Exception as e:
        logger.error(f"Error getting document consistency issues: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting document consistency issues: {str(e)}")

@router.post("/render-mermaid")
async def render_mermaid_diagram(
    diagram_code: str = Body(..., description="The Mermaid diagram code to render"),
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> Dict[str, Any]:
    """
    Render a Mermaid diagram to SVG.
    
    Args:
        diagram_code: The Mermaid diagram code to render
        service: The document processing service
        
    Returns:
        A dictionary containing the SVG output and any error message
    """
    try:
        svg_output, error = await service.render_mermaid_diagram(diagram_code)
        
        return {
            "svg_output": svg_output,
            "error": error
        }
    except Exception as e:
        logger.error(f"Error rendering Mermaid diagram: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error rendering Mermaid diagram: {str(e)}")