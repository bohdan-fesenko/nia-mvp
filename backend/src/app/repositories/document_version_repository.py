"""
DocumentVersion repository implementation.
This module provides the repository implementation for DocumentVersion entities.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..db.models import DocumentVersion
from .neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)

class DocumentVersionRepository(Neo4jRepository[DocumentVersion]):
    """Repository for DocumentVersion entities."""
    
    @property
    def label(self) -> str:
        """
        Get the Neo4j label for this repository.
        
        Returns:
            The Neo4j label
        """
        return "DocumentVersion"
    
    def map_to_entity(self, record: Dict[str, Any]) -> DocumentVersion:
        """
        Map a Neo4j record to a DocumentVersion entity.
        
        Args:
            record: Neo4j record
            
        Returns:
            The mapped DocumentVersion entity
        """
        created_at = record.get('created_at')
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
        return DocumentVersion(
            id=record.get('id'),
            document_id=record.get('document_id'),
            version_number=record.get('version_number'),
            content=record.get('content'),
            created_by=record.get('created_by'),
            change_summary=record.get('change_summary'),
            created_at=created_at
        )
    
    def map_to_db(self, entity: Union[Dict[str, Any], DocumentVersion]) -> Dict[str, Any]:
        """
        Map a DocumentVersion entity to a Neo4j record.
        
        Args:
            entity: DocumentVersion entity or dictionary
            
        Returns:
            The mapped Neo4j record
        """
        if isinstance(entity, DocumentVersion):
            # Convert DocumentVersion object to dictionary
            return {
                'id': entity.id,
                'document_id': entity.document_id,
                'version_number': entity.version_number,
                'content': entity.content,
                'created_by': entity.created_by,
                'change_summary': entity.change_summary,
                'created_at': entity.created_at.isoformat() if entity.created_at else None
            }
        
        # Entity is already a dictionary
        return entity
    
    async def get_versions_by_document(self, document_id: str) -> List[DocumentVersion]:
        """
        Get all versions of a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of document versions
        """
        query = """
        MATCH (d:Document {id: $document_id})-[:HAS_VERSION]->(v:DocumentVersion)
        RETURN v
        ORDER BY v.version_number DESC
        """
        
        try:
            result = await self.client.execute_query_async(query, {"document_id": document_id})
            return [self.map_to_entity(record['v']) for record in result]
        except Exception as e:
            logger.error(f"Error getting versions by document: {str(e)}")
            raise
    
    async def get_latest_version(self, document_id: str) -> Optional[DocumentVersion]:
        """
        Get the latest version of a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            The latest document version if found, None otherwise
        """
        query = """
        MATCH (d:Document {id: $document_id})-[:HAS_LATEST_VERSION]->(v:DocumentVersion)
        RETURN v
        """
        
        try:
            result = await self.client.execute_query_async(query, {"document_id": document_id})
            if not result:
                return None
            
            return self.map_to_entity(result[0]['v'])
        except Exception as e:
            logger.error(f"Error getting latest version: {str(e)}")
            raise
    
    async def get_version_by_number(self, document_id: str, version_number: int) -> Optional[DocumentVersion]:
        """
        Get a specific version of a document by version number.
        
        Args:
            document_id: Document ID
            version_number: Version number
            
        Returns:
            The document version if found, None otherwise
        """
        query = """
        MATCH (d:Document {id: $document_id})-[:HAS_VERSION]->(v:DocumentVersion)
        WHERE v.version_number = $version_number
        RETURN v
        """
        
        try:
            result = await self.client.execute_query_async(
                query, 
                {"document_id": document_id, "version_number": version_number}
            )
            if not result:
                return None
            
            return self.map_to_entity(result[0]['v'])
        except Exception as e:
            logger.error(f"Error getting version by number: {str(e)}")
            raise
    
    async def compare_versions(self, document_id: str, version1: int, version2: int) -> Dict[str, Any]:
        """
        Compare two versions of a document.
        
        Args:
            document_id: Document ID
            version1: First version number
            version2: Second version number
            
        Returns:
            Dictionary with comparison results
        """
        # Get both versions
        v1 = await self.get_version_by_number(document_id, version1)
        v2 = await self.get_version_by_number(document_id, version2)
        
        if not v1 or not v2:
            raise ValueError("One or both versions not found")
        
        # For now, return a simple comparison
        # In a real implementation, you would use a diff algorithm
        return {
            "version1": {
                "number": v1.version_number,
                "content": v1.content,
                "created_at": v1.created_at,
                "created_by": v1.created_by,
                "change_summary": v1.change_summary
            },
            "version2": {
                "number": v2.version_number,
                "content": v2.content,
                "created_at": v2.created_at,
                "created_by": v2.created_by,
                "change_summary": v2.change_summary
            },
            # Simple character count comparison
            "diff_stats": {
                "added": len(v2.content) - len(v1.content) if len(v2.content) > len(v1.content) else 0,
                "removed": len(v1.content) - len(v2.content) if len(v1.content) > len(v2.content) else 0,
                "total_diff": abs(len(v2.content) - len(v1.content))
            }
        }
    
    async def set_as_latest_version(self, document_id: str, version_id: str) -> bool:
        """
        Set a specific version as the latest version of a document.
        
        Args:
            document_id: Document ID
            version_id: Version ID to set as latest
            
        Returns:
            True if successful, False otherwise
        """
        # Remove existing HAS_LATEST_VERSION relationship
        remove_rel_query = """
        MATCH (d:Document {id: $document_id})-[r:HAS_LATEST_VERSION]->(:DocumentVersion)
        DELETE r
        """
        
        # Create new HAS_LATEST_VERSION relationship
        create_rel_query = """
        MATCH (d:Document {id: $document_id}), (v:DocumentVersion {id: $version_id})
        MERGE (d)-[r:HAS_LATEST_VERSION]->(v)
        RETURN r
        """
        
        try:
            # Execute queries in transaction
            await self.client.execute_query_async(remove_rel_query, {"document_id": document_id})
            result = await self.client.execute_query_async(
                create_rel_query, 
                {"document_id": document_id, "version_id": version_id}
            )
            
            return len(result) > 0
        except Exception as e:
            logger.error(f"Error setting latest version: {str(e)}")
            raise
    
    async def get_version_with_creator(self, version_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document version with creator information.
        
        Args:
            version_id: Version ID
            
        Returns:
            Dictionary with version and creator information if found, None otherwise
        """
        query = """
        MATCH (v:DocumentVersion {id: $version_id})
        OPTIONAL MATCH (u:User)-[:CREATES]->(v)
        RETURN v, u
        """
        
        try:
            result = await self.client.execute_query_async(query, {"version_id": version_id})
            if not result:
                return None
            
            version = self.map_to_entity(result[0]['v'])
            user = result[0]['u'] if 'u' in result[0] else None
            
            version_dict = version.__dict__
            if user:
                version_dict['creator'] = {
                    "id": user.get('id'),
                    "name": user.get('name'),
                    "email": user.get('email'),
                    "image": user.get('image')
                }
            
            return version_dict
        except Exception as e:
            logger.error(f"Error getting version with creator: {str(e)}")
            raise