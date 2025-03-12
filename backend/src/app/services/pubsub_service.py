"""
Pub/Sub service for the application.
This module provides a service for real-time communication using Redis pub/sub.
"""
import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable, Set
import threading
from datetime import datetime

from ..config import settings
from ..db.redis_client import redis_client

logger = logging.getLogger(__name__)


class PubSubService:
    """
    Pub/Sub service for real-time communication.
    """
    def __init__(self):
        """
        Initialize the pub/sub service.
        """
        self._client = redis_client
        self._channels = settings.PUBSUB_CHANNELS
        self._subscribers: Dict[str, Set[Callable[[str, Any], None]]] = {}
        self._async_subscribers: Dict[str, Set[Callable[[str, Any], None]]] = {}
        self._pubsub = None
        self._async_pubsub = None
        self._listener_thread = None
        self._async_listener_task = None
        self._running = False
        self._async_running = False

    def get_channel(self, channel_name: str) -> str:
        """
        Get the full channel name.
        
        Args:
            channel_name: The channel name.
            
        Returns:
            The full channel name.
        """
        return self._channels.get(channel_name, channel_name)

    async def start(self):
        """
        Start the pub/sub service.
        """
        # Start the sync listener in a separate thread
        self._start_sync_listener()
        
        # Start the async listener
        await self._start_async_listener()
        
        logger.info("PubSub service started")

    async def stop(self):
        """
        Stop the pub/sub service.
        """
        # Stop the sync listener
        self._stop_sync_listener()
        
        # Stop the async listener
        await self._stop_async_listener()
        
        logger.info("PubSub service stopped")

    def _start_sync_listener(self):
        """
        Start the synchronous listener thread.
        """
        if self._listener_thread is not None and self._listener_thread.is_alive():
            return
        
        self._running = True
        self._listener_thread = threading.Thread(target=self._sync_listener_loop)
        self._listener_thread.daemon = True
        self._listener_thread.start()

    def _stop_sync_listener(self):
        """
        Stop the synchronous listener thread.
        """
        self._running = False
        if self._listener_thread is not None:
            self._listener_thread.join(timeout=1.0)
            self._listener_thread = None
        
        if self._pubsub is not None:
            self._pubsub.close()
            self._pubsub = None

    async def _start_async_listener(self):
        """
        Start the asynchronous listener task.
        """
        if self._async_listener_task is not None and not self._async_listener_task.done():
            return
        
        self._async_running = True
        self._async_listener_task = asyncio.create_task(self._async_listener_loop())

    async def _stop_async_listener(self):
        """
        Stop the asynchronous listener task.
        """
        self._async_running = False
        if self._async_listener_task is not None:
            self._async_listener_task.cancel()
            try:
                await self._async_listener_task
            except asyncio.CancelledError:
                pass
            self._async_listener_task = None
        
        if self._async_pubsub is not None:
            await self._async_pubsub.close()
            self._async_pubsub = None

    def _sync_listener_loop(self):
        """
        Synchronous listener loop.
        """
        try:
            self._client.connect()
            self._pubsub = self._client._client.pubsub()
            
            # Subscribe to all channels with subscribers
            for channel in self._subscribers.keys():
                self._pubsub.subscribe(channel)
            
            # Listen for messages
            while self._running:
                message = self._pubsub.get_message(timeout=0.1)
                if message and message['type'] == 'message':
                    channel = message['channel']
                    if isinstance(channel, bytes):
                        channel = channel.decode('utf-8')
                    
                    data = message['data']
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    
                    # Try to parse as JSON
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        pass
                    
                    # Notify subscribers
                    if channel in self._subscribers:
                        for callback in self._subscribers[channel]:
                            try:
                                callback(channel, data)
                            except Exception as e:
                                logger.error(f"Error in subscriber callback for channel {channel}: {str(e)}")
        except Exception as e:
            logger.error(f"Error in sync listener loop: {str(e)}")
            if self._running:
                # Restart the listener
                self._start_sync_listener()

    async def _async_listener_loop(self):
        """
        Asynchronous listener loop.
        """
        try:
            await self._client.connect_async()
            self._async_pubsub = await self._client._async_client.pubsub()
            
            # Subscribe to all channels with subscribers
            for channel in self._async_subscribers.keys():
                await self._async_pubsub.subscribe(channel)
            
            # Listen for messages
            while self._async_running:
                message = await self._async_pubsub.get_message(timeout=0.1)
                if message and message['type'] == 'message':
                    channel = message['channel']
                    if isinstance(channel, bytes):
                        channel = channel.decode('utf-8')
                    
                    data = message['data']
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    
                    # Try to parse as JSON
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        pass
                    
                    # Notify subscribers
                    if channel in self._async_subscribers:
                        for callback in self._async_subscribers[channel]:
                            try:
                                await callback(channel, data)
                            except Exception as e:
                                logger.error(f"Error in async subscriber callback for channel {channel}: {str(e)}")
                
                # Small delay to prevent CPU hogging
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Error in async listener loop: {str(e)}")
            if self._async_running:
                # Restart the listener
                await self._start_async_listener()

    def publish(self, channel_name: str, message: Any) -> int:
        """
        Publish a message to a channel.
        
        Args:
            channel_name: The channel name.
            message: The message to publish.
            
        Returns:
            The number of subscribers that received the message.
        """
        channel = self.get_channel(channel_name)
        
        # Convert message to JSON if it's not a string
        if not isinstance(message, str):
            message = json.dumps(message)
        
        return self._client.publish(channel, message)

    async def publish_async(self, channel_name: str, message: Any) -> int:
        """
        Publish a message to a channel asynchronously.
        
        Args:
            channel_name: The channel name.
            message: The message to publish.
            
        Returns:
            The number of subscribers that received the message.
        """
        channel = self.get_channel(channel_name)
        
        # Convert message to JSON if it's not a string
        if not isinstance(message, str):
            message = json.dumps(message)
        
        return await self._client.publish_async(channel, message)

    def subscribe(self, channel_name: str, callback: Callable[[str, Any], None]) -> bool:
        """
        Subscribe to a channel.
        
        Args:
            channel_name: The channel name.
            callback: The callback function to call when a message is received.
                     The callback takes two arguments: channel and message.
            
        Returns:
            True if the subscription was successful, False otherwise.
        """
        channel = self.get_channel(channel_name)
        
        # Add the callback to the subscribers
        if channel not in self._subscribers:
            self._subscribers[channel] = set()
        
        self._subscribers[channel].add(callback)
        
        # Subscribe to the channel if we have a pubsub connection
        if self._pubsub is not None:
            self._pubsub.subscribe(channel)
        
        return True

    async def subscribe_async(self, channel_name: str, callback: Callable[[str, Any], None]) -> bool:
        """
        Subscribe to a channel asynchronously.
        
        Args:
            channel_name: The channel name.
            callback: The callback function to call when a message is received.
                     The callback takes two arguments: channel and message.
            
        Returns:
            True if the subscription was successful, False otherwise.
        """
        channel = self.get_channel(channel_name)
        
        # Add the callback to the subscribers
        if channel not in self._async_subscribers:
            self._async_subscribers[channel] = set()
        
        self._async_subscribers[channel].add(callback)
        
        # Subscribe to the channel if we have a pubsub connection
        if self._async_pubsub is not None:
            await self._async_pubsub.subscribe(channel)
        
        return True

    def unsubscribe(self, channel_name: str, callback: Callable[[str, Any], None]) -> bool:
        """
        Unsubscribe from a channel.
        
        Args:
            channel_name: The channel name.
            callback: The callback function to remove.
            
        Returns:
            True if the unsubscription was successful, False otherwise.
        """
        channel = self.get_channel(channel_name)
        
        # Remove the callback from the subscribers
        if channel in self._subscribers and callback in self._subscribers[channel]:
            self._subscribers[channel].remove(callback)
            
            # If there are no more subscribers, unsubscribe from the channel
            if not self._subscribers[channel]:
                if self._pubsub is not None:
                    self._pubsub.unsubscribe(channel)
                del self._subscribers[channel]
        
        return True

    async def unsubscribe_async(self, channel_name: str, callback: Callable[[str, Any], None]) -> bool:
        """
        Unsubscribe from a channel asynchronously.
        
        Args:
            channel_name: The channel name.
            callback: The callback function to remove.
            
        Returns:
            True if the unsubscription was successful, False otherwise.
        """
        channel = self.get_channel(channel_name)
        
        # Remove the callback from the subscribers
        if channel in self._async_subscribers and callback in self._async_subscribers[channel]:
            self._async_subscribers[channel].remove(callback)
            
            # If there are no more subscribers, unsubscribe from the channel
            if not self._async_subscribers[channel]:
                if self._async_pubsub is not None:
                    await self._async_pubsub.unsubscribe(channel)
                del self._async_subscribers[channel]
        
        return True

    def unsubscribe_all(self, channel_name: str) -> bool:
        """
        Unsubscribe all callbacks from a channel.
        
        Args:
            channel_name: The channel name.
            
        Returns:
            True if the unsubscription was successful, False otherwise.
        """
        channel = self.get_channel(channel_name)
        
        # Remove all callbacks from the subscribers
        if channel in self._subscribers:
            if self._pubsub is not None:
                self._pubsub.unsubscribe(channel)
            del self._subscribers[channel]
        
        return True

    async def unsubscribe_all_async(self, channel_name: str) -> bool:
        """
        Unsubscribe all callbacks from a channel asynchronously.
        
        Args:
            channel_name: The channel name.
            
        Returns:
            True if the unsubscription was successful, False otherwise.
        """
        channel = self.get_channel(channel_name)
        
        # Remove all callbacks from the subscribers
        if channel in self._async_subscribers:
            if self._async_pubsub is not None:
                await self._async_pubsub.unsubscribe(channel)
            del self._async_subscribers[channel]
        
        return True

    # ==================== Specific Channel Methods ====================

    async def publish_document_update(self, document_id: str, update_type: str, data: Any) -> int:
        """
        Publish a document update.
        
        Args:
            document_id: The ID of the document.
            update_type: The type of update (e.g., 'created', 'updated', 'deleted').
            data: The update data.
            
        Returns:
            The number of subscribers that received the message.
        """
        message = {
            'document_id': document_id,
            'update_type': update_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return await self.publish_async('document_updates', message)

    async def publish_project_update(self, project_id: str, update_type: str, data: Any) -> int:
        """
        Publish a project update.
        
        Args:
            project_id: The ID of the project.
            update_type: The type of update (e.g., 'created', 'updated', 'deleted').
            data: The update data.
            
        Returns:
            The number of subscribers that received the message.
        """
        message = {
            'project_id': project_id,
            'update_type': update_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return await self.publish_async('project_updates', message)

    async def publish_agent_task(self, task_id: str, task_type: str, data: Any) -> int:
        """
        Publish an agent task.
        
        Args:
            task_id: The ID of the task.
            task_type: The type of task.
            data: The task data.
            
        Returns:
            The number of subscribers that received the message.
        """
        message = {
            'task_id': task_id,
            'task_type': task_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return await self.publish_async('agent_tasks', message)

    async def publish_notification(self, user_id: str, notification_type: str, data: Any) -> int:
        """
        Publish a notification.
        
        Args:
            user_id: The ID of the user.
            notification_type: The type of notification.
            data: The notification data.
            
        Returns:
            The number of subscribers that received the message.
        """
        message = {
            'user_id': user_id,
            'notification_type': notification_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return await self.publish_async('notifications', message)

    async def publish_system_event(self, event_type: str, data: Any) -> int:
        """
        Publish a system event.
        
        Args:
            event_type: The type of event.
            data: The event data.
            
        Returns:
            The number of subscribers that received the message.
        """
        message = {
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return await self.publish_async('system_events', message)


# Create a singleton instance
pubsub_service = PubSubService()

# Create a factory function for the service
def create_pubsub_service(redis_client) -> PubSubService:
    """
    Create a pub/sub service.
    
    Args:
        redis_client: Redis client
        
    Returns:
        A pub/sub service
    """
    # We're using a singleton pattern, so just return the existing instance
    # In a real implementation, you might create a new instance with the provided client
    return pubsub_service