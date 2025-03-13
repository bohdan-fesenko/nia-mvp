"""
Execution Agent Service for the AI Project Assistant.
This module provides specialized agent services for executing tasks.
"""
from typing import Dict, List, Any, Optional, Union, Tuple, AsyncGenerator
import json
import asyncio
from datetime import datetime
import uuid
from loguru import logger
from pydantic import BaseModel, Field

from ..models.agent import (
    Agent, AgentTask, TaskExecutionStep, TaskStatusUpdate, AgentActivityLog,
    AgentType, AgentTaskType, AgentTaskStatus, AgentActivityType, DocumentDiff
)
from ..repositories.agent_repository import (
    agent_repository, agent_task_repository, activity_log_repository
)
from ..services.llm_service import llm_service, structured_llm_service, LLMMessage
from ..services.event_service import event_service
from ..services.token_manager import token_manager
from ..services.output_parser import output_parser
from ..config import settings


# Define structured output schemas
class DocumentContent(BaseModel):
    """Model for document content generation."""
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content in Markdown format")
    sections: List[Dict[str, Any]] = Field(default_factory=list, description="Document sections")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")


class DocumentAnalysis(BaseModel):
    """Model for document analysis results."""
    summary: str = Field(..., description="Summary of the document")
    strengths: List[str] = Field(default_factory=list, description="Document strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Document weaknesses")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")
    missing_sections: List[str] = Field(default_factory=list, description="Missing sections or information")
    overall_assessment: str = Field(..., description="Overall assessment of the document")


class TaskDefinition(BaseModel):
    """Model for task definition generation."""
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Acceptance criteria")
    implementation_details: str = Field(..., description="Implementation details")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    estimated_effort: str = Field(..., description="Estimated effort")
    priority: str = Field(..., description="Task priority")
    notes: Optional[str] = Field(None, description="Additional notes")


