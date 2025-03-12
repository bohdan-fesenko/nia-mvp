"""
WebSocket routes for real-time updates.
"""
from typing import Optional, Dict, Any, Set
import time
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import json
import asyncio
from loguru import logger

from ...services.websocket_service import connection_manager, EventType
from ...utils.auth import decode_jwt_token, get_current_user
from ...config import settings

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
        # Check if we're in development mode and should bypass auth
        # This is useful for testing but should be disabled in production
        if settings.ENVIRONMENT == "development" and settings.DEBUG and websocket.query_params.get("dev_mode") == "true":
            logger.warning("Using development mode authentication bypass")
            # Return a mock user payload for development
            return {
                "sub": "dev-user-id",
                "email": "dev@example.com",
                "name": "Development User"
            }
            
        # Try to get token from query parameters
        token = websocket.query_params.get("token")
        
        # Try to get token from cookies - check multiple possible cookie names
        if not token:
            # Check for our own token cookie
            token = websocket.cookies.get("token")
            
            # Check for Next Auth session token
            if not token:
                next_auth_token = websocket.cookies.get("next-auth.session-token")
                if next_auth_token:
                    logger.info("Found Next Auth session token")
                    token = next_auth_token
                    
            # Check for Next Auth CSRF token as fallback
            if not token:
                next_auth_csrf = websocket.cookies.get("next-auth.csrf-token")
                if next_auth_csrf:
                    logger.info("Found Next Auth CSRF token")
                    token = next_auth_csrf
            
        # Try to get token from headers
        if not token:
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
        
        # Try to decode token as JWT
        payload = decode_jwt_token(token)
        
        # If standard JWT decode fails, try to parse as Next Auth token
        if not payload:
            try:
                # Next Auth tokens might have different structure
                # This is a simplified example - you may need to adjust based on your Next Auth configuration
                import json
                import base64
                
                # Try to decode as base64 (Next Auth sometimes uses this format)
                try:
                    # Add padding if needed
                    padded_token = token + "=" * ((4 - len(token) % 4) % 4)
                    decoded = base64.b64decode(padded_token).decode('utf-8')
                    next_auth_data = json.loads(decoded)
                    
                    # Extract user info from Next Auth data
                    if next_auth_data and "sub" in next_auth_data:
                        logger.info("Successfully decoded Next Auth token")
                        return next_auth_data
                except Exception as decode_error:
                    logger.debug(f"Failed to decode as base64: {str(decode_error)}")
                    
                # If that fails, try to parse as JSON directly (some Next Auth configurations)
                try:
                    next_auth_data = json.loads(token)
                    if next_auth_data and "sub" in next_auth_data:
                        logger.info("Successfully parsed Next Auth token as JSON")
                        return next_auth_data
                except json.JSONDecodeError:
                    logger.debug("Failed to parse token as JSON")
                    
                # If all parsing attempts fail, reject the connection
                logger.warning("Invalid authentication token format")
                try:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                except Exception as close_error:
                    logger.error(f"Error closing WebSocket: {str(close_error)}")
                raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)
            except Exception as next_auth_error:
                logger.error(f"Error parsing Next Auth token: {str(next_auth_error)}")
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

# Connection management with proper cleanup
active_connections_per_user = {}
connection_timestamps = {}  # Track when connections were established
connection_last_activity = {}  # Track last activity time for each connection
connection_attempts_per_user = {}  # Track connection attempts per user
MAX_CONNECTIONS_PER_USER = 10  # Increased to allow more legitimate connections
CONNECTION_TIMEOUT_SECONDS = 60  # Reduced to 60 seconds timeout for inactive connections
MAX_CONNECTION_ATTEMPTS_PER_MINUTE = 20  # Maximum connection attempts per minute

# Function to clean up rate limiting data
def cleanup_rate_limiting_data():
    """Clean up old rate limiting data"""
    current_time = time.time()
    keys_to_remove = []
    
    for key, timestamps in connection_attempts_per_user.items():
        # Remove timestamps older than 1 minute
        connection_attempts_per_user[key] = [
            t for t in timestamps if current_time - t < 60
        ]
        
        # If no recent attempts, remove the key
        if not connection_attempts_per_user[key]:
            keys_to_remove.append(key)
    
    # Remove empty keys
    for key in keys_to_remove:
        del connection_attempts_per_user[key]

