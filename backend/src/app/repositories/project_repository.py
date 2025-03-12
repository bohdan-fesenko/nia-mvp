"""
Project repository implementation.
This module provides the repository implementation for Project entities.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..db.models import Project
from .neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)

class ProjectRepository(Neo4jRepository[Project]):
    """Repository for Project entities."""
    
    @property
    def label(self) -> str:
        """
        Get the Neo4j label for this repository.
        
        Returns:
            The Neo4j label
        """
        return "Project"
    
    def map_to_entity(self, record: Dict[str, Any]) -> Project:
        """
        Map a Neo4j record to a Project entity.
        
        Args:
            record: Neo4j record
            
        Returns:
            The mapped Project entity
        """
        created_at = record.get('created_at')
        updated_at = record.get('updated_at')
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
        return Project(
            id=record.get('id'),
            name=record.get('name'),
            description=record.get('description'),
            is_archived=record.get('is_archived', False),
            created_at=created_at,
            updated_at=updated_at
        )
    
    def map_to_db(self, entity: Union[Dict[str, Any], Project]) -> Dict[str, Any]:
        """
        Map a Project entity to a Neo4j record.
        
        Args:
            entity: Project entity or dictionary
            
        Returns:
            The mapped Neo4j record
        """
        if isinstance(entity, Project):
            # Convert Project object to dictionary
            return {
                'id': entity.id,
                'name': entity.name,
                'description': entity.description,
                'is_archived': entity.is_archived,
                'created_at': entity.created_at.isoformat() if entity.created_at else None,
                'updated_at': entity.updated_at.isoformat() if entity.updated_at else None
            }
        
        # Entity is already a dictionary
        return entity
    
    async def get_projects_by_user(self, user_id: str, include_archived: bool = False) -> List[Project]:
        """
        Get all projects owned by a user.
        
        Args:
            user_id: User ID
            include_archived: Whether to include archived projects
            
        Returns:
            List of projects
        """
        where_clause = "WHERE (u)-[:OWNS]->(p)"
        if not include_archived:
            where_clause += " AND p.is_archived = false"
            
        query = f"""
        MATCH (u:User {{id: $user_id}}), (p:Project)
        {where_clause}
        RETURN p
        ORDER BY p.updated_at DESC
        """
        
        try:
            result = await self.client.execute_query_async(query, {"user_id": user_id})
            return [self.map_to_entity(record['p']) for record in result]
        except Exception as e:
            logger.error(f"Error getting projects by user: {str(e)}")
            raise
    
    async def add_user_to_project(self, project_id: str, user_id: str, role: str = "member") -> bool:
        """
        Add a user to a project with a specific role.
        
        Args:
            project_id: Project ID
            user_id: User ID
            role: User's role in the project
            
        Returns:
            True if user was added, False otherwise
        """
        query = """
        MATCH (u:User {id: $user_id}), (p:Project {id: $project_id})
        MERGE (u)-[r:OWNS]->(p)
        ON CREATE SET r.role = $role, r.created_at = datetime()
        RETURN r
        """
        
        try:
            result = await self.client.execute_query_async(
                query, 
                {"project_id": project_id, "user_id": user_id, "role": role}
            )
            return len(result) > 0
        except Exception as e:
            logger.error(f"Error adding user to project: {str(e)}")
            raise
    
    async def remove_user_from_project(self, project_id: str, user_id: str) -> bool:
        """
        Remove a user from a project.
        
        Args:
            project_id: Project ID
            user_id: User ID
            
        Returns:
            True if user was removed, False otherwise
        """
        query = """
        MATCH (u:User {id: $user_id})-[r:OWNS]->(p:Project {id: $project_id})
        DELETE r
        RETURN count(r) as deleted
        """
        
        try:
            result = await self.client.execute_query_async(
                query, 
                {"project_id": project_id, "user_id": user_id}
            )
            return result[0]['deleted'] > 0
        except Exception as e:
            logger.error(f"Error removing user from project: {str(e)}")
            raise
    
    async def get_project_users(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all users associated with a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of users with their roles
        """
        query = """
        MATCH (u:User)-[r:OWNS]->(p:Project {id: $project_id})
        RETURN u, r.role as role
        """
        
        try:
            result = await self.client.execute_query_async(query, {"project_id": project_id})
            return [
                {
                    "user": {
                        "id": record['u']['id'],
                        "name": record['u']['name'],
                        "email": record['u']['email'],
                        "image": record['u'].get('image')
                    },
                    "role": record['role']
                }
                for record in result
            ]
        except Exception as e:
            logger.error(f"Error getting project users: {str(e)}")
            raise
    
    async def update_user_role(self, project_id: str, user_id: str, role: str) -> bool:
        """
        Update a user's role in a project.
        
        Args:
            project_id: Project ID
            user_id: User ID
            role: New role
            
        Returns:
            True if role was updated, False otherwise
        """
        query = """
        MATCH (u:User {id: $user_id})-[r:OWNS]->(p:Project {id: $project_id})
        SET r.role = $role
        RETURN r
        """
        
        try:
            result = await self.client.execute_query_async(
                query, 
                {"project_id": project_id, "user_id": user_id, "role": role}
            )
            return len(result) > 0
        except Exception as e:
            logger.error(f"Error updating user role: {str(e)}")
            raise
    
    async def archive_project(self, project_id: str) -> Optional[Project]:
        """
        Archive a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            The archived project if found, None otherwise
        """
        return await self.update(project_id, {"is_archived": True})
    
    async def unarchive_project(self, project_id: str) -> Optional[Project]:
        """
        Unarchive a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            The unarchived project if found, None otherwise
        """
        return await self.update(project_id, {"is_archived": False})