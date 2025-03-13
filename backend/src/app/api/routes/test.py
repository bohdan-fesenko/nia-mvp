"""
Test API routes.
This module provides API routes for testing purposes.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, Optional

from ...db.models import EventCreate, EventResponse
from ...repositories.event_repository import event_repository
from ...utils.auth import get_current_user

router = APIRouter()

@router.post("/test/create-event", response_model=EventResponse)
async def create_test_event(
    event_data: Dict[str, Any] = Body(...),
    current_user = Depends(get_current_user)
):
    """
    Create a test event.
    This endpoint is for testing purposes only.
    
    Args:
        event_data: Event data containing type, data, target_type, and target_id
        
    Returns:
        The created event
    """
    try:
        event_type = event_data.get("type")
        data = event_data.get("data", {})
        target_type = event_data.get("target_type")
        target_id = event_data.get("target_id")
        
        if not event_type:
            raise HTTPException(status_code=400, detail="Event type is required")
            
        event = await event_repository.create_event(
            event_type=event_type,
            data=data,
            target_type=target_type,
            target_id=target_id,
            created_by=current_user.id
        )
        
        return event
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating test event: {str(e)}")