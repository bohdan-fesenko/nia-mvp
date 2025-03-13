"""
Event repository implementation.
This module provides the repository implementation for Event entities.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..db.models import Event
from .neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)

class EventRepository(Neo4jRepository[Event]):
    """Repository for Event entities."""
    
    @property
    def label(self) -> str:
        """
        Get the Neo4j label for this repository.
        
        Returns:
            The Neo4j label
        """
        return "Event"
    
    def map_to_entity(self, record: Dict[str, Any]) -> Event:
        """
        Map a Neo4j record to an Event entity.
        
        Args:
            record: Neo4j record
            
        Returns:
            The mapped Event entity
        """
        created_at = record.get('created_at')
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
        return Event(
            id=record.get('id'),
            type=record.get('type'),
            data=record.get('data'),
            target_type=record.get('target_type'),
            target_id=record.get('target_id'),
            created_at=created_at,
            created_by=record.get('created_by')
        )
    
    def map_to_db(self, entity: Union[Dict[str, Any], Event]) -> Dict[str, Any]:
        """
        Map an Event entity to a Neo4j record.
        
        Args:
            entity: Event entity or dictionary
            
        Returns:
            The mapped Neo4j record
        """
        if isinstance(entity, Event):
            # Convert Event object to dictionary
            return {
                'id': entity.id,
                'type': entity.type,
                'data': entity.data,
                'target_type': entity.target_type,
                'target_id': entity.target_id,
                'created_at': entity.created_at.isoformat() if entity.created_at else None,
                'created_by': entity.created_by
            }
        
        # Entity is already a dictionary
        return entity
    
    async def create_event(self, event_type: str, data: Dict[str, Any], 
                          target_type: Optional[str] = None, target_id: Optional[str] = None,
                          created_by: Optional[str] = None) -> Event:
        """
        Create a new event and establish relationships.
        
        Args:
            event_type: The type of event
            data: The event data
            target_type: Optional target type (user, project, document, chat_session)
            target_id: Optional target ID
            created_by: Optional user ID who created the event
            
        Returns:
            The created event
        """
        # Create event data
        event_data = {
            'id': str(uuid.uuid4()),
            'type': event_type,
            'data': data,
            'target_type': target_type,
            'target_id': target_id,
            'created_at': datetime.utcnow().isoformat(),
            'created_by': created_by
        }
        
        # Create event node
        event = await self.create(event_data)
        
        # Create relationships
        queries = []
        
        # Relationship to target
        if target_type and target_id:
            target_label = {
                'user': 'User',
                'project': 'Project',
                'document': 'Document',
                'chat_session': 'ChatSession',
                'task': 'Task',
                'folder': 'Folder'
            }.get(target_type)
            
            if target_label:
                queries.append((
                    f"""
                    MATCH (e:Event {{id: $event_id}}), (t:{target_label} {{id: $target_id}})
                    MERGE (t)-[r:HAS_EVENT]->(e)
                    RETURN r
                    """,
                    {"event_id": event.id, "target_id": target_id}
                ))
        
        # Relationship to creator
        if created_by:
            queries.append((
                """
                MATCH (e:Event {id: $event_id}), (u:User {id: $user_id})
                MERGE (u)-[r:CREATES]->(e)
                RETURN r
                """,
                {"event_id": event.id, "user_id": created_by}
            ))
        
        # Execute relationship queries
        if queries:
            await self.execute_transaction(queries)
        
        return event
    
    async def get_events_by_target(self, target_type: str, target_id: str, 
                                  since_timestamp: Optional[str] = None) -> List[Event]:
        """
        Get events for a specific target since a given timestamp.
        
        Args:
            target_type: The target type (user, project, document, chat_session)
            target_id: The target ID
            since_timestamp: Optional timestamp to filter events (ISO format)
            
        Returns:
            List of events
        """
        if since_timestamp:
            query = """
            MATCH (t)-[:HAS_EVENT]->(e:Event)
            WHERE e.target_type = $target_type AND e.target_id = $target_id
            AND e.created_at > $since_timestamp
            RETURN e
            ORDER BY e.created_at ASC
            """
            params = {
                "target_type": target_type,
                "target_id": target_id,
                "since_timestamp": since_timestamp
            }
        else:
            query = """
            MATCH (t)-[:HAS_EVENT]->(e:Event)
            WHERE e.target_type = $target_type AND e.target_id = $target_id
            RETURN e
            ORDER BY e.created_at ASC
            """
            params = {
                "target_type": target_type,
                "target_id": target_id
            }
        
        try:
            result = await self.client.execute_query_async(query, params)
            return [self.map_to_entity(record['e']) for record in result]
        except Exception as e:
            logger.error(f"Error getting events by target: {str(e)}")
            raise
    
    async def get_events_by_type(self, event_type: str, 
                               since_timestamp: Optional[str] = None) -> List[Event]:
        """
        Get events of a specific type since a given timestamp.
        
        Args:
            event_type: The event type
            since_timestamp: Optional timestamp to filter events (ISO format)
            
        Returns:
            List of events
        """
        if since_timestamp:
            query = """
            MATCH (e:Event)
            WHERE e.type = $event_type AND e.created_at > $since_timestamp
            RETURN e
            ORDER BY e.created_at ASC
            """
            params = {
                "event_type": event_type,
                "since_timestamp": since_timestamp
            }
        else:
            query = """
            MATCH (e:Event)
            WHERE e.type = $event_type
            RETURN e
            ORDER BY e.created_at ASC
            """
            params = {
                "event_type": event_type
            }
        
        try:
            result = await self.client.execute_query_async(query, params)
            return [self.map_to_entity(record['e']) for record in result]
        except Exception as e:
            logger.error(f"Error getting events by type: {str(e)}")
            raise

# Create a singleton instance
event_repository = EventRepository()