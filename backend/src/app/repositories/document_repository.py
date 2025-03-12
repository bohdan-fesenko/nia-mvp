"""
Document repository implementation.
This module provides the repository implementation for Document entities.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Tuple

from ..db.models import Document, DocumentVersion
from .neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)

class DocumentRepository(Neo4jRepository[Document]):
    """Repository for Document entities."""
    
    @property
    def label(self) -> str:
        """
        Get the Neo4j label for this repository.
        
        Returns:
            The Neo4j label
        """
        return "Document"
    
    def map_to_entity(self, record: Dict[str, Any]) -> Document:
        """
        Map a Neo4j record to a Document entity.
        
        Args:
            record: Neo4j record
            
        Returns:
            The mapped Document entity
        """
        created_at = record.get('created_at')
        updated_at = record.get('updated_at')
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
        return Document(
            id=record.get('id'),
            name=record.get('name'),  # Use name instead of title
            type=record.get('type'),
            is_task=record.get('is_task', False),
            status=record.get('status'),
            is_pinned=record.get('is_pinned', False),
            project_id=record.get('project_id'),
            folder_id=record.get('folder_id'),
            created_by=record.get('created_by'),
            created_at=created_at,
            updated_at=updated_at,
            owner_id=record.get('owner_id') or record.get('created_by')  # Use created_by as fallback
        )
    
    def map_to_db(self, entity: Union[Dict[str, Any], Document]) -> Dict[str, Any]:
        """
        Map a Document entity to a Neo4j record.
        
        Args:
            entity: Document entity or dictionary
            
        Returns:
            The mapped Neo4j record
        """
        if isinstance(entity, Document):
            # Convert Document object to dictionary
            return {
                'id': entity.id,
                'name': entity.name,  # Use name instead of title
                'type': entity.type,
                'is_task': entity.is_task,
                'status': entity.status,
                'is_pinned': entity.is_pinned,
                'project_id': entity.project_id,
                'folder_id': entity.folder_id,
                'created_by': entity.created_by,
                'created_at': entity.created_at.isoformat() if entity.created_at else None,
                'updated_at': entity.updated_at.isoformat() if entity.updated_at else None,
                'owner_id': entity.owner_id
            }
        
        # Entity is already a dictionary
        return entity
    
    async def create_document(self, data: Dict[str, Any], content: str = "") -> Tuple[Document, DocumentVersion]:
        """
        Create a new document with initial version and establish relationships.
        
        Args:
            data: Dictionary containing document data
            content: Initial document content
            
        Returns:
            Tuple of (document, document_version)
        """
        # Create document node
        document = await self.create(data)
        
        # Create relationships
        queries = []
        
        # Relationship to project
        if data.get('project_id'):
            queries.append((
                """
                MATCH (d:Document {id: $document_id}), (p:Project {id: $project_id})
                MERGE (p)-[r:CONTAINS]->(d)
                RETURN r
                """,
                {"document_id": document.id, "project_id": data['project_id']}
            ))
        
        # Relationship to folder
        if data.get('folder_id'):
            queries.append((
                """
                MATCH (d:Document {id: $document_id}), (f:Folder {id: $folder_id})
                MERGE (f)-[r:CONTAINS]->(d)
                RETURN r
                """,
                {"document_id": document.id, "folder_id": data['folder_id']}
            ))
        
        # Relationship to creator
        if data.get('created_by'):
            queries.append((
                """
                MATCH (d:Document {id: $document_id}), (u:User {id: $user_id})
                MERGE (u)-[r:CREATES]->(d)
                RETURN r
                """,
                {"document_id": document.id, "user_id": data['created_by']}
            ))
        
        # Execute relationship queries
        if queries:
            await self.execute_transaction(queries)
        
        # Create initial version
        version = await self.create_version(document.id, content, data.get('created_by'))
        
        return document, version
    
    async def create_version(self, document_id: str, content: str, user_id: Optional[str] = None, change_summary: Optional[str] = None) -> DocumentVersion:
        """
        Create a new version of a document.
        
        Args:
            document_id: Document ID
            content: Document content
            user_id: User ID of the creator
            change_summary: Summary of changes
            
        Returns:
            The created document version
        """
        # Get current max version number
        query = """
        MATCH (d:Document {id: $document_id})-[:HAS_VERSION]->(v:DocumentVersion)
        RETURN max(v.version_number) as max_version
        """
        
        try:
            result = await self.client.execute_query_async(query, {"document_id": document_id})
            current_version = result[0]['max_version'] if result and result[0]['max_version'] is not None else 0
            
            # Calculate new version number
            new_version_number = current_version + 1
            
            # Create version node
            version_data = {
                'document_id': document_id,
                'version_number': new_version_number,
                'content': content,
                'created_by': user_id,
                'change_summary': change_summary,
                'created_at': datetime.utcnow().isoformat()
            }
            
            create_version_query = """
            CREATE (v:DocumentVersion {
                id: $id,
                document_id: $document_id,
                version_number: $version_number,
                content: $content,
                created_by: $created_by,
                change_summary: $change_summary,
                created_at: datetime($created_at)
            })
            RETURN v
            """
            
            # Generate ID for version
            version_data['id'] = str(uuid.uuid4())
            
            # Create version node
            version_result = await self.client.execute_query_async(create_version_query, version_data)
            
            if not version_result:
                raise Exception("Failed to create document version")
            
            version_node = version_result[0]['v']
            
            # Create relationships
            relationship_queries = [
                # Document HAS_VERSION Version
                ("""
                MATCH (d:Document {id: $document_id}), (v:DocumentVersion {id: $version_id})
                MERGE (d)-[r:HAS_VERSION]->(v)
                RETURN r
                """,
                {"document_id": document_id, "version_id": version_data['id']}),
                
                # Document HAS_LATEST_VERSION Version
                ("""
                MATCH (d:Document {id: $document_id}), (v:DocumentVersion {id: $version_id})
                MERGE (d)-[r:HAS_LATEST_VERSION]->(v)
                RETURN r
                """,
                {"document_id": document_id, "version_id": version_data['id']}),
                
                # User CREATES Version (if user_id provided)
                ("""
                MATCH (v:DocumentVersion {id: $version_id})
                MATCH (u:User {id: $user_id})
                MERGE (u)-[r:CREATES]->(v)
                RETURN r
                """,
                {"version_id": version_data['id'], "user_id": user_id}) if user_id else None
            ]
            
            # Filter out None queries
            relationship_queries = [q for q in relationship_queries if q]
            
            # Execute relationship queries
            for query, params in relationship_queries:
                await self.client.execute_query_async(query, params)
            
            # Update document updated_at timestamp
            await self.update(document_id, {"updated_at": datetime.utcnow().isoformat()})
            
            # Create DocumentVersion object
            return DocumentVersion(
                id=version_data['id'],
                document_id=document_id,
                version_number=new_version_number,
                content=content,
                created_by=user_id,
                change_summary=change_summary,
                created_at=datetime.utcnow(),
                author_id=user_id  # Use user_id as author_id
            )
        except Exception as e:
            logger.error(f"Error creating document version: {str(e)}")
            raise
    
    async def get_version(self, document_id: str, version_number: Optional[int] = None) -> Optional[DocumentVersion]:
        """
        Get a specific version of a document.
        
        Args:
            document_id: Document ID
            version_number: Version number, or None for latest version
            
        Returns:
            The document version if found, None otherwise
        """
        if version_number:
            # Get specific version
            query = """
            MATCH (d:Document {id: $document_id})-[:HAS_VERSION]->(v:DocumentVersion)
            WHERE v.version_number = $version_number
            RETURN v
            """
            params = {"document_id": document_id, "version_number": version_number}
        else:
            # Get latest version
            query = """
            MATCH (d:Document {id: $document_id})-[:HAS_LATEST_VERSION]->(v:DocumentVersion)
            RETURN v
            """
            params = {"document_id": document_id}
        
        try:
            result = await self.client.execute_query_async(query, params)
            if not result:
                return None
            
            version_node = result[0]['v']
            
            # Create DocumentVersion object
            return DocumentVersion(
                id=version_node.get('id'),
                document_id=document_id,
                version_number=version_node.get('version_number'),
                content=version_node.get('content'),
                created_by=version_node.get('created_by'),
                change_summary=version_node.get('change_summary'),
                created_at=datetime.fromisoformat(version_node.get('created_at').replace('Z', '+00:00'))
                    if isinstance(version_node.get('created_at'), str) else version_node.get('created_at'),
                author_id=version_node.get('created_by')  # Use created_by as author_id
            )
        except Exception as e:
            logger.error(f"Error getting document version: {str(e)}")
            raise
    
    async def get_version_history(self, document_id: str) -> List[DocumentVersion]:
        """
        Get the version history of a document.
        
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
            
            versions = []
            for record in result:
                version_node = record['v']
                
                # Create DocumentVersion object
                version = DocumentVersion(
                    id=version_node.get('id'),
                    document_id=document_id,
                    version_number=version_node.get('version_number'),
                    content=version_node.get('content'),
                    created_by=version_node.get('created_by'),
                    change_summary=version_node.get('change_summary'),
                    created_at=datetime.fromisoformat(version_node.get('created_at').replace('Z', '+00:00'))
                        if isinstance(version_node.get('created_at'), str) else version_node.get('created_at'),
                    author_id=version_node.get('created_by')  # Use created_by as author_id
                )
                
                versions.append(version)
            
            return versions
        except Exception as e:
            logger.error(f"Error getting document version history: {str(e)}")
            raise
    
    async def restore_version(self, document_id: str, version_number: int, user_id: Optional[str] = None) -> Optional[DocumentVersion]:
        """
        Restore a previous version of a document.
        
        Args:
            document_id: Document ID
            version_number: Version number to restore
            user_id: User ID performing the restoration
            
        Returns:
            The new document version if successful, None otherwise
        """
        # Get the version to restore
        version_to_restore = await self.get_version(document_id, version_number)
        if not version_to_restore:
            return None
        
        # Create a new version with the content from the version to restore
        change_summary = f"Restored from version {version_number}"
        return await self.create_version(
            document_id=document_id,
            content=version_to_restore.content,
            user_id=user_id,
            change_summary=change_summary
        )
    
    async def get_documents_by_project(self, project_id: str, include_content: bool = False) -> List[Dict[str, Any]]:
        """
        Get all documents in a project.
        
        Args:
            project_id: Project ID
            include_content: Whether to include document content
            
        Returns:
            List of documents with optional content
        """
        if include_content:
            query = """
            MATCH (p:Project {id: $project_id})-[:CONTAINS*]->(d:Document)
            OPTIONAL MATCH (d)-[:HAS_LATEST_VERSION]->(v:DocumentVersion)
            RETURN d, v
            ORDER BY d.updated_at DESC
            """
        else:
            query = """
            MATCH (p:Project {id: $project_id})-[:CONTAINS*]->(d:Document)
            RETURN d
            ORDER BY d.updated_at DESC
            """
        
        try:
            result = await self.client.execute_query_async(query, {"project_id": project_id})
            
            documents = []
            for record in result:
                document = self.map_to_entity(record['d'])
                
                if include_content and 'v' in record and record['v']:
                    version = record['v']
                    document_dict = document.__dict__
                    document_dict['content'] = version.get('content')
                    document_dict['version_number'] = version.get('version_number')
                    documents.append(document_dict)
                else:
                    documents.append(document.__dict__)
            
            return documents
        except Exception as e:
            logger.error(f"Error getting documents by project: {str(e)}")
            raise
    
    async def get_documents_by_folder(self, folder_id: str, include_content: bool = False) -> List[Dict[str, Any]]:
        """
        Get all documents in a folder.
        
        Args:
            folder_id: Folder ID
            include_content: Whether to include document content
            
        Returns:
            List of documents with optional content
        """
        if include_content:
            query = """
            MATCH (f:Folder {id: $folder_id})-[:CONTAINS]->(d:Document)
            OPTIONAL MATCH (d)-[:HAS_LATEST_VERSION]->(v:DocumentVersion)
            RETURN d, v
            ORDER BY d.name
            """
        else:
            query = """
            MATCH (f:Folder {id: $folder_id})-[:CONTAINS]->(d:Document)
            RETURN d
            ORDER BY d.name
            """
        
        try:
            result = await self.client.execute_query_async(query, {"folder_id": folder_id})
            
            documents = []
            for record in result:
                document = self.map_to_entity(record['d'])
                
                if include_content and 'v' in record and record['v']:
                    version = record['v']
                    document_dict = document.__dict__
                    document_dict['content'] = version.get('content')
                    document_dict['version_number'] = version.get('version_number')
                    documents.append(document_dict)
                else:
                    documents.append(document.__dict__)
            
            return documents
        except Exception as e:
            logger.error(f"Error getting documents by folder: {str(e)}")
            raise
    
    async def get_document_with_content(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document with its latest content.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document with content if found, None otherwise
        """
        query = """
        MATCH (d:Document {id: $document_id})
        OPTIONAL MATCH (d)-[:HAS_LATEST_VERSION]->(v:DocumentVersion)
        RETURN d, v
        """
        
        try:
            result = await self.client.execute_query_async(query, {"document_id": document_id})
            if not result:
                return None
            
            document = self.map_to_entity(result[0]['d'])
            document_dict = document.__dict__
            
            if 'v' in result[0] and result[0]['v']:
                version = result[0]['v']
                document_dict['content'] = version.get('content')
                document_dict['version_number'] = version.get('version_number')
            else:
                document_dict['content'] = ""
                document_dict['version_number'] = 0
            
            return document_dict
        except Exception as e:
            logger.error(f"Error getting document with content: {str(e)}")
            raise
    
    async def move_document(self, document_id: str, new_folder_id: Optional[str] = None) -> Optional[Document]:
        """
        Move a document to a new folder or to the root level.
        
        Args:
            document_id: Document ID
            new_folder_id: New folder ID, or None to move to root
            
        Returns:
            The updated document if found, None otherwise
        """
        document = await self.get_by_id(document_id)
        if not document:
            return None
        
        # Get project ID
        project_id = document.project_id
        
        # Remove existing CONTAINS relationship
        remove_rel_query = """
        MATCH (d:Document {id: $document_id})
        OPTIONAL MATCH (parent)-[r:CONTAINS]->(d)
        WHERE parent:Folder OR parent:Project
        DELETE r
        """
        
        # Create new CONTAINS relationship
        if new_folder_id:
            create_rel_query = """
            MATCH (d:Document {id: $document_id}), (f:Folder {id: $new_folder_id})
            MERGE (f)-[r:CONTAINS]->(d)
            """
            
            params = {
                "document_id": document_id,
                "new_folder_id": new_folder_id
            }
        else:
            create_rel_query = """
            MATCH (d:Document {id: $document_id}), (p:Project {id: $project_id})
            MERGE (p)-[r:CONTAINS]->(d)
            """
            
            params = {
                "document_id": document_id,
                "project_id": project_id
            }
        
        # Update document folder_id
        update_data = {
            "folder_id": new_folder_id,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Execute queries in transaction
        try:
            # Remove old relationship
            await self.client.execute_query_async(remove_rel_query, {"document_id": document_id})
            
            # Create new relationship
            await self.client.execute_query_async(create_rel_query, params)
            
            # Update document
            return await self.update(document_id, update_data)
        except Exception as e:
            logger.error(f"Error moving document: {str(e)}")
            raise
    
    async def pin_document(self, document_id: str) -> Optional[Document]:
        """
        Pin a document to the dashboard.
        
        Args:
            document_id: Document ID
            
        Returns:
            The updated document if found, None otherwise
        """
        return await self.update(document_id, {"is_pinned": True})
    
    async def unpin_document(self, document_id: str) -> Optional[Document]:
        """
        Unpin a document from the dashboard.
        
        Args:
            document_id: Document ID
            
        Returns:
            The updated document if found, None otherwise
        """
        return await self.update(document_id, {"is_pinned": False})
    
    async def get_pinned_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all pinned documents for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of pinned documents with content
        """
        query = """
        MATCH (u:User {id: $user_id})-[:CREATES]->(d:Document)
        WHERE d.is_pinned = true
        OPTIONAL MATCH (d)-[:HAS_LATEST_VERSION]->(v:DocumentVersion)
        RETURN d, v
        ORDER BY d.updated_at DESC
        """
        
        try:
            result = await self.client.execute_query_async(query, {"user_id": user_id})
            
            documents = []
            for record in result:
                document = self.map_to_entity(record['d'])
                document_dict = document.__dict__
                
                if 'v' in record and record['v']:
                    version = record['v']
                    document_dict['content'] = version.get('content')
                    document_dict['version_number'] = version.get('version_number')
                else:
                    document_dict['content'] = ""
                    document_dict['version_number'] = 0
                
                documents.append(document_dict)
            
            return documents
        except Exception as e:
            logger.error(f"Error getting pinned documents: {str(e)}")
            raise
    
    async def update_document_status(self, document_id: str, status: str, user_id: Optional[str] = None) -> Optional[Document]:
        """
        Update a document's status.
        
        Args:
            document_id: Document ID
            status: New status
            user_id: User ID performing the update
            
        Returns:
            The updated document if found, None otherwise
        """
        document = await self.get_by_id(document_id)
        if not document:
            return None
        
        # Get current status
        previous_status = document.status
        
        # Update document status
        updated_document = await self.update(document_id, {"status": status})
        
        # Create status update record
        if updated_document:
            status_update_query = """
            CREATE (s:StatusUpdate {
                id: $id,
                document_id: $document_id,
                previous_status: $previous_status,
                new_status: $status,
                created_by: $user_id,
                created_at: datetime()
            })
            RETURN s
            """
            
            status_update_params = {
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "previous_status": previous_status,
                "status": status,
                "user_id": user_id
            }
            
            try:
                await self.client.execute_query_async(status_update_query, status_update_params)
                
                # Create relationship between document and status update
                rel_query = """
                MATCH (d:Document {id: $document_id}), (s:StatusUpdate {id: $status_update_id})
                MERGE (d)-[r:HAS_STATUS]->(s)
                RETURN r
                """
                
                rel_params = {
                    "document_id": document_id,
                    "status_update_id": status_update_params["id"]
                }
                
                await self.client.execute_query_async(rel_query, rel_params)
            except Exception as e:
                logger.error(f"Error creating status update: {str(e)}")
                # Continue even if status update creation fails
        
        return updated_document
    
    async def get_document_status_history(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get the status update history of a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of status updates
        """
        query = """
        MATCH (d:Document {id: $document_id})-[:HAS_STATUS]->(s:StatusUpdate)
        OPTIONAL MATCH (u:User {id: s.created_by})
        RETURN s, u.name as user_name
        ORDER BY s.created_at DESC
        """
        
        try:
            result = await self.client.execute_query_async(query, {"document_id": document_id})
            
            status_updates = []
            for record in result:
                status_update = record['s']
                user_name = record['user_name']
                
                created_at = status_update.get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                status_updates.append({
                    "id": status_update.get('id'),
                    "document_id": document_id,
                    "previous_status": status_update.get('previous_status'),
                    "new_status": status_update.get('new_status'),
                    "created_by": status_update.get('created_by'),
                    "created_by_name": user_name,
                    "created_at": created_at,
                    "comment": status_update.get('comment')
                })
            
            return status_updates
        except Exception as e:
            logger.error(f"Error getting document status history: {str(e)}")
            raise