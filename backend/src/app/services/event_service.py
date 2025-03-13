"""
Event service for publishing events.
This module provides a centralized way to publish events to clients via polling.
"""
import asyncio
import json
from typing import Dict, Any, Optional, List, Set, Union
from enum import Enum, auto
from pydantic import BaseModel, Field
from loguru import logger
from datetime import datetime

from .polling_service import EventType
from .diff_service import diff_service
from ..repositories.event_repository import event_repository

class EventPriority(Enum):
    """
    Priority levels for events.
    """
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class EventPublisher:
    """
    Event publisher for broadcasting events to clients.
    """
    def __init__(self):
        # Queue for events to be published
        self._event_queue: asyncio.Queue = asyncio.Queue()
        
        # Flag to indicate if the publisher is running
        self._running = False
        
        # Background task for processing events
        self._task = None
        
        # Event handlers for different event types
        self._event_handlers = {}
        
        # Event filters for different event types
        self._event_filters = {}

    async def start(self):
        """
        Start the event publisher.
        """
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._process_events())
        logger.success("Event publisher started")

    async def stop(self):
        """
        Stop the event publisher.
        """
        if not self._running:
            return
            
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.success("Event publisher stopped")

    async def publish(
        self, 
        event_type: str, 
        data: Any, 
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        priority: EventPriority = EventPriority.MEDIUM
    ):
        """
        Publish an event to clients.
        
        Args:
            event_type: The type of event
            data: The event data
            target_type: Optional target type (user, project, document, chat_session)
            target_id: Optional target ID
            priority: Event priority
        """
        event = {
            "type": event_type,
            "data": data,
            "target_type": target_type,
            "target_id": target_id,
            "priority": priority
        }
        
        await self._event_queue.put(event)

    async def publish_document_updated(self, document_id: str, data: Dict[str, Any]):
        """
        Publish a document updated event.
        
        Args:
            document_id: The document ID
            data: The event data
        """
        await self.publish(
            EventType.DOCUMENT_UPDATED,
            data,
            target_type="document",
            target_id=document_id,
            priority=EventPriority.MEDIUM
        )

    async def publish_folder_updated(self, folder_id: str, data: Dict[str, Any]):
        """
        Publish a folder updated event.
        
        Args:
            folder_id: The folder ID
            data: The event data
        """
        await self.publish(
            EventType.FOLDER_UPDATED,
            data,
            target_type="folder",
            target_id=folder_id,
            priority=EventPriority.MEDIUM
        )

    async def publish_ai_typing(self, session_id: str, data: Dict[str, Any]):
        """
        Publish an AI typing event.
        
        Args:
            session_id: The chat session ID
            data: The event data
        """
        await self.publish(
            EventType.AI_TYPING,
            data,
            target_type="chat_session",
            target_id=session_id,
            priority=EventPriority.LOW
        )

    async def publish_ai_response(self, session_id: str, data: Dict[str, Any]):
        """
        Publish an AI response event.
        
        Args:
            session_id: The chat session ID
            data: The event data
        """
        await self.publish(
            EventType.AI_RESPONSE,
            data,
            target_type="chat_session",
            target_id=session_id,
            priority=EventPriority.MEDIUM
        )

    async def publish_task_status(self, task_id: str, data: Dict[str, Any]):
        """
        Publish a task status event.
        
        Args:
            task_id: The task ID
            data: The event data
        """
        await self.publish(
            EventType.TASK_STATUS,
            data,
            target_type="task",
            target_id=task_id,
            priority=EventPriority.MEDIUM
        )

    async def publish_agent_task_created(self, task_id: str, data: Dict[str, Any]):
        """
        Publish an agent task created event.
        
        Args:
            task_id: The task ID
            data: The event data
        """
        await self.publish(
            EventType.AGENT_TASK_CREATED,
            data,
            target_type="task",
            target_id=task_id,
            priority=EventPriority.MEDIUM
        )

    async def publish_agent_task_updated(self, task_id: str, data: Dict[str, Any]):
        """
        Publish an agent task updated event.
        
        Args:
            task_id: The task ID
            data: The event data
        """
        await self.publish(
            EventType.AGENT_TASK_UPDATED,
            data,
            target_type="task",
            target_id=task_id,
            priority=EventPriority.MEDIUM
        )

    async def publish_agent_task_progress(self, task_id: str, data: Dict[str, Any]):
        """
        Publish an agent task progress event.
        
        Args:
            task_id: The task ID
            data: The event data
        """
        await self.publish(
            EventType.AGENT_TASK_PROGRESS,
            data,
            target_type="task",
            target_id=task_id,
            priority=EventPriority.LOW
        )

    async def publish_agent_task_completed(self, task_id: str, data: Dict[str, Any]):
        """
        Publish an agent task completed event.
        
        Args:
            task_id: The task ID
            data: The event data
        """
        await self.publish(
            EventType.AGENT_TASK_COMPLETED,
            data,
            target_type="task",
            target_id=task_id,
            priority=EventPriority.HIGH
        )

    async def publish_agent_task_failed(self, task_id: str, data: Dict[str, Any]):
        """
        Publish an agent task failed event.
        
        Args:
            task_id: The task ID
            data: The event data
        """
        await self.publish(
            EventType.AGENT_TASK_FAILED,
            data,
            target_type="task",
            target_id=task_id,
            priority=EventPriority.HIGH
        )

    async def publish_notification(self, user_id: str, data: Dict[str, Any]):
        """
        Publish a notification event.
        
        Args:
            user_id: The user ID
            data: The event data
        """
        await self.publish(
            EventType.NOTIFICATION,
            data,
            target_type="user",
            target_id=user_id,
            priority=EventPriority.HIGH
        )

    async def publish_chat_message(self, session_id: str, data: Dict[str, Any]):
        """
        Publish a chat message event.
        
        Args:
            session_id: The chat session ID
            data: The event data
        """
        await self.publish(
            EventType.CHAT_MESSAGE,
            data,
            target_type="chat_session",
            target_id=session_id,
            priority=EventPriority.MEDIUM
        )

    async def publish_chat_session_status(self, session_id: str, data: Dict[str, Any]):
        """
        Publish a chat session status event.
        
        Args:
            session_id: The chat session ID
            data: The event data
        """
        await self.publish(
            EventType.CHAT_SESSION_STATUS,
            data,
            target_type="chat_session",
            target_id=session_id,
            priority=EventPriority.MEDIUM
        )
        
    async def publish_document_diff(self, document_id: str, old_version: Dict[str, Any], new_version: Dict[str, Any]):
        """
        Publish a document diff event.
        
        Args:
            document_id: The document ID
            old_version: The old document version
            new_version: The new document version
        """
        # Generate diff
        diff_data = diff_service.generate_document_diff(old_version, new_version)
        
        # Generate summary
        summary = diff_service.generate_summary(diff_data.get("text_diff", {}))
        
        # Create event data
        data = {
            "id": document_id,
            "diff": diff_data,
            "summary": summary,
            "old_version": old_version.get("version_number"),
            "new_version": new_version.get("version_number"),
            "timestamp": new_version.get("created_at")
        }
        
        # Publish diff event
        await self.publish(
            EventType.DOCUMENT_DIFF,
            data,
            target_type="document",
            target_id=document_id,
            priority=EventPriority.MEDIUM
        )
        
        # Also publish as a notification with summary
        notification_data = {
            "type": "document_diff",
            "document_id": document_id,
            "document_name": new_version.get("name", ""),
            "summary": summary,
            "timestamp": new_version.get("created_at"),
            "user_id": new_version.get("created_by")
        }
        
        await self.publish(
            EventType.NOTIFICATION,
            notification_data,
            target_type="user",
            target_id=new_version.get("created_by"),
            priority=EventPriority.MEDIUM
        )
    
    async def publish_chat_priority_message(self, session_id: str, data: Dict[str, Any], priority: EventPriority = EventPriority.HIGH):
        """
        Publish a priority chat message event.
        
        Args:
            session_id: The chat session ID
            data: The event data
            priority: The event priority (default: HIGH)
        """
        await self.publish(
            EventType.CHAT_PRIORITY_MESSAGE,
            data,
            target_type="chat_session",
            target_id=session_id,
            priority=priority
        )
    
    async def publish_agent_question(self, session_id: str, data: Dict[str, Any]):
        """
        Publish an agent question event.
        
        Args:
            session_id: The chat session ID
            data: The event data
        """
        await self.publish(
            EventType.AGENT_QUESTION,
            data,
            target_type="chat_session",
            target_id=session_id,
            priority=EventPriority.HIGH
        )
        
        # Also publish as a notification
        notification_data = {
            "type": "agent_question",
            "session_id": session_id,
            "question": data.get("question", ""),
            "context": data.get("context", {}),
            "timestamp": data.get("timestamp"),
            "user_id": data.get("user_id")
        }
        
        await self.publish(
            EventType.NOTIFICATION,
            notification_data,
            target_type="user",
            target_id=data.get("user_id"),
            priority=EventPriority.HIGH
        )
    
    async def publish_agent_approval_request(self, session_id: str, data: Dict[str, Any]):
        """
        Publish an agent approval request event.
        
        Args:
            session_id: The chat session ID
            data: The event data
        """
        await self.publish(
            EventType.AGENT_APPROVAL_REQUEST,
            data,
            target_type="chat_session",
            target_id=session_id,
            priority=EventPriority.HIGH
        )
        
        # Also publish as a notification
        notification_data = {
            "type": "agent_approval_request",
            "session_id": session_id,
            "request": data.get("request", ""),
            "context": data.get("context", {}),
            "options": data.get("options", []),
            "timestamp": data.get("timestamp"),
            "user_id": data.get("user_id")
        }
        
        await self.publish(
            EventType.NOTIFICATION,
            notification_data,
            target_type="user",
            target_id=data.get("user_id"),
            priority=EventPriority.HIGH
        )

    def register_event_handler(self, event_type: str, handler):
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: The event type to handle
            handler: The handler function
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def register_event_filter(self, event_type: str, filter_func):
        """
        Register a filter for a specific event type.
        
        Args:
            event_type: The event type to filter
            filter_func: The filter function
        """
        if event_type not in self._event_filters:
            self._event_filters[event_type] = []
        self._event_filters[event_type].append(filter_func)

    async def _process_events(self):
        """
        Process events from the queue.
        Store events in Neo4j for polling.
        """
        try:
            while self._running:
                # Get event from queue
                event = await self._event_queue.get()
                
                try:
                    # Extract event details
                    event_type = event["type"]
                    data = event["data"]
                    target_type = event["target_type"]
                    target_id = event["target_id"]
                    priority = event["priority"]
                    created_by = data.get("user_id") if isinstance(data, dict) else None
                    
                    # Apply filters
                    if event_type in self._event_filters:
                        should_process = True
                        for filter_func in self._event_filters[event_type]:
                            if not await filter_func(event):
                                should_process = False
                                break
                                
                        if not should_process:
                            self._event_queue.task_done()
                            continue
                    
                    # Call event handlers
                    if event_type in self._event_handlers:
                        for handler in self._event_handlers[event_type]:
                            try:
                                await handler(event)
                            except Exception as e:
                                logger.error(f"Error in event handler for {event_type}: {str(e)}")
                                logger.exception("Handler exception details:")
                    
                    # Store event in Neo4j using the event repository
                    try:
                        await event_repository.create_event(
                            event_type=event_type,
                            data=data,
                            target_type=target_type,
                            target_id=target_id,
                            created_by=created_by
                        )
                        logger.info(f"Event stored in Neo4j: {event_type} for {target_type}:{target_id}")
                    except Exception as e:
                        logger.error(f"Error storing event in Neo4j: {str(e)}")
                        logger.exception("Event storage exception details:")
                    
                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")
                    logger.exception("Event processing exception details:")
                
                finally:
                    # Mark event as processed
                    self._event_queue.task_done()
        
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            logger.warning("Event processing task cancelled")
        
        except Exception as e:
            logger.error(f"Error in event processing loop: {str(e)}")
            logger.exception("Event processing loop exception details:")
            # Restart the task if it fails
            if self._running:
                self._task = asyncio.create_task(self._process_events())


# Create a singleton instance
event_publisher = EventPublisher()

# Export the event_publisher as event_service for backward compatibility
event_service = event_publisher