class ExecutionAgentService:
    """Service for execution agent operations."""
    
    def __init__(self):
        """Initialize the execution agent service."""
        self.document_agent_id = "a70e8400-e29b-41d4-a716-446655440000"
        self.task_agent_id = "a80e8400-e29b-41d4-a716-446655440000"
        self.analysis_agent_id = "a90e8400-e29b-41d4-a716-446655440000"
        self.initialized = False
    
    async def initialize(self):
        """Initialize the execution agent service."""
        if self.initialized:
            return
        
        # Register document agent
        document_agent = Agent(
            id=self.document_agent_id,
            name="Document Agent",
            type=AgentType.DOCUMENT,
            description="Specialized agent for document operations",
            capabilities=["document_creation", "document_modification", "markdown_generation"]
        )
        
        await agent_repository.create_agent(document_agent)
        
        # Register task agent
        task_agent = Agent(
            id=self.task_agent_id,
            name="Task Agent",
            type=AgentType.TASK,
            description="Specialized agent for task operations",
            capabilities=["task_creation", "task_analysis", "task_tracking"]
        )
        
        await agent_repository.create_agent(task_agent)
        
        # Register analysis agent
        analysis_agent = Agent(
            id=self.analysis_agent_id,
            name="Analysis Agent",
            type=AgentType.ANALYSIS,
            description="Specialized agent for analysis operations",
            capabilities=["document_analysis", "project_analysis", "code_analysis"]
        )
        
        await agent_repository.create_agent(analysis_agent)
        
        logger.info("Execution agents initialized")
        self.initialized = True
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a task.
        
        Args:
            task: Agent task
            
        Returns:
            Task execution result
        """
        # Log activity
        await activity_log_repository.log_activity(AgentActivityLog(
            agent_id=task.agent_id,
            session_id=task.session_id,
            task_id=task.id,
            activity_type=AgentActivityType.TASK_STARTED,
            description=f"Started executing task: {task.description}"
        ))
        
        # Emit event
        await event_service.publish(
            "agent_task_started",
            {
                "task_id": task.id,
                "session_id": task.session_id,
                "agent_id": task.agent_id,
                "task_type": task.task_type.value,
                "description": task.description
            }
        )
        
        # Execute task based on type
        if task.task_type == AgentTaskType.DOCUMENT_CREATION:
            return await self._execute_document_creation_task(task)
        elif task.task_type == AgentTaskType.DOCUMENT_MODIFICATION:
            return await self._execute_document_modification_task(task)
        elif task.task_type == AgentTaskType.DOCUMENT_ANALYSIS:
            return await self._execute_document_analysis_task(task)
        elif task.task_type == AgentTaskType.TASK_CREATION:
            return await self._execute_task_creation_task(task)
        elif task.task_type == AgentTaskType.TASK_ANALYSIS:
            return await self._execute_task_analysis_task(task)
        elif task.task_type == AgentTaskType.PROJECT_ANALYSIS:
            return await self._execute_project_analysis_task(task)
        elif task.task_type == AgentTaskType.CODE_GENERATION:
            return await self._execute_code_generation_task(task)
        elif task.task_type == AgentTaskType.CODE_ANALYSIS:
            return await self._execute_code_analysis_task(task)
        else:
            raise ValueError(f"Unsupported task type: {task.task_type}")
    
    async def _execute_document_creation_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a document creation task.
        
        Args:
            task: Agent task
            
        Returns:
            Task execution result
        """
        # Add task step
        step1 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=1,
            description="Analyze requirements and context",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number,
                "description": step1.description
            }
        )
        
        # Analyze requirements
        # This is a placeholder implementation
        # In a real implementation, this would analyze the task context
        await asyncio.sleep(1)  # Simulate processing time
        
        # Update step status
        step1.status = AgentTaskStatus.COMPLETED
        step1.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step1)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number
            }
        )
        
        # Add task step
        step2 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=2,
            description="Generate document content",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number,
                "description": step2.description
            }
        )
        
        # Update task progress
        await agent_task_repository.update_task_status(
            task.id,
            AgentTaskStatus.IN_PROGRESS,
            progress_percentage=50,
            message="Generating document content"
        )
        
        # Generate document content
        # This is a placeholder implementation
        # In a real implementation, this would use the LLM to generate content
        
        # Create system prompt
        system_prompt = """
You are an AI assistant specialized in creating high-quality documentation for software projects.
Your task is to create a document based on the provided requirements and context.
The document should be well-structured, clear, and comprehensive.
Use Markdown formatting for the document.
"""
        
        # Create prompt
        prompt = f"""
Create a document with the following details:

Description: {task.description}

Context:
{json.dumps(task.context, indent=2)}

The document should follow best practices for software documentation and include appropriate sections based on the document type.
"""
        
        # Generate content using structured output
        success, document, error_message = await output_parser.generate_structured_output(
            prompt=prompt,
            schema=DocumentContent,
            max_retries=2
        )
        
        if not success:
            logger.error(f"Error generating document content: {error_message}")
            document_content = f"# Error Generating Document\n\nThere was an error generating the document content: {error_message}"
        else:
            # Format document content
            document_content = f"# {document.title}\n\n{document.content}"
        
        # Update step status
        step2.status = AgentTaskStatus.COMPLETED
        step2.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step2)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number
            }
        )
        
        # Add task step
        step3 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=3,
            description="Create document in the system",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step3.id,
                "step_number": step3.step_number,
                "description": step3.description
            }
        )
        
        # Update task progress
        await agent_task_repository.update_task_status(
            task.id,
            AgentTaskStatus.IN_PROGRESS,
            progress_percentage=75,
            message="Creating document in the system"
        )
        
        # Create document in the system
        # This is a placeholder implementation
        # In a real implementation, this would create a document in the database
        
        # Extract document name from context
        document_name = task.context.get("document_name", f"document_{uuid.uuid4()}.md")
        
        # Extract folder ID from context
        folder_id = task.context.get("folder_id")
        
        # Extract project ID from context
        project_id = task.context.get("project_id")
        
        # Create document
        # In a real implementation, this would use a document repository
        document_id = str(uuid.uuid4())
        
        # Update step status
        step3.status = AgentTaskStatus.COMPLETED
        step3.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step3)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step3.id,
                "step_number": step3.step_number
            }
        )
        
        # Update task with result document ID
        task.result_document_id = document_id
        await agent_task_repository.update_task(task)
        
        # Return result
        return {
            "document_id": document_id,
            "document_name": document_name,
            "content": document_content
        }
    
    async def _execute_document_modification_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a document modification task.
        
        Args:
            task: Agent task
            
        Returns:
            Task execution result
        """
        # Add task step
        step1 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=1,
            description="Retrieve current document content",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number,
                "description": step1.description
            }
        )
        
        # Retrieve document
        # This is a placeholder implementation
        # In a real implementation, this would retrieve the document from the database
        
        # Extract document ID from context
        document_id = task.context.get("document_id")
        
        if not document_id:
            raise ValueError("Document ID not provided in task context")
        
        # Retrieve document content
        # In a real implementation, this would use a document repository
        current_content = "# Document\n\nThis is the current document content."
        
        # Update step status
        step1.status = AgentTaskStatus.COMPLETED
        step1.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step1)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number
            }
        )
        
        # Add task step
        step2 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=2,
            description="Generate modified content",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number,
                "description": step2.description
            }
        )
        
        # Update task progress
        await agent_task_repository.update_task_status(
            task.id,
            AgentTaskStatus.IN_PROGRESS,
            progress_percentage=50,
            message="Generating modified content"
        )
        
        # Generate modified content
        # This is a placeholder implementation
        # In a real implementation, this would use the LLM to generate modified content
        
        # Create system prompt
        system_prompt = """
