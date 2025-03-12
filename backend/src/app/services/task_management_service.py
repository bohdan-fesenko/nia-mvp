"""
Task management service.
This module provides functionality for managing tasks, including task detection, metadata extraction,
status tracking, and relationship management.
"""
import logging
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set, Union

from ..models.task_management import (
    TaskStatus, TaskPriority, TaskRelationshipType,
    TaskStatusUpdate, TaskRelationship, TaskMetadata,
    TaskSummary, TaskDetailResponse, TaskListResponse,
    TaskFilter, TaskStatistics
)
from ..repositories.task_management_repository import TaskManagementRepository
from ..repositories.document_repository import DocumentRepository
from ..repositories.document_version_repository import DocumentVersionRepository

logger = logging.getLogger(__name__)

class TaskManagementService:
    """Service for managing tasks."""
    
    def __init__(self, 
                 task_management_repo: TaskManagementRepository,
                 document_repo: DocumentRepository,
                 document_version_repo: DocumentVersionRepository):
        """
        Initialize the task management service.
        
        Args:
            task_management_repo: Repository for task management
            document_repo: Repository for documents
            document_version_repo: Repository for document versions
        """
        self.task_management_repo = task_management_repo
        self.document_repo = document_repo
        self.document_version_repo = document_version_repo
    
    async def detect_task_documents(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Detect documents that follow the task naming convention.
        
        Args:
            project_id: Optional project ID to filter by
            
        Returns:
            A list of detected task documents
        """
        try:
            # Detect task documents using the repository
            task_documents = await self.task_management_repo.detect_task_documents(project_id)
            
            # For each detected task document, check if it already has task metadata
            for task_doc in task_documents:
                if not task_doc.get('is_task'):
                    # If not marked as a task, try to extract metadata and save it
                    try:
                        await self.extract_and_save_task_metadata(task_doc['id'])
                    except Exception as e:
                        logger.error(f"Error extracting metadata for task {task_doc['id']}: {str(e)}")
            
            # Refresh the list after potential updates
            return await self.task_management_repo.detect_task_documents(project_id)
        except Exception as e:
            logger.error(f"Error detecting task documents: {str(e)}")
            raise
    
    async def extract_and_save_task_metadata(self, document_id: str) -> TaskMetadata:
        """
        Extract metadata from a task document and save it.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            The extracted and saved task metadata
        """
        try:
            # Get the document
            document = await self.document_repo.get_by_id(document_id)
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            # Get the latest version
            version = await self.document_version_repo.get_latest_version(document_id)
            if not version:
                raise ValueError(f"No versions found for document: {document_id}")
            
            # Extract task ID from document name
            task_id_match = re.match(r'^(TASK_\d+)_.*$', document.name)
            task_id = task_id_match.group(1) if task_id_match else f"TASK_{document_id[:8]}"
            
            # Parse the content to extract metadata
            content = version.content
            metadata = await self._extract_task_metadata_from_content(document_id, task_id, content)
            
            # Save the metadata
            metadata_id = await self.task_management_repo.save_task_metadata(metadata)
            
            # If the document doesn't have a status yet, set it to the metadata status
            if not document.status:
                # Create a status update
                status_update = TaskStatusUpdate(
                    document_id=document_id,
                    previous_status=None,
                    new_status=metadata.status,
                    comment="Initial status set from metadata extraction",
                    created_by=document.created_by
                )
                
                await self.task_management_repo.save_task_status_update(status_update)
            
            return metadata
        except Exception as e:
            logger.error(f"Error extracting and saving task metadata: {str(e)}")
            raise
    
    async def _extract_task_metadata_from_content(self, document_id: str, task_id: str, content: str) -> TaskMetadata:
        """
        Extract task metadata from document content.
        
        Args:
            document_id: The ID of the document
            task_id: The task identifier
            content: The document content
            
        Returns:
            The extracted task metadata
        """
        # Initialize metadata with defaults
        title = None
        description = None
        status = TaskStatus.TODO
        priority = None
        assignee = None
        due_date = None
        estimated_effort = None
        completion_percentage = None
        tags = []
        related_tasks = []
        custom_fields = {}
        
        # Split content into lines
        lines = content.splitlines()
        
        # Extract title from first heading
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        # Extract description from first paragraph after title
        description_lines = []
        in_description = False
        for line in lines:
            if line.startswith('# '):
                in_description = True
                continue
            elif in_description and line.strip() == '':
                continue
            elif in_description and line.startswith('#'):
                break
            elif in_description:
                description_lines.append(line)
        
        if description_lines:
            description = '\n'.join(description_lines).strip()
        
        # Extract status
        status_pattern = re.compile(r'status:?\s*(todo|in[_\s]progress|done|blocked|cancelled)', re.IGNORECASE)
        for line in lines:
            match = status_pattern.search(line)
            if match:
                status_str = match.group(1).lower().replace(' ', '_')
                if status_str == 'in_progress' or status_str == 'inprogress':
                    status = TaskStatus.IN_PROGRESS
                elif status_str == 'done':
                    status = TaskStatus.DONE
                elif status_str == 'blocked':
                    status = TaskStatus.BLOCKED
                elif status_str == 'cancelled':
                    status = TaskStatus.CANCELLED
                else:
                    status = TaskStatus.TODO
                break
        
        # Extract priority
        priority_pattern = re.compile(r'priority:?\s*(low|medium|high|critical)', re.IGNORECASE)
        for line in lines:
            match = priority_pattern.search(line)
            if match:
                priority_str = match.group(1).lower()
                if priority_str == 'low':
                    priority = TaskPriority.LOW
                elif priority_str == 'medium':
                    priority = TaskPriority.MEDIUM
                elif priority_str == 'high':
                    priority = TaskPriority.HIGH
                elif priority_str == 'critical':
                    priority = TaskPriority.CRITICAL
                break
        
        # Extract assignee
        assignee_pattern = re.compile(r'assignee:?\s*(.+?)(?:$|\s*[,;])', re.IGNORECASE)
        for line in lines:
            match = assignee_pattern.search(line)
            if match:
                assignee = match.group(1).strip()
                break
        
        # Extract due date
        due_date_pattern = re.compile(r'due[_\s]date:?\s*(\d{4}-\d{2}-\d{2})', re.IGNORECASE)
        for line in lines:
            match = due_date_pattern.search(line)
            if match:
                try:
                    due_date = datetime.fromisoformat(match.group(1))
                except ValueError:
                    logger.warning(f"Invalid due date format in task {document_id}")
                break
        
        # Extract estimated effort
        effort_pattern = re.compile(r'estimated[_\s]effort:?\s*(.+?)(?:$|\s*[,;])', re.IGNORECASE)
        for line in lines:
            match = effort_pattern.search(line)
            if match:
                estimated_effort = match.group(1).strip()
                break
        
        # Extract completion percentage
        completion_pattern = re.compile(r'completion:?\s*(\d+)%', re.IGNORECASE)
        for line in lines:
            match = completion_pattern.search(line)
            if match:
                try:
                    completion_percentage = int(match.group(1))
                    if completion_percentage < 0 or completion_percentage > 100:
                        completion_percentage = None
                except ValueError:
                    logger.warning(f"Invalid completion percentage in task {document_id}")
                break
        
        # Extract tags
        tags_pattern = re.compile(r'tags:?\s*(.+?)(?:$|;)', re.IGNORECASE)
        for line in lines:
            match = tags_pattern.search(line)
            if match:
                tags_str = match.group(1).strip()
                tags = [tag.strip() for tag in tags_str.split(',')]
                break
        
        # Extract related tasks
        related_pattern = re.compile(r'related[_\s]tasks:?\s*(.+?)(?:$|;)', re.IGNORECASE)
        for line in lines:
            match = related_pattern.search(line)
            if match:
                related_str = match.group(1).strip()
                related_tasks = [task.strip() for task in related_str.split(',')]
                break
        
        # Extract dependencies from content
        depends_pattern = re.compile(r'depends[_\s]on:?\s*(.+?)(?:$|;)', re.IGNORECASE)
        for line in lines:
            match = depends_pattern.search(line)
            if match:
                depends_str = match.group(1).strip()
                depends_tasks = [task.strip() for task in depends_str.split(',')]
                for task in depends_tasks:
                    if task not in related_tasks:
                        related_tasks.append(task)
                break
        
        # Extract custom fields from any section titled "Custom Fields" or similar
        in_custom_fields = False
        for i, line in enumerate(lines):
            if re.match(r'^#+\s*Custom\s+Fields', line, re.IGNORECASE):
                in_custom_fields = True
                continue
            
            if in_custom_fields and line.strip() == '':
                continue
            elif in_custom_fields and line.startswith('#'):
                break
            elif in_custom_fields and ':' in line:
                key, value = line.split(':', 1)
                custom_fields[key.strip()] = value.strip()
        
        # If no title was found, use the task ID as title
        if not title:
            title = f"Task {task_id}"
        
        # Create the metadata object
        metadata = TaskMetadata(
            document_id=document_id,
            task_id=task_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            assignee=assignee,
            due_date=due_date,
            estimated_effort=estimated_effort,
            completion_percentage=completion_percentage,
            tags=tags,
            related_tasks=related_tasks,
            custom_fields=custom_fields
        )
        
        return metadata
    
    async def update_task_status(self, document_id: str, new_status: TaskStatus, comment: Optional[str] = None, user_id: str = None) -> TaskStatusUpdate:
        """
        Update the status of a task.
        
        Args:
            document_id: The ID of the document
            new_status: The new status
            comment: Optional comment about the status change
            user_id: The ID of the user making the change
            
        Returns:
            The status update
        """
        try:
            # Get the document
            document = await self.document_repo.get_by_id(document_id)
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            # Get current status
            current_status = document.status
            
            # If status hasn't changed, return early
            if current_status == new_status:
                logger.info(f"Task {document_id} status unchanged: {new_status}")
                return None
            
            # Create status update
            status_update = TaskStatusUpdate(
                document_id=document_id,
                previous_status=current_status,
                new_status=new_status,
                comment=comment,
                created_by=user_id or document.created_by
            )
            
            # Save the status update
            await self.task_management_repo.save_task_status_update(status_update)
            
            return status_update
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            raise
    
    async def get_task_status_history(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get the status history for a task.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            A list of status updates with user information
        """
        try:
            # Get status updates from repository
            status_updates = await self.task_management_repo.get_task_status_history(document_id)
            
            # Enrich with user information
            result = []
            for update in status_updates:
                # Convert to dict for easier manipulation
                update_dict = update.dict()
                
                # TODO: Add user information lookup if needed
                # For now, just include the user ID
                update_dict["user_id"] = update.created_by
                update_dict["user_name"] = "Unknown"  # Placeholder
                
                result.append(update_dict)
            
            return result
        except Exception as e:
            logger.error(f"Error getting task status history: {str(e)}")
            raise
    
    async def create_task_relationship(self, source_document_id: str, target_document_id: str, 
                                      relationship_type: TaskRelationshipType, 
                                      description: Optional[str] = None, 
                                      user_id: Optional[str] = None) -> TaskRelationship:
        """
        Create a relationship between two tasks.
        
        Args:
            source_document_id: The ID of the source document
            target_document_id: The ID of the target document
            relationship_type: The type of relationship
            description: Optional description of the relationship
            user_id: The ID of the user creating the relationship
            
        Returns:
            The created relationship
        """
        try:
            # Verify both documents exist
            source_doc = await self.document_repo.get_by_id(source_document_id)
            if not source_doc:
                raise ValueError(f"Source document not found: {source_document_id}")
            
            target_doc = await self.document_repo.get_by_id(target_document_id)
            if not target_doc:
                raise ValueError(f"Target document not found: {target_document_id}")
            
            # Create relationship
            relationship = TaskRelationship(
                source_document_id=source_document_id,
                target_document_id=target_document_id,
                relationship_type=relationship_type,
                description=description,
                created_by=user_id or source_doc.created_by
            )
            
            # Save the relationship
            await self.task_management_repo.save_task_relationship(relationship)
            
            return relationship
        except Exception as e:
            logger.error(f"Error creating task relationship: {str(e)}")
            raise
    
    async def get_task_relationships(self, document_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all relationships for a task, categorized by direction and type.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            A dictionary with categorized relationships
        """
        try:
            # Get relationships from repository
            relationships = await self.task_management_repo.get_task_relationships(document_id)
            
            # Categorize relationships
            result = {
                "outgoing": [],
                "incoming": []
            }
            
            for rel in relationships:
                # Convert to dict for easier manipulation
                rel_dict = rel.dict()
                
                # Add document names
                if rel.source_document_id == document_id:
                    # This is an outgoing relationship
                    target_doc = await self.document_repo.get_by_id(rel.target_document_id)
                    if target_doc:
                        rel_dict["target_document_name"] = target_doc.name
                    
                    result["outgoing"].append(rel_dict)
                else:
                    # This is an incoming relationship
                    source_doc = await self.document_repo.get_by_id(rel.source_document_id)
                    if source_doc:
                        rel_dict["source_document_name"] = source_doc.name
                    
                    result["incoming"].append(rel_dict)
            
            return result
        except Exception as e:
            logger.error(f"Error getting task relationships: {str(e)}")
            raise
    
    async def get_task_metadata(self, document_id: str) -> Optional[TaskMetadata]:
        """
        Get task metadata for a document.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            The task metadata if found, None otherwise
        """
        try:
            return await self.task_management_repo.get_task_metadata(document_id)
        except Exception as e:
            logger.error(f"Error getting task metadata: {str(e)}")
            raise
    
    async def get_task_details(self, document_id: str) -> TaskDetailResponse:
        """
        Get detailed information about a task.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            Detailed task information
        """
        try:
            # Get the document
            document = await self.document_repo.get_by_id(document_id)
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            # Get task metadata
            metadata = await self.task_management_repo.get_task_metadata(document_id)
            if not metadata:
                # If no metadata exists, try to extract it
                metadata = await self.extract_and_save_task_metadata(document_id)
            
            # Get status history
            status_history = await self.get_task_status_history(document_id)
            
            # Get relationships
            relationships = await self.get_task_relationships(document_id)
            
            # Get related task details
            related_tasks = []
            for task_id in metadata.related_tasks:
                # Find the document with this task ID
                # This is a simplified approach - in a real implementation, you would have a more robust way to find related tasks
                related_doc = None
                
                # First check outgoing relationships
                for rel in relationships["outgoing"]:
                    related_metadata = await self.task_management_repo.get_task_metadata(rel["target_document_id"])
                    if related_metadata and related_metadata.task_id == task_id:
                        related_doc = await self.document_repo.get_by_id(rel["target_document_id"])
                        break
                
                # Then check incoming relationships
                if not related_doc:
                    for rel in relationships["incoming"]:
                        related_metadata = await self.task_management_repo.get_task_metadata(rel["source_document_id"])
                        if related_metadata and related_metadata.task_id == task_id:
                            related_doc = await self.document_repo.get_by_id(rel["source_document_id"])
                            break
                
                if related_doc and related_metadata:
                    related_tasks.append({
                        "document_id": related_doc.id,
                        "task_id": related_metadata.task_id,
                        "title": related_metadata.title,
                        "status": related_metadata.status
                    })
            
            # Create response
            return TaskDetailResponse(
                document_id=document.id,
                task_id=metadata.task_id,
                title=metadata.title,
                description=metadata.description,
                status=metadata.status,
                priority=metadata.priority,
                assignee=metadata.assignee,
                due_date=metadata.due_date,
                estimated_effort=metadata.estimated_effort,
                completion_percentage=metadata.completion_percentage,
                tags=metadata.tags,
                related_tasks=related_tasks,
                custom_fields=metadata.custom_fields,
                status_history=status_history,
                created_at=document.created_at,
                updated_at=document.updated_at
            )
        except Exception as e:
            logger.error(f"Error getting task details: {str(e)}")
            raise
    
    async def get_tasks(self, filter_criteria: Optional[Dict[str, Any]] = None, 
                       page: int = 1, per_page: int = 20) -> TaskListResponse:
        """
        Get a list of tasks based on filter criteria.
        
        Args:
            filter_criteria: Optional filter criteria
            page: Page number
            per_page: Number of items per page
            
        Returns:
            A list of tasks with pagination information
        """
        try:
            # Use empty dict if no filter criteria provided
            filter_criteria = filter_criteria or {}
            
            # Get tasks from repository
            tasks, total_count = await self.task_management_repo.get_tasks_by_filter(
                filter_criteria, page, per_page
            )
            
            # Create response
            return TaskListResponse(
                tasks=tasks,
                total_count=total_count,
                page=page,
                per_page=per_page,
                filters_applied=filter_criteria
            )
        except Exception as e:
            logger.error(f"Error getting tasks: {str(e)}")
            raise
    
    async def get_task_statistics(self, project_id: Optional[str] = None) -> TaskStatistics:
        """
        Get statistics about tasks.
        
        Args:
            project_id: Optional project ID to filter by
            
        Returns:
            Task statistics
        """
        try:
            return await self.task_management_repo.get_task_statistics(project_id)
        except Exception as e:
            logger.error(f"Error getting task statistics: {str(e)}")
            raise
    
    async def detect_task_relationships(self, document_id: Optional[str] = None, project_id: Optional[str] = None) -> List[TaskRelationship]:
        """
        Detect relationships between tasks based on content analysis.
        
        Args:
            document_id: Optional document ID to analyze
            project_id: Optional project ID to analyze all tasks within
            
        Returns:
            A list of detected relationships
        """
        try:
            detected_relationships = []
            
            # If document_id is provided, analyze just that document
            if document_id:
                # Get the document
                document = await self.document_repo.get_by_id(document_id)
                if not document:
                    raise ValueError(f"Document not found: {document_id}")
                
                # Get the latest version
                version = await self.document_version_repo.get_latest_version(document_id)
                if not version:
                    raise ValueError(f"No versions found for document: {document_id}")
                
                # Get task metadata
                metadata = await self.task_management_repo.get_task_metadata(document_id)
                if not metadata:
                    # If no metadata exists, try to extract it
                    metadata = await self.extract_and_save_task_metadata(document_id)
                
                # Analyze content for relationships
                relationships = await self._detect_relationships_in_content(document, version.content, metadata)
                detected_relationships.extend(relationships)
            
            # If project_id is provided, analyze all tasks in the project
            elif project_id:
                # Get all task documents in the project
                task_documents = await self.task_management_repo.detect_task_documents(project_id)
                
                # Analyze each task document
                for task_doc in task_documents:
                    # Skip if we already analyzed this document
                    if document_id and task_doc['id'] == document_id:
                        continue
                    
                    # Get the document
                    document = await self.document_repo.get_by_id(task_doc['id'])
                    if not document:
                        continue
                    
                    # Get the latest version
                    version = await self.document_version_repo.get_latest_version(task_doc['id'])
                    if not version:
                        continue
                    
                    # Get task metadata
                    metadata = await self.task_management_repo.get_task_metadata(task_doc['id'])
                    if not metadata:
                        # If no metadata exists, try to extract it
                        try:
                            metadata = await self.extract_and_save_task_metadata(task_doc['id'])
                        except Exception:
                            continue
                    
                    # Analyze content for relationships
                    relationships = await self._detect_relationships_in_content(document, version.content, metadata)
                    detected_relationships.extend(relationships)
            
            return detected_relationships
        except Exception as e:
            logger.error(f"Error detecting task relationships: {str(e)}")
            raise
    
    async def _detect_relationships_in_content(self, document, content: str, metadata: TaskMetadata) -> List[TaskRelationship]:
        """
        Detect relationships in document content.
        
        Args:
            document: The document object
            content: The document content
            metadata: The task metadata
            
        Returns:
            A list of detected relationships
        """
        detected_relationships = []
        
        # Get all task documents to match against
        all_tasks = await self.task_management_repo.detect_task_documents()
        task_id_to_doc_id = {task['task_id']: task['id'] for task in all_tasks if 'task_id' in task}
        
        # Look for explicit mentions of dependencies
        depends_pattern = re.compile(r'depends[_\s]on:?\s*(.+?)(?:$|;)', re.IGNORECASE)
        for line in content.splitlines():
            match = depends_pattern.search(line)
            if match:
                depends_str = match.group(1).strip()
                depends_tasks = [task.strip() for task in depends_str.split(',')]
                
                for task_id in depends_tasks:
                    # Find the document ID for this task ID
                    if task_id in task_id_to_doc_id:
                        target_document_id = task_id_to_doc_id[task_id]
                        
                        # Create relationship
                        relationship = TaskRelationship(
                            source_document_id=document.id,
                            target_document_id=target_document_id,
                            relationship_type=TaskRelationshipType.DEPENDS_ON,
                            description=f"Detected dependency in document content",
                            created_by=document.created_by
                        )
                        
                        # Save the relationship
                        try:
                            await self.task_management_repo.save_task_relationship(relationship)
                            detected_relationships.append(relationship)
                        except Exception as e:
                            logger.error(f"Error saving detected relationship: {str(e)}")
        
        # Look for explicit mentions of related tasks
        related_pattern = re.compile(r'related[_\s]to:?\s*(.+?)(?:$|;)', re.IGNORECASE)
        for line in content.splitlines():
            match = related_pattern.search(line)
            if match:
                related_str = match.group(1).strip()
                related_tasks = [task.strip() for task in related_str.split(',')]
                
                for task_id in related_tasks:
                    # Find the document ID for this task ID
                    if task_id in task_id_to_doc_id:
                        target_document_id = task_id_to_doc_id[task_id]
                        
                        # Create relationship
                        relationship = TaskRelationship(
                            source_document_id=document.id,
                            target_document_id=target_document_id,
                            relationship_type=TaskRelationshipType.RELATED_TO,
                            description=f"Detected related task in document content",
                            created_by=document.created_by
                        )
                        
                        # Save the relationship
                        try:
                            await self.task_management_repo.save_task_relationship(relationship)
                            detected_relationships.append(relationship)
                        except Exception as e:
                            logger.error(f"Error saving detected relationship: {str(e)}")
        
        # Look for explicit mentions of parent/child relationships
        parent_pattern = re.compile(r'parent[_\s]of:?\s*(.+?)(?:$|;)', re.IGNORECASE)
        for line in content.splitlines():
            match = parent_pattern.search(line)
            if match:
                children_str = match.group(1).strip()
                children_tasks = [task.strip() for task in children_str.split(',')]
                
                for task_id in children_tasks:
                    # Find the document ID for this task ID
                    if task_id in task_id_to_doc_id:
                        target_document_id = task_id_to_doc_id[task_id]
                        
                        # Create relationship
                        relationship = TaskRelationship(
                            source_document_id=document.id,
                            target_document_id=target_document_id,
                            relationship_type=TaskRelationshipType.PARENT_OF,
                            description=f"Detected parent-child relationship in document content",
                            created_by=document.created_by
                        )
                        
                        # Save the relationship
                        try:
                            await self.task_management_repo.save_task_relationship(relationship)
                            detected_relationships.append(relationship)
                        except Exception as e:
                            logger.error(f"Error saving detected relationship: {str(e)}")
        
        # Look for explicit mentions of blocking relationships
        blocks_pattern = re.compile(r'blocks:?\s*(.+?)(?:$|;)', re.IGNORECASE)
        for line in content.splitlines():
            match = blocks_pattern.search(line)
            if match:
                blocked_str = match.group(1).strip()
                blocked_tasks = [task.strip() for task in blocked_str.split(',')]
                
                for task_id in blocked_tasks:
                    # Find the document ID for this task ID
                    if task_id in task_id_to_doc_id:
                        target_document_id = task_id_to_doc_id[task_id]
                        
                        # Create relationship
                        relationship = TaskRelationship(
                            source_document_id=document.id,
                            target_document_id=target_document_id,
                            relationship_type=TaskRelationshipType.BLOCKS,
                            description=f"Detected blocking relationship in document content",
                            created_by=document.created_by
                        )
                        
                        # Save the relationship
                        try:
                            await self.task_management_repo.save_task_relationship(relationship)
                            detected_relationships.append(relationship)
                        except Exception as e:
                            logger.error(f"Error saving detected relationship: {str(e)}")
        
        return detected_relationships

# Create a factory function for the service
def create_task_management_service(
    task_management_repo: TaskManagementRepository,
    document_repo: DocumentRepository,
    document_version_repo: DocumentVersionRepository
) -> TaskManagementService:
    """
    Create a task management service.
    
    Args:
        task_management_repo: Repository for task management
        document_repo: Repository for documents
        document_version_repo: Repository for document versions
        
    Returns:
        A task management service
    """
    return TaskManagementService(
        task_management_repo=task_management_repo,
        document_repo=document_repo,
        document_version_repo=document_version_repo
    )