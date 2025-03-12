"""
Conversation Agent Service for the AI Project Assistant.
This module provides the main agent interface for user interactions.
"""
from typing import Dict, List, Any, Optional, Union, Tuple, AsyncGenerator
import json
import asyncio
from datetime import datetime
import uuid
from loguru import logger
from pydantic import BaseModel, Field

from ..models.agent import (
    Agent, AgentTask, ChatSession, ChatMessage, AgentQuestion, AgentApprovalRequest,
    Notification, AgentActivityLog, AgentType, AgentTaskType, AgentTaskStatus,
    MessageSenderType, QuestionType, ApprovalStatus, NotificationType,
    NotificationPriority, AgentActivityType
)
from ..repositories.agent_repository import (
    agent_repository, agent_task_repository, chat_session_repository,
    notification_repository, activity_log_repository
)
from ..services.llm_service import llm_service, structured_llm_service, LLMMessage
from ..services.execution_agent_service import execution_agent_service
from ..services.event_service import event_service
from ..services.token_manager import token_manager
from ..services.output_parser import output_parser
from ..config import settings


# Define structured output schemas
class UserIntent(BaseModel):
    """Model for user intent detection."""
    primary_intent: str = Field(..., description="The primary intent of the user's message")
    secondary_intents: List[str] = Field(default_factory=list, description="Any secondary intents detected")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Entities extracted from the message")
    confidence: float = Field(..., description="Confidence score for the intent detection (0-1)")
    requires_clarification: bool = Field(default=False, description="Whether clarification is needed")
    clarification_question: Optional[str] = Field(None, description="Question to ask for clarification if needed")


class AgentResponse(BaseModel):
    """Model for structured agent responses."""
    message: str = Field(..., description="The response message to show to the user")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Actions to take based on the response")
    requires_user_input: bool = Field(default=False, description="Whether user input is required")
    user_question: Optional[Dict[str, Any]] = Field(None, description="Question to ask the user if input is required")
    context_updates: Dict[str, Any] = Field(default_factory=dict, description="Updates to the conversation context")


