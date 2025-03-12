"""
Server-Sent Events (SSE) service for real-time updates.
This module provides SSE connection management and event broadcasting.
"""
import asyncio
import json
import time
from typing import Dict, List, Set, Any, Optional, Callable, Awaitable
from fastapi import Request, Response
from sse_starlette.sse import EventSourceResponse
import uuid
from loguru import logger

class EventType:
    DOCUMENT_UPDATED = "document:updated"
    DOCUMENT_DIFF = "document:diff"
    FOLDER_UPDATED = "folder:updated"
    AI_TYPING = "ai:typing"
    AI_RESPONSE = "ai:response"
    TASK_STATUS = "task:status"
    AGENT_TASK_CREATED = "agent:task:created"
    AGENT_TASK_UPDATED = "agent:task:updated"
    AGENT_TASK_PROGRESS = "agent:task:progress"
    AGENT_TASK_COMPLETED = "agent:task:completed"
    AGENT_TASK_FAILED = "agent:task:failed"
    AGENT_QUESTION = "agent:question"
    AGENT_APPROVAL_REQUEST = "agent:approval:request"
    NOTIFICATION = "notification"
    CHAT_MESSAGE = "chat:message"
    CHAT_SESSION_STATUS = "chat:session:status"
    CHAT_PRIORITY_MESSAGE = "chat:priority:message"
    PING = "ping"
    PONG = "pong"


