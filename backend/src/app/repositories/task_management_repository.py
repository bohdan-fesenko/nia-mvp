"""
Task management repository implementation.
This module provides the repository implementation for task management entities.
"""
import logging
import uuid
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple

from ..db.models import Document, DocumentVersion
from ..models.task_management import (
    TaskStatus, TaskPriority, TaskRelationshipType,
    TaskStatusUpdate, TaskRelationship, TaskMetadata,
    TaskSummary, TaskStatistics
)
from .neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)

class TaskManagementRepository:
    """Repository for task management entities."""
    
    def __init__(self, client):
        """
        Initialize the repository with a Neo4j client.
        
        Args:
            client: Neo4j client
        """
        self.client = client
    
    async def save_task_metadata(self, metadata: TaskMetadata) -> str:
        """
        Save task metadata to the database.
        
        Args:
            metadata: The task metadata to save
            
        Returns:
            The ID of the saved metadata
        """
        try:
            # Convert the metadata to a dictionary
            metadata_dict = metadata.dict()
            
            # Create the metadata node
            create_metadata_query = """
            CREATE (m:TaskMetadata {
                id: $id,
                document_id: $document_id,
                task_id: $task_id,
                title: $title,
                description: $description,
                status: $status,
                priority: $priority,
                assignee: $assignee,
                due_date: $due_date,
                estimated_effort: $estimated_effort,
                completion_percentage: $completion_percentage,
                tags: $tags,
                related_tasks: $related_tasks,
                custom_fields: $custom_fields,
                created_at: datetime($created_at),
                updated_at: datetime($updated_at)
            })
            RETURN m
            """
            
            # Prepare parameters for the query
            params = {
                "id": metadata.id,
                "document_id": metadata.document_id,
                "task_id": metadata.task_id,
                "title": metadata.title,
                "description": metadata.description,
                "status": metadata.status,
                "priority": metadata.priority,
                "assignee": metadata.assignee,
                "due_date": metadata.due_date.isoformat() if metadata.due_date else None,
                "estimated_effort": metadata.estimated_effort,
                "completion_percentage": metadata.completion_percentage,
                "tags": metadata_dict["tags"],
                "related_tasks": metadata_dict["related_tasks"],
                "custom_fields": metadata_dict["custom_fields"],
                "created_at": metadata.created_at.isoformat(),
                "updated_at": metadata.updated_at.isoformat()
            }
            
            # Execute the query
            result = await self.client.execute_query_async(create_metadata_query, params)
            
            if not result:
                raise Exception("Failed to create task metadata")
            
            # Create relationship to document
            doc_metadata_rel_query = """
            MATCH (d:Document {id: $document_id}), (m:TaskMetadata {id: $metadata_id})
            CREATE (d)-[r:HAS_TASK_METADATA]->(m)
            RETURN r
            """
            
            doc_metadata_params = {
                "document_id": metadata.document_id,
                "metadata_id": metadata.id
            }
            
            await self.client.execute_query_async(doc_metadata_rel_query, doc_metadata_params)
            
            # Update document node to mark it as a task
            update_doc_query = """
            MATCH (d:Document {id: $document_id})
            SET d.is_task = true, d.status = $status
            RETURN d
            """
            
            update_doc_params = {
                "document_id": metadata.document_id,
                "status": metadata.status
            }
            
            await self.client.execute_query_async(update_doc_query, update_doc_params)
            
            return metadata.id
        except Exception as e:
            logger.error(f"Error saving task metadata: {str(e)}")
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
            # Get the metadata node
            query = """
            MATCH (d:Document {id: $document_id})-[:HAS_TASK_METADATA]->(m:TaskMetadata)
            RETURN m
            ORDER BY m.updated_at DESC
            LIMIT 1
            """
            
            result = await self.client.execute_query_async(query, {"document_id": document_id})
            
            if not result:
                return None
            
            metadata_node = result[0]['m']
            
            # Convert datetime strings to datetime objects
            created_at = metadata_node.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            updated_at = metadata_node.get('updated_at')
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
            due_date = metadata_node.get('due_date')
            if isinstance(due_date, str):
                due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            
            # Create the TaskMetadata object
            return TaskMetadata(
                id=metadata_node.get('id'),
                document_id=metadata_node.get('document_id'),
                task_id=metadata_node.get('task_id'),
                title=metadata_node.get('title'),
                description=metadata_node.get('description'),
                status=metadata_node.get('status', TaskStatus.TODO),
                priority=metadata_node.get('priority'),
                assignee=metadata_node.get('assignee'),
                due_date=due_date,
                estimated_effort=metadata_node.get('estimated_effort'),
                completion_percentage=metadata_node.get('completion_percentage'),
                tags=metadata_node.get('tags', []),
                related_tasks=metadata_node.get('related_tasks', []),
                custom_fields=metadata_node.get('custom_fields', {}),
                created_at=created_at,
                updated_at=updated_at
            )
        except Exception as e:
            logger.error(f"Error getting task metadata: {str(e)}")
            raise
    
    async def save_task_status_update(self, status_update: TaskStatusUpdate) -> str:
        """
        Save a task status update to the database.
        
        Args:
            status_update: The status update to save
            
        Returns:
            The ID of the saved status update
        """
        try:
            # Create the status update node
            create_update_query = """
            CREATE (u:TaskStatusUpdate {
                id: $id,
                document_id: $document_id,
                previous_status: $previous_status,
                new_status: $new_status,
                comment: $comment,
                created_by: $created_by,
                created_at: datetime($created_at)
            })
            RETURN u
            """
            
            # Prepare parameters for the query
            params = {
                "id": status_update.id,
                "document_id": status_update.document_id,
                "previous_status": status_update.previous_status,
                "new_status": status_update.new_status,
                "comment": status_update.comment,
                "created_by": status_update.created_by,
                "created_at": status_update.created_at.isoformat()
            }
            
            # Execute the query
            result = await self.client.execute_query_async(create_update_query, params)
            
            if not result:
                raise Exception("Failed to create task status update")
            
            # Create relationship to document
            doc_update_rel_query = """
            MATCH (d:Document {id: $document_id}), (u:TaskStatusUpdate {id: $update_id})
            CREATE (d)-[r:HAS_STATUS_UPDATE]->(u)
            RETURN r
            """
            
            doc_update_params = {
                "document_id": status_update.document_id,
                "update_id": status_update.id
            }
            
            await self.client.execute_query_async(doc_update_rel_query, doc_update_params)
            
            # Update document status
            update_doc_query = """
            MATCH (d:Document {id: $document_id})
            SET d.status = $new_status
            RETURN d
            """
            
            update_doc_params = {
                "document_id": status_update.document_id,
                "new_status": status_update.new_status
            }
            
            await self.client.execute_query_async(update_doc_query, update_doc_params)
            
            # Update task metadata status
            update_metadata_query = """
            MATCH (d:Document {id: $document_id})-[:HAS_TASK_METADATA]->(m:TaskMetadata)
            SET m.status = $new_status, m.updated_at = datetime($updated_at)
            RETURN m
            """
            
            update_metadata_params = {
                "document_id": status_update.document_id,
                "new_status": status_update.new_status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            await self.client.execute_query_async(update_metadata_query, update_metadata_params)
            
            return status_update.id
        except Exception as e:
            logger.error(f"Error saving task status update: {str(e)}")
            raise
    
    async def get_task_status_history(self, document_id: str) -> List[TaskStatusUpdate]:
        """
        Get the status history for a task.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            A list of status updates
        """
        try:
            # Get all status updates for the document
            query = """
            MATCH (d:Document {id: $document_id})-[:HAS_STATUS_UPDATE]->(u:TaskStatusUpdate)
            RETURN u
            ORDER BY u.created_at DESC
            """
            
            result = await self.client.execute_query_async(query, {"document_id": document_id})
            
            status_updates = []
            
            for record in result:
                update_node = record['u']
                
                created_at = update_node.get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                update = TaskStatusUpdate(
                    id=update_node.get('id'),
                    document_id=update_node.get('document_id'),
                    previous_status=update_node.get('previous_status'),
                    new_status=update_node.get('new_status'),
                    comment=update_node.get('comment'),
                    created_by=update_node.get('created_by'),
                    created_at=created_at
                )
                
                status_updates.append(update)
            
            return status_updates
        except Exception as e:
            logger.error(f"Error getting task status history: {str(e)}")
            raise
    
    async def save_task_relationship(self, relationship: TaskRelationship) -> str:
        """
        Save a task relationship to the database.
        
        Args:
            relationship: The relationship to save
            
        Returns:
            The ID of the saved relationship
        """
        try:
            # Create the relationship node
            create_rel_query = """
            CREATE (r:TaskRelationship {
                id: $id,
                source_document_id: $source_document_id,
                target_document_id: $target_document_id,
                relationship_type: $relationship_type,
                description: $description,
                is_valid: $is_valid,
                created_by: $created_by,
                created_at: datetime($created_at)
            })
            RETURN r
            """
            
            # Prepare parameters for the query
            params = {
                "id": relationship.id,
                "source_document_id": relationship.source_document_id,
                "target_document_id": relationship.target_document_id,
                "relationship_type": relationship.relationship_type,
                "description": relationship.description,
                "is_valid": relationship.is_valid,
                "created_by": relationship.created_by,
                "created_at": relationship.created_at.isoformat()
            }
            
            # Execute the query
            result = await self.client.execute_query_async(create_rel_query, params)
            
            if not result:
                raise Exception("Failed to create task relationship")
            
            # Create relationships between documents
            doc_rel_query = """
            MATCH (source:Document {id: $source_id}), (target:Document {id: $target_id})
            CREATE (source)-[r:TASK_RELATIONSHIP {
                type: $rel_type,
                relationship_id: $rel_id
            }]->(target)
            RETURN r
            """
            
            doc_rel_params = {
                "source_id": relationship.source_document_id,
                "target_id": relationship.target_document_id,
                "rel_type": relationship.relationship_type,
                "rel_id": relationship.id
            }
            
            await self.client.execute_query_async(doc_rel_query, doc_rel_params)
            
            # Update task metadata related_tasks
            update_source_metadata_query = """
            MATCH (d:Document {id: $document_id})-[:HAS_TASK_METADATA]->(m:TaskMetadata)
            SET m.related_tasks = CASE 
                WHEN NOT $target_id IN m.related_tasks THEN m.related_tasks + $target_id 
                ELSE m.related_tasks 
                END,
                m.updated_at = datetime($updated_at)
            RETURN m
            """
            
            update_source_params = {
                "document_id": relationship.source_document_id,
                "target_id": relationship.target_document_id,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            await self.client.execute_query_async(update_source_metadata_query, update_source_params)
            
            return relationship.id
        except Exception as e:
            logger.error(f"Error saving task relationship: {str(e)}")
            raise
    
    async def get_task_relationships(self, document_id: str) -> List[TaskRelationship]:
        """
        Get all relationships for a task.
        
        Args:
            document_id: The ID of the document
            
        Returns:
            A list of task relationships
        """
        try:
            # Get all relationships where this document is the source
            outgoing_query = """
            MATCH (source:Document {id: $document_id})-[r:TASK_RELATIONSHIP]->(target:Document)
            MATCH (rel:TaskRelationship {id: r.relationship_id})
            RETURN rel, target.id as target_id, target.name as target_name
            """
            
            outgoing_result = await self.client.execute_query_async(outgoing_query, {"document_id": document_id})
            
            # Get all relationships where this document is the target
            incoming_query = """
            MATCH (source:Document)-[r:TASK_RELATIONSHIP]->(target:Document {id: $document_id})
            MATCH (rel:TaskRelationship {id: r.relationship_id})
            RETURN rel, source.id as source_id, source.name as source_name
            """
            
            incoming_result = await self.client.execute_query_async(incoming_query, {"document_id": document_id})
            
            relationships = []
            
            # Process outgoing relationships
            for record in outgoing_result:
                rel_node = record['rel']
                
                created_at = rel_node.get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                relationship = TaskRelationship(
                    id=rel_node.get('id'),
                    source_document_id=rel_node.get('source_document_id'),
                    target_document_id=rel_node.get('target_document_id'),
                    relationship_type=rel_node.get('relationship_type'),
                    description=rel_node.get('description'),
                    is_valid=rel_node.get('is_valid', True),
                    created_by=rel_node.get('created_by'),
                    created_at=created_at
                )
                
                relationships.append(relationship)
            
            # Process incoming relationships
            for record in incoming_result:
                rel_node = record['rel']
                
                created_at = rel_node.get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                relationship = TaskRelationship(
                    id=rel_node.get('id'),
                    source_document_id=rel_node.get('source_document_id'),
                    target_document_id=rel_node.get('target_document_id'),
                    relationship_type=rel_node.get('relationship_type'),
                    description=rel_node.get('description'),
                    is_valid=rel_node.get('is_valid', True),
                    created_by=rel_node.get('created_by'),
                    created_at=created_at
                )
                
                relationships.append(relationship)
            
            return relationships
        except Exception as e:
            logger.error(f"Error getting task relationships: {str(e)}")
            raise
    
    async def detect_task_documents(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Detect documents that follow the task naming convention.
        
        Args:
            project_id: Optional project ID to filter by
            
        Returns:
            A list of detected task documents
        """
        try:
            # Define the task naming pattern
            task_pattern = r'^TASK_\d+_.*$'
            
            # Query to find documents matching the pattern
            if project_id:
                query = """
                MATCH (d:Document)
                WHERE d.project_id = $project_id AND d.name =~ $task_pattern
                RETURN d
                ORDER BY d.name
                """
                params = {"project_id": project_id, "task_pattern": task_pattern}
            else:
                query = """
                MATCH (d:Document)
                WHERE d.name =~ $task_pattern
                RETURN d
                ORDER BY d.name
                """
                params = {"task_pattern": task_pattern}
            
            result = await self.client.execute_query_async(query, params)
            
            task_documents = []
            
            for record in result:
                doc_node = record['d']
                
                # Extract task ID from name
                name = doc_node.get('name', '')
                task_id_match = re.match(r'^(TASK_\d+)_.*$', name)
                task_id = task_id_match.group(1) if task_id_match else None
                
                created_at = doc_node.get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                updated_at = doc_node.get('updated_at')
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                
                task_doc = {
                    "id": doc_node.get('id'),
                    "name": name,
                    "task_id": task_id,
                    "project_id": doc_node.get('project_id'),
                    "folder_id": doc_node.get('folder_id'),
                    "status": doc_node.get('status'),
                    "is_task": doc_node.get('is_task', False),
                    "created_by": doc_node.get('created_by'),
                    "created_at": created_at,
                    "updated_at": updated_at
                }
                
                task_documents.append(task_doc)
            
            return task_documents
        except Exception as e:
            logger.error(f"Error detecting task documents: {str(e)}")
            raise
    
    async def get_tasks_by_filter(self, filter_criteria: Dict[str, Any], page: int = 1, per_page: int = 20) -> Tuple[List[TaskSummary], int]:
        """
        Get tasks based on filter criteria.
        
        Args:
            filter_criteria: Filter criteria
            page: Page number
            per_page: Number of items per page
            
        Returns:
            A tuple containing a list of task summaries and the total count
        """
        try:
            # Build the query based on filter criteria
            query_parts = ["MATCH (d:Document)-[:HAS_TASK_METADATA]->(m:TaskMetadata)"]
            where_clauses = []
            params = {}
            
            # Add filter conditions
            if filter_criteria.get('status'):
                where_clauses.append("m.status IN $status")
                params['status'] = filter_criteria['status']
            
            if filter_criteria.get('priority'):
                where_clauses.append("m.priority IN $priority")
                params['priority'] = filter_criteria['priority']
            
            if filter_criteria.get('assignee'):
                where_clauses.append("m.assignee IN $assignee")
                params['assignee'] = filter_criteria['assignee']
            
            if filter_criteria.get('due_date_before'):
                where_clauses.append("m.due_date <= datetime($due_date_before)")
                params['due_date_before'] = filter_criteria['due_date_before'].isoformat()
            
            if filter_criteria.get('due_date_after'):
                where_clauses.append("m.due_date >= datetime($due_date_after)")
                params['due_date_after'] = filter_criteria['due_date_after'].isoformat()
            
            if filter_criteria.get('tags'):
                where_clauses.append("ANY(tag IN $tags WHERE tag IN m.tags)")
                params['tags'] = filter_criteria['tags']
            
            if filter_criteria.get('search_query'):
                where_clauses.append("(m.title CONTAINS $search_query OR m.description CONTAINS $search_query)")
                params['search_query'] = filter_criteria['search_query']
            
            if filter_criteria.get('project_id'):
                where_clauses.append("d.project_id = $project_id")
                params['project_id'] = filter_criteria['project_id']
            
            if filter_criteria.get('folder_id'):
                where_clauses.append("d.folder_id = $folder_id")
                params['folder_id'] = filter_criteria['folder_id']
            
            # Add WHERE clause if there are any conditions
            if where_clauses:
                query_parts.append("WHERE " + " AND ".join(where_clauses))
            
            # Add return and pagination
            query_parts.append("RETURN d, m")
            query_parts.append("ORDER BY m.updated_at DESC")
            query_parts.append(f"SKIP {(page - 1) * per_page} LIMIT {per_page}")
            
            # Execute the query
            query = " ".join(query_parts)
            result = await self.client.execute_query_async(query, params)
            
            # Get total count
            count_query_parts = query_parts.copy()
            count_query_parts[-3] = "RETURN COUNT(d) as total"
            count_query_parts.pop()  # Remove LIMIT
            count_query_parts.pop()  # Remove SKIP
            
            count_query = " ".join(count_query_parts)
            count_result = await self.client.execute_query_async(count_query, params)
            
            total_count = count_result[0]['total'] if count_result else 0
            
            # Process results
            task_summaries = []
            
            for record in result:
                doc_node = record['d']
                metadata_node = record['m']
                
                updated_at = metadata_node.get('updated_at')
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                
                due_date = metadata_node.get('due_date')
                if isinstance(due_date, str):
                    due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                
                summary = TaskSummary(
                    document_id=doc_node.get('id'),
                    task_id=metadata_node.get('task_id'),
                    title=metadata_node.get('title'),
                    status=metadata_node.get('status', TaskStatus.TODO),
                    priority=metadata_node.get('priority'),
                    assignee=metadata_node.get('assignee'),
                    due_date=due_date,
                    completion_percentage=metadata_node.get('completion_percentage'),
                    updated_at=updated_at
                )
                
                task_summaries.append(summary)
            
            return task_summaries, total_count
        except Exception as e:
            logger.error(f"Error getting tasks by filter: {str(e)}")
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
            # Base query
            if project_id:
                base_query = """
                MATCH (d:Document)-[:HAS_TASK_METADATA]->(m:TaskMetadata)
                WHERE d.project_id = $project_id
                """
                params = {"project_id": project_id}
            else:
                base_query = """
                MATCH (d:Document)-[:HAS_TASK_METADATA]->(m:TaskMetadata)
                """
                params = {}
            
            # Get total count
            count_query = base_query + "RETURN COUNT(d) as total"
            count_result = await self.client.execute_query_async(count_query, params)
            total_tasks = count_result[0]['total'] if count_result else 0
            
            # Get counts by status
            status_query = base_query + """
            RETURN m.status as status, COUNT(m) as count
            """
            status_result = await self.client.execute_query_async(status_query, params)
            
            by_status = {}
            for record in status_result:
                status = record['status']
                count = record['count']
                by_status[status] = count
            
            # Get counts by priority
            priority_query = base_query + """
            WHERE m.priority IS NOT NULL
            RETURN m.priority as priority, COUNT(m) as count
            """
            priority_result = await self.client.execute_query_async(priority_query, params)
            
            by_priority = {}
            for record in priority_result:
                priority = record['priority']
                count = record['count']
                by_priority[priority] = count
            
            # Get counts by assignee
            assignee_query = base_query + """
            WHERE m.assignee IS NOT NULL
            RETURN m.assignee as assignee, COUNT(m) as count
            """
            assignee_result = await self.client.execute_query_async(assignee_query, params)
            
            by_assignee = {}
            for record in assignee_result:
                assignee = record['assignee']
                count = record['count']
                by_assignee[assignee] = count
            
            # Get overdue tasks
            now = datetime.utcnow()
            overdue_query = base_query + """
            WHERE m.due_date < datetime($now) AND m.status <> 'done'
            RETURN COUNT(m) as count
            """
            overdue_params = params.copy()
            overdue_params['now'] = now.isoformat()
            
            overdue_result = await self.client.execute_query_async(overdue_query, overdue_params)
            overdue_tasks = overdue_result[0]['count'] if overdue_result else 0
            
            # Get tasks completed in the last week
            week_ago = now - timedelta(days=7)
            completed_query = base_query + """
            MATCH (d)-[:HAS_STATUS_UPDATE]->(u:TaskStatusUpdate)
            WHERE u.new_status = 'done' AND u.created_at >= datetime($week_ago)
            RETURN COUNT(DISTINCT d) as count
            """
            completed_params = params.copy()
            completed_params['week_ago'] = week_ago.isoformat()
            
            completed_result = await self.client.execute_query_async(completed_query, completed_params)
            completed_tasks = completed_result[0]['count'] if completed_result else 0
            
            # Get tasks created in the last week
            created_query = base_query + """
            WHERE m.created_at >= datetime($week_ago)
            RETURN COUNT(m) as count
            """
            created_params = params.copy()
            created_params['week_ago'] = week_ago.isoformat()
            
            created_result = await self.client.execute_query_async(created_query, created_params)
            created_tasks = created_result[0]['count'] if created_result else 0
            
            # Get average completion time
            avg_time_query = base_query + """
            MATCH (d)-[:HAS_STATUS_UPDATE]->(start:TaskStatusUpdate)
            MATCH (d)-[:HAS_STATUS_UPDATE]->(end:TaskStatusUpdate)
            WHERE start.new_status = 'in_progress' AND end.new_status = 'done'
            AND start.created_at < end.created_at
            WITH d, MIN(start.created_at) as start_time, MIN(end.created_at) as end_time
            RETURN AVG(duration.between(start_time, end_time).days) as avg_days
            """
            
            avg_time_result = await self.client.execute_query_async(avg_time_query, params)
            avg_completion_time = avg_time_result[0]['avg_days'] if avg_time_result and avg_time_result[0]['avg_days'] is not None else None
            
            # Create statistics object
            return TaskStatistics(
                total_tasks=total_tasks,
                by_status=by_status,
                by_priority=by_priority,
                by_assignee=by_assignee,
                overdue_tasks=overdue_tasks,
                completed_tasks_last_week=completed_tasks,
                created_tasks_last_week=created_tasks,
                average_completion_time_days=avg_completion_time
            )
        except Exception as e:
            logger.error(f"Error getting task statistics: {str(e)}")
            raise