class ConversationAgentService:
    """Service for conversation agent operations."""
    
    def __init__(self):
        """Initialize the conversation agent service."""
        self.agent_id = "a60e8400-e29b-41d4-a716-446655440000"  # Conversation agent ID
        self.max_context_messages = 30  # Maximum number of messages to keep in context
        self.max_context_tokens = 200000  # Maximum number of tokens in context window
        self.initialized = False
    
    async def initialize(self):
        """Initialize the conversation agent service."""
        if self.initialized:
            return
        
        # Register with agent repository
        agent = Agent(
            id=self.agent_id,
            name="Conversation Agent",
            type=AgentType.CONVERSATION,
            description="Main agent for handling user interactions and delegating tasks",
            capabilities=["chat", "task_delegation", "document_creation"]
        )
        
        await agent_repository.create_agent(agent)
        logger.info(f"Conversation agent initialized with ID: {self.agent_id}")
        
        self.initialized = True
    
    async def get_or_create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ChatSession:
        """
        Get or create a chat session for a user.
        
        Args:
            user_id: User ID
            title: Optional session title
            context: Optional session context
            
        Returns:
            Chat session
        """
        # Get user's sessions
        sessions = await chat_session_repository.get_sessions(user_id)
        
        # If no sessions, create a new one
        if not sessions:
            # Create title if not provided
            if not title:
                title = f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Create session
            session = ChatSession(
                user_id=user_id,
                title=title,
                context=context or {}
            )
            
            # Save session
            session = await chat_session_repository.create_session(session)
            
            # Log activity
            await activity_log_repository.log_activity(AgentActivityLog(
                agent_id=self.agent_id,
                session_id=session.id,
                activity_type=AgentActivityType.SESSION_CREATED,
                description=f"Created new chat session: {title}"
            ))
            
            # Emit event
            await event_service.emit_event(
                "chat_session_created",
                {
                    "session_id": session.id,
                    "user_id": user_id,
                    "title": title
                }
            )
            
            return session
        
        # Return the most recent session
        return sessions[0]
    
    async def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process a user message and generate a response.
        
        Args:
            user_id: User ID
            message: User message
            session_id: Optional session ID
            context: Optional message context
            
        Yields:
            Response chunks
        """
        # Generate correlation ID for tracking
        correlation_id = await token_manager.generate_correlation_id(user_id, session_id)
        # Get or create session
        if session_id:
            session = await chat_session_repository.get_session(session_id)
            
            if not session:
                raise ValueError(f"Session not found: {session_id}")
        else:
            session = await self.get_or_create_session(user_id, context=context)
        
        # Add user message to session
        user_message = ChatMessage(
            session_id=session.id,
            content=message,
            sender_type=MessageSenderType.USER,
            sender_id=user_id
        )
        
        await chat_session_repository.add_message(user_message)
        
        # Log activity
        await activity_log_repository.log_activity(AgentActivityLog(
            agent_id=self.agent_id,
            session_id=session.id,
            activity_type=AgentActivityType.MESSAGE_RECEIVED,
            description=f"Received message from user: {message[:50]}..."
        ))
        
        # Emit event
        await event_service.emit_event(
            "chat_message_received",
            {
                "session_id": session.id,
                "message_id": user_message.id,
                "user_id": user_id,
                "content": message
            }
        )
        
        # Update session
        session.updated_at = datetime.now()
        await chat_session_repository.update_session(session)
        
        # Get conversation history
        history = await self._get_conversation_history(session.id)
        
        # Process message with LLM
        try:
            # Create system prompt
            system_prompt = self._create_system_prompt(session)
            
            # Create messages for LLM
            messages = [
                LLMMessage(role="system", content=system_prompt)
            ]
            
            # Add conversation history
            for msg in history:
                role = "user" if msg.sender_type == MessageSenderType.USER else "assistant"
                messages.append(LLMMessage(role=role, content=msg.content))
            
            # Check if we need to prune context due to token limits
            messages = await self._prune_context_if_needed(messages)
            
            # Detect user intent
            intent = await self._detect_intent(user_id, message, session, messages)
            
            # Update session context with intent
            if session.context is None:
                session.context = {}
            session.context["last_intent"] = {
                "primary": intent.primary_intent,
                "secondary": intent.secondary_intents,
                "entities": intent.entities,
                "confidence": intent.confidence
            }
            await chat_session_repository.update_session(session)
            
            # Check if clarification is needed
            if intent.requires_clarification:
                # Create clarification question
                question = await self.ask_question(
                    session_id=session.id,
                    question=intent.clarification_question or "Could you please clarify what you mean?",
                    question_type=QuestionType.TEXT,
                    context={"intent": intent.dict()}
                )
                
                # Return clarification request
                clarification_message = f"I need to understand better. {intent.clarification_question or 'Could you please clarify what you mean?'}"
                yield clarification_message
                
                # Create AI message
                ai_message = ChatMessage(
                    session_id=session.id,
                    content=clarification_message,
                    sender_type=MessageSenderType.AI,
                    sender_id=self.agent_id
                )
                
                await chat_session_repository.add_message(ai_message)
                return
            
            # Generate streaming response
            response_content = ""
            
            # Emit typing event
            await event_service.publish_ai_typing(
                session_id=session.id,
                data={"user_id": user_id, "session_id": session.id}
            )
            
            async for chunk in llm_service.generate_stream(
                prompt="",  # Prompt is already in messages
                messages=messages,
                user_id=user_id,
                session_id=session.id,
                correlation_id=correlation_id
            ):
                response_content += chunk
                yield chunk
            
            # Create AI message
            ai_message = ChatMessage(
                session_id=session.id,
                content=response_content,
                sender_type=MessageSenderType.AI,
                sender_id=self.agent_id
            )
            
            await chat_session_repository.add_message(ai_message)
            
            # Log activity
            await activity_log_repository.log_activity(AgentActivityLog(
                agent_id=self.agent_id,
                session_id=session.id,
                activity_type=AgentActivityType.MESSAGE_SENT,
                description=f"Sent response to user: {response_content[:50]}..."
            ))
            
            # Emit event
            await event_service.emit_event(
                "chat_message_sent",
                {
                    "session_id": session.id,
                    "message_id": ai_message.id,
                    "agent_id": self.agent_id,
                    "content": response_content
                }
            )
            
            # Process agent actions
            await self._process_agent_actions(session, user_id, message, response_content)
        
        except Exception as e:
            # Log error
            logger.exception(f"Error processing message: {str(e)}")
            
            # Create error message
            error_message = f"I'm sorry, but I encountered an error while processing your message: {str(e)}"
            
            # Create AI message
            ai_message = ChatMessage(
                session_id=session.id,
                content=error_message,
                sender_type=MessageSenderType.AI,
                sender_id=self.agent_id
            )
            
            await chat_session_repository.add_message(ai_message)
            
            # Log activity
            await activity_log_repository.log_activity(AgentActivityLog(
                agent_id=self.agent_id,
                session_id=session.id,
                activity_type=AgentActivityType.MESSAGE_SENT,
                description=f"Sent error response to user: {error_message}"
            ))
            
            # Emit event
            await event_service.emit_event(
                "chat_message_sent",
                {
                    "session_id": session.id,
                    "message_id": ai_message.id,
                    "agent_id": self.agent_id,
                    "content": error_message,
                    "is_error": True
                }
            )
            
            # Yield error message
            yield error_message
    
    async def ask_question(
        self,
        session_id: str,
        question: str,
        question_type: QuestionType,
        options: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> AgentQuestion:
        """
        Ask a question to the user.
        
        Args:
            session_id: Session ID
            question: Question text
            question_type: Question type
            options: Optional list of options for multiple choice questions
            context: Optional question context
            timeout: Optional timeout in seconds
            
        Returns:
            Agent question
        """
        # Get session
        session = await chat_session_repository.get_session(session_id)
        
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Create question
        agent_question = AgentQuestion(
            session_id=session_id,
            agent_id=self.agent_id,
            question=question,
            question_type=question_type,
            options=options,
            context=context,
            timeout=timeout
        )
        
        # Save question
        agent_question = await chat_session_repository.add_question(agent_question)
        
        # Create notification
        notification = Notification(
            user_id=session.user_id,
            title="Question from AI Assistant",
            content=question,
            notification_type=NotificationType.QUESTION,
            priority=NotificationPriority.HIGH,
            related_id=agent_question.id,
            related_type="question"
        )
        
        await notification_repository.add_notification(notification)
        
        # Log activity
        await activity_log_repository.log_activity(AgentActivityLog(
            agent_id=self.agent_id,
            session_id=session_id,
            activity_type=AgentActivityType.QUESTION_ASKED,
            description=f"Asked question to user: {question}"
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_question",
            {
                "question_id": agent_question.id,
                "session_id": session_id,
                "agent_id": self.agent_id,
                "question": question,
                "question_type": question_type.value,
                "options": options
            }
        )
        
        return agent_question
    
    async def answer_question(
        self,
        question_id: str,
        answer: str
    ) -> AgentQuestion:
        """
        Answer a question.
        
        Args:
            question_id: Question ID
            answer: Answer text
            
        Returns:
            Updated agent question
        """
        # Get question
        questions = await chat_session_repository.get_questions()
        question = next((q for q in questions if q.id == question_id), None)
        
        if not question:
            raise ValueError(f"Question not found: {question_id}")
        
        # Update question
        question.answer = answer
        question.answered_at = datetime.now()
        
        # Save question
        question = await chat_session_repository.update_question(question)
        
        # Get session
        session = await chat_session_repository.get_session(question.session_id)
        
        # Create AI message
        ai_message = ChatMessage(
            session_id=question.session_id,
            content=f"Question: {question.question}\nAnswer: {answer}",
            sender_type=MessageSenderType.SYSTEM,
            sender_id=self.agent_id
        )
        
        await chat_session_repository.add_message(ai_message)
        
        # Log activity
        await activity_log_repository.log_activity(AgentActivityLog(
            agent_id=self.agent_id,
            session_id=question.session_id,
            activity_type=AgentActivityType.QUESTION_ANSWERED,
            description=f"Question answered by user: {question.question} -> {answer}"
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_question_answered",
            {
                "question_id": question.id,
                "session_id": question.session_id,
                "agent_id": self.agent_id,
                "answer": answer
            }
        )
        
        return question
    
    async def request_approval(
        self,
        session_id: str,
        action: str,
        details: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> AgentApprovalRequest:
        """
        Request approval for an action.
        
        Args:
            session_id: Session ID
            action: Action description
            details: Action details
            context: Optional approval context
            timeout: Optional timeout in seconds
            
        Returns:
            Agent approval request
        """
        # Get session
        session = await chat_session_repository.get_session(session_id)
        
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Create approval request
        approval_request = AgentApprovalRequest(
            session_id=session_id,
            agent_id=self.agent_id,
            action=action,
            details=details,
            context=context,
            timeout=timeout
        )
        
        # Save approval request
        approval_request = await chat_session_repository.add_approval_request(approval_request)
        
        # Create notification
        notification = Notification(
            user_id=session.user_id,
            title="Approval Request",
            content=f"The AI assistant is requesting approval to: {action}",
            notification_type=NotificationType.APPROVAL_REQUEST,
            priority=NotificationPriority.HIGH,
            related_id=approval_request.id,
            related_type="approval_request"
        )
        
        await notification_repository.add_notification(notification)
        
        # Log activity
        await activity_log_repository.log_activity(AgentActivityLog(
            agent_id=self.agent_id,
            session_id=session_id,
            activity_type=AgentActivityType.APPROVAL_REQUESTED,
            description=f"Requested approval for action: {action}"
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_approval_request",
            {
                "approval_id": approval_request.id,
                "session_id": session_id,
                "agent_id": self.agent_id,
                "action": action,
                "details": details
            }
        )
        
        return approval_request
    
    async def respond_to_approval(
        self,
        approval_id: str,
        approved: bool,
        response: Optional[str] = None
    ) -> AgentApprovalRequest:
        """
        Respond to an approval request.
        
        Args:
            approval_id: Approval request ID
            approved: Whether the action is approved
            response: Optional response message
            
        Returns:
            Updated agent approval request
        """
        # Get approval request
        approval_requests = await chat_session_repository.get_approval_requests()
        approval_request = next((ar for ar in approval_requests if ar.id == approval_id), None)
        
        if not approval_request:
            raise ValueError(f"Approval request not found: {approval_id}")
        
        # Update approval request
        approval_request.approved = approved
        approval_request.response = response
        approval_request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        approval_request.responded_at = datetime.now()
        
        # Save approval request
        approval_request = await chat_session_repository.update_approval_request(approval_request)
        
        # Get session
        session = await chat_session_repository.get_session(approval_request.session_id)
        
        # Create AI message
        status_text = "approved" if approved else "rejected"
        message_content = f"Approval request for '{approval_request.action}' was {status_text}."
        
        if response:
            message_content += f" Response: {response}"
        
        ai_message = ChatMessage(
            session_id=approval_request.session_id,
            content=message_content,
            sender_type=MessageSenderType.SYSTEM,
            sender_id=self.agent_id
        )
        
        await chat_session_repository.add_message(ai_message)
        
        # Log activity
        await activity_log_repository.log_activity(AgentActivityLog(
            agent_id=self.agent_id,
            session_id=approval_request.session_id,
            activity_type=AgentActivityType.APPROVAL_RESPONSE,
            description=f"Approval request {status_text} by user: {approval_request.action}"
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_approval_response",
            {
                "approval_id": approval_request.id,
                "session_id": approval_request.session_id,
                "agent_id": self.agent_id,
                "approved": approved,
                "response": response
            }
        )
        
        # If approved, execute the action
        if approved:
            await self._execute_approved_action(approval_request)
        
        return approval_request
    
    async def delegate_task(
        self,
        session_id: str,
        user_id: str,
        task_type: AgentTaskType,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 3
    ) -> AgentTask:
        """
        Delegate a task to an execution agent.
        
        Args:
            session_id: Session ID
            user_id: User ID
            task_type: Task type
            description: Task description
            context: Optional task context
            priority: Task priority (1-5, where 1 is highest)
            
        Returns:
            Created agent task
        """
        # Determine agent type based on task type
        agent_type = None
        
        if task_type in [AgentTaskType.DOCUMENT_CREATION, AgentTaskType.DOCUMENT_MODIFICATION]:
            agent_type = AgentType.DOCUMENT
        elif task_type in [AgentTaskType.TASK_CREATION, AgentTaskType.TASK_ANALYSIS]:
            agent_type = AgentType.TASK
        elif task_type in [AgentTaskType.DOCUMENT_ANALYSIS, AgentTaskType.PROJECT_ANALYSIS, AgentTaskType.CODE_ANALYSIS]:
            agent_type = AgentType.ANALYSIS
        
        if not agent_type:
            raise ValueError(f"Unknown task type: {task_type}")
        
        # Get appropriate agent
        agents = await agent_repository.get_agents(agent_type=agent_type, active=True)
        
        if not agents:
            raise ValueError(f"No active {agent_type} agents found")
        
        agent = agents[0]
        
        # Create task
        task = AgentTask(
            agent_id=agent.id,
            requested_by=user_id,
            session_id=session_id,
            description=description,
            task_type=task_type,
            priority=priority,
            context=context or {}
        )
        
        # Save task
        task = await agent_task_repository.create_task(task)
        
        # Log activity
        await activity_log_repository.log_activity(AgentActivityLog(
            agent_id=self.agent_id,
            session_id=session_id,
            task_id=task.id,
            activity_type=AgentActivityType.TASK_DELEGATED,
            description=f"Delegated {task_type} task to {agent_type}: {description}"
        ))
        
        # Create notification
        notification = Notification(
            user_id=user_id,
            title="Task Created",
            content=f"A new task has been created: {description}",
            notification_type=NotificationType.TASK_CREATED,
            priority=NotificationPriority.MEDIUM,
            related_id=task.id,
            related_type="task"
        )
        
        await notification_repository.add_notification(notification)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_created",
            {
                "task_id": task.id,
                "session_id": session_id,
                "agent_id": agent.id,
                "task_type": task_type.value,
                "description": description
            }
        )
        
        # Execute task
        asyncio.create_task(self._execute_task(task))
        
        return task
    
    async def _execute_task(self, task: AgentTask) -> None:
        """
        Execute a task.
        
        Args:
            task: Agent task
        """
        try:
            # Update task status
            task, _ = await agent_task_repository.update_task_status(
                task.id,
                AgentTaskStatus.IN_PROGRESS,
                message="Task execution started"
            )
            
            # Execute task
            result = await execution_agent_service.execute_task(task)
            
            # Update task status
            task, _ = await agent_task_repository.update_task_status(
                task.id,
                AgentTaskStatus.COMPLETED,
                message="Task execution completed"
            )
            
            # Get session
            session = await chat_session_repository.get_session(task.session_id)
            
            # Create notification
            notification = Notification(
                user_id=session.user_id,
                title="Task Completed",
                content=f"Task completed: {task.description}",
                notification_type=NotificationType.TASK_COMPLETED,
                priority=NotificationPriority.MEDIUM,
                related_id=task.id,
                related_type="task"
            )
            
            await notification_repository.add_notification(notification)
            
            # Log activity
            await activity_log_repository.log_activity(AgentActivityLog(
                agent_id=task.agent_id,
                session_id=task.session_id,
                task_id=task.id,
                activity_type=AgentActivityType.TASK_COMPLETED,
                description=f"Task completed: {task.description}"
            ))
            
            # Emit event
            await event_service.emit_event(
                "agent_task_completed",
                {
                    "task_id": task.id,
                    "session_id": task.session_id,
                    "agent_id": task.agent_id,
                    "result": result
                }
            )
        
        except Exception as e:
            # Log error
            logger.exception(f"Error executing task: {str(e)}")
            
            # Update task status
            task, _ = await agent_task_repository.update_task_status(
                task.id,
                AgentTaskStatus.FAILED,
                message=f"Task execution failed: {str(e)}"
            )
            
            # Get session
            session = await chat_session_repository.get_session(task.session_id)
            
            # Create notification
            notification = Notification(
                user_id=session.user_id,
                title="Task Failed",
                content=f"Task failed: {task.description}. Error: {str(e)}",
                notification_type=NotificationType.TASK_FAILED,
                priority=NotificationPriority.HIGH,
                related_id=task.id,
                related_type="task"
            )
            
            await notification_repository.add_notification(notification)
            
            # Log activity
            await activity_log_repository.log_activity(AgentActivityLog(
                agent_id=task.agent_id,
                session_id=task.session_id,
                task_id=task.id,
                activity_type=AgentActivityType.TASK_FAILED,
                description=f"Task failed: {task.description}. Error: {str(e)}"
            ))
            
            # Emit event
            await event_service.emit_event(
                "agent_task_failed",
                {
                    "task_id": task.id,
                    "session_id": task.session_id,
                    "agent_id": task.agent_id,
                    "error": str(e)
                }
            )
    
    async def _get_conversation_history(self, session_id: str) -> List[ChatMessage]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of chat messages
        """
        # Get messages
        messages = await chat_session_repository.get_messages(session_id)
        
        # Limit to max context messages
        if len(messages) > self.max_context_messages:
            messages = messages[-self.max_context_messages:]
        
        return messages
    
    async def _prune_context_if_needed(self, messages: List[LLMMessage]) -> List[LLMMessage]:
        """
        Prune context if it exceeds token limit.
        
        Args:
            messages: List of messages
            
        Returns:
            Pruned list of messages
        """
        # Count tokens in messages
        message_dicts = [msg.dict() for msg in messages]
        token_count = await token_manager.count_messages_tokens(message_dicts)
        
        # If within limit, return as is
        if token_count <= self.max_context_tokens:
            return messages
        
        # Keep system message
        system_message = messages[0]
        history_messages = messages[1:]
        
        # Calculate tokens to remove
        tokens_to_remove = token_count - self.max_context_tokens + 1000  # Add buffer
        
        # Remove oldest messages until under limit
        while tokens_to_remove > 0 and history_messages:
            # Remove oldest message
            removed_message = history_messages.pop(0)
            
            # Calculate tokens in removed message
            removed_tokens = await token_manager.count_tokens(removed_message.content)
            tokens_to_remove -= removed_tokens
        
        # Reconstruct messages with system message
        pruned_messages = [system_message] + history_messages
        
        logger.info(f"Pruned context from {token_count} to approximately {self.max_context_tokens} tokens")
        
        return pruned_messages
    
    async def _detect_intent(
        self,
        user_id: str,
        message: str,
        session: ChatSession,
        messages: List[LLMMessage]
    ) -> UserIntent:
        """
        Detect user intent from message.
        
        Args:
            user_id: User ID
            message: User message
            session: Chat session
            messages: Conversation history
            
        Returns:
            Detected intent
        """
        # Create prompt for intent detection
        prompt = f"""
Analyze the user's message and detect the primary intent, any secondary intents, and entities.

User message: {message}

Session context: {json.dumps(session.context or {}, indent=2)}

Respond with a structured analysis of the user's intent.
"""
        
        # Generate correlation ID
        correlation_id = await token_manager.generate_correlation_id(user_id, session.id)
        
        try:
            # Use structured output to get intent
            intent, _, _ = await output_parser.generate_structured_output(
                prompt=prompt,
                schema=UserIntent,
                max_retries=1
            )
            
            return intent
        except Exception as e:
            logger.error(f"Error detecting intent: {str(e)}")
            
            # Return default intent
            return UserIntent(
                primary_intent="general_query",
                secondary_intents=[],
                entities={},
                confidence=0.5,
                requires_clarification=False
            )
    
    def _create_system_prompt(self, session: ChatSession) -> str:
        """
        Create a system prompt for the LLM.
        
        Args:
            session: Chat session
            
        Returns:
            System prompt
        """
        # Create system prompt
        system_prompt = f"""
You are an AI assistant for the AI Project Assistant platform. Your role is to help users manage their software projects through documentation, task management, and AI-assisted interactions.

Key capabilities:
1. Create and modify project documentation
2. Generate task definitions based on requirements
3. Analyze project structure and relationships
4. Answer questions about software development
5. Provide guidance on best practices

When users ask you to perform actions like creating documents or analyzing code, you should delegate these tasks to specialized execution agents rather than trying to perform them directly.

Always be helpful, clear, and concise in your responses. If you don't know something, admit it rather than making up information.

You can ask clarifying questions when needed to better understand the user's request.

You can create and modify documents, analyze code, and perform other project-related tasks by delegating to specialized agents.

Current date and time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        # Add session context if available
        if session.context:
            context_str = json.dumps(session.context, indent=2)
            system_prompt += f"\n\nSession Context:\n{context_str}"
        
        return system_prompt
    
    async def _process_agent_actions(
        self,
        session: ChatSession,
        user_id: str,
        user_message: str,
        ai_response: str
    ) -> None:
        """
        Process agent actions from the AI response.
        
        Args:
            session: Chat session
            user_id: User ID
            user_message: User message
            ai_response: AI response
        """
        try:
            # Create prompt for action detection
            prompt = f"""