class SSEManager:
    """
    SSE connection manager for handling multiple client connections.
    """
    def __init__(self):
        # Map of connection_id to client queue
        self.active_connections: Dict[str, asyncio.Queue] = {}
        
        # Map of user_id to set of connection_ids
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Map of project_id to set of connection_ids
        self.project_connections: Dict[str, Set[str]] = {}
        
        # Map of document_id to set of connection_ids
        self.document_connections: Dict[str, Set[str]] = {}
        
        # Map of chat_session_id to set of connection_ids
        self.chat_session_connections: Dict[str, Set[str]] = {}
        
        # Map of connection_id to user_id
        self.connection_user: Dict[str, str] = {}
        
        # Map of connection_id to last activity timestamp
        self.connection_activity: Dict[str, float] = {}
        
        # Event history for replay (limited size per event type)
        self.event_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Maximum history size per event type
        self.max_history_size = 100
        
        # Ping interval in seconds
        self.ping_interval = 30
        
        # Background tasks
        self.background_tasks = set()
        
        # Connection cleanup task
        self.start_cleanup_task()
    
    def start_cleanup_task(self):
        """Start the background task to clean up stale connections"""
        task = asyncio.create_task(self.cleanup_stale_connections())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.remove)
    
    async def cleanup_stale_connections(self):
        """Periodically clean up stale connections that haven't been active"""
        while True:
            try:
                current_time = time.time()
                stale_connections = []
                
                # Find stale connections (inactive for more than 2 minutes)
                for conn_id, last_activity in self.connection_activity.items():
                    if current_time - last_activity > 120:  # 2 minutes
                        stale_connections.append(conn_id)
                
                # Clean up stale connections
                for conn_id in stale_connections:
                    logger.info(f"Cleaning up stale SSE connection: {conn_id}")
                    await self.disconnect(conn_id)
                
                # Sleep for a while before checking again
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in SSE cleanup task: {str(e)}")
                await asyncio.sleep(60)  # Sleep and retry
    
    async def connect(self, user_id: str) -> str:
        """
        Register a new SSE connection.
        
        Args:
            user_id: The ID of the authenticated user
            
        Returns:
            str: The connection ID
        """
        connection_id = str(uuid.uuid4())
        
        # Create a queue for this connection
        self.active_connections[connection_id] = asyncio.Queue()
        self.connection_user[connection_id] = user_id
        self.connection_activity[connection_id] = time.time()
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Send initial connection event
        await self.send_personal_message(
            connection_id,
            "connection:established",
            {
                "message": "Connected to SSE server",
                "connection_id": connection_id,
                "user_id": user_id
            }
        )
        
        logger.info(f"SSE client connected: {connection_id} (User: {user_id})")
        return connection_id
    
    async def disconnect(self, connection_id: str) -> None:
        """
        Handle disconnection of a client.
        
        Args:
            connection_id: The ID of the connection to disconnect
        """
        if connection_id not in self.active_connections:
            return
            
        # Get user_id before removing connection
        user_id = self.connection_user.get(connection_id)
        
        # Remove from active connections
        queue = self.active_connections.pop(connection_id, None)
        self.connection_user.pop(connection_id, None)
        self.connection_activity.pop(connection_id, None)
        
        # Close the queue
        if queue:
            await queue.put(None)  # Signal to stop the event generator
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                self.user_connections.pop(user_id)
        
        # Remove from project connections
        for project_id, connections in list(self.project_connections.items()):
            connections.discard(connection_id)
            if not connections:
                self.project_connections.pop(project_id)
        
        # Remove from document connections
        for document_id, connections in list(self.document_connections.items()):
            connections.discard(connection_id)
            if not connections:
                self.document_connections.pop(document_id)
        
        # Remove from chat session connections
        for session_id, connections in list(self.chat_session_connections.items()):
            connections.discard(connection_id)
            if not connections:
                self.chat_session_connections.pop(session_id)
        
        logger.info(f"SSE client disconnected: {connection_id} (User: {user_id})")
    
    async def subscribe_to_project(self, connection_id: str, project_id: str) -> None:
        """
        Subscribe a connection to events for a specific project.
        
        Args:
            connection_id: The connection ID
            project_id: The project ID to subscribe to
        """
        if connection_id not in self.active_connections:
            return
            
        if project_id not in self.project_connections:
            self.project_connections[project_id] = set()
        self.project_connections[project_id].add(connection_id)
        
        # Send confirmation
        await self.send_personal_message(
            connection_id,
            "subscription:success",
            {"type": "project", "id": project_id}
        )
        
        logger.debug(f"SSE connection {connection_id} subscribed to project {project_id}")
    
    async def subscribe_to_document(self, connection_id: str, document_id: str) -> None:
        """
        Subscribe a connection to events for a specific document.
        
        Args:
            connection_id: The connection ID
            document_id: The document ID to subscribe to
        """
        if connection_id not in self.active_connections:
            return
            
        if document_id not in self.document_connections:
            self.document_connections[document_id] = set()
        self.document_connections[document_id].add(connection_id)
        
        # Send confirmation
        await self.send_personal_message(
            connection_id,
            "subscription:success",
            {"type": "document", "id": document_id}
        )
        
        logger.debug(f"SSE connection {connection_id} subscribed to document {document_id}")
    
    async def subscribe_to_chat_session(self, connection_id: str, session_id: str) -> None:
        """
        Subscribe a connection to events for a specific chat session.
        
        Args:
            connection_id: The connection ID
            session_id: The chat session ID to subscribe to
        """
        if connection_id not in self.active_connections:
            return
            
        if session_id not in self.chat_session_connections:
            self.chat_session_connections[session_id] = set()
        self.chat_session_connections[session_id].add(connection_id)
        
        # Send confirmation
        await self.send_personal_message(
            connection_id,
            "subscription:success",
            {"type": "chat_session", "id": session_id}
        )
        
        logger.debug(f"SSE connection {connection_id} subscribed to chat session {session_id}")
    
    async def broadcast_to_user(self, user_id: str, event_type: str, data: Any) -> None:
        """
        Broadcast an event to all connections of a specific user.
        
        Args:
            user_id: The user ID to broadcast to
            event_type: The type of event
            data: The event data
        """
        if user_id not in self.user_connections:
            return
            
        connections = self.user_connections[user_id]
        await self._broadcast_to_connections(connections, event_type, data)
    
    async def broadcast_to_project(self, project_id: str, event_type: str, data: Any) -> None:
        """
        Broadcast an event to all connections subscribed to a specific project.
        
        Args:
            project_id: The project ID to broadcast to
            event_type: The type of event
            data: The event data
        """
        if project_id not in self.project_connections:
            return
            
        connections = self.project_connections[project_id]
        await self._broadcast_to_connections(connections, event_type, data)
    
    async def broadcast_to_document(self, document_id: str, event_type: str, data: Any) -> None:
        """
        Broadcast an event to all connections subscribed to a specific document.
        
        Args:
            document_id: The document ID to broadcast to
            event_type: The type of event
            data: The event data
        """
        if document_id not in self.document_connections:
            return
            
        connections = self.document_connections[document_id]
        await self._broadcast_to_connections(connections, event_type, data)
    
    async def broadcast_to_chat_session(self, session_id: str, event_type: str, data: Any) -> None:
        """
        Broadcast an event to all connections subscribed to a specific chat session.
        
        Args:
            session_id: The chat session ID to broadcast to
            event_type: The type of event
            data: The event data
        """
        if session_id not in self.chat_session_connections:
            return
            
        connections = self.chat_session_connections[session_id]
        await self._broadcast_to_connections(connections, event_type, data)
    
    async def broadcast_to_all(self, event_type: str, data: Any) -> None:
        """
        Broadcast an event to all active connections.
        
        Args:
            event_type: The type of event
            data: The event data
        """
        connections = set(self.active_connections.keys())
        await self._broadcast_to_connections(connections, event_type, data)
    
    async def send_personal_message(self, connection_id: str, event_type: str, data: Any) -> None:
        """
        Send a message to a specific connection.
        
        Args:
            connection_id: The connection ID to send to
            event_type: The type of event
            data: The event data
        """
        if connection_id not in self.active_connections:
            return
            
        queue = self.active_connections[connection_id]
        message = {
            "type": event_type,
            "data": data
        }
        
        try:
            await queue.put(message)
            self.connection_activity[connection_id] = time.time()
        except Exception as e:
            logger.error(f"Error sending SSE message to {connection_id}: {str(e)}")
            await self.disconnect(connection_id)
    
    async def _broadcast_to_connections(self, connections: Set[str], event_type: str, data: Any) -> None:
        """
        Broadcast an event to a set of connections.
        
        Args:
            connections: Set of connection IDs to broadcast to
            event_type: The type of event
            data: The event data
        """
        # Store in event history
        self._add_to_event_history(event_type, data)
        
        # Broadcast to active connections
        for connection_id in connections:
            await self.send_personal_message(connection_id, event_type, data)
    
    def _add_to_event_history(self, event_type: str, data: Any) -> None:
        """
        Add an event to the history for replay.
        
        Args:
            event_type: The type of event
            data: The event data
        """
        if event_type not in self.event_history:
            self.event_history[event_type] = []
            
        self.event_history[event_type].append({
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        })
        
        # Limit history size
        if len(self.event_history[event_type]) > self.max_history_size:
            self.event_history[event_type] = self.event_history[event_type][-self.max_history_size:]
    
    async def get_event_history(self, event_type: Optional[str] = None, since_timestamp: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Get event history for replay.
        
        Args:
            event_type: Optional event type to filter by
            since_timestamp: Optional timestamp to filter events after
            
        Returns:
            List of event history items
        """
        result = []
        
        if event_type:
            # Get history for specific event type
            if event_type in self.event_history:
                history = self.event_history[event_type]
                if since_timestamp:
                    history = [event for event in history if event["timestamp"] > since_timestamp]
                result.extend(history)
        else:
            # Get all history
            for events in self.event_history.values():
                if since_timestamp:
                    events = [event for event in events if event["timestamp"] > since_timestamp]
                result.extend(events)
                
        # Sort by timestamp
        result.sort(key=lambda x: x["timestamp"])
        return result
    
    async def event_generator(self, connection_id: str):
        """
        Generate SSE events for a specific connection.
        
        Args:
            connection_id: The connection ID
            
        Yields:
            SSE events
        """
        if connection_id not in self.active_connections:
            return
            
        queue = self.active_connections[connection_id]
        
        # Send ping every 30 seconds to keep connection alive
        ping_task = asyncio.create_task(self._ping_connection(connection_id))
        
        try:
            while True:
                # Wait for message from queue
                message = await queue.get()
                
                # None is the signal to stop
                if message is None:
                    break
                
                # Update activity timestamp
                self.connection_activity[connection_id] = time.time()
                
                # Yield the event
                event_data = json.dumps(message)
                yield {
                    "event": message["type"],
                    "data": event_data
                }
        except asyncio.CancelledError:
            # Connection was closed
            logger.info(f"SSE connection {connection_id} cancelled")
        except Exception as e:
            logger.error(f"Error in SSE event generator for {connection_id}: {str(e)}")
        finally:
            # Clean up
            ping_task.cancel()
            await self.disconnect(connection_id)
    
    async def _ping_connection(self, connection_id: str) -> None:
        """
        Send periodic pings to keep the connection alive.
        
        Args:
            connection_id: The connection ID to ping
        """
        try:
            while connection_id in self.active_connections:
                await asyncio.sleep(self.ping_interval)
                
                if connection_id not in self.active_connections:
                    break
                
                # Send ping
                await self.send_personal_message(
                    connection_id,
                    EventType.PING,
                    {"timestamp": time.time()}
                )
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            pass
        except Exception as e:
            logger.error(f"Error in SSE ping task for {connection_id}: {str(e)}")
            await self.disconnect(connection_id)


# Create a singleton instance
sse_manager = SSEManager()