# Background task to clean up stale connections
async def cleanup_stale_connections():
    """Periodically clean up stale connections that haven't been active"""
    while True:
        try:
            current_time = time.time()
            stale_connections = []
            
            # Log current connection state before cleanup
            logger.info(f"Connection state before cleanup: {len(connection_last_activity)} tracked connections")
            for user_id, connections in active_connections_per_user.items():
                logger.info(f"User {user_id} has {len(connections)} active connections")
            
            # Find stale connections
            for conn_id, last_activity in connection_last_activity.items():
                time_inactive = current_time - last_activity
                if time_inactive > CONNECTION_TIMEOUT_SECONDS:
                    stale_connections.append(conn_id)
                    logger.info(f"Found stale connection: {conn_id} (inactive for {time_inactive:.1f}s)")
                elif time_inactive > CONNECTION_TIMEOUT_SECONDS / 2:
                    # Log connections that are becoming stale
                    logger.debug(f"Connection {conn_id} becoming stale (inactive for {time_inactive:.1f}s)")
            
            # Clean up stale connections
            logger.info(f"Found {len(stale_connections)} stale connections to clean up")
            for conn_id in stale_connections:
                logger.info(f"Cleaning up stale connection: {conn_id}")
                user_id = connection_manager.connection_user.get(conn_id)
                
                if user_id and conn_id in active_connections_per_user.get(user_id, set()):
                    logger.info(f"Removing connection {conn_id} from user {user_id} tracking")
                    active_connections_per_user[user_id].discard(conn_id)
                    if not active_connections_per_user[user_id]:
                        logger.info(f"User {user_id} has no more active connections, removing from tracking")
                        del active_connections_per_user[user_id]
                else:
                    logger.warning(f"Connection {conn_id} not found in user tracking for user {user_id}")
                
                # Remove from tracking
                connection_last_activity.pop(conn_id, None)
                connection_timestamps.pop(conn_id, None)
                
                # Disconnect from connection manager
                await connection_manager.disconnect(conn_id)
            
            # Clean up rate limiting data
            cleanup_rate_limiting_data()
            
            # Log connection state after cleanup
            logger.info(f"Connection state after cleanup: {len(connection_last_activity)} tracked connections")
            for user_id, connections in active_connections_per_user.items():
                logger.info(f"User {user_id} has {len(connections)} active connections")
            
            # Sleep for a while before checking again
            await asyncio.sleep(15)  # Check every 15 seconds
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            await asyncio.sleep(15)  # Sleep and retry

