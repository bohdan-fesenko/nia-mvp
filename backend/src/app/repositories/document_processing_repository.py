"""
Document processing repository implementation.
This module provides the repository implementation for document processing entities.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Tuple

from ..db.models import Document, DocumentVersion
from ..models.document_processing import (
    DocumentDiff, DiffHunk, DiffLine, DiffChangeType,
    ExtractedMetadata, DocumentReference, ConsistencyIssue, ConsistencyReport
)
from .neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)

class DocumentProcessingRepository:
    """Repository for document processing entities."""
    
    def __init__(self, client):
        """
        Initialize the repository with a Neo4j client.
        
        Args:
            client: Neo4j client
        """
        self.client = client
    
    async def save_document_diff(self, diff: DocumentDiff) -> str:
        """
        Save a document diff to the database.
        
        Args:
            diff: The document diff to save
            
        Returns:
            The ID of the saved diff
        """
        try:
            # Convert the diff to a dictionary
            diff_dict = diff.dict()
            
            # Create the diff node
            create_diff_query = """
            CREATE (d:DocumentDiff {
                id: $id,
                document_id: $document_id,
                old_version_id: $old_version_id,
                new_version_id: $new_version_id,
                old_version_number: $old_version_number,
                new_version_number: $new_version_number,
                stats: $stats,
                created_at: datetime($created_at),
                created_by: $created_by
            })
            RETURN d
            """
            
            # Prepare parameters for the query
            params = {
                "id": diff.id,
                "document_id": diff.document_id,
                "old_version_id": diff.old_version_id,
                "new_version_id": diff.new_version_id,
                "old_version_number": diff.old_version_number,
                "new_version_number": diff.new_version_number,
                "stats": diff_dict["stats"],
                "created_at": diff.created_at.isoformat(),
                "created_by": diff.created_by
            }
            
            # Execute the query
            result = await self.client.execute_query_async(create_diff_query, params)
            
            if not result:
                raise Exception("Failed to create document diff")
            
            # Create hunks and lines
            for hunk in diff.hunks:
                # Create hunk node
                create_hunk_query = """
                CREATE (h:DiffHunk {
                    id: $id,
                    old_start: $old_start,
                    old_count: $old_count,
                    new_start: $new_start,
                    new_count: $new_count,
                    header: $header
                })
                RETURN h
                """
                
                hunk_params = {
                    "id": hunk.id,
                    "old_start": hunk.old_start,
                    "old_count": hunk.old_count,
                    "new_start": hunk.new_start,
                    "new_count": hunk.new_count,
                    "header": hunk.header
                }
                
                hunk_result = await self.client.execute_query_async(create_hunk_query, hunk_params)
                
                if not hunk_result:
                    logger.error(f"Failed to create hunk node for diff {diff.id}")
                    continue
                
                # Create relationship between diff and hunk
                diff_hunk_rel_query = """
                MATCH (d:DocumentDiff {id: $diff_id}), (h:DiffHunk {id: $hunk_id})
                CREATE (d)-[r:HAS_HUNK]->(h)
                RETURN r
                """
                
                diff_hunk_params = {
                    "diff_id": diff.id,
                    "hunk_id": hunk.id
                }
                
                await self.client.execute_query_async(diff_hunk_rel_query, diff_hunk_params)
                
                # Create line nodes for each line in the hunk
                for i, line in enumerate(hunk.lines):
                    create_line_query = """
                    CREATE (l:DiffLine {
                        id: $id,
                        line_number_old: $line_number_old,
                        line_number_new: $line_number_new,
                        content: $content,
                        change_type: $change_type,
                        inline_changes: $inline_changes,
                        line_index: $line_index
                    })
                    RETURN l
                    """
                    
                    line_id = str(uuid.uuid4())
                    line_params = {
                        "id": line_id,
                        "line_number_old": line.line_number_old,
                        "line_number_new": line.line_number_new,
                        "content": line.content,
                        "change_type": line.change_type,
                        "inline_changes": line.inline_changes,
                        "line_index": i
                    }
                    
                    line_result = await self.client.execute_query_async(create_line_query, line_params)
                    
                    if not line_result:
                        logger.error(f"Failed to create line node for hunk {hunk.id}")
                        continue
                    
                    # Create relationship between hunk and line
                    hunk_line_rel_query = """
                    MATCH (h:DiffHunk {id: $hunk_id}), (l:DiffLine {id: $line_id})
                    CREATE (h)-[r:HAS_LINE {index: $index}]->(l)
                    RETURN r
                    """
                    
                    hunk_line_params = {
                        "hunk_id": hunk.id,
                        "line_id": line_id,
                        "index": i
                    }
                    
                    await self.client.execute_query_async(hunk_line_rel_query, hunk_line_params)
            
            # Create relationships to document and versions
            doc_diff_rel_query = """
            MATCH (d:Document {id: $document_id}), (diff:DocumentDiff {id: $diff_id})
            CREATE (d)-[r:HAS_DIFF]->(diff)
            RETURN r
            """
            
            doc_diff_params = {
                "document_id": diff.document_id,
                "diff_id": diff.id
            }
            
            await self.client.execute_query_async(doc_diff_rel_query, doc_diff_params)
            
            # Create relationships to versions
            old_version_rel_query = """
            MATCH (v:DocumentVersion {id: $version_id}), (diff:DocumentDiff {id: $diff_id})
            CREATE (v)-[r:IS_OLD_VERSION_IN]->(diff)
            RETURN r
            """
            
            old_version_params = {
                "version_id": diff.old_version_id,
                "diff_id": diff.id
            }
            
            await self.client.execute_query_async(old_version_rel_query, old_version_params)
            
            new_version_rel_query = """
            MATCH (v:DocumentVersion {id: $version_id}), (diff:DocumentDiff {id: $diff_id})
            CREATE (v)-[r:IS_NEW_VERSION_IN]->(diff)
            RETURN r
            """
            
            new_version_params = {
                "version_id": diff.new_version_id,
                "diff_id": diff.id
            }
            
            await self.client.execute_query_async(new_version_rel_query, new_version_params)
            
            return diff.id
        except Exception as e:
            logger.error(f"Error saving document diff: {str(e)}")
            raise
    
    async def get_document_diff(self, diff_id: str) -> Optional[DocumentDiff]:
        """
        Get a document diff by ID.
        
        Args:
            diff_id: The ID of the diff to get
            
        Returns:
            The document diff if found, None otherwise
        """
        try:
            # Get the diff node
            query = """
            MATCH (d:DocumentDiff {id: $diff_id})
            RETURN d
            """
            
            result = await self.client.execute_query_async(query, {"diff_id": diff_id})
            
            if not result:
                return None
            
            diff_node = result[0]['d']
            
            # Get the hunks
            hunks_query = """
            MATCH (d:DocumentDiff {id: $diff_id})-[:HAS_HUNK]->(h:DiffHunk)
            RETURN h
            ORDER BY h.old_start
            """
            
            hunks_result = await self.client.execute_query_async(hunks_query, {"diff_id": diff_id})
            
            hunks = []
            
            for hunk_record in hunks_result:
                hunk_node = hunk_record['h']
                
                # Get the lines for this hunk
                lines_query = """
                MATCH (h:DiffHunk {id: $hunk_id})-[r:HAS_LINE]->(l:DiffLine)
                RETURN l, r.index as line_index
                ORDER BY r.index
                """
                
                lines_result = await self.client.execute_query_async(lines_query, {"hunk_id": hunk_node['id']})
                
                lines = []
                
                for line_record in lines_result:
                    line_node = line_record['l']
                    
                    line = DiffLine(
                        line_number_old=line_node.get('line_number_old'),
                        line_number_new=line_node.get('line_number_new'),
                        content=line_node.get('content', ''),
                        change_type=line_node.get('change_type', DiffChangeType.UNCHANGED),
                        inline_changes=line_node.get('inline_changes')
                    )
                    
                    lines.append(line)
                
                hunk = DiffHunk(
                    id=hunk_node.get('id'),
                    old_start=hunk_node.get('old_start'),
                    old_count=hunk_node.get('old_count'),
                    new_start=hunk_node.get('new_start'),
                    new_count=hunk_node.get('new_count'),
                    header=hunk_node.get('header', ''),
                    lines=lines
                )
                
                hunks.append(hunk)
            
            # Create the DocumentDiff object
            created_at = diff_node.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            return DocumentDiff(
                id=diff_node.get('id'),
                document_id=diff_node.get('document_id'),
                old_version_id=diff_node.get('old_version_id'),
                new_version_id=diff_node.get('new_version_id'),
                old_version_number=diff_node.get('old_version_number'),
                new_version_number=diff_node.get('new_version_number'),
                hunks=hunks,
                stats=diff_node.get('stats', {}),
                created_at=created_at,
                created_by=diff_node.get('created_by')
            )
        except Exception as e:
            logger.error(f"Error getting document diff: {str(e)}")
            raise
    
    async def get_document_diffs(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all diffs for a document.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            A list of document diffs
        """
        try:
            # Get all diffs for the document
            query = """
            MATCH (d:Document {id: $document_id})-[:HAS_DIFF]->(diff:DocumentDiff)
            RETURN diff
            ORDER BY diff.created_at DESC
            """
            
            result = await self.client.execute_query_async(query, {"document_id": document_id})
            
            diffs = []
            
            for record in result:
                diff_node = record['diff']
                
                created_at = diff_node.get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                # Create a simplified diff object (without hunks and lines)
                diff = {
                    "id": diff_node.get('id'),
                    "document_id": diff_node.get('document_id'),
                    "old_version_id": diff_node.get('old_version_id'),
                    "new_version_id": diff_node.get('new_version_id'),
                    "old_version_number": diff_node.get('old_version_number'),
                    "new_version_number": diff_node.get('new_version_number'),
                    "stats": diff_node.get('stats', {}),
                    "created_at": created_at,
                    "created_by": diff_node.get('created_by')
                }
                
                diffs.append(diff)
            
            return diffs
        except Exception as e:
            logger.error(f"Error getting document diffs: {str(e)}")
            raise
    
    async def save_extracted_metadata(self, metadata: ExtractedMetadata) -> str:
        """
        Save extracted metadata to the database.
        
        Args:
            metadata: The extracted metadata to save
            
        Returns:
            The ID of the saved metadata
        """
        try:
            # Convert the metadata to a dictionary
            metadata_dict = metadata.dict()
            
            # Create the metadata node
            create_metadata_query = """
            CREATE (m:ExtractedMetadata {
                id: $id,
                document_id: $document_id,
                title: $title,
                headings: $headings,
                tasks: $tasks,
                entities: $entities,
                summary: $summary,
                created_at: datetime($created_at),
                updated_at: datetime($updated_at)
            })
            RETURN m
            """
            
            # Prepare parameters for the query
            params = {
                "id": metadata.id,
                "document_id": metadata.document_id,
                "title": metadata.title,
                "headings": metadata_dict["headings"],
                "tasks": metadata_dict["tasks"],
                "entities": metadata_dict["entities"],
                "summary": metadata.summary,
                "created_at": metadata.created_at.isoformat(),
                "updated_at": metadata.updated_at.isoformat()
            }
            
            # Execute the query
            result = await self.client.execute_query_async(create_metadata_query, params)
            
            if not result:
                raise Exception("Failed to create extracted metadata")
            
            # Create relationship to document
            doc_metadata_rel_query = """
            MATCH (d:Document {id: $document_id}), (m:ExtractedMetadata {id: $metadata_id})
            CREATE (d)-[r:HAS_METADATA]->(m)
            RETURN r
            """
            
            doc_metadata_params = {
                "document_id": metadata.document_id,
                "metadata_id": metadata.id
            }
            
            await self.client.execute_query_async(doc_metadata_rel_query, doc_metadata_params)
            
            # Create document references
            for reference in metadata.references:
                # Create reference node
                create_ref_query = """
                CREATE (r:DocumentReference {
                    id: $id,
                    source_document_id: $source_document_id,
                    target_document_id: $target_document_id,
                    reference_type: $reference_type,
                    context: $context,
                    is_valid: $is_valid,
                    created_at: datetime($created_at)
                })
                RETURN r
                """
                
                ref_params = {
                    "id": reference.id,
                    "source_document_id": reference.source_document_id,
                    "target_document_id": reference.target_document_id,
                    "reference_type": reference.reference_type,
                    "context": reference.context,
                    "is_valid": reference.is_valid,
                    "created_at": reference.created_at.isoformat()
                }
                
                ref_result = await self.client.execute_query_async(create_ref_query, ref_params)
                
                if not ref_result:
                    logger.error(f"Failed to create reference node for metadata {metadata.id}")
                    continue
                
                # Create relationship between metadata and reference
                metadata_ref_rel_query = """
                MATCH (m:ExtractedMetadata {id: $metadata_id}), (r:DocumentReference {id: $ref_id})
                CREATE (m)-[rel:HAS_REFERENCE]->(r)
                RETURN rel
                """
                
                metadata_ref_params = {
                    "metadata_id": metadata.id,
                    "ref_id": reference.id
                }
                
                await self.client.execute_query_async(metadata_ref_rel_query, metadata_ref_params)
                
                # Create relationships between documents
                doc_ref_rel_query = """
                MATCH (source:Document {id: $source_id}), (target:Document {id: $target_id})
                MERGE (source)-[r:REFERENCES {type: $ref_type}]->(target)
                RETURN r
                """
                
                doc_ref_params = {
                    "source_id": reference.source_document_id,
                    "target_id": reference.target_document_id,
                    "ref_type": reference.reference_type
                }
                
                await self.client.execute_query_async(doc_ref_rel_query, doc_ref_params)
            
            return metadata.id
        except Exception as e:
            logger.error(f"Error saving extracted metadata: {str(e)}")
            raise
    
    async def get_extracted_metadata(self, document_id: str) -> Optional[ExtractedMetadata]:
        """
        Get extracted metadata for a document.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            The extracted metadata if found, None otherwise
        """
        try:
            # Get the metadata node
            query = """
            MATCH (d:Document {id: $document_id})-[:HAS_METADATA]->(m:ExtractedMetadata)
            RETURN m
            ORDER BY m.updated_at DESC
            LIMIT 1
            """
            
            result = await self.client.execute_query_async(query, {"document_id": document_id})
            
            if not result:
                return None
            
            metadata_node = result[0]['m']
            
            # Get the references
            refs_query = """
            MATCH (m:ExtractedMetadata {id: $metadata_id})-[:HAS_REFERENCE]->(r:DocumentReference)
            RETURN r
            """
            
            refs_result = await self.client.execute_query_async(refs_query, {"metadata_id": metadata_node['id']})
            
            references = []
            
            for ref_record in refs_result:
                ref_node = ref_record['r']
                
                created_at = ref_node.get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                reference = DocumentReference(
                    id=ref_node.get('id'),
                    source_document_id=ref_node.get('source_document_id'),
                    target_document_id=ref_node.get('target_document_id'),
                    reference_type=ref_node.get('reference_type'),
                    context=ref_node.get('context', ''),
                    is_valid=ref_node.get('is_valid', True),
                    created_at=created_at
                )
                
                references.append(reference)
            
            # Create the ExtractedMetadata object
            created_at = metadata_node.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            updated_at = metadata_node.get('updated_at')
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
            return ExtractedMetadata(
                id=metadata_node.get('id'),
                document_id=metadata_node.get('document_id'),
                title=metadata_node.get('title'),
                headings=metadata_node.get('headings', []),
                references=references,
                tasks=metadata_node.get('tasks', []),
                entities=metadata_node.get('entities', {}),
                summary=metadata_node.get('summary'),
                created_at=created_at,
                updated_at=updated_at
            )
        except Exception as e:
            logger.error(f"Error getting extracted metadata: {str(e)}")
            raise
    
    async def save_consistency_report(self, report: ConsistencyReport) -> str:
        """
        Save a consistency report to the database.
        
        Args:
            report: The consistency report to save
            
        Returns:
            The ID of the saved report
        """
        try:
            # Convert the report to a dictionary
            report_dict = report.dict()
            
            # Create the report node
            create_report_query = """
            CREATE (r:ConsistencyReport {
                id: $id,
                document_id: $document_id,
                project_id: $project_id,
                summary: $summary,
                created_at: datetime($created_at)
            })
            RETURN r
            """
            
            # Prepare parameters for the query
            params = {
                "id": report.id,
                "document_id": report.document_id,
                "project_id": report.project_id,
                "summary": report_dict["summary"],
                "created_at": report.created_at.isoformat()
            }
            
            # Execute the query
            result = await self.client.execute_query_async(create_report_query, params)
            
            if not result:
                raise Exception("Failed to create consistency report")
            
            # Create relationships
            if report.document_id:
                doc_report_rel_query = """
                MATCH (d:Document {id: $document_id}), (r:ConsistencyReport {id: $report_id})
                CREATE (d)-[rel:HAS_CONSISTENCY_REPORT]->(r)
                RETURN rel
                """
                
                doc_report_params = {
                    "document_id": report.document_id,
                    "report_id": report.id
                }
                
                await self.client.execute_query_async(doc_report_rel_query, doc_report_params)
            
            if report.project_id:
                proj_report_rel_query = """
                MATCH (p:Project {id: $project_id}), (r:ConsistencyReport {id: $report_id})
                CREATE (p)-[rel:HAS_CONSISTENCY_REPORT]->(r)
                RETURN rel
                """
                
                proj_report_params = {
                    "project_id": report.project_id,
                    "report_id": report.id
                }
                
                await self.client.execute_query_async(proj_report_rel_query, proj_report_params)
            
            # Create issues
            for issue in report.issues:
                # Create issue node
                create_issue_query = """
                CREATE (i:ConsistencyIssue {
                    id: $id,
                    document_id: $document_id,
                    issue_type: $issue_type,
                    description: $description,
                    location: $location,
                    suggested_fix: $suggested_fix,
                    severity: $severity,
                    created_at: datetime($created_at)
                })
                RETURN i
                """
                
                issue_dict = issue.dict()
                issue_params = {
                    "id": issue.id,
                    "document_id": issue.document_id,
                    "issue_type": issue.issue_type,
                    "description": issue.description,
                    "location": issue_dict["location"],
                    "suggested_fix": issue.suggested_fix,
                    "severity": issue.severity,
                    "created_at": issue.created_at.isoformat()
                }
                
                issue_result = await self.client.execute_query_async(create_issue_query, issue_params)
                
                if not issue_result:
                    logger.error(f"Failed to create issue node for report {report.id}")
                    continue
                
                # Create relationship between report and issue
                report_issue_rel_query = """
                MATCH (r:ConsistencyReport {id: $report_id}), (i:ConsistencyIssue {id: $issue_id})
                CREATE (r)-[rel:HAS_ISSUE]->(i)
                RETURN rel
                """
                
                report_issue_params = {
                    "report_id": report.id,
                    "issue_id": issue.id
                }
                
                await self.client.execute_query_async(report_issue_rel_query, report_issue_params)
                
                # Create relationship between document and issue
                doc_issue_rel_query = """
                MATCH (d:Document {id: $document_id}), (i:ConsistencyIssue {id: $issue_id})
                CREATE (d)-[rel:HAS_ISSUE]->(i)
                RETURN rel
                """
                
                doc_issue_params = {
                    "document_id": issue.document_id,
                    "issue_id": issue.id
                }
                
                await self.client.execute_query_async(doc_issue_rel_query, doc_issue_params)
            
            return report.id
        except Exception as e:
            logger.error(f"Error saving consistency report: {str(e)}")
            raise
    
    async def get_consistency_report(self, report_id: str) -> Optional[ConsistencyReport]:
        """
        Get a consistency report by ID.
        
        Args:
            report_id: The ID of the report to get
            
        Returns:
            The consistency report if found, None otherwise
        """
        try:
            # Get the report node
            query = """
            MATCH (r:ConsistencyReport {id: $report_id})
            RETURN r
            """
            
            result = await self.client.execute_query_async(query, {"report_id": report_id})
            
            if not result:
                return None
            
            report_node = result[0]['r']
            
            # Get the issues
            issues_query = """
            MATCH (r:ConsistencyReport {id: $report_id})-[:HAS_ISSUE]->(i:ConsistencyIssue)
            RETURN i
            """
            
            issues_result = await self.client.execute_query_async(issues_query, {"report_id": report_id})
            
            issues = []
            
            for issue_record in issues_result:
                issue_node = issue_record['i']
                
                created_at = issue_node.get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                issue = ConsistencyIssue(
                    id=issue_node.get('id'),
                    document_id=issue_node.get('document_id'),
                    issue_type=issue_node.get('issue_type'),
                    description=issue_node.get('description'),
                    location=issue_node.get('location', {}),
                    suggested_fix=issue_node.get('suggested_fix'),
                    severity=issue_node.get('severity', 'warning'),
                    created_at=created_at
                )
                
                issues.append(issue)
            
            # Create the ConsistencyReport object
            created_at = report_node.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            return ConsistencyReport(
                id=report_node.get('id'),
                document_id=report_node.get('document_id'),
                project_id=report_node.get('project_id'),
                issues=issues,
                created_at=created_at,
                summary=report_node.get('summary', {})
            )
        except Exception as e:
            logger.error(f"Error getting consistency report: {str(e)}")
            raise
    
    async def get_document_consistency_issues(self, document_id: str) -> List[ConsistencyIssue]:
        """
        Get all consistency issues for a document.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            A list of consistency issues
        """
        try:
            # Get all issues for the document
            query = """
            MATCH (d:Document {id: $document_id})-[:HAS_ISSUE]->(i:ConsistencyIssue)
            RETURN i
            ORDER BY i.created_at DESC
            """
            
            result = await self.client.execute_query_async(query, {"document_id": document_id})
            
            issues = []
            
            for record in result:
                issue_node = record['i']
                
                created_at = issue_node.get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                issue = ConsistencyIssue(
                    id=issue_node.get('id'),
                    document_id=issue_node.get('document_id'),
                    issue_type=issue_node.get('issue_type'),
                    description=issue_node.get('description'),
                    location=issue_node.get('location', {}),
                    suggested_fix=issue_node.get('suggested_fix'),
                    severity=issue_node.get('severity', 'warning'),
                    created_at=created_at
                )
                
                issues.append(issue)
            
            return issues
        except Exception as e:
            logger.error(f"Error getting document consistency issues: {str(e)}")
            raise