Analyze the conversation and determine if any actions need to be taken.

User message: {user_message}

AI response: {ai_response}

Session context: {json.dumps(session.context or {}, indent=2)}

Identify any actions that should be performed based on this conversation, such as:
1. Creating or modifying documents
2. Creating tasks
3. Analyzing code or documents
4. Asking the user for more information
5. Requesting approval for significant actions

Respond with a structured analysis of the actions to take.
"""
            
            # Use structured output to get actions
            response, _, _ = await output_parser.generate_structured_output(
                prompt=prompt,
                schema=AgentResponse,
                max_retries=1
            )
            
            # Process actions
            if response and response.actions:
                for action in response.actions:
                    action_type = action.get("type")
                    
                    if action_type == "create_document":
                        # Delegate document creation task
                        await self.delegate_task(
                            session_id=session.id,
                            user_id=user_id,
                            task_type=AgentTaskType.DOCUMENT_CREATION,
                            description=action.get("description", "Create document"),
                            context=action.get("parameters", {})
                        )
                    
                    elif action_type == "modify_document":
                        # Delegate document modification task
                        await self.delegate_task(
                            session_id=session.id,
                            user_id=user_id,
                            task_type=AgentTaskType.DOCUMENT_MODIFICATION,
                            description=action.get("description", "Modify document"),
                            context=action.get("parameters", {})
                        )
                    
                    elif action_type == "analyze_document":
                        # Delegate document analysis task
                        await self.delegate_task(
                            session_id=session.id,
                            user_id=user_id,
                            task_type=AgentTaskType.DOCUMENT_ANALYSIS,
                            description=action.get("description", "Analyze document"),
                            context=action.get("parameters", {})
                        )
                    
                    elif action_type == "create_task":
                        # Delegate task creation
                        await self.delegate_task(
                            session_id=session.id,
                            user_id=user_id,
                            task_type=AgentTaskType.TASK_CREATION,
                            description=action.get("description", "Create task"),
                            context=action.get("parameters", {})
                        )
                    
                    elif action_type == "ask_question":
                        # Ask question to user
                        question_text = action.get("question", "")
                        question_type_str = action.get("question_type", "text")
                        
                        question_type = QuestionType.TEXT
                        if question_type_str == "yes_no":
                            question_type = QuestionType.YES_NO
                        elif question_type_str == "multiple_choice":
                            question_type = QuestionType.MULTIPLE_CHOICE
                        
                        await self.ask_question(
                            session_id=session.id,
                            question=question_text,
                            question_type=question_type,
                            options=action.get("options"),
                            context=action.get("context", {})
                        )
                    
                    elif action_type == "request_approval":
                        # Request approval
                        await self.request_approval(
                            session_id=session.id,
                            action=action.get("description", ""),
                            details=action.get("parameters", {}),
                            context=action.get("context", {})
                        )
            
            # Update session context if needed
            if response and response.context_updates:
                if session.context is None:
                    session.context = {}
                
                session.context.update(response.context_updates)
                await chat_session_repository.update_session(session)
        
        except Exception as e:
            logger.error(f"Error processing agent actions: {str(e)}")
    
    async def _execute_approved_action(self, approval_request: AgentApprovalRequest) -> None:
        """
        Execute an approved action.
        
        Args:
            approval_request: Agent approval request
        """
        try:
            # Get action details
            action = approval_request.action
            details = approval_request.details
            
            # Log action
            logger.info(f"Executing approved action: {action}")
            
            # Execute based on action type
            if "create_document" in action.lower():
                # Delegate document creation task
                await self.delegate_task(
                    session_id=approval_request.session_id,
                    user_id=details.get("user_id"),
                    task_type=AgentTaskType.DOCUMENT_CREATION,
                    description=f"Create document: {details.get('document_name', '')}",
                    context=details
                )
            
            elif "modify_document" in action.lower():
                # Delegate document modification task
                await self.delegate_task(
                    session_id=approval_request.session_id,
                    user_id=details.get("user_id"),
                    task_type=AgentTaskType.DOCUMENT_MODIFICATION,
                    description=f"Modify document: {details.get('document_name', '')}",
                    context=details
                )
            
            elif "delete_document" in action.lower():
                # Handle document deletion
                document_id = details.get("document_id")
                if document_id:
                    # In a real implementation, this would delete the document
                    logger.info(f"Document deletion approved: {document_id}")
                    
                    # Create notification
                    notification = Notification(
                        user_id=details.get("user_id"),
                        title="Document Deleted",
                        content=f"Document '{details.get('document_name', '')}' has been deleted",
                        notification_type=NotificationType.DOCUMENT_CREATED,
                        priority=NotificationPriority.MEDIUM,
                        related_id=document_id,
                        related_type="document"
                    )
                    
                    await notification_repository.add_notification(notification)
            
            elif "create_task" in action.lower():
                # Delegate task creation
                await self.delegate_task(
                    session_id=approval_request.session_id,
                    user_id=details.get("user_id"),
                    task_type=AgentTaskType.TASK_CREATION,
                    description=f"Create task: {details.get('task_name', '')}",
                    context=details
                )
            
            # Log completion
            logger.info(f"Approved action executed: {action}")
            
            # Create notification
            notification = Notification(
                user_id=details.get("user_id"),
                title="Action Completed",
                content=f"The approved action '{action}' has been completed",
                notification_type=NotificationType.SYSTEM,
                priority=NotificationPriority.MEDIUM,
                related_id=approval_request.id,
                related_type="approval_request"
            )
            
            await notification_repository.add_notification(notification)
        
        except Exception as e:
            logger.error(f"Error executing approved action: {str(e)}")
            
            # Create error notification
            notification = Notification(
                user_id=approval_request.details.get("user_id"),
                title="Action Failed",
                content=f"The approved action '{approval_request.action}' failed: {str(e)}",
                notification_type=NotificationType.SYSTEM,
                priority=NotificationPriority.HIGH,
                related_id=approval_request.id,
                related_type="approval_request"
            )
            
            await notification_repository.add_notification(notification)


# Create singleton instance
conversation_agent_service = ConversationAgentService()