# Start the cleanup task
@router.on_event("startup")
async def start_cleanup_task():
    asyncio.create_task(cleanup_stale_connections())

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    """
    connection_id = None
    client_ip = websocket.client.host
    logger.info(f"New WebSocket connection attempt from {client_ip}")
    
    try:
        # Authenticate user
        user_data = await get_websocket_user(websocket)
        
        # Try to get user ID from different possible fields
        # This handles both our JWT tokens and Next Auth tokens
        user_id = None
        
        # Implement rate limiting for connection attempts
        client_ip = websocket.client.host
        rate_limit_key = f"{client_ip}"  # Use IP address for rate limiting
        current_time = time.time()
        
        # Initialize or update connection attempts tracking
        if rate_limit_key not in connection_attempts_per_user:
            connection_attempts_per_user[rate_limit_key] = []
        
        # Add current attempt
        connection_attempts_per_user[rate_limit_key].append(current_time)
        
        # Remove attempts older than 1 minute
        connection_attempts_per_user[rate_limit_key] = [
            t for t in connection_attempts_per_user[rate_limit_key]
            if current_time - t < 60
        ]
        
        # Check if rate limit exceeded
        if len(connection_attempts_per_user[rate_limit_key]) > MAX_CONNECTION_ATTEMPTS_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for {rate_limit_key}: {len(connection_attempts_per_user[rate_limit_key])} attempts in the last minute")
            try:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION,
                                     reason=f"Too many connection attempts. Please try again later.")
            except Exception as close_error:
                logger.error(f"Error closing WebSocket: {str(close_error)}")
            return
        
        # Check standard JWT sub claim
        if "sub" in user_data:
            user_id = user_data.get("sub")
        
        # Check Next Auth format (might use id instead of sub)
        elif "id" in user_data:
            user_id = user_data.get("id")
            
        # Check for email as fallback
        elif "email" in user_data:
            # Find user by email
            find_user_query = """
            MATCH (u:User {email: $email})
            RETURN u
            """
            
            try:
                from ...db.neo4j_client import neo4j_client
                result = await neo4j_client.execute_query_async(
                    find_user_query,
                    {"email": user_data.get("email")}
                )
                
                if result and result[0] and "u" in result[0]:
                    user_id = result[0]["u"]["id"]
                    logger.info(f"Found user ID {user_id} from email")
            except Exception as db_error:
                logger.error(f"Error finding user by email: {str(db_error)}")
        
        if not user_id:
            logger.warning("User ID not found in token")
            try:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            except Exception as close_error:
                logger.error(f"Error closing WebSocket: {str(close_error)}")
            return
        
        # Check if user has too many active connections
        if user_id in active_connections_per_user:
            # Log current connection count for this user
            current_connections = len(active_connections_per_user[user_id])
            logger.info(f"User {user_id} has {current_connections}/{MAX_CONNECTIONS_PER_USER} active connections")
            
            # Aggressively clean up stale connections for this user
            current_time = time.time()
            stale_connections = []
            
            # Find stale connections for this user
            for conn_id in active_connections_per_user[user_id]:
                # Check if connection is stale (no activity for 60 seconds)
                last_activity = connection_last_activity.get(conn_id, 0)
                time_inactive = current_time - last_activity
                if time_inactive > 60:  # 60 seconds timeout
                    stale_connections.append(conn_id)
                    logger.info(f"Found stale connection {conn_id} for user {user_id} (inactive for {time_inactive:.1f}s)")
            
            # Log stale connections found
            logger.info(f"Found {len(stale_connections)} stale connections for user {user_id}")
            
            # Remove stale connections
            for conn_id in stale_connections:
                logger.info(f"Removing stale connection {conn_id} for user {user_id}")
                active_connections_per_user[user_id].discard(conn_id)
                connection_last_activity.pop(conn_id, None)
                connection_timestamps.pop(conn_id, None)
                await connection_manager.disconnect(conn_id)
            
            # Now check if user still has too many connections
            remaining_connections = len(active_connections_per_user[user_id])
            logger.info(f"User {user_id} has {remaining_connections}/{MAX_CONNECTIONS_PER_USER} connections after cleanup")
            
            if remaining_connections >= MAX_CONNECTIONS_PER_USER:
                logger.warning(f"Too many connections for user {user_id} (max: {MAX_CONNECTIONS_PER_USER})")
                # Log connection details for debugging
                for conn_id in active_connections_per_user[user_id]:
                    conn_time = connection_timestamps.get(conn_id, 0)
                    last_activity = connection_last_activity.get(conn_id, 0)
                    age = current_time - conn_time
                    idle = current_time - last_activity
                    logger.info(f"Connection {conn_id}: age={age:.1f}s, idle={idle:.1f}s")
                
                try:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION,
                                         reason=f"Too many connections (max: {MAX_CONNECTIONS_PER_USER})")
                except Exception as close_error:
                    logger.error(f"Error closing WebSocket: {str(close_error)}")
                return
        else:
            logger.info(f"First connection for user {user_id}")
            active_connections_per_user[user_id] = set()
            
        # Accept connection
        connection_id = await connection_manager.connect(websocket, user_id)
        logger.info(f"Connection accepted: {connection_id} for user {user_id}")
        
        # Track this connection
        active_connections_per_user[user_id].add(connection_id)
        new_count = len(active_connections_per_user[user_id])
        logger.info(f"User {user_id} now has {new_count}/{MAX_CONNECTIONS_PER_USER} active connections")
        
        # Record connection timestamp and last activity
        current_time = time.time()
        connection_timestamps[connection_id] = current_time
        connection_last_activity[connection_id] = current_time
        logger.info(f"Connection {connection_id} timestamp recorded at {current_time}")
        
        # Log connection manager state
        cm_connections = len(connection_manager.active_connections)
        logger.info(f"Connection manager now has {cm_connections} active connections")
        
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
            
            # Update last activity timestamp
            connection_last_activity[connection_id] = time.time()
            
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
        logger.info(f"WebSocket disconnected: {connection_id} for user {user_id}")
        if connection_id:
            logger.info(f"Disconnecting connection {connection_id} from connection manager")
            await connection_manager.disconnect(connection_id)
            
            # Remove from tracking
            if user_id in active_connections_per_user:
                logger.info(f"Removing connection {connection_id} from user {user_id} tracking")
                active_connections_per_user[user_id].discard(connection_id)
                if not active_connections_per_user[user_id]:
                    logger.info(f"User {user_id} has no more active connections, removing from tracking")
                    del active_connections_per_user[user_id]
                else:
                    remaining = len(active_connections_per_user[user_id])
                    logger.info(f"User {user_id} has {remaining} remaining connections")
    
    
    except Exception as e:
        # Other error
        logger.error(f"WebSocket error: {str(e)}")
        try:
            if connection_id:
                logger.info(f"Disconnecting connection {connection_id} due to error")
                await connection_manager.disconnect(connection_id)
                
                # Remove from tracking
                if user_id in active_connections_per_user:
                    logger.info(f"Removing connection {connection_id} from user {user_id} tracking due to error")
                    active_connections_per_user[user_id].discard(connection_id)
                    if not active_connections_per_user[user_id]:
                        logger.info(f"User {user_id} has no more active connections, removing from tracking")
                        del active_connections_per_user[user_id]
                    else:
                        remaining = len(active_connections_per_user[user_id])
                        logger.info(f"User {user_id} has {remaining} remaining connections after error")
        except Exception as disconnect_error:
            logger.error(f"Error disconnecting: {str(disconnect_error)}")