"""
Server-Sent Events (SSE) routes for real-time updates.
"""
from typing import Optional, Dict, Any
import time
import asyncio
from fastapi import APIRouter, Request, Depends, Query, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sse_starlette.sse import EventSourceResponse
import json
from loguru import logger

from ...services.sse_service import sse_manager
from ...utils.auth import decode_jwt_token, get_current_user
from ...config import settings

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_token_from_query(
    token: Optional[str] = Query(None)
) -> Optional[str]:
    """
    Extract token from query parameters for SSE authentication.
    """
    return token

async def get_sse_user(request: Request):
    """
    Authenticate user from SSE connection.
    
    Args:
        request: The HTTP request
        
    Returns:
        dict: User information
    
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Check if we're in development mode and should bypass auth
        # This is useful for testing but should be disabled in production
        if settings.ENVIRONMENT == "development" and settings.DEBUG and request.query_params.get("dev_mode") == "true":
            logger.warning("Using development mode authentication bypass")
            # Return a mock user payload for development
            return {
                "sub": "dev-user-id",
                "email": "dev@example.com",
                "name": "Development User"
            }
            
        # Try to get token from query parameters
        token = request.query_params.get("token")
        
        # Try to get token from cookies - check multiple possible cookie names
        if not token:
            # Check for our own token cookie
            token = request.cookies.get("token")
            
            # Check for Next Auth session token
            if not token:
                next_auth_token = request.cookies.get("next-auth.session-token")
                if next_auth_token:
                    logger.info("Found Next Auth session token")
                    token = next_auth_token
                    
            # Check for Next Auth CSRF token as fallback
            if not token:
                next_auth_csrf = request.cookies.get("next-auth.csrf-token")
                if next_auth_csrf:
                    logger.info("Found Next Auth CSRF token")
                    token = next_auth_csrf
            
        # Try to get token from headers
        if not token:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                
        if not token:
            logger.warning("No authentication token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
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
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format"
                )
            except Exception as next_auth_error:
                logger.error(f"Error parsing Next Auth token: {str(next_auth_error)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication error"
                )
        
        return payload
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication error"
        )

# Rate limiting for SSE connections
connection_attempts_per_ip = {}
MAX_CONNECTION_ATTEMPTS_PER_MINUTE = 20

@router.get("/events")
async def sse_endpoint(request: Request):
    """
    SSE endpoint for real-time updates.
    """
    client_ip = request.client.host
    logger.info(f"New SSE connection attempt from {client_ip}")
    
    try:
        # Implement rate limiting for connection attempts
        current_time = time.time()
        rate_limit_key = client_ip
        
        # Initialize or update connection attempts tracking
        if rate_limit_key not in connection_attempts_per_ip:
            connection_attempts_per_ip[rate_limit_key] = []
        
        # Add current attempt
        connection_attempts_per_ip[rate_limit_key].append(current_time)
        
        # Remove attempts older than 1 minute
        connection_attempts_per_ip[rate_limit_key] = [
            t for t in connection_attempts_per_ip[rate_limit_key]
            if current_time - t < 60
        ]
        
        # Check if rate limit exceeded
        if len(connection_attempts_per_ip[rate_limit_key]) > MAX_CONNECTION_ATTEMPTS_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for {rate_limit_key}: {len(connection_attempts_per_ip[rate_limit_key])} attempts in the last minute")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many connection attempts. Please try again later."
            )
        
        # Authenticate user
        user_data = await get_sse_user(request)
        
        # Try to get user ID from different possible fields
        user_id = None
        
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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found"
            )
        
        # Connect to SSE manager
        connection_id = await sse_manager.connect(user_id)
        
        # Return EventSourceResponse
        return EventSourceResponse(
            sse_manager.event_generator(connection_id),
            media_type="text/event-stream"
        )
    
    except HTTPException as http_error:
        # Re-raise HTTP exceptions
        raise http_error
    except Exception as e:
        logger.error(f"SSE error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SSE error: {str(e)}"
        )

# REST API endpoints for client-to-server communication

@router.post("/subscribe/project/{project_id}")
async def subscribe_to_project(
    project_id: str,
    request: Request,
    user_data: Dict = Depends(get_sse_user)
):
    """
    Subscribe to project events.
    """
    try:
        # Get user ID
        user_id = user_data.get("sub") or user_data.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found"
            )
        
        # Find connection IDs for this user
        if user_id not in sse_manager.user_connections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active SSE connections found for user"
            )
        
        # Subscribe all user connections to this project
        for connection_id in sse_manager.user_connections[user_id]:
            await sse_manager.subscribe_to_project(connection_id, project_id)
        
        return {"status": "success", "message": f"Subscribed to project {project_id}"}
    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        logger.error(f"Error subscribing to project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error subscribing to project: {str(e)}"
        )

@router.post("/subscribe/document/{document_id}")
async def subscribe_to_document(
    document_id: str,
    request: Request,
    user_data: Dict = Depends(get_sse_user)
):
    """
    Subscribe to document events.
    """
    try:
        # Get user ID
        user_id = user_data.get("sub") or user_data.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found"
            )
        
        # Find connection IDs for this user
        if user_id not in sse_manager.user_connections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active SSE connections found for user"
            )
        
        # Subscribe all user connections to this document
        for connection_id in sse_manager.user_connections[user_id]:
            await sse_manager.subscribe_to_document(connection_id, document_id)
        
        return {"status": "success", "message": f"Subscribed to document {document_id}"}
    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        logger.error(f"Error subscribing to document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error subscribing to document: {str(e)}"
        )

@router.post("/subscribe/chat_session/{session_id}")
async def subscribe_to_chat_session(
    session_id: str,
    request: Request,
    user_data: Dict = Depends(get_sse_user)
):
    """
    Subscribe to chat session events.
    """
    try:
        # Get user ID
        user_id = user_data.get("sub") or user_data.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found"
            )
        
        # Find connection IDs for this user
        if user_id not in sse_manager.user_connections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active SSE connections found for user"
            )
        
        # Subscribe all user connections to this chat session
        for connection_id in sse_manager.user_connections[user_id]:
            await sse_manager.subscribe_to_chat_session(connection_id, session_id)
        
        return {"status": "success", "message": f"Subscribed to chat session {session_id}"}
    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        logger.error(f"Error subscribing to chat session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error subscribing to chat session: {str(e)}"
        )

@router.get("/history")
async def get_event_history(
    event_type: Optional[str] = None,
    since_timestamp: Optional[float] = None,
    user_data: Dict = Depends(get_sse_user)
):
    """
    Get event history.
    """
    try:
        # Get history
        history = await sse_manager.get_event_history(event_type, since_timestamp)
        return {"events": history}
    except Exception as e:
        logger.error(f"Error getting event history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting event history: {str(e)}"
        )