"""
Folder repository implementation.
This module provides the repository implementation for Folder entities.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..db.models import Folder
from .neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)

class FolderRepository(Neo4jRepository[Folder]):
    """Repository for Folder entities."""
    
    @property
    def label(self) -> str:
        """
        Get the Neo4j label for this repository.
        
        Returns:
            The Neo4j label
        """
        return "Folder"
    
    def map_to_entity(self, record: Dict[str, Any]) -> Folder:
        """
        Map a Neo4j record to a Folder entity.
        
        Args:
            record: Neo4j record
            
        Returns:
            The mapped Folder entity
        """
        created_at = record.get('created_at')
        updated_at = record.get('updated_at')
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
        return Folder(
            id=record.get('id'),
            name=record.get('name'),
            path=record.get('path'),
            project_id=record.get('project_id'),
            parent_folder_id=record.get('parent_folder_id'),
            created_at=created_at,
            updated_at=updated_at
        )
    
    def map_to_db(self, entity: Union[Dict[str, Any], Folder]) -> Dict[str, Any]:
        """
        Map a Folder entity to a Neo4j record.
        
        Args:
            entity: Folder entity or dictionary
            
        Returns:
            The mapped Neo4j record
        """
        if isinstance(entity, Folder):
            # Convert Folder object to dictionary
            return {
                'id': entity.id,
                'name': entity.name,
                'path': entity.path,
                'project_id': entity.project_id,
                'parent_folder_id': entity.parent_folder_id,
                'created_at': entity.created_at.isoformat() if entity.created_at else None,
                'updated_at': entity.updated_at.isoformat() if entity.updated_at else None
            }
        
        # Entity is already a dictionary
        return entity
    
    async def create_folder(self, data: Dict[str, Any]) -> Folder:
        """
        Create a new folder and establish relationships.
        
        Args:
            data: Dictionary containing folder data
            
        Returns:
            The created folder
        """
        # Generate path if not provided
        if 'path' not in data:
            if data.get('parent_folder_id'):
                # Get parent folder path
                parent_folder = await self.get_by_id(data['parent_folder_id'])
                if parent_folder:
                    data['path'] = f"{parent_folder.path}/{data['name']}"
                else:
                    data['path'] = f"/{data['name']}"
            else:
                data['path'] = f"/{data['name']}"
        
        # Create folder node
        folder = await self.create(data)
        
        # Create relationships
        queries = []
        
        # Relationship to project
        if data.get('project_id'):
            queries.append((
                """
                MATCH (f:Folder {id: $folder_id}), (p:Project {id: $project_id})
                MERGE (p)-[r:CONTAINS]->(f)
                RETURN r
                """,
                {"folder_id": folder.id, "project_id": data['project_id']}
            ))
        
        # Relationship to parent folder
        if data.get('parent_folder_id'):
            queries.append((
                """
                MATCH (f:Folder {id: $folder_id}), (pf:Folder {id: $parent_folder_id})
                MERGE (pf)-[r:CONTAINS]->(f)
                RETURN r
                """,
                {"folder_id": folder.id, "parent_folder_id": data['parent_folder_id']}
            ))
        
        # Execute relationship queries
        if queries:
            await self.execute_transaction(queries)
        
        return folder
    
    async def get_folders_by_project(self, project_id: str) -> List[Folder]:
        """
        Get all folders in a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of folders
        """
        query = """
        MATCH (p:Project {id: $project_id})-[:CONTAINS*]->(f:Folder)
        RETURN f
        ORDER BY f.path
        """
        
        try:
            result = await self.client.execute_query_async(query, {"project_id": project_id})
            return [self.map_to_entity(record['f']) for record in result]
        except Exception as e:
            logger.error(f"Error getting folders by project: {str(e)}")
            raise
    
    async def get_folders_by_parent(self, parent_folder_id: str) -> List[Folder]:
        """
        Get all folders within a parent folder.
        
        Args:
            parent_folder_id: Parent folder ID
            
        Returns:
            List of folders
        """
        query = """
        MATCH (pf:Folder {id: $parent_folder_id})-[:CONTAINS]->(f:Folder)
        RETURN f
        ORDER BY f.name
        """
        
        try:
            result = await self.client.execute_query_async(query, {"parent_folder_id": parent_folder_id})
            return [self.map_to_entity(record['f']) for record in result]
        except Exception as e:
            logger.error(f"Error getting folders by parent: {str(e)}")
            raise
    
    async def get_root_folders(self, project_id: str) -> List[Folder]:
        """
        Get all root folders in a project (folders without a parent folder).
        
        Args:
            project_id: Project ID
            
        Returns:
            List of root folders
        """
        query = """
        MATCH (p:Project {id: $project_id})-[:CONTAINS]->(f:Folder)
        WHERE NOT EXISTS { MATCH (pf:Folder)-[:CONTAINS]->(f) }
        RETURN f
        ORDER BY f.name
        """
        
        try:
            result = await self.client.execute_query_async(query, {"project_id": project_id})
            return [self.map_to_entity(record['f']) for record in result]
        except Exception as e:
            logger.error(f"Error getting root folders: {str(e)}")
            raise
    
    async def move_folder(self, folder_id: str, new_parent_id: Optional[str] = None) -> Optional[Folder]:
        """
        Move a folder to a new parent folder or to the root level.
        
        Args:
            folder_id: Folder ID
            new_parent_id: New parent folder ID, or None to move to root
            
        Returns:
            The updated folder if found, None otherwise
        """
        folder = await self.get_by_id(folder_id)
        if not folder:
            return None
        
        # Get project ID
        project_id = folder.project_id
        
        # Remove existing CONTAINS relationship
        remove_rel_query = """
        MATCH (f:Folder {id: $folder_id})
        OPTIONAL MATCH (parent)-[r:CONTAINS]->(f)
        WHERE parent:Folder OR parent:Project
        DELETE r
        """
        
        # Create new CONTAINS relationship
        if new_parent_id:
            # Get new parent folder
            new_parent = await self.get_by_id(new_parent_id)
            if not new_parent:
                return None
            
            # Update path
            new_path = f"{new_parent.path}/{folder.name}"
            
            # Create relationship to new parent folder
            create_rel_query = """
            MATCH (f:Folder {id: $folder_id}), (pf:Folder {id: $new_parent_id})
            MERGE (pf)-[r:CONTAINS]->(f)
            """
            
            params = {
                "folder_id": folder_id,
                "new_parent_id": new_parent_id
            }
        else:
            # Update path
            new_path = f"/{folder.name}"
            
            # Create relationship to project
            create_rel_query = """
            MATCH (f:Folder {id: $folder_id}), (p:Project {id: $project_id})
            MERGE (p)-[r:CONTAINS]->(f)
            """
            
            params = {
                "folder_id": folder_id,
                "project_id": project_id
            }
        
        # Update folder path and parent_folder_id
        update_data = {
            "path": new_path,
            "parent_folder_id": new_parent_id
        }
        
        # Execute queries in transaction
        try:
            # Remove old relationship
            await self.client.execute_query_async(remove_rel_query, {"folder_id": folder_id})
            
            # Create new relationship
            await self.client.execute_query_async(create_rel_query, params)
            
            # Update folder
            updated_folder = await self.update(folder_id, update_data)
            
            # Update paths of all child folders
            await self._update_child_paths(folder_id, new_path)
            
            return updated_folder
        except Exception as e:
            logger.error(f"Error moving folder: {str(e)}")
            raise
    
    async def _update_child_paths(self, folder_id: str, new_parent_path: str) -> None:
        """
        Recursively update paths of all child folders.
        
        Args:
            folder_id: Folder ID
            new_parent_path: New parent path
        """
        # Get all child folders
        query = """
        MATCH (pf:Folder {id: $folder_id})-[:CONTAINS*]->(f:Folder)
        RETURN f, pf
        """
        
        try:
            result = await self.client.execute_query_async(query, {"folder_id": folder_id})
            
            # Update each child folder's path
            for record in result:
                child = self.map_to_entity(record['f'])
                parent = self.map_to_entity(record['pf'])
                
                # Calculate new path
                relative_path = child.path.replace(parent.path, "", 1)
                new_path = f"{new_parent_path}{relative_path}"
                
                # Update path
                await self.update(child.id, {"path": new_path})
        except Exception as e:
            logger.error(f"Error updating child paths: {str(e)}")
            raise
    
    async def delete_with_contents(self, folder_id: str) -> bool:
        """
        Delete a folder and all its contents (subfolders and documents).
        
        Args:
            folder_id: Folder ID
            
        Returns:
            True if folder was deleted, False otherwise
        """
        # Delete all documents in the folder and its subfolders
        delete_docs_query = """
        MATCH (f:Folder {id: $folder_id})-[:CONTAINS*]->(d:Document)
        DETACH DELETE d
        """
        
        # Delete all subfolders
        delete_subfolders_query = """
        MATCH (f:Folder {id: $folder_id})-[:CONTAINS*]->(sf:Folder)
        DETACH DELETE sf
        """
        
        # Delete the folder itself
        delete_folder_query = """
        MATCH (f:Folder {id: $folder_id})
        DETACH DELETE f
        RETURN count(f) as deleted
        """
        
        try:
            # Execute queries in transaction
            await self.client.execute_query_async(delete_docs_query, {"folder_id": folder_id})
            await self.client.execute_query_async(delete_subfolders_query, {"folder_id": folder_id})
            result = await self.client.execute_query_async(delete_folder_query, {"folder_id": folder_id})
            
            return result[0]['deleted'] > 0
        except Exception as e:
            logger.error(f"Error deleting folder with contents: {str(e)}")
            raise
    
    async def get_folder_hierarchy(self, project_id: str) -> Dict[str, Any]:
        """
        Get the complete folder hierarchy for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dictionary representing the folder hierarchy
        """
        query = """
        MATCH (p:Project {id: $project_id})-[:CONTAINS*]->(f:Folder)
        OPTIONAL MATCH (f)-[:CONTAINS]->(d:Document)
        RETURN f, collect(d) as documents
        ORDER BY f.path
        """
        
        try:
            result = await self.client.execute_query_async(query, {"project_id": project_id})
            
            # Build hierarchy
            hierarchy = {
                "id": project_id,
                "type": "project",
                "children": {}
            }
            
            # Process folders
            for record in result:
                folder = self.map_to_entity(record['f'])
                documents = record['documents']
                
                # Split path into components
                path_components = folder.path.strip('/').split('/')
                
                # Navigate to the correct position in the hierarchy
                current = hierarchy
                for i, component in enumerate(path_components[:-1]):
                    if component not in current["children"]:
                        # This should not happen with a properly maintained path structure
                        logger.warning(f"Unexpected path component: {component}")
                        continue
                    current = current["children"][component]
                
                # Add this folder
                folder_name = path_components[-1] if path_components else folder.name
                current["children"][folder_name] = {
                    "id": folder.id,
                    "type": "folder",
                    "name": folder.name,
                    "children": {},
                    "documents": [doc for doc in documents if doc]
                }
            
            return hierarchy
        except Exception as e:
            logger.error(f"Error getting folder hierarchy: {str(e)}")
            raise