You are an AI assistant specialized in modifying documentation for software projects.
Your task is to modify a document based on the provided requirements and context.
The document should remain well-structured, clear, and comprehensive after your modifications.
Use Markdown formatting for the document.
"""
        
        # Create prompt
        prompt = f"""
Modify the following document based on these requirements:

Description: {task.description}

Context:
{json.dumps(task.context, indent=2)}

Current document content:
{current_content}

Make the requested modifications while preserving the overall structure and style of the document.
Return the complete modified document content.
"""
        
        # Generate content using structured output
        success, document, error_message = await output_parser.generate_structured_output(
            prompt=prompt,
            schema=DocumentContent,
            max_retries=2
        )
        
        if not success:
            logger.error(f"Error generating modified document content: {error_message}")
            modified_content = f"# Error Modifying Document\n\nThere was an error modifying the document content: {error_message}"
        else:
            # Format document content
            modified_content = f"# {document.title}\n\n{document.content}"
        
        # Update step status
        step2.status = AgentTaskStatus.COMPLETED
        step2.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step2)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number
            }
        )
        
        # Add task step
        step3 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=3,
            description="Generate document diff",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step3.id,
                "step_number": step3.step_number,
                "description": step3.description
            }
        )
        
        # Generate diff
        # This is a placeholder implementation
        # In a real implementation, this would generate a proper diff
        
        # Simple diff for demonstration
        changes = [
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
        ]
        
        # Create document diff
        document_diff = DocumentDiff(
            document_id=document_id,
            before_content=current_content,
            after_content=modified_content,
            changes=changes,
            created_by=task.agent_id,
            task_id=task.id
        )
        
        # Save document diff
        await activity_log_repository.add_document_diff(document_diff)
        
        # Update step status
        step3.status = AgentTaskStatus.COMPLETED
        step3.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step3)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step3.id,
                "step_number": step3.step_number
            }
        )
        
        # Add task step
        step4 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=4,
            description="Update document in the system",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step4.id,
                "step_number": step4.step_number,
                "description": step4.description
            }
        )
        
        # Update task progress
        await agent_task_repository.update_task_status(
            task.id,
            AgentTaskStatus.IN_PROGRESS,
            progress_percentage=75,
            message="Updating document in the system"
        )
        
        # Update document in the system
        # This is a placeholder implementation
        # In a real implementation, this would update the document in the database
        
        # Update step status
        step4.status = AgentTaskStatus.COMPLETED
        step4.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step4)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step4.id,
                "step_number": step4.step_number
            }
        )
        
        # Emit document updated event
        await event_service.emit_event(
            "document_updated",
            {
                "document_id": document_id,
                "task_id": task.id,
                "agent_id": task.agent_id,
                "diff_id": document_diff.id
            }
        )
        
        # Return result
        return {
            "document_id": document_id,
            "content": modified_content,
            "diff_id": document_diff.id
        }
    
    async def _execute_document_analysis_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a document analysis task.
        
        Args:
            task: Agent task
            
        Returns:
            Task execution result
        """
        # Add task step
        step1 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=1,
            description="Retrieve document content",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number,
                "description": step1.description
            }
        )
        
        # Retrieve document
        # This is a placeholder implementation
        # In a real implementation, this would retrieve the document from the database
        
        # Extract document ID from context
        document_id = task.context.get("document_id")
        
        if not document_id:
            raise ValueError("Document ID not provided in task context")
        
        # Retrieve document content
        # In a real implementation, this would use a document repository
        document_content = "# Document\n\nThis is the document content to analyze."
        
        # Update step status
        step1.status = AgentTaskStatus.COMPLETED
        step1.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step1)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number
            }
        )
        
        # Add task step
        step2 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=2,
            description="Analyze document content",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number,
                "description": step2.description
            }
        )
        
        # Update task progress
        await agent_task_repository.update_task_status(
            task.id,
            AgentTaskStatus.IN_PROGRESS,
            progress_percentage=50,
            message="Analyzing document content"
        )
        
        # Analyze document
        # This is a placeholder implementation
        # In a real implementation, this would use the LLM to analyze the document
        
        # Create system prompt
        system_prompt = """
You are an AI assistant specialized in analyzing documentation for software projects.
Your task is to analyze a document and provide insights based on the provided requirements and context.
Your analysis should be thorough, clear, and actionable.
"""
        
        # Create prompt
        prompt = f"""
Analyze the following document based on these requirements:

Description: {task.description}

Context:
{json.dumps(task.context, indent=2)}

Document content:
{document_content}

Provide a comprehensive analysis of the document, including:
1. Summary of the document
2. Strengths and weaknesses
3. Suggestions for improvement
4. Any missing information or sections
5. Overall assessment
"""
        
        # Generate analysis using structured output
        success, analysis_result, error_message = await output_parser.generate_structured_output(
            prompt=prompt,
            schema=DocumentAnalysis,
            max_retries=2
        )
        
        if not success:
            logger.error(f"Error generating document analysis: {error_message}")
            analysis = f"# Error Analyzing Document\n\nThere was an error analyzing the document: {error_message}"
        else:
            # Format analysis content
            analysis = f"""# Document Analysis

## Summary
{analysis_result.summary}

## Strengths
{chr(10).join(['- ' + strength for strength in analysis_result.strengths])}

## Weaknesses
{chr(10).join(['- ' + weakness for weakness in analysis_result.weaknesses])}

## Suggestions for Improvement
{chr(10).join(['- ' + suggestion for suggestion in analysis_result.suggestions])}

## Missing Information
{chr(10).join(['- ' + missing for missing in analysis_result.missing_sections])}

## Overall Assessment
{analysis_result.overall_assessment}
"""
        
        # Update step status
        step2.status = AgentTaskStatus.COMPLETED
        step2.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step2)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number
            }
        )
        
        # Return result
        return {
            "document_id": document_id,
            "analysis": analysis
        }
    
    async def _execute_task_creation_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a task creation task.
        
        Args:
            task: Agent task
            
        Returns:
            Task execution result
        """
        # This is a placeholder implementation
        # In a real implementation, this would create a task document
        
        # Add task step
        step1 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=1,
            description="Analyze requirements and context",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number,
                "description": step1.description
            }
        )
        
        # Analyze requirements
        await asyncio.sleep(1)  # Simulate processing time
        
        # Update step status
        step1.status = AgentTaskStatus.COMPLETED
        step1.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step1)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number
            }
        )
        
        # Add task step
        step2 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=2,
            description="Generate task document content",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number,
                "description": step2.description
            }
        )
        
        # Update task progress
        await agent_task_repository.update_task_status(
            task.id,
            AgentTaskStatus.IN_PROGRESS,
            progress_percentage=50,
            message="Generating task document content"
        )
        
        # Generate task document content
        # In a real implementation, this would use the LLM to generate content
        
        # Create system prompt
        system_prompt = """
You are an AI assistant specialized in creating task definitions for software projects.
Your task is to create a task document based on the provided requirements and context.
The task document should be well-structured, clear, and actionable.
Use Markdown formatting for the document.
"""
        
        # Create prompt
        prompt = f"""
Create a task document with the following details:

Description: {task.description}

Context:
{json.dumps(task.context, indent=2)}

The task document should follow this structure:
1. Task title and ID
2. Overview
3. Context and background
4. Acceptance criteria
5. Implementation details
6. Dependencies
7. Estimated effort
8. Notes
"""
        
        # Generate task definition using structured output
        success, task_def, error_message = await output_parser.generate_structured_output(
            prompt=prompt,
            schema=TaskDefinition,
            max_retries=2
        )
        
        if not success:
            logger.error(f"Error generating task definition: {error_message}")
            task_document_content = f"# Error Creating Task\n\nThere was an error creating the task: {error_message}"
        else:
            # Format task document content
            task_document_content = f"""# {task_def.title}

## Overview
{task_def.description}

## Acceptance Criteria
{chr(10).join(['- ' + criterion for criterion in task_def.acceptance_criteria])}

## Implementation Details
{task_def.implementation_details}

## Dependencies
{chr(10).join(['- ' + dependency for dependency in task_def.dependencies])}

## Estimated Effort
{task_def.estimated_effort}

## Priority
{task_def.priority}

## Notes
{task_def.notes or "No additional notes."}
"""
        
        # Update step status
        step2.status = AgentTaskStatus.COMPLETED
        step2.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step2)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number
            }
        )
        
        # Add task step
        step3 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=3,
            description="Create task document in the system",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step3.id,
                "step_number": step3.step_number,
                "description": step3.description
            }
        )
        
        # Update task progress
        await agent_task_repository.update_task_status(
            task.id,
            AgentTaskStatus.IN_PROGRESS,
            progress_percentage=75,
            message="Creating task document in the system"
        )
        
        # Create task document in the system
        # In a real implementation, this would create a document in the database
        
        # Generate task ID
        task_number = 1  # In a real implementation, this would be determined dynamically
        task_id_str = f"TASK_{task_number:03d}"
        
        # Extract document name from context or generate one
        document_name = task.context.get("document_name", f"{task_id_str}_task.md")
        
        # Extract folder ID from context
        folder_id = task.context.get("folder_id")
        
        # Extract project ID from context
        project_id = task.context.get("project_id")
        
        # Create document
        # In a real implementation, this would use a document repository
        document_id = str(uuid.uuid4())
        
        # Update step status
        step3.status = AgentTaskStatus.COMPLETED
        step3.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step3)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step3.id,
                "step_number": step3.step_number
            }
        )
        
        # Update task with result document ID
        task.result_document_id = document_id
        await agent_task_repository.update_task(task)
        
        # Return result
        return {
            "document_id": document_id,
            "document_name": document_name,
            "task_id": task_id_str,
            "content": task_document_content
        }
    
    async def _execute_task_analysis_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a task analysis task.
        
        Args:
            task: Agent task
            
        Returns:
            Task execution result
        """
        # This is a placeholder implementation
        # In a real implementation, this would analyze a task document
        
        # Similar to document analysis, but focused on task documents
        return await self._execute_document_analysis_task(task)
    
    async def _execute_project_analysis_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a project analysis task.
        
        Args:
            task: Agent task
            
        Returns:
            Task execution result
        """
        # This is a placeholder implementation
        # In a real implementation, this would analyze a project
        
        # Add task step
        step1 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=1,
            description="Retrieve project structure and documents",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number,
                "description": step1.description
            }
        )
        
        # Retrieve project
        # This is a placeholder implementation
        # In a real implementation, this would retrieve the project from the database
        
        # Extract project ID from context
        project_id = task.context.get("project_id")
        
        if not project_id:
            raise ValueError("Project ID not provided in task context")
        
        # Retrieve project structure
        # In a real implementation, this would use a project repository
        project_structure = {
            "name": "AI Project Assistant",
            "documents": [
                {"id": "doc1", "name": "project_charter.md", "type": "markdown"},
                {"id": "doc2", "name": "system_requirements.md", "type": "markdown"},
                {"id": "doc3", "name": "TASK_001_implement_feature.md", "type": "markdown", "is_task": True}
            ],
            "folders": [
                {"id": "folder1", "name": "Documentation", "documents": [
                    {"id": "doc4", "name": "api_documentation.md", "type": "markdown"}
                ]}
            ]
        }
        
        # Update step status
        step1.status = AgentTaskStatus.COMPLETED
        step1.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step1)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number
            }
        )
        
        # Add task step
        step2 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=2,
            description="Analyze project structure and documents",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number,
                "description": step2.description
            }
        )
        
        # Update task progress
        await agent_task_repository.update_task_status(
            task.id,
            AgentTaskStatus.IN_PROGRESS,
            progress_percentage=50,
            message="Analyzing project structure and documents"
        )
        
        # Analyze project
        # This is a placeholder implementation
        # In a real implementation, this would use the LLM to analyze the project
        
        # Create system prompt
        system_prompt = """
