"""
Base repository interface.
This module provides the base repository interface that all repositories should implement.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    """Base repository interface for database operations."""
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> T:
        """
        Create a new entity.
        
        Args:
            data: Dictionary containing entity data
            
        Returns:
            The created entity
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """
        Get an entity by its ID.
        
        Args:
            id: Entity ID
            
        Returns:
            The entity if found, None otherwise
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[T]:
        """
        Update an entity.
        
        Args:
            id: Entity ID
            data: Dictionary containing updated entity data
            
        Returns:
            The updated entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        Delete an entity.
        
        Args:
            id: Entity ID
            
        Returns:
            True if entity was deleted, False otherwise
        """
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities with optional filtering.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            Number of entities
        """
        pass