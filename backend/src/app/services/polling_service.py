"""
Polling service for timestamp-based updates.
This module provides event types for polling-based updates.
"""

class EventType:
    """
    Event types for polling-based updates.
    These are used to identify the type of event in the polling API.
    """
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

# Export the event types
event_types = EventType