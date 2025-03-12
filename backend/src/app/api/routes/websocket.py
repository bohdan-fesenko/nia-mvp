"""
WebSocket routes for real-time updates.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import json
import asyncio
from loguru import logger

from ...services.websocket_service import connection_manager, EventType
from ...utils.auth import decode_jwt_token, get_current_user

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_token_from_query(
    token: Optional[str] = Query(None)
) -> Optional[str]:
    """
    Extract token from query parameters for WebSocket authentication.
    """
    return token

async def get_websocket_user(websocket: WebSocket):
    """
    Authenticate user from WebSocket connection.
    
    Args:
        websocket: The WebSocket connection
        
    Returns:
        dict: User information
    
    Raises:
        WebSocketDisconnect: If authentication fails
    """
    try:
        # Try to get token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            # Try to get token from cookies
            token = websocket.cookies.get("token")
            
        if not token:
            # Try to get token from headers
            auth_header = websocket.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                
        if not token:
            logger.warning("No authentication token provided")
            try:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            except Exception as close_error:
                logger.error(f"Error closing WebSocket: {str(close_error)}")
            raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)
            
        # Decode token
        payload = decode_jwt_token(token)
        if not payload:
            logger.warning("Invalid authentication token")
            try:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            except Exception as close_error:
                logger.error(f"Error closing WebSocket: {str(close_error)}")
            raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)
            
        return payload
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        # Close the connection without trying to send a message first
        try:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except Exception as close_error:
            logger.error(f"Error closing WebSocket: {str(close_error)}")
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    """
    connection_id = None
    try:
        # Authenticate user
        user_data = await get_websocket_user(websocket)
        user_id = user_data.get("sub")
        
        if not user_id:
            logger.warning("User ID not found in token")
            try:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            except Exception as close_error:
                logger.error(f"Error closing WebSocket: {str(close_error)}")
            return
            
        # Accept connection
        connection_id = await connection_manager.connect(websocket, user_id)
        
        # Process any missed events
        await connection_manager.process_missed_events(connection_id)
        
        # Send welcome message
        await connection_manager.send_personal_message(
            connection_id,
            "connection:established",
            {
                "message": "Connected to WebSocket server",
                "connection_id": connection_id,
                "user_id": user_id
            }
        )
        
        # Handle incoming messages
        while True:
            # Wait for message
            message_text = await websocket.receive_text()
            
            try:
                # Parse message
                message = json.loads(message_text)
                
                # Handle message based on type
                message_type = message.get("type")
                data = message.get("data", {})
                
                if message_type == "ping":
                    # Respond to ping
                    await connection_manager.send_personal_message(
                        connection_id,
                        EventType.PONG,
                        {"timestamp": asyncio.get_event_loop().time()}
                    )
                
                elif message_type == "subscribe:project":
                    # Subscribe to project events
                    project_id = data.get("project_id")
                    if project_id:
                        await connection_manager.subscribe_to_project(connection_id, project_id)
                        await connection_manager.send_personal_message(
                            connection_id,
                            "subscription:success",
                            {"type": "project", "id": project_id}
                        )
                
                elif message_type == "subscribe:document":
                    # Subscribe to document events
                    document_id = data.get("document_id")
                    if document_id:
                        await connection_manager.subscribe_to_document(connection_id, document_id)
                        await connection_manager.send_personal_message(
                            connection_id,
                            "subscription:success",
                            {"type": "document", "id": document_id}
                        )
                
                elif message_type == "subscribe:chat_session":
                    # Subscribe to chat session events
                    session_id = data.get("session_id")
                    if session_id:
                        await connection_manager.subscribe_to_chat_session(connection_id, session_id)
                        await connection_manager.send_personal_message(
                            connection_id,
                            "subscription:success",
                            {"type": "chat_session", "id": session_id}
                        )
                
                elif message_type == "get:history":
                    # Get event history
                    event_type = data.get("event_type")
                    since_timestamp = data.get("since_timestamp")
                    
                    history = await connection_manager.get_event_history(event_type, since_timestamp)
                    await connection_manager.send_personal_message(
                        connection_id,
                        "history:result",
                        {"events": history}
                    )
                
                elif message_type == EventType.PONG:
                    # Update activity timestamp
                    if connection_id in connection_manager.connection_activity:
                        connection_manager.connection_activity[connection_id] = asyncio.get_event_loop().time()
                
                else:
                    # Unknown message type
                    logger.warning(f"Unknown message type: {message_type}")
                    try:
                        await connection_manager.send_personal_message(
                            connection_id,
                            "error",
                            {"message": f"Unknown message type: {message_type}"}
                        )
                    except Exception as send_error:
                        logger.error(f"Error sending error message: {str(send_error)}")
            
            except json.JSONDecodeError:
                # Invalid JSON
                logger.warning(f"Invalid JSON message: {message_text}")
                try:
                    await connection_manager.send_personal_message(
                        connection_id,
                        "error",
                        {"message": "Invalid JSON message"}
                    )
                except Exception as send_error:
                    logger.error(f"Error sending error message: {str(send_error)}")
            
            except Exception as e:
                # Other error
                logger.error(f"Error processing message: {str(e)}")
                try:
                    await connection_manager.send_personal_message(
                        connection_id,
                        "error",
                        {"message": f"Error processing message: {str(e)}"}
                    )
                except Exception as send_error:
                    logger.error(f"Error sending error message: {str(send_error)}")
    
    except WebSocketDisconnect:
        # Client disconnected
        if connection_id:
            await connection_manager.disconnect(connection_id)
    
    except Exception as e:
        # Other error
        logger.error(f"WebSocket error: {str(e)}")
        try:
            if connection_id:
                await connection_manager.disconnect(connection_id)
        except Exception as disconnect_error:
            logger.error(f"Error disconnecting: {str(disconnect_error)}")