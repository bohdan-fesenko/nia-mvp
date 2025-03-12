"""
Neo4j client for database operations.
This module provides a client for interacting with the Neo4j database.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, TypeVar, Generic, Type
import asyncio

from neo4j import GraphDatabase, AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import Neo4jError
from pydantic import BaseModel

from ..config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class Neo4jClient:
    """
    Neo4j client for database operations.
    """
    def __init__(self):
        """
        Initialize the Neo4j client.
        """
        self._driver = None
        self._async_driver = None
        self._uri = settings.NEO4J_URI
        self._username = settings.NEO4J_USERNAME
        self._password = settings.NEO4J_PASSWORD
        self._database = settings.NEO4J_DATABASE

    def connect(self):
        """
        Connect to the Neo4j database.
        """
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    self._uri,
                    auth=(self._username, self._password)
                )
                logger.info("Connected to Neo4j database")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {str(e)}")
                raise

    async def connect_async(self):
        """
        Connect to the Neo4j database asynchronously.
        """
        if self._async_driver is None:
            try:
                self._async_driver = AsyncGraphDatabase.driver(
                    self._uri,
                    auth=(self._username, self._password)
                )
                logger.info("Connected to Neo4j database (async)")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j (async): {str(e)}")
                raise

    def close(self):
        """
        Close the connection to the Neo4j database.
        """
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Disconnected from Neo4j database")

    async def close_async(self):
        """
        Close the async connection to the Neo4j database.
        """
        if self._async_driver is not None:
            await self._async_driver.close()
            self._async_driver = None
            logger.info("Disconnected from Neo4j database (async)")

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query.
        
        Args:
            query: The Cypher query to execute.
            parameters: The parameters for the query.
            
        Returns:
            The result of the query.
        """
        self.connect()
        
        try:
            with self._driver.session(database=self._database) as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Neo4jError as e:
            logger.error(f"Neo4j query error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error executing Neo4j query: {str(e)}")
            raise

    async def execute_query_async(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query asynchronously.
        
        Args:
            query: The Cypher query to execute.
            parameters: The parameters for the query.
            
        Returns:
            The result of the query.
        """
        await self.connect_async()
        
        try:
            async with self._async_driver.session(database=self._database) as session:
                result = await session.run(query, parameters or {})
                records = await result.values()
                return [dict(zip(result.keys(), record)) for record in records]
        except Neo4jError as e:
            logger.error(f"Neo4j async query error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error executing Neo4j async query: {str(e)}")
            raise

    def create_node(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a node in the Neo4j database.
        
        Args:
            label: The label of the node.
            properties: The properties of the node.
            
        Returns:
            The created node.
        """
        # Ensure ID is set
        if 'id' not in properties:
            properties['id'] = str(uuid.uuid4())
        
        # Add timestamps
        now = datetime.utcnow().isoformat()
        if 'created_at' not in properties:
            properties['created_at'] = now
        if 'updated_at' not in properties:
            properties['updated_at'] = now
        
        query = f"""
        CREATE (n:{label} $properties)
        RETURN n
        """
        
        result = self.execute_query(query, {'properties': properties})
        return result[0]['n'] if result else None

    async def create_node_async(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a node in the Neo4j database asynchronously.
        
        Args:
            label: The label of the node.
            properties: The properties of the node.
            
        Returns:
            The created node.
        """
        # Ensure ID is set
        if 'id' not in properties:
            properties['id'] = str(uuid.uuid4())
        
        # Add timestamps
        now = datetime.utcnow().isoformat()
        if 'created_at' not in properties:
            properties['created_at'] = now
        if 'updated_at' not in properties:
            properties['updated_at'] = now
        
        query = f"""
        CREATE (n:{label} $properties)
        RETURN n
        """
        
        result = await self.execute_query_async(query, {'properties': properties})
        return result[0]['n'] if result else None

    def get_node_by_id(self, label: str, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID.
        
        Args:
            label: The label of the node.
            node_id: The ID of the node.
            
        Returns:
            The node, or None if not found.
        """
        query = f"""
        MATCH (n:{label} {{id: $id}})
        RETURN n
        """
        
        result = self.execute_query(query, {'id': node_id})
        return result[0]['n'] if result else None

    async def get_node_by_id_async(self, label: str, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID asynchronously.
        
        Args:
            label: The label of the node.
            node_id: The ID of the node.
            
        Returns:
            The node, or None if not found.
        """
        query = f"""
        MATCH (n:{label} {{id: $id}})
        RETURN n
        """
        
        result = await self.execute_query_async(query, {'id': node_id})
        return result[0]['n'] if result else None

    def update_node(self, label: str, node_id: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a node.
        
        Args:
            label: The label of the node.
            node_id: The ID of the node.
            properties: The properties to update.
            
        Returns:
            The updated node, or None if not found.
        """
        # Add updated_at timestamp
        properties['updated_at'] = datetime.utcnow().isoformat()
        
        # Build the SET clause
        set_clause = ", ".join([f"n.{key} = ${key}" for key in properties.keys()])
        
        query = f"""
        MATCH (n:{label} {{id: $id}})
        SET {set_clause}
        RETURN n
        """
        
        # Add id to parameters
        parameters = {**properties, 'id': node_id}
        
        result = self.execute_query(query, parameters)
        return result[0]['n'] if result else None

    async def update_node_async(self, label: str, node_id: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a node asynchronously.
        
        Args:
            label: The label of the node.
            node_id: The ID of the node.
            properties: The properties to update.
            
        Returns:
            The updated node, or None if not found.
        """
        # Add updated_at timestamp
        properties['updated_at'] = datetime.utcnow().isoformat()
        
        # Build the SET clause
        set_clause = ", ".join([f"n.{key} = ${key}" for key in properties.keys()])
        
        query = f"""
        MATCH (n:{label} {{id: $id}})
        SET {set_clause}
        RETURN n
        """
        
        # Add id to parameters
        parameters = {**properties, 'id': node_id}
        
        result = await self.execute_query_async(query, parameters)
        return result[0]['n'] if result else None

    def delete_node(self, label: str, node_id: str) -> bool:
        """
        Delete a node.
        
        Args:
            label: The label of the node.
            node_id: The ID of the node.
            
        Returns:
            True if the node was deleted, False otherwise.
        """
        query = f"""
        MATCH (n:{label} {{id: $id}})
        DETACH DELETE n
        """
        
        self.execute_query(query, {'id': node_id})
        return True

    async def delete_node_async(self, label: str, node_id: str) -> bool:
        """
        Delete a node asynchronously.
        
        Args:
            label: The label of the node.
            node_id: The ID of the node.
            
        Returns:
            True if the node was deleted, False otherwise.
        """
        query = f"""
        MATCH (n:{label} {{id: $id}})
        DETACH DELETE n
        """
        
        await self.execute_query_async(query, {'id': node_id})
        return True

    def create_relationship(
        self, 
        from_label: str, 
        from_id: str, 
        to_label: str, 
        to_id: str, 
        relationship_type: str, 
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a relationship between two nodes.
        
        Args:
            from_label: The label of the source node.
            from_id: The ID of the source node.
            to_label: The label of the target node.
            to_id: The ID of the target node.
            relationship_type: The type of the relationship.
            properties: The properties of the relationship.
            
        Returns:
            The created relationship.
        """
        query = f"""
        MATCH (a:{from_label} {{id: $from_id}}), (b:{to_label} {{id: $to_id}})
        CREATE (a)-[r:{relationship_type} $properties]->(b)
        RETURN r
        """
        
        result = self.execute_query(query, {
            'from_id': from_id,
            'to_id': to_id,
            'properties': properties or {}
        })
        
        return result[0]['r'] if result else None

    async def create_relationship_async(
        self, 
        from_label: str, 
        from_id: str, 
        to_label: str, 
        to_id: str, 
        relationship_type: str, 
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a relationship between two nodes asynchronously.
        
        Args:
            from_label: The label of the source node.
            from_id: The ID of the source node.
            to_label: The label of the target node.
            to_id: The ID of the target node.
            relationship_type: The type of the relationship.
            properties: The properties of the relationship.
            
        Returns:
            The created relationship.
        """
        query = f"""
        MATCH (a:{from_label} {{id: $from_id}}), (b:{to_label} {{id: $to_id}})
        CREATE (a)-[r:{relationship_type} $properties]->(b)
        RETURN r
        """
        
        result = await self.execute_query_async(query, {
            'from_id': from_id,
            'to_id': to_id,
            'properties': properties or {}
        })
        
        return result[0]['r'] if result else None

    def get_related_nodes(
        self, 
        label: str, 
        node_id: str, 
        relationship_type: str, 
        direction: str = "OUTGOING", 
        target_label: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get nodes related to a node.
        
        Args:
            label: The label of the source node.
            node_id: The ID of the source node.
            relationship_type: The type of the relationship.
            direction: The direction of the relationship ("OUTGOING" or "INCOMING").
            target_label: The label of the target nodes.
            
        Returns:
            The related nodes.
        """
        if direction == "OUTGOING":
            relationship = f"-[:{relationship_type}]->"
        else:
            relationship = f"<-[:{relationship_type}]-"
        
        target_node = f"(b{f':{target_label}' if target_label else ''})"
        
        query = f"""
        MATCH (a:{label} {{id: $id}}) {relationship} {target_node}
        RETURN b
        """
        
        result = self.execute_query(query, {'id': node_id})
        return [record['b'] for record in result]

    async def get_related_nodes_async(
        self, 
        label: str, 
        node_id: str, 
        relationship_type: str, 
        direction: str = "OUTGOING", 
        target_label: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get nodes related to a node asynchronously.
        
        Args:
            label: The label of the source node.
            node_id: The ID of the source node.
            relationship_type: The type of the relationship.
            direction: The direction of the relationship ("OUTGOING" or "INCOMING").
            target_label: The label of the target nodes.
            
        Returns:
            The related nodes.
        """
        if direction == "OUTGOING":
            relationship = f"-[:{relationship_type}]->"
        else:
            relationship = f"<-[:{relationship_type}]-"
        
        target_node = f"(b{f':{target_label}' if target_label else ''})"
        
        query = f"""
        MATCH (a:{label} {{id: $id}}) {relationship} {target_node}
        RETURN b
        """
        
        result = await self.execute_query_async(query, {'id': node_id})
        return [record['b'] for record in result]

# Create a singleton instance
neo4j_client = Neo4jClient()

# Function to get the Neo4j client
async def get_neo4j_client():
    """
    Get the Neo4j client.
    
    Returns:
        The Neo4j client
    """
    await neo4j_client.connect_async()
    return neo4j_client
neo4j_client = Neo4jClient()