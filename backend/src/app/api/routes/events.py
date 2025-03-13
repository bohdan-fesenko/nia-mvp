"""
Events API routes.
This module provides API routes for polling events.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from ...db.models import EventResponse
from ...repositories.event_repository import event_repository
from ...utils.auth import get_current_user

router = APIRouter()

@router.get("/events/poll", response_model=List[EventResponse])
async def poll_events(
    target_type: str,
    target_id: str,
    since: Optional[str] = Query(None, description="ISO format timestamp to get events since"),
    current_user = Depends(get_current_user)
):
    """
    Poll for events for a specific target since a given timestamp.
    
    Args:
        target_type: The target type (user, project, document, chat_session)
        target_id: The target ID
        since: Optional timestamp to filter events (ISO format)
        
    Returns:
        List of events
    """
    try:
        events = await event_repository.get_events_by_target(
            target_type=target_type,
            target_id=target_id,
            since_timestamp=since
        )
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error polling events: {str(e)}")

@router.get("/events/type/{event_type}", response_model=List[EventResponse])
async def get_events_by_type(
    event_type: str,
    since: Optional[str] = Query(None, description="ISO format timestamp to get events since"),
    current_user = Depends(get_current_user)
):
    """
    Get events of a specific type since a given timestamp.
    
    Args:
        event_type: The event type
        since: Optional timestamp to filter events (ISO format)
        
    Returns:
        List of events
    """
    try:
        events = await event_repository.get_events_by_type(
            event_type=event_type,
            since_timestamp=since
        )
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting events by type: {str(e)}")

@router.get("/events/user", response_model=List[EventResponse])
async def get_user_events(
    since: Optional[str] = Query(None, description="ISO format timestamp to get events since"),
    current_user = Depends(get_current_user)
):
    """
    Get events for the current user since a given timestamp.
    
    Args:
        since: Optional timestamp to filter events (ISO format)
        
    Returns:
        List of events
    """
    try:
        events = await event_repository.get_events_by_target(
            target_type="user",
            target_id=current_user.id,
            since_timestamp=since
        )
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user events: {str(e)}")