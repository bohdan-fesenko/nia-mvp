"""
Agent repository for the AI Project Assistant.
This module provides database operations for agents, tasks, chat sessions, and related entities.
"""
from typing import Dict, List, Any, Optional, Union, Tuple
import json
import asyncio
from datetime import datetime
import uuid
from loguru import logger

from ..models.agent import (
    Agent, AgentTask, TaskExecutionStep, TaskStatusUpdate, ChatSession, ChatMessage,
    AgentQuestion, AgentApprovalRequest, Notification, AgentActivityLog, DocumentDiff,
    AgentType, AgentTaskStatus, AgentTaskType, MessageSenderType, QuestionType,
    ApprovalStatus, NotificationType, NotificationPriority, AgentActivityType
)


class AgentRepository:
    """Repository for agent operations."""
    
    async def create_agent(self, agent: Agent) -> Agent:
        """
        Create a new agent.
        
        Args:
            agent: Agent to create
            
        Returns:
            Created agent
        """
        # This is a placeholder implementation
        # In a real implementation, this would store the agent in the database
        
        # For now, just return the agent
        logger.info(f"Created agent: {agent.id} ({agent.type})")
        return agent
    
    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """
        Get an agent by ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent if found, None otherwise
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve the agent from the database
        
        # For now, return a mock agent
        agent = Agent(
            id=agent_id,
            name="Mock Agent",
            type=AgentType.CONVERSATION,
            description="Mock agent for testing",
            capabilities=["chat", "task_delegation"]
        )
        
        return agent
    
    async def get_agents(
        self,
        agent_type: Optional[AgentType] = None,
        active: Optional[bool] = None
    ) -> List[Agent]:
        """
        Get agents.
        
        Args:
            agent_type: Optional agent type filter
            active: Optional active status filter
            
        Returns:
            List of agents
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve agents from the database
        
        # For now, return mock agents
        agents = []
        
        # Add conversation agent
        if agent_type is None or agent_type == AgentType.CONVERSATION:
            agents.append(Agent(
                id="a60e8400-e29b-41d4-a716-446655440000",
                name="Conversation Agent",
                type=AgentType.CONVERSATION,
                description="Main agent for handling user interactions and delegating tasks",
                capabilities=["chat", "task_delegation", "document_creation"]
            ))
        
        # Add document agent
        if agent_type is None or agent_type == AgentType.DOCUMENT:
            agents.append(Agent(
                id="a70e8400-e29b-41d4-a716-446655440000",
                name="Document Agent",
                type=AgentType.DOCUMENT,
                description="Specialized agent for document operations",
                capabilities=["document_creation", "document_modification", "markdown_generation"]
            ))
        
        # Add task agent
        if agent_type is None or agent_type == AgentType.TASK:
            agents.append(Agent(
                id="a80e8400-e29b-41d4-a716-446655440000",
                name="Task Agent",
                type=AgentType.TASK,
                description="Specialized agent for task operations",
                capabilities=["task_creation", "task_analysis", "task_tracking"]
            ))
        
        # Add analysis agent
        if agent_type is None or agent_type == AgentType.ANALYSIS:
            agents.append(Agent(
                id="a90e8400-e29b-41d4-a716-446655440000",
                name="Analysis Agent",
                type=AgentType.ANALYSIS,
                description="Specialized agent for analysis operations",
                capabilities=["document_analysis", "project_analysis", "code_analysis"]
            ))
        
        # Filter by active status if provided
        if active is not None:
            agents = [agent for agent in agents if agent.active == active]
        
        return agents
    
    async def update_agent(self, agent: Agent) -> Agent:
        """
        Update an agent.
        
        Args:
            agent: Agent to update
            
        Returns:
            Updated agent
        """
        # This is a placeholder implementation
        # In a real implementation, this would update the agent in the database
        
        # For now, just return the agent
        logger.info(f"Updated agent: {agent.id}")
        return agent


