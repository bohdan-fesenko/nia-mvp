"""
WebSocket service for real-time updates.
This module provides WebSocket connection management and event broadcasting.
"""
import asyncio
import json
from typing import Dict, List, Set, Any, Optional, Callable, Awaitable
from fastapi import WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
import uuid
from loguru import logger

# Event types
class EventType:
    DOCUMENT_UPDATED = "document:updated"
    DOCUMENT_DIFF = "document:diff"  # New event type for document diffs
    FOLDER_UPDATED = "folder:updated"
    AI_TYPING = "ai:typing"
    AI_RESPONSE = "ai:response"
    TASK_STATUS = "task:status"
    AGENT_TASK_CREATED = "agent:task:created"
    AGENT_TASK_UPDATED = "agent:task:updated"
    AGENT_TASK_PROGRESS = "agent:task:progress"
    AGENT_TASK_COMPLETED = "agent:task:completed"
    AGENT_TASK_FAILED = "agent:task:failed"
    AGENT_QUESTION = "agent:question"  # New event type for agent questions
    AGENT_APPROVAL_REQUEST = "agent:approval:request"  # New event type for approval requests
    NOTIFICATION = "notification"
    CHAT_MESSAGE = "chat:message"
    CHAT_SESSION_STATUS = "chat:session:status"
    CHAT_PRIORITY_MESSAGE = "chat:priority:message"  # New event type for priority messages
    PING = "ping"
    PONG = "pong"


class ConnectionManager:
    """
    WebSocket connection manager for handling multiple client connections.
    """
    def __init__(self):
        # Map of connection_id to WebSocket instance
        self.active_connections: Dict[str, WebSocket] = {}
        
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
        
        # Map of connection_id to missed events queue
        self.missed_events: Dict[str, List[Dict[str, Any]]] = {}
        
        # Event history for replay (limited size per event type)
        self.event_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Maximum history size per event type
        self.max_history_size = 100
        
        # Ping interval in seconds
        self.ping_interval = 30
        
        # Background tasks
        self.background_tasks = set()

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """
        Accept a new WebSocket connection and register it.
        
        Args:
            websocket: The WebSocket connection
            user_id: The ID of the authenticated user
            
        Returns:
            str: The connection ID
        """
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        
        self.active_connections[connection_id] = websocket
        self.connection_user[connection_id] = user_id
        self.connection_activity[connection_id] = asyncio.get_event_loop().time()
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Initialize missed events queue
        self.missed_events[connection_id] = []
        
        # Start ping task
        task = asyncio.create_task(self._ping_connection(connection_id))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.remove)
        
        logger.info(f"Client connected: {connection_id} (User: {user_id})")
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
        websocket = self.active_connections.pop(connection_id, None)
        self.connection_user.pop(connection_id, None)
        self.connection_activity.pop(connection_id, None)
        
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
        
        # Keep missed events for reconnection
        # They will be cleaned up after a timeout or delivered on reconnection
        
        logger.info(f"Client disconnected: {connection_id} (User: {user_id})")

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
        
        logger.debug(f"Connection {connection_id} subscribed to project {project_id}")

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
        
        logger.debug(f"Connection {connection_id} subscribed to document {document_id}")

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
        
        logger.debug(f"Connection {connection_id} subscribed to chat session {session_id}")

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
            # Queue message for when the client reconnects
            if connection_id in self.missed_events:
                self.missed_events[connection_id].append({
                    "type": event_type,
                    "data": data
                })
            return
            
        websocket = self.active_connections[connection_id]
        message = {
            "type": event_type,
            "data": data
        }
        
        try:
            await websocket.send_json(message)
            self.connection_activity[connection_id] = asyncio.get_event_loop().time()
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {str(e)}")
            try:
                await self.disconnect(connection_id)
            except Exception as disconnect_error:
                logger.error(f"Error disconnecting: {str(disconnect_error)}")

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
            "timestamp": asyncio.get_event_loop().time()
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

    async def process_missed_events(self, connection_id: str) -> None:
        """
        Process missed events for a connection.
        
        Args:
            connection_id: The connection ID to process missed events for
        """
        if connection_id not in self.missed_events or connection_id not in self.active_connections:
            return
            
        events = self.missed_events[connection_id]
        if not events:
            return
            
        websocket = self.active_connections[connection_id]
        
        for event in events:
            try:
                await websocket.send_json(event)
            except Exception as e:
                logger.error(f"Error sending missed event to {connection_id}: {str(e)}")
                try:
                    await self.disconnect(connection_id)
                except Exception as disconnect_error:
                    logger.error(f"Error disconnecting: {str(disconnect_error)}")
                return
                
        # Clear missed events
        self.missed_events[connection_id] = []
        logger.debug(f"Processed {len(events)} missed events for connection {connection_id}")

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
                    
                # Check if connection is still active
                last_activity = self.connection_activity.get(connection_id, 0)
                current_time = asyncio.get_event_loop().time()
                
                # If no activity for 2 ping intervals, disconnect
                if current_time - last_activity > self.ping_interval * 2:
                    logger.warning(f"Connection {connection_id} timed out")
                    await self.disconnect(connection_id)
                    break
                
                # Send ping
                await self.send_personal_message(connection_id, EventType.PING, {"timestamp": current_time})
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            if connection_id in self.active_connections:
                try:
                    await self.disconnect(connection_id)
                except Exception as disconnect_error:
                    logger.error(f"Error disconnecting: {str(disconnect_error)}")
        except Exception as e:
            logger.error(f"Error in ping task for {connection_id}: {str(e)}")
            if connection_id in self.active_connections:
                try:
                    await self.disconnect(connection_id)
                except Exception as disconnect_error:
                    logger.error(f"Error disconnecting: {str(disconnect_error)}")


# Create a singleton instance
connection_manager = ConnectionManager()