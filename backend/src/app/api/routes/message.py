"""
Message routes for client-to-server communication.
This module provides endpoints for sending messages from client to server.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from ...utils.auth import get_current_user
from ...services.event_service import event_publisher

router = APIRouter()

class MessageRequest(BaseModel):
    """
    Message request model.
    """
    type: str
    data: Dict[str, Any]

@router.post("/message")
async def send_message(
    message: MessageRequest,
    user_data: Dict = Depends(get_current_user)
):
    """
    Send a message from client to server.
    
    This endpoint handles generic messages that don't have specific endpoints.
    """
    try:
        # Get user ID
        user_id = user_data.get("sub") or user_data.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found"
            )
        
        # Process message based on type
        message_type = message.type
        data = message.data
        
        # Add user ID to data
        data["user_id"] = user_id
        
        # Handle different message types
        if message_type == "ping":
            # Respond to ping
            return {"type": "pong", "data": {"timestamp": data.get("timestamp")}}
        
        # For other message types, publish to event service
        await event_publisher.publish(message_type, data)
        
        return {"status": "success", "message": f"Message of type {message_type} sent"}
    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )