"""
Agent API routes for the AI Project Assistant.
This module provides API endpoints for agent interactions.
"""
from typing import Dict, List, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, Body, Path
from fastapi.responses import StreamingResponse
import json
import asyncio
from loguru import logger

from ...models.agent import (
    Agent, AgentTask, ChatSession, ChatMessage, AgentQuestion, AgentApprovalRequest,
    AgentActivityLog, Notification, AgentType, AgentTaskStatus, AgentTaskType,
    MessageSenderType, QuestionType, ApprovalStatus, NotificationType, NotificationPriority,
    AgentActivityType
)
from ...repositories.agent_repository import (
    agent_repository, agent_task_repository, chat_session_repository,
    activity_log_repository, notification_repository
)
from ...services.conversation_agent_service import conversation_agent_service
from ...services.event_service import event_service
from ...utils.auth import get_current_user, User


router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/")
async def get_agents(
    agent_type: Optional[AgentType] = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_user)
):
    """
    Get available agents.
    
    Args:
        agent_type: Optional agent type filter
        active_only: Whether to return only active agents
        current_user: Current authenticated user
        
    Returns:
        List of agents
    """
    agents = await agent_repository.get_agents(
        agent_type=agent_type,
        active_only=active_only
    )
    
    return {"data": agents}


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str = Path(..., description="Agent ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get agent details.
    
    Args:
        agent_id: Agent ID
        current_user: Current authenticated user
        
    Returns:
        Agent details
    """
    agent = await agent_repository.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent


@router.post("/chat")
async def chat(
    message: str = Body(..., embed=True, description="User message"),
    session_id: Optional[str] = Body(None, embed=True, description="Optional session ID"),
    context: Optional[Dict[str, Any]] = Body(None, embed=True, description="Optional context"),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message to the conversation agent.
    
    Args:
        message: User message
        session_id: Optional session ID
        context: Optional context
        current_user: Current authenticated user
        
    Returns:
        Agent response
    """
    try:
        # Process message
        response_text = ""
        async for chunk in conversation_agent_service.process_message(
            user_id=current_user.id,
            message=message,
            session_id=session_id,
            context=context
        ):
            response_text += chunk
        
        return {
            "message_id": "placeholder",  # In a real implementation, this would be the message ID
            "response": response_text,
            "created_at": "placeholder",  # In a real implementation, this would be the timestamp
            "session_id": session_id,
            "tasks": [],  # In a real implementation, this would be any tasks created
            "agent_id": "placeholder"  # In a real implementation, this would be the agent ID
        }
    
    except Exception as e:
        logger.exception(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(
    message: str = Body(..., embed=True, description="User message"),
    session_id: Optional[str] = Body(None, embed=True, description="Optional session ID"),
    context: Optional[Dict[str, Any]] = Body(None, embed=True, description="Optional context"),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message to the conversation agent and get a streaming response.
    
    Args:
        message: User message
        session_id: Optional session ID
        context: Optional context
        current_user: Current authenticated user
        
    Returns:
        Streaming response
    """
    try:
        async def generate():
            async for chunk in conversation_agent_service.process_message(
                user_id=current_user.id,
                message=message,
                session_id=session_id,
                context=context
            ):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
    
    except Exception as e:
        logger.exception(f"Error in chat stream endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks")
async def create_task(
    agent_type: AgentType = Body(..., embed=True, description="Agent type"),
    task_type: AgentTaskType = Body(..., embed=True, description="Task type"),
    description: str = Body(..., embed=True, description="Task description"),
    session_id: Optional[str] = Body(None, embed=True, description="Optional session ID"),
    priority: int = Body(3, embed=True, description="Task priority (1-5, where 1 is highest)"),
    context: Optional[Dict[str, Any]] = Body(None, embed=True, description="Optional context"),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new agent task.
    
    Args:
        agent_type: Agent type
        task_type: Task type
        description: Task description
        session_id: Optional session ID
        priority: Task priority
        context: Optional context
        current_user: Current authenticated user
        
    Returns:
        Created task
    """
    try:
        task_id = await conversation_agent_service.delegate_task(
            user_id=current_user.id,
            task_type=task_type,
            description=description,
            agent_type=agent_type,
            session_id=session_id,
            priority=priority,
            context=context
        )
        
        task = await agent_task_repository.get_task(task_id)
        
        return task
    
    except Exception as e:
        logger.exception(f"Error in create task endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def get_tasks(
    agent_id: Optional[str] = None,
    status: Optional[AgentTaskStatus] = None,
    task_type: Optional[AgentTaskType] = None,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get agent tasks.
    
    Args:
        agent_id: Optional agent ID filter
        status: Optional status filter
        task_type: Optional task type filter
        session_id: Optional session ID filter
        current_user: Current authenticated user
        
    Returns:
        List of tasks
    """
    tasks = await agent_task_repository.get_tasks(
        agent_id=agent_id,
        status=status,
        task_type=task_type,
        session_id=session_id,
        user_id=current_user.id
    )
    
    return {"data": tasks}


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get task details.
    
    Args:
        task_id: Task ID
        current_user: Current authenticated user
        
    Returns:
        Task details
    """
    task = await agent_task_repository.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.requested_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    
    # Get task steps
    steps = await agent_task_repository.get_task_steps(task_id)
    
    # Get task status updates
    status_updates = await agent_task_repository.get_task_status_updates(task_id)
    
    return {
        **task.dict(),
        "execution_steps": steps,
        "status_updates": status_updates
    }


@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: str = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get task status.
    
    Args:
        task_id: Task ID
        current_user: Current authenticated user
        
    Returns:
        Task status
    """
    task = await agent_task_repository.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.requested_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    
    # Get latest status update
    status_updates = await agent_task_repository.get_task_status_updates(task_id)
    latest_update = status_updates[-1] if status_updates else None
    
    return {
        "id": task.id,
        "status": task.status,
        "progress_percentage": task.progress_percentage,
        "last_update": latest_update.created_at if latest_update else None,
        "last_message": latest_update.message if latest_update else None,
        "result_document_id": task.result_document_id
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a task.
    
    Args:
        task_id: Task ID
        current_user: Current authenticated user
        
    Returns:
        Cancelled task
    """
    task = await agent_task_repository.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.requested_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this task")
    
    if task.status in (AgentTaskStatus.COMPLETED, AgentTaskStatus.FAILED, AgentTaskStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Task is already in {task.status} state")
    
    # Update task status
    task, status_update = await agent_task_repository.update_task_status(
        task_id=task_id,
        status=AgentTaskStatus.CANCELLED,
        message="Task cancelled by user"
    )
    
    return {
        "id": task.id,
        "status": task.status,
        "message": "Task cancelled by user"
    }


@router.get("/sessions")
async def get_sessions(
    current_user: User = Depends(get_current_user)
):
    """
    Get chat sessions for the current user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of chat sessions
    """
    sessions = await chat_session_repository.get_sessions(current_user.id)
    
    return {"data": sessions}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str = Path(..., description="Session ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get chat session details.
    
    Args:
        session_id: Session ID
        current_user: Current authenticated user
        
    Returns:
        Session details
    """
    session = await chat_session_repository.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    
    return session


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str = Path(..., description="Session ID"),
    limit: int = Query(100, description="Maximum number of messages to return"),
    before_id: Optional[str] = Query(None, description="Get messages before this ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get messages for a chat session.
    
    Args:
        session_id: Session ID
        limit: Maximum number of messages to return
        before_id: Optional message ID to get messages before
        current_user: Current authenticated user
        
    Returns:
        List of messages
    """
    session = await chat_session_repository.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    
    messages = await chat_session_repository.get_messages(
        session_id=session_id,
        limit=limit,
        before_id=before_id
    )
    
    return {"data": messages}


@router.post("/sessions/{session_id}/questions/{question_id}/answer")
async def answer_question(
    session_id: str = Path(..., description="Session ID"),
    question_id: str = Path(..., description="Question ID"),
    answer: str = Body(..., embed=True, description="Answer to the question"),
    current_user: User = Depends(get_current_user)
):
    """
    Answer a question.
    
    Args:
        session_id: Session ID
        question_id: Question ID
        answer: Answer to the question
        current_user: Current authenticated user
        
    Returns:
        Updated question
    """
    session = await chat_session_repository.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    
    # Get question
    questions = await chat_session_repository.get_pending_questions(session_id)
    question = next((q for q in questions if q.id == question_id), None)
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found or already answered")
    
    # Answer question
    updated_question = await chat_session_repository.answer_question(
        question_id=question_id,
        answer=answer
    )
    
    # Send event
    await event_service.emit(
        "agent:question:answered",
        {
            "question_id": question_id,
            "session_id": session_id,
            "answer": answer
        },
        user_id=current_user.id
    )
    
    return updated_question


@router.post("/sessions/{session_id}/approvals/{approval_id}/respond")
async def respond_to_approval(
    session_id: str = Path(..., description="Session ID"),
    approval_id: str = Path(..., description="Approval ID"),
    approved: bool = Body(..., embed=True, description="Whether the request is approved"),
    response: Optional[str] = Body(None, embed=True, description="Optional response message"),
    current_user: User = Depends(get_current_user)
):
    """
    Respond to an approval request.
    
    Args:
        session_id: Session ID
        approval_id: Approval ID
        approved: Whether the request is approved
        response: Optional response message
        current_user: Current authenticated user
        
    Returns:
        Updated approval request
    """
    session = await chat_session_repository.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    
    # Get approval request
    approvals = await chat_session_repository.get_pending_approvals(session_id)
    approval = next((a for a in approvals if a.id == approval_id), None)
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found or already responded to")
    
    # Respond to approval
    updated_approval = await chat_session_repository.respond_to_approval(
        approval_id=approval_id,
        approved=approved,
        response=response
    )
    
    # Send event
    await event_service.emit(
        "agent:approval:response",
        {
            "approval_id": approval_id,
            "session_id": session_id,
            "approved": approved,
            "response": response
        },
        user_id=current_user.id
    )
    
    return updated_approval


@router.get("/notifications")
async def get_notifications(
    unread_only: bool = Query(False, description="Whether to return only unread notifications"),
    notification_type: Optional[NotificationType] = Query(None, description="Optional notification type filter"),
    priority: Optional[NotificationPriority] = Query(None, description="Optional priority filter"),
    limit: int = Query(50, description="Maximum number of notifications to return"),
    current_user: User = Depends(get_current_user)
):
    """
    Get notifications for the current user.
    
    Args:
        unread_only: Whether to return only unread notifications
        notification_type: Optional notification type filter
        priority: Optional priority filter
        limit: Maximum number of notifications to return
        current_user: Current authenticated user
        
    Returns:
        List of notifications
    """
    notifications = await notification_repository.get_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        notification_type=notification_type,
        priority=priority,
        limit=limit
    )
    
    return {"data": notifications}


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str = Path(..., description="Notification ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a notification as read.
    
    Args:
        notification_id: Notification ID
        current_user: Current authenticated user
        
    Returns:
        Updated notification
    """
    # Get notification
    notifications = await notification_repository.get_notifications(
        user_id=current_user.id,
        unread_only=True
    )
    
    notification = next((n for n in notifications if n.id == notification_id), None)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found or already read")
    
    # Mark as read
    updated_notification = await notification_repository.mark_notification_read(notification_id)
    
    return updated_notification


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user)
):
    """
    Mark all notifications for the current user as read.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Number of notifications marked as read
    """
    count = await notification_repository.mark_all_notifications_read(current_user.id)
    
    return {"count": count}


@router.get("/activities")
async def get_activities(
    agent_id: Optional[str] = Query(None, description="Optional agent ID filter"),
    session_id: Optional[str] = Query(None, description="Optional session ID filter"),
    task_id: Optional[str] = Query(None, description="Optional task ID filter"),
    document_id: Optional[str] = Query(None, description="Optional document ID filter"),
    activity_type: Optional[AgentActivityType] = Query(None, description="Optional activity type filter"),
    limit: int = Query(100, description="Maximum number of activities to return"),
    current_user: User = Depends(get_current_user)
):
    """
    Get agent activities.
    
    Args:
        agent_id: Optional agent ID filter
        session_id: Optional session ID filter
        task_id: Optional task ID filter
        document_id: Optional document ID filter
        activity_type: Optional activity type filter
        limit: Maximum number of activities to return
        current_user: Current authenticated user
        
    Returns:
        List of activities
    """
    # Verify session ownership if session_id is provided
    if session_id:
        session = await chat_session_repository.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
    
    # Verify task ownership if task_id is provided
    if task_id:
        task = await agent_task_repository.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.requested_by != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this task")
    
    activities = await activity_log_repository.get_activities(
        agent_id=agent_id,
        session_id=session_id,
        task_id=task_id,
        document_id=document_id,
        activity_type=activity_type,
        limit=limit
    )
    
    return {"data": activities}


@router.get("/document-diffs/{document_id}")
async def get_document_diffs(
    document_id: str = Path(..., description="Document ID"),
    limit: int = Query(10, description="Maximum number of diffs to return"),
    current_user: User = Depends(get_current_user)
):
    """
    Get diffs for a document.
    
    Args:
        document_id: Document ID
        limit: Maximum number of diffs to return
        current_user: Current authenticated user
        
    Returns:
        List of document diffs
    """
    # In a real implementation, you would verify document ownership here
    
    diffs = await activity_log_repository.get_document_diffs(
        document_id=document_id,
        limit=limit
    )
    
    return {"data": diffs}