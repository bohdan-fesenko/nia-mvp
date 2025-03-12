"""
Qdrant client for vector database operations.
This module provides a client for interacting with the Qdrant vector database.
"""
import logging
from typing import List, Dict, Any, Optional, Union
import uuid
import numpy as np

from qdrant_client import QdrantClient as BaseQdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from ..config import settings

logger = logging.getLogger(__name__)


class QdrantClient:
    """
    Qdrant client for vector database operations.
    """
    def __init__(self):
        """
        Initialize the Qdrant client.
        """
        self._client = None
        self._url = settings.QDRANT_URL
        self._api_key = settings.QDRANT_API_KEY
        self._collection_name = settings.QDRANT_COLLECTION

    def connect(self):
        """
        Connect to the Qdrant database.
        """
        if self._client is None:
            try:
                self._client = BaseQdrantClient(
                    url=self._url,
                    api_key=self._api_key
                )
                logger.info("Connected to Qdrant database")
            except Exception as e:
                logger.error(f"Failed to connect to Qdrant: {str(e)}")
                raise

    def close(self):
        """
        Close the connection to the Qdrant database.
        """
        if self._client is not None:
            self._client = None
            logger.info("Disconnected from Qdrant database")

    def create_collection(self, vector_size: int = 1536, distance: str = "Cosine"):
        """
        Create a collection in Qdrant.
        
        Args:
            vector_size: The size of the vectors to store.
            distance: The distance function to use.
        """
        self.connect()
        
        try:
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            logger.info(f"Created Qdrant collection: {self._collection_name}")
        except UnexpectedResponse as e:
            if "already exists" in str(e):
                logger.info(f"Collection {self._collection_name} already exists")
            else:
                logger.error(f"Error creating Qdrant collection: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Error creating Qdrant collection: {str(e)}")
            raise

    def collection_exists(self) -> bool:
        """
        Check if a collection exists.
        
        Returns:
            True if the collection exists, False otherwise.
        """
        self.connect()
        
        try:
            collections = self._client.get_collections().collections
            return any(collection.name == self._collection_name for collection in collections)
        except Exception as e:
            logger.error(f"Error checking if collection exists: {str(e)}")
            raise

    def upsert_vector(
        self, 
        vector: List[float], 
        payload: Dict[str, Any], 
        vector_id: Optional[str] = None
    ) -> str:
        """
        Insert or update a vector in Qdrant.
        
        Args:
            vector: The vector to insert.
            payload: The payload to associate with the vector.
            vector_id: The ID of the vector. If None, a new ID will be generated.
            
        Returns:
            The ID of the inserted vector.
        """
        self.connect()
        
        if vector_id is None:
            vector_id = str(uuid.uuid4())
        
        try:
            self._client.upsert(
                collection_name=self._collection_name,
                points=[
                    qdrant_models.PointStruct(
                        id=vector_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            logger.info(f"Upserted vector with ID: {vector_id}")
            return vector_id
        except Exception as e:
            logger.error(f"Error upserting vector: {str(e)}")
            raise

    def delete_vector(self, vector_id: str) -> bool:
        """
        Delete a vector from Qdrant.
        
        Args:
            vector_id: The ID of the vector to delete.
            
        Returns:
            True if the vector was deleted, False otherwise.
        """
        self.connect()
        
        try:
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=qdrant_models.PointIdsList(
                    points=[vector_id]
                )
            )
            logger.info(f"Deleted vector with ID: {vector_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting vector: {str(e)}")
            raise

    def search_vectors(
        self, 
        query_vector: List[float], 
        limit: int = 10, 
        filter_condition: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for vectors in Qdrant.
        
        Args:
            query_vector: The query vector.
            limit: The maximum number of results to return.
            filter_condition: The filter condition to apply.
            
        Returns:
            A list of search results.
        """
        self.connect()
        
        try:
            filter_obj = None
            if filter_condition:
                filter_obj = qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key=key,
                            match=qdrant_models.MatchValue(value=value)
                        )
                        for key, value in filter_condition.items()
                    ]
                )
            
            search_result = self._client.search(
                collection_name=self._collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=filter_obj
            )
            
            return [
                {
                    "id": str(result.id),
                    "score": result.score,
                    "payload": result.payload
                }
                for result in search_result
            ]
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise

    def get_vector(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a vector from Qdrant.
        
        Args:
            vector_id: The ID of the vector to get.
            
        Returns:
            The vector, or None if not found.
        """
        self.connect()
        
        try:
            result = self._client.retrieve(
                collection_name=self._collection_name,
                ids=[vector_id]
            )
            
            if not result:
                return None
            
            return {
                "id": str(result[0].id),
                "vector": result[0].vector,
                "payload": result[0].payload
            }
        except Exception as e:
            logger.error(f"Error getting vector: {str(e)}")
            raise

    def batch_upsert_vectors(
        self, 
        vectors: List[List[float]], 
        payloads: List[Dict[str, Any]], 
        vector_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Insert or update multiple vectors in Qdrant.
        
        Args:
            vectors: The vectors to insert.
            payloads: The payloads to associate with the vectors.
            vector_ids: The IDs of the vectors. If None, new IDs will be generated.
            
        Returns:
            The IDs of the inserted vectors.
        """
        self.connect()
        
        if len(vectors) != len(payloads):
            raise ValueError("The number of vectors and payloads must be the same")
        
        if vector_ids is None:
            vector_ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
        elif len(vector_ids) != len(vectors):
            raise ValueError("The number of vector_ids must match the number of vectors")
        
        try:
            points = [
                qdrant_models.PointStruct(
                    id=vector_id,
                    vector=vector,
                    payload=payload
                )
                for vector_id, vector, payload in zip(vector_ids, vectors, payloads)
            ]
            
            self._client.upsert(
                collection_name=self._collection_name,
                points=points
            )
            
            logger.info(f"Batch upserted {len(vectors)} vectors")
            return vector_ids
        except Exception as e:
            logger.error(f"Error batch upserting vectors: {str(e)}")
            raise


# Create a singleton instance
qdrant_client = QdrantClient()