You are an AI assistant specialized in analyzing software projects.
Your task is to analyze a project structure and provide insights based on the provided requirements and context.
Your analysis should be thorough, clear, and actionable.
"""
        
        # Create prompt
        prompt = f"""
Analyze the following project based on these requirements:

Description: {task.description}

Context:
{json.dumps(task.context, indent=2)}

Project structure:
{json.dumps(project_structure, indent=2)}

Provide a comprehensive analysis of the project, including:
1. Summary of the project
2. Assessment of project structure and organization
3. Identification of missing documents or components
4. Suggestions for improvement
5. Overall assessment
"""
        
        # Generate project analysis using structured output
        success, analysis_result, error_message = await output_parser.generate_structured_output(
            prompt=prompt,
            schema=DocumentAnalysis,  # Reusing the same schema for project analysis
            max_retries=2
        )
        
        if not success:
            logger.error(f"Error generating project analysis: {error_message}")
            analysis = f"# Error Analyzing Project\n\nThere was an error analyzing the project: {error_message}"
        else:
            # Format analysis content
            analysis = f"""# Project Analysis

## Summary
{analysis_result.summary}

## Strengths
{chr(10).join(['- ' + strength for strength in analysis_result.strengths])}

## Weaknesses
{chr(10).join(['- ' + weakness for weakness in analysis_result.weaknesses])}

## Suggestions for Improvement
{chr(10).join(['- ' + suggestion for suggestion in analysis_result.suggestions])}

## Missing Components
{chr(10).join(['- ' + missing for missing in analysis_result.missing_sections])}

