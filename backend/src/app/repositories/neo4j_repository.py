"""
Neo4j repository base implementation.
This module provides a base Neo4j repository implementation that all Neo4j repositories can extend.
"""
import logging
import uuid
from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union, Tuple

from ..db.neo4j_client import neo4j_client
from .base_repository import BaseRepository

T = TypeVar('T')
logger = logging.getLogger(__name__)

class Neo4jRepository(BaseRepository[T]):
    """Base Neo4j repository implementation."""
    
    def __init__(self):
        """Initialize the repository."""
        self.client = neo4j_client
    
    @property
    @abstractmethod
    def label(self) -> str:
        """
        Get the Neo4j label for this repository.
        
        Returns:
            The Neo4j label
        """
        pass
    
    @abstractmethod
    def map_to_entity(self, record: Dict[str, Any]) -> T:
        """
        Map a Neo4j record to an entity.
        
        Args:
            record: Neo4j record
            
        Returns:
            The mapped entity
        """
        pass
    
    @abstractmethod
    def map_to_db(self, entity: Union[Dict[str, Any], T]) -> Dict[str, Any]:
        """
        Map an entity to a Neo4j record.
        
        Args:
            entity: Entity to map
            
        Returns:
            The mapped Neo4j record
        """
        pass
    
    async def create(self, data: Dict[str, Any]) -> T:
        """
        Create a new entity.
        
        Args:
            data: Dictionary containing entity data
            
        Returns:
            The created entity
        """
        # Generate ID if not provided
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        
        # Add timestamps
        now = datetime.utcnow().isoformat()
        data['created_at'] = now
        data['updated_at'] = now
        
        # Map data to Neo4j format
        db_data = self.map_to_db(data)
        
        # Build dynamic property string for Cypher query
        props = ', '.join([f"{k}: ${k}" for k in db_data.keys()])
        
        query = f"""
        CREATE (n:{self.label} {{{props}}})
        RETURN n
        """
        
        try:
            result = await self.client.execute_query_async(query, db_data)
            if not result:
                logger.error(f"Failed to create {self.label}")
                raise Exception(f"Failed to create {self.label}")
            
            return self.map_to_entity(result[0]['n'])
        except Exception as e:
            logger.error(f"Error creating {self.label}: {str(e)}")
            raise
    
    async def get_by_id(self, id: str) -> Optional[T]:
        """
        Get an entity by its ID.
        
        Args:
            id: Entity ID
            
        Returns:
            The entity if found, None otherwise
        """
        query = f"""
        MATCH (n:{self.label} {{id: $id}})
        RETURN n
        """
        
        try:
            result = await self.client.execute_query_async(query, {"id": id})
            if not result:
                return None
            
            return self.map_to_entity(result[0]['n'])
        except Exception as e:
            logger.error(f"Error getting {self.label} by ID: {str(e)}")
            raise
    
    async def get_all(self, 
                     skip: int = 0, 
                     limit: int = 100, 
                     filters: Optional[Dict[str, Any]] = None,
                     sort_by: Optional[str] = None,
                     sort_desc: bool = False) -> List[T]:
        """
        Get all entities with optional filtering, sorting, and pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters to apply
            sort_by: Optional field to sort by
            sort_desc: Whether to sort in descending order
            
        Returns:
            List of entities
        """
        # Build WHERE clause if filters are provided
        where_clause = ""
        params = {"skip": skip, "limit": limit}
        
        if filters:
            conditions = []
            for key, value in filters.items():
                params[key] = value
                conditions.append(f"n.{key} = ${key}")
            
            if conditions:
                where_clause = f"WHERE {' AND '.join(conditions)}"
        
        # Build ORDER BY clause if sort_by is provided
        order_clause = ""
        if sort_by:
            direction = "DESC" if sort_desc else "ASC"
            order_clause = f"ORDER BY n.{sort_by} {direction}"
        
        query = f"""
        MATCH (n:{self.label})
        {where_clause}
        {order_clause}
        RETURN n
        SKIP $skip
        LIMIT $limit
        """
        
        try:
            result = await self.client.execute_query_async(query, params)
            return [self.map_to_entity(record['n']) for record in result]
        except Exception as e:
            logger.error(f"Error getting all {self.label}: {str(e)}")
            raise
    
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[T]:
        """
        Update an entity.
        
        Args:
            id: Entity ID
            data: Dictionary containing updated entity data
            
        Returns:
            The updated entity if found, None otherwise
        """
        # Add updated timestamp
        data['updated_at'] = datetime.utcnow().isoformat()
        
        # Map data to Neo4j format
        db_data = self.map_to_db(data)
        db_data['id'] = id  # Ensure ID is included
        
        # Build dynamic SET clause for Cypher query
        set_clause = ', '.join([f"n.{k} = ${k}" for k in db_data.keys() if k != 'id'])
        
        query = f"""
        MATCH (n:{self.label} {{id: $id}})
        SET {set_clause}
        RETURN n
        """
        
        try:
            result = await self.client.execute_query_async(query, db_data)
            if not result:
                return None
            
            return self.map_to_entity(result[0]['n'])
        except Exception as e:
            logger.error(f"Error updating {self.label}: {str(e)}")
            raise
    
    async def delete(self, id: str) -> bool:
        """
        Delete an entity.
        
        Args:
            id: Entity ID
            
        Returns:
            True if entity was deleted, False otherwise
        """
        query = f"""
        MATCH (n:{self.label} {{id: $id}})
        DELETE n
        RETURN count(n) as deleted
        """
        
        try:
            result = await self.client.execute_query_async(query, {"id": id})
            return result[0]['deleted'] > 0
        except Exception as e:
            logger.error(f"Error deleting {self.label}: {str(e)}")
            raise
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities with optional filtering.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            Number of entities
        """
        # Build WHERE clause if filters are provided
        where_clause = ""
        params = {}
        
        if filters:
            conditions = []
            for key, value in filters.items():
                params[key] = value
                conditions.append(f"n.{key} = ${key}")
            
            if conditions:
                where_clause = f"WHERE {' AND '.join(conditions)}"
        
        query = f"""
        MATCH (n:{self.label})
        {where_clause}
        RETURN count(n) as count
        """
        
        try:
            result = await self.client.execute_query_async(query, params)
            return result[0]['count']
        except Exception as e:
            logger.error(f"Error counting {self.label}: {str(e)}")
            raise
    
    async def exists(self, id: str) -> bool:
        """
        Check if an entity exists.
        
        Args:
            id: Entity ID
            
        Returns:
            True if entity exists, False otherwise
        """
        query = f"""
        MATCH (n:{self.label} {{id: $id}})
        RETURN count(n) as count
        """
        
        try:
            result = await self.client.execute_query_async(query, {"id": id})
            return result[0]['count'] > 0
        except Exception as e:
            logger.error(f"Error checking if {self.label} exists: {str(e)}")
            raise
    
    async def execute_transaction(self, queries: List[Tuple[str, Dict[str, Any]]]) -> List[Any]:
        """
        Execute multiple queries in a transaction.
        
        Args:
            queries: List of (query, params) tuples
            
        Returns:
            List of results for each query
        """
        try:
            results = []
            for query, params in queries:
                result = await self.client.execute_query_async(query, params)
                results.append(result)
            return results
        except Exception as e:
            logger.error(f"Error executing transaction: {str(e)}")
            raise