class AgentTaskRepository:
    """Repository for agent task operations."""
    
    async def create_task(self, task: AgentTask) -> AgentTask:
        """
        Create a new task.
        
        Args:
            task: Task to create
            
        Returns:
            Created task
        """
        # This is a placeholder implementation
        # In a real implementation, this would store the task in the database
        
        # For now, just return the task
        logger.info(f"Created task: {task.id} ({task.task_type})")
        return task
    
    async def get_task(self, task_id: str) -> Optional[AgentTask]:
        """
        Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task if found, None otherwise
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve the task from the database
        
        # For now, return a mock task
        task = AgentTask(
            id=task_id,
            agent_id="a70e8400-e29b-41d4-a716-446655440000",
            requested_by="550e8400-e29b-41d4-a716-446655440000",
            description="Mock task for testing",
            task_type=AgentTaskType.DOCUMENT_CREATION,
            status=AgentTaskStatus.PENDING
        )
        
        return task
    
    async def get_tasks(
        self,
        agent_id: Optional[str] = None,
        status: Optional[AgentTaskStatus] = None,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentTask]:
        """
        Get tasks.
        
        Args:
            agent_id: Optional agent ID filter
            status: Optional status filter
            session_id: Optional session ID filter
            limit: Maximum number of tasks to return
            
        Returns:
            List of tasks
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve tasks from the database
        
        # For now, return mock tasks
        tasks = []
        
        # Add document creation task
        tasks.append(AgentTask(
            id="d80e8400-e29b-41d4-a716-446655440000",
            agent_id="a70e8400-e29b-41d4-a716-446655440000",
            requested_by="550e8400-e29b-41d4-a716-446655440000",
            description="Create a new document",
            task_type=AgentTaskType.DOCUMENT_CREATION,
            status=AgentTaskStatus.COMPLETED,
            session_id="i50e8400-e29b-41d4-a716-446655440000",
            result_document_id="950e8400-e29b-41d4-a716-446655440000"
        ))
        
        # Add document modification task
        tasks.append(AgentTask(
            id="d90e8400-e29b-41d4-a716-446655440000",
            agent_id="a70e8400-e29b-41d4-a716-446655440000",
            requested_by="550e8400-e29b-41d4-a716-446655440000",
            description="Modify document",
            task_type=AgentTaskType.DOCUMENT_MODIFICATION,
            status=AgentTaskStatus.IN_PROGRESS,
            session_id="i50e8400-e29b-41d4-a716-446655440000"
        ))
        
        # Filter by agent ID if provided
        if agent_id:
            tasks = [task for task in tasks if task.agent_id == agent_id]
        
        # Filter by status if provided
        if status:
            tasks = [task for task in tasks if task.status == status]
        
        # Filter by session ID if provided
        if session_id:
            tasks = [task for task in tasks if task.session_id == session_id]
        
        # Limit number of tasks
        tasks = tasks[:limit]
        
        return tasks
    
    async def update_task(self, task: AgentTask) -> AgentTask:
        """
        Update a task.
        
        Args:
            task: Task to update
            
        Returns:
            Updated task
        """
        # This is a placeholder implementation
        # In a real implementation, this would update the task in the database
        
        # For now, just return the task
        logger.info(f"Updated task: {task.id}")
        return task
    
    async def update_task_status(
        self,
        task_id: str,
        status: AgentTaskStatus,
        progress_percentage: Optional[int] = None,
        message: Optional[str] = None
    ) -> Tuple[AgentTask, TaskStatusUpdate]:
        """
        Update a task's status.
        
        Args:
            task_id: Task ID
            status: New status
            progress_percentage: Optional progress percentage
            message: Optional status message
            
        Returns:
            Tuple of updated task and status update
        """
        # This is a placeholder implementation
        # In a real implementation, this would update the task in the database
        
        # Get task
        task = await self.get_task(task_id)
        
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        # Create status update
        status_update = TaskStatusUpdate(
            task_id=task_id,
            previous_status=task.status,
            new_status=status,
            progress_percentage=progress_percentage,
            message=message
        )
        
        # Update task
        task.status = status
        
        if status == AgentTaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = datetime.now()
        
        if status in [AgentTaskStatus.COMPLETED, AgentTaskStatus.FAILED, AgentTaskStatus.CANCELLED]:
            task.completed_at = datetime.now()
        
        # Save task
        task = await self.update_task(task)
        
        # Save status update
        # In a real implementation, this would store the status update in the database
        logger.info(f"Updated task status: {task_id} -> {status}")
        
        return task, status_update
    
    async def add_task_step(self, step: TaskExecutionStep) -> TaskExecutionStep:
        """
        Add a task execution step.
        
        Args:
            step: Task execution step
            
        Returns:
            Added task execution step
        """
        # This is a placeholder implementation
        # In a real implementation, this would store the step in the database
        
        # For now, just return the step
        logger.info(f"Added task step: {step.task_id} -> {step.description}")
        return step
    
    async def update_task_step(self, step: TaskExecutionStep) -> TaskExecutionStep:
        """
        Update a task execution step.
        
        Args:
            step: Task execution step
            
        Returns:
            Updated task execution step
        """
        # This is a placeholder implementation
        # In a real implementation, this would update the step in the database
        
        # For now, just return the step
        logger.info(f"Updated task step: {step.task_id} -> {step.description}")
        return step
    
    async def get_task_steps(self, task_id: str) -> List[TaskExecutionStep]:
        """
        Get task execution steps.
        
        Args:
            task_id: Task ID
            
        Returns:
            List of task execution steps
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve steps from the database
        
        # For now, return mock steps
        steps = []
        
        # Add steps
        steps.append(TaskExecutionStep(
            id="e90e8400-e29b-41d4-a716-446655440000",
            task_id=task_id,
            step_number=1,
            description="Analyze requirements",
            status=AgentTaskStatus.COMPLETED,
            completed_at=datetime.now()
        ))
        
        steps.append(TaskExecutionStep(
            id="ea0e8400-e29b-41d4-a716-446655440000",
            task_id=task_id,
            step_number=2,
            description="Generate content",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        return steps


class ChatSessionRepository:
    """Repository for chat session operations."""
    
    async def create_session(self, session: ChatSession) -> ChatSession:
        """
        Create a new chat session.
        
        Args:
            session: Chat session to create
            
        Returns:
            Created chat session
        """
        # This is a placeholder implementation
        # In a real implementation, this would store the session in the database
        
        # For now, just return the session
        logger.info(f"Created chat session: {session.id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Get a chat session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Chat session if found, None otherwise
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve the session from the database
        
        # For now, return a mock session
        session = ChatSession(
            id=session_id,
            user_id="550e8400-e29b-41d4-a716-446655440000",
            title="Mock Session"
        )
        
        return session
    
    async def get_sessions(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[ChatSession]:
        """
        Get chat sessions for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of sessions to return
            
        Returns:
            List of chat sessions
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve sessions from the database
        
        # For now, return mock sessions
        sessions = []
        
        # Add sessions
        sessions.append(ChatSession(
            id="i50e8400-e29b-41d4-a716-446655440000",
            user_id=user_id,
            title="Project Discussion"
        ))
        
        sessions.append(ChatSession(
            id="i60e8400-e29b-41d4-a716-446655440000",
            user_id=user_id,
            title="Document Creation"
        ))
        
        # Limit number of sessions
        sessions = sessions[:limit]
        
        return sessions
    
    async def update_session(self, session: ChatSession) -> ChatSession:
        """
        Update a chat session.
        
        Args:
            session: Chat session to update
            
        Returns:
            Updated chat session
        """
        # This is a placeholder implementation
        # In a real implementation, this would update the session in the database
        
        # For now, just return the session
        logger.info(f"Updated chat session: {session.id}")
        return session
    
    async def add_message(self, message: ChatMessage) -> ChatMessage:
        """
        Add a message to a chat session.
        
        Args:
            message: Chat message
            
        Returns:
            Added chat message
        """
        # This is a placeholder implementation
        # In a real implementation, this would store the message in the database
        
        # For now, just return the message
        logger.info(f"Added chat message: {message.session_id} -> {message.content[:50]}...")
        return message
    
    async def get_messages(
        self,
        session_id: str,
        limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get messages for a chat session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            
        Returns:
            List of chat messages
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve messages from the database
        
        # For now, return mock messages
        messages = []
        
        # Add user message
        messages.append(ChatMessage(
            id="j50e8400-e29b-41d4-a716-446655440000",
            session_id=session_id,
            content="Can you help me create a project charter?",
            sender_type=MessageSenderType.USER,
            sender_id="550e8400-e29b-41d4-a716-446655440000",
            created_at=datetime.now()
        ))
        
        # Add AI message
        messages.append(ChatMessage(
            id="j60e8400-e29b-41d4-a716-446655440000",
            session_id=session_id,
            content="I'd be happy to help you create a project charter. Let me ask you a few questions to get started.",
            sender_type=MessageSenderType.AI,
            sender_id="a60e8400-e29b-41d4-a716-446655440000",
            created_at=datetime.now()
        ))
        
        # Limit number of messages
        messages = messages[:limit]
        
        return messages
    
    async def add_question(self, question: AgentQuestion) -> AgentQuestion:
        """
        Add a question.
        
        Args:
            question: Agent question
            
        Returns:
            Added agent question
        """
        # This is a placeholder implementation
        # In a real implementation, this would store the question in the database
        
        # For now, just return the question
        logger.info(f"Added question: {question.session_id} -> {question.question}")
        return question
    
    async def update_question(self, question: AgentQuestion) -> AgentQuestion:
        """
        Update a question.
        
        Args:
            question: Agent question
            
        Returns:
            Updated agent question
        """
        # This is a placeholder implementation
        # In a real implementation, this would update the question in the database
        
        # For now, just return the question
        logger.info(f"Updated question: {question.id} -> {question.answer}")
        return question
    
    async def get_questions(
        self,
        session_id: Optional[str] = None,
        answered: Optional[bool] = None,
        limit: int = 100
    ) -> List[AgentQuestion]:
        """
        Get questions.
        
        Args:
            session_id: Optional session ID filter
            answered: Optional answered status filter
            limit: Maximum number of questions to return
            
        Returns:
            List of agent questions
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve questions from the database
        
        # For now, return mock questions
        questions = []
        
        # Add questions
        questions.append(AgentQuestion(
            id="k50e8400-e29b-41d4-a716-446655440000",
            session_id="i50e8400-e29b-41d4-a716-446655440000",
            agent_id="a60e8400-e29b-41d4-a716-446655440000",
            question="What is the name of your project?",
            question_type=QuestionType.TEXT,
            answer="AI Project Assistant"
        ))
        
        questions.append(AgentQuestion(
            id="k60e8400-e29b-41d4-a716-446655440000",
            session_id="i50e8400-e29b-41d4-a716-446655440000",
            agent_id="a60e8400-e29b-41d4-a716-446655440000",
            question="Do you want to include a risk assessment section?",
            question_type=QuestionType.YES_NO
        ))
        
        # Filter by session ID if provided
        if session_id:
            questions = [q for q in questions if q.session_id == session_id]
        
        # Filter by answered status if provided
        if answered is not None:
            questions = [q for q in questions if (q.answer is not None) == answered]
        
        # Limit number of questions
        questions = questions[:limit]
        
        return questions
    
    async def add_approval_request(self, approval_request: AgentApprovalRequest) -> AgentApprovalRequest:
        """
        Add an approval request.
        
        Args:
            approval_request: Agent approval request
            
        Returns:
            Added agent approval request
        """
        # This is a placeholder implementation
        # In a real implementation, this would store the approval request in the database
        
        # For now, just return the approval request
        logger.info(f"Added approval request: {approval_request.session_id} -> {approval_request.action}")
        return approval_request
    
    async def update_approval_request(self, approval_request: AgentApprovalRequest) -> AgentApprovalRequest:
        """
        Update an approval request.
        
        Args:
            approval_request: Agent approval request
            
        Returns:
            Updated agent approval request
        """
        # This is a placeholder implementation
        # In a real implementation, this would update the approval request in the database
        
        # For now, just return the approval request
        logger.info(f"Updated approval request: {approval_request.id} -> {approval_request.status}")
        return approval_request
    
    async def get_approval_requests(
        self,
        session_id: Optional[str] = None,
        status: Optional[ApprovalStatus] = None,
        limit: int = 100
    ) -> List[AgentApprovalRequest]:
        """
        Get approval requests.
        
        Args:
            session_id: Optional session ID filter
            status: Optional status filter
            limit: Maximum number of approval requests to return
            
        Returns:
            List of agent approval requests
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve approval requests from the database
        
        # For now, return mock approval requests
        approval_requests = []
        
        # Add approval requests
        approval_requests.append(AgentApprovalRequest(
            id="l50e8400-e29b-41d4-a716-446655440000",
            session_id="i50e8400-e29b-41d4-a716-446655440000",
            agent_id="a60e8400-e29b-41d4-a716-446655440000",
            action="Create a new project charter document",
            details={
                "document_name": "project_charter.md",
                "document_type": "markdown"
            },
            status=ApprovalStatus.APPROVED,
            approved=True
        ))
        
        approval_requests.append(AgentApprovalRequest(
            id="l60e8400-e29b-41d4-a716-446655440000",
            session_id="i50e8400-e29b-41d4-a716-446655440000",
            agent_id="a60e8400-e29b-41d4-a716-446655440000",
            action="Modify the project charter document",
            details={
                "document_id": "950e8400-e29b-41d4-a716-446655440000",
                "changes": "Add risk assessment section"
            },
            status=ApprovalStatus.PENDING
        ))
        
        # Filter by session ID if provided
        if session_id:
            approval_requests = [ar for ar in approval_requests if ar.session_id == session_id]
        
        # Filter by status if provided
        if status:
            approval_requests = [ar for ar in approval_requests if ar.status == status]
        
        # Limit number of approval requests
        approval_requests = approval_requests[:limit]
        
        return approval_requests


class NotificationRepository:
    """Repository for notification operations."""
    
    async def add_notification(self, notification: Notification) -> Notification:
        """
        Add a notification.
        
        Args:
            notification: Notification
            
        Returns:
            Added notification
        """
        # This is a placeholder implementation
        # In a real implementation, this would store the notification in the database
        
        # For now, just return the notification
        logger.info(f"Added notification: {notification.user_id} -> {notification.title}")
        return notification
    
    async def get_notification(self, notification_id: str) -> Optional[Notification]:
        """
        Get a notification by ID.
        
        Args:
            notification_id: Notification ID
            
        Returns:
            Notification if found, None otherwise
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve the notification from the database
        
        # For now, return a mock notification
        notification = Notification(
            id=notification_id,
            user_id="550e8400-e29b-41d4-a716-446655440000",
            title="Mock Notification",
            content="This is a mock notification for testing",
            notification_type=NotificationType.SYSTEM
        )
        
        return notification
    
    async def get_notifications(
        self,
        user_id: str,
        is_read: Optional[bool] = None,
        notification_type: Optional[NotificationType] = None,
        limit: int = 100
    ) -> List[Notification]:
        """
        Get notifications for a user.
        
        Args:
            user_id: User ID
            is_read: Optional read status filter
            notification_type: Optional notification type filter
            limit: Maximum number of notifications to return
            
        Returns:
            List of notifications
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve notifications from the database
        
        # For now, return mock notifications
        notifications = []
        
        # Add notifications
        notifications.append(Notification(
            id="m50e8400-e29b-41d4-a716-446655440000",
            user_id=user_id,
            title="Task Created",
            content="A new task has been created: Create a project charter",
            notification_type=NotificationType.TASK_CREATED,
            priority=NotificationPriority.MEDIUM,
            related_id="d80e8400-e29b-41d4-a716-446655440000",
            related_type="task",
            is_read=True
        ))
        
        notifications.append(Notification(
            id="m60e8400-e29b-41d4-a716-446655440000",
            user_id=user_id,
            title="Question",
            content="The AI assistant has a question: Do you want to include a risk assessment section?",
            notification_type=NotificationType.QUESTION,
            priority=NotificationPriority.HIGH,
            related_id="k60e8400-e29b-41d4-a716-446655440000",
            related_type="question",
            is_read=False
        ))
        
        # Filter by read status if provided
        if is_read is not None:
            notifications = [n for n in notifications if n.is_read == is_read]
        
        # Filter by notification type if provided
        if notification_type:
            notifications = [n for n in notifications if n.notification_type == notification_type]
        
        # Limit number of notifications
        notifications = notifications[:limit]
        
        return notifications
    
    async def mark_notification_read(
        self,
        notification_id: str,
        is_read: bool = True
    ) -> Notification:
        """
        Mark a notification as read or unread.
        
        Args:
            notification_id: Notification ID
            is_read: Whether the notification is read
            
        Returns:
            Updated notification
        """
        # This is a placeholder implementation
        # In a real implementation, this would update the notification in the database
        
        # Get notification
        notification = await self.get_notification(notification_id)
        
        if not notification:
            raise ValueError(f"Notification not found: {notification_id}")
        
        # Update notification
        notification.is_read = is_read
        
        if is_read and not notification.read_at:
            notification.read_at = datetime.now()
        
        # Save notification
        # In a real implementation, this would update the notification in the database
        logger.info(f"Marked notification as {'read' if is_read else 'unread'}: {notification_id}")
        
        return notification


class ActivityLogRepository:
    """Repository for activity log operations."""
    
    async def log_activity(self, activity: AgentActivityLog) -> AgentActivityLog:
        """
        Log an agent activity.
        
        Args:
            activity: Agent activity log
            
        Returns:
            Added agent activity log
        """
        # This is a placeholder implementation
        # In a real implementation, this would store the activity in the database
        
        # For now, just return the activity
        logger.info(f"Logged activity: {activity.agent_id} -> {activity.activity_type}: {activity.description[:50]}...")
        return activity
    
    async def get_activities(
        self,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        document_id: Optional[str] = None,
        activity_type: Optional[AgentActivityType] = None,
        limit: int = 100
    ) -> List[AgentActivityLog]:
        """
        Get agent activities.
        
        Args:
            agent_id: Optional agent ID filter
            session_id: Optional session ID filter
            task_id: Optional task ID filter
            document_id: Optional document ID filter
            activity_type: Optional activity type filter
            limit: Maximum number of activities to return
            
        Returns:
            List of agent activity logs
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve activities from the database
        
        # For now, return mock activities
        activities = []
        
        # Add activities
        activities.append(AgentActivityLog(
            id="n50e8400-e29b-41d4-a716-446655440000",
            agent_id="a60e8400-e29b-41d4-a716-446655440000",
            session_id="i50e8400-e29b-41d4-a716-446655440000",
            activity_type=AgentActivityType.SESSION_CREATED,
            description="Created new chat session"
        ))
        
        activities.append(AgentActivityLog(
            id="n60e8400-e29b-41d4-a716-446655440000",
            agent_id="a60e8400-e29b-41d4-a716-446655440000",
            session_id="i50e8400-e29b-41d4-a716-446655440000",
            task_id="d80e8400-e29b-41d4-a716-446655440000",
            activity_type=AgentActivityType.TASK_DELEGATED,
            description="Delegated document creation task to document_agent"
        ))
        
        # Filter by agent ID if provided
        if agent_id:
            activities = [a for a in activities if a.agent_id == agent_id]
        
        # Filter by session ID if provided
        if session_id:
            activities = [a for a in activities if a.session_id == session_id]
        
        # Filter by task ID if provided
        if task_id:
            activities = [a for a in activities if a.task_id == task_id]
        
        # Filter by document ID if provided
        if document_id:
            activities = [a for a in activities if a.document_id == document_id]
        
        # Filter by activity type if provided
        if activity_type:
            activities = [a for a in activities if a.activity_type == activity_type]
        
        # Limit number of activities
        activities = activities[:limit]
        
        return activities
    
    async def add_document_diff(self, document_diff: DocumentDiff) -> DocumentDiff:
        """
        Add a document diff.
        
        Args:
            document_diff: Document diff
            
        Returns:
            Added document diff
        """
        # This is a placeholder implementation
        # In a real implementation, this would store the document diff in the database
        
        # For now, just return the document diff
        logger.info(f"Added document diff: {document_diff.document_id}")
        return document_diff
    
    async def get_document_diffs(
        self,
        document_id: str,
        limit: int = 100
    ) -> List[DocumentDiff]:
        """
        Get document diffs.
        
        Args:
            document_id: Document ID
            limit: Maximum number of diffs to return
            
        Returns:
            List of document diffs
        """
        # This is a placeholder implementation
        # In a real implementation, this would retrieve document diffs from the database
        
        # For now, return mock diffs
        diffs = []
        
        # Add diffs
        diffs.append(DocumentDiff(
            id="o50e8400-e29b-41d4-a716-446655440000",
            document_id=document_id,
            before_content="# Document\n\nThis is the current document content.",
            after_content="# Document\n\nThis is the current document content.\n\n## New Section\n\nThis is a new section added to the document.",
            changes=[
                {
                    "type": "add",
                    "before_start": 3,
                    "before_count": 0,
                    "after_start": 3,
                    "after_count": 2,
                    "before_lines": [],
                    "after_lines": [
                        "",
                        "## New Section",
                        "",
                        "This is a new section added to the document."
                    ]
                }
            ],
            created_by="a70e8400-e29b-41d4-a716-446655440000",
            task_id="d90e8400-e29b-41d4-a716-446655440000"
        ))
        
        # Limit number of diffs
        diffs = diffs[:limit]
        
        return diffs


# Create singleton instances
agent_repository = AgentRepository()
agent_task_repository = AgentTaskRepository()
chat_session_repository = ChatSessionRepository()
notification_repository = NotificationRepository()
activity_log_repository = ActivityLogRepository()