## Overall Assessment
{analysis_result.overall_assessment}
"""
        
        # Update step status
        step2.status = AgentTaskStatus.COMPLETED
        step2.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step2)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number
            }
        )
        
        # Return result
        return {
            "project_id": project_id,
            "analysis": analysis
        }
    
    async def _execute_code_generation_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a code generation task.
        
        Args:
            task: Agent task
            
        Returns:
            Task execution result
        """
        # This is a placeholder implementation
        # In a real implementation, this would generate code
        
        # Add task step
        step1 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=1,
            description="Analyze requirements and context",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number,
                "description": step1.description
            }
        )
        
        # Analyze requirements
        await asyncio.sleep(1)  # Simulate processing time
        
        # Update step status
        step1.status = AgentTaskStatus.COMPLETED
        step1.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step1)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number
            }
        )
        
        # Add task step
        step2 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=2,
            description="Generate code",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number,
                "description": step2.description
            }
        )
        
        # Update task progress
        await agent_task_repository.update_task_status(
            task.id,
            AgentTaskStatus.IN_PROGRESS,
            progress_percentage=50,
            message="Generating code"
        )
        
        # Generate code
        # This is a placeholder implementation
        # In a real implementation, this would use the LLM to generate code
        
        # Create system prompt
        system_prompt = """
You are an AI assistant specialized in generating code for software projects.
Your task is to generate code based on the provided requirements and context.
The code should be well-structured, clear, and follow best practices.
"""
        
        # Create prompt
        prompt = f"""
Generate code with the following details:

Description: {task.description}

Context:
{json.dumps(task.context, indent=2)}

The code should follow best practices for the specified language and include appropriate comments.
"""
        
        # Generate code using LLM
        response = await llm_service.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            user_id=task.requested_by,
            session_id=task.session_id
        )
        
        code = response.content
        
        # Update step status
        step2.status = AgentTaskStatus.COMPLETED
        step2.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step2)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number
            }
        )
        
        # Return result
        return {
            "code": code,
            "language": task.context.get("language", "python")
        }
    
    async def _execute_code_analysis_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a code analysis task.
        
        Args:
            task: Agent task
            
        Returns:
            Task execution result
        """
        # This is a placeholder implementation
        # In a real implementation, this would analyze code
        
        # Add task step
        step1 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=1,
            description="Retrieve code",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number,
                "description": step1.description
            }
        )
        
        # Retrieve code
        # This is a placeholder implementation
        # In a real implementation, this would retrieve the code from the database or file system
        
        # Extract code from context
        code = task.context.get("code")
        
        if not code:
            # Extract file path from context
            file_path = task.context.get("file_path")
            
            if not file_path:
                raise ValueError("Neither code nor file path provided in task context")
            
            # Read code from file
            # In a real implementation, this would read the file from the file system
            code = "def example_function():\n    return 'Hello, World!'"
        
        # Update step status
        step1.status = AgentTaskStatus.COMPLETED
        step1.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step1)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step1.id,
                "step_number": step1.step_number
            }
        )
        
        # Add task step
        step2 = await agent_task_repository.add_task_step(TaskExecutionStep(
            task_id=task.id,
            step_number=2,
            description="Analyze code",
            status=AgentTaskStatus.IN_PROGRESS
        ))
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_started",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number,
                "description": step2.description
            }
        )
        
        # Update task progress
        await agent_task_repository.update_task_status(
            task.id,
            AgentTaskStatus.IN_PROGRESS,
            progress_percentage=50,
            message="Analyzing code"
        )
        
        # Analyze code
        # This is a placeholder implementation
        # In a real implementation, this would use the LLM to analyze the code
        
        # Create system prompt
        system_prompt = """
You are an AI assistant specialized in analyzing code for software projects.
Your task is to analyze code and provide insights based on the provided requirements and context.
Your analysis should be thorough, clear, and actionable.
"""
        
        # Create prompt
        prompt = f"""
Analyze the following code based on these requirements:

Description: {task.description}

Context:
{json.dumps(task.context, indent=2)}

Code:
```
{code}
```

Provide a comprehensive analysis of the code, including:
1. Summary of the code functionality
2. Code quality assessment
3. Potential bugs or issues
4. Suggestions for improvement
5. Overall assessment
"""
        
        # Generate code analysis
        response = await llm_service.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            user_id=task.requested_by,
            session_id=task.session_id
        )
        
        analysis = response.content
        
        # Update step status
        step2.status = AgentTaskStatus.COMPLETED
        step2.completed_at = datetime.now()
        await agent_task_repository.update_task_step(step2)
        
        # Emit event
        await event_service.emit_event(
            "agent_task_step_completed",
            {
                "task_id": task.id,
                "step_id": step2.id,
                "step_number": step2.step_number
            }
        )
        
        # Return result
        return {
            "code": code,
            "language": task.context.get("language", "python"),
            "analysis": analysis
        }


# Create singleton instance
execution_agent_service = ExecutionAgentService()