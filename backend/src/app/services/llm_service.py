"""
LLM Service for the AI Project Assistant.
This module provides interfaces for interacting with Language Model providers.
"""
from typing import Dict, List, Any, Optional, Union, Tuple, AsyncGenerator, TypeVar, Generic, Type
import json
import asyncio
from datetime import datetime
import uuid
from enum import Enum
from pydantic import BaseModel, Field, create_model
from loguru import logger
import os
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import config
from ..config import settings

# Import token manager and output parser
from .token_manager import token_manager
from .output_parser import output_parser

class LLMProvider(str, Enum):
    """Enum for LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class LLMMessage(BaseModel):
    """Model for LLM messages."""
    role: str
    content: str
    name: Optional[str] = None


class LLMResponse(BaseModel):
    """Model for LLM responses."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: Optional[str] = None


class LLMConfig(BaseModel):
    """Configuration for LLM requests."""
    provider: LLMProvider = LLMProvider.OPENAI
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    timeout: int = 60


T = TypeVar('T', bound=BaseModel)


class LLMService:
    """Service for LLM operations."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.default_provider = LLMProvider(settings.DEFAULT_LLM_PROVIDER)
        self.default_completion_model = settings.DEFAULT_COMPLETION_MODEL
        self.default_embedding_model = settings.DEFAULT_EMBEDDING_MODEL
        
        # API keys
        self.openai_api_key = settings.OPENAI_API_KEY
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        
        # HTTP client
        self.http_client = httpx.AsyncClient(timeout=60.0)
        
        # Check if we should use mock LLM
        self.use_mock = settings.USE_MOCK_LLM
        
        # Initialize provider-specific clients
        if self.default_provider == LLMProvider.OPENAI and not self.use_mock:
            try:
                import openai
                self.openai_client = openai.AsyncClient(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("OpenAI package not installed, falling back to HTTP client")
                self.openai_client = None
        else:
            self.openai_client = None
        
        if self.default_provider == LLMProvider.ANTHROPIC and not self.use_mock:
            try:
                import anthropic
                self.anthropic_client = anthropic.AsyncAnthropic(api_key=self.anthropic_api_key)
                logger.info("Anthropic client initialized")
            except ImportError:
                logger.warning("Anthropic package not installed, falling back to HTTP client")
                self.anthropic_client = None
        else:
            self.anthropic_client = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None,
        config: Optional[LLMConfig] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: Optional LLM configuration
            user_id: Optional user ID for token tracking
            session_id: Optional session ID for token tracking
            correlation_id: Optional correlation ID for token tracking
            
        Returns:
            LLM response
        """
        # Use default config if not provided
        if config is None:
            config = LLMConfig(
                provider=self.default_provider,
                model=self.default_completion_model
            )
        
        # Generate correlation ID if user_id is provided and correlation_id is not
        if user_id and not correlation_id:
            correlation_id = await token_manager.generate_correlation_id(user_id, session_id)
        
        # Check rate limit if user_id is provided
        if user_id:
            # Estimate token usage
            estimated_tokens = 0
            if messages:
                estimated_tokens = await token_manager.count_messages_tokens([msg.dict() for msg in messages])
            else:
                estimated_tokens = await token_manager.count_tokens(prompt)
                if system_prompt:
                    estimated_tokens += await token_manager.count_tokens(system_prompt)
            
            # Add buffer for completion tokens
            estimated_tokens += config.max_tokens or 1000
            
            # Check rate limit
            within_limit = await token_manager.check_rate_limit(user_id, estimated_tokens)
            if not within_limit:
                raise ValueError(f"Rate limit exceeded for user {user_id}")
        
        # If using mock LLM, return mock response
        if self.use_mock:
            return await self._generate_mock_response(prompt, system_prompt, messages, config)
        
        # Generate based on provider
        response = None
        if config.provider == LLMProvider.OPENAI:
            response = await self._generate_openai(prompt, system_prompt, messages, config)
        elif config.provider == LLMProvider.ANTHROPIC:
            response = await self._generate_anthropic(prompt, system_prompt, messages, config)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
        
        # Track token usage if user_id is provided
        if user_id:
            await token_manager.track_usage(
                user_id=user_id,
                prompt_tokens=response.usage.get("prompt_tokens", 0),
                completion_tokens=response.usage.get("completion_tokens", 0),
                correlation_id=correlation_id,
                session_id=session_id,
                model=response.model,
                endpoint="generate"
            )
        
        return response
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None,
        config: Optional[LLMConfig] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: Optional LLM configuration
            user_id: Optional user ID for token tracking
            session_id: Optional session ID for token tracking
            correlation_id: Optional correlation ID for token tracking
            
        Yields:
            Response chunks
        """
        # Use default config if not provided
        if config is None:
            config = LLMConfig(
                provider=self.default_provider,
                model=self.default_completion_model
            )
        
        # Generate correlation ID if user_id is provided and correlation_id is not
        if user_id and not correlation_id:
            correlation_id = await token_manager.generate_correlation_id(user_id, session_id)
        
        # Check rate limit if user_id is provided
        if user_id:
            # Estimate token usage
            estimated_tokens = 0
            if messages:
                estimated_tokens = await token_manager.count_messages_tokens([msg.dict() for msg in messages])
            else:
                estimated_tokens = await token_manager.count_tokens(prompt)
                if system_prompt:
                    estimated_tokens += await token_manager.count_tokens(system_prompt)
            
            # Add buffer for completion tokens
            estimated_tokens += config.max_tokens or 1000
            
            # Check rate limit
            within_limit = await token_manager.check_rate_limit(user_id, estimated_tokens)
            if not within_limit:
                raise ValueError(f"Rate limit exceeded for user {user_id}")
        
        # Variables for token tracking
        prompt_tokens = 0
        completion_tokens = 0
        completion_text = ""
        
        # If using mock LLM, return mock response
        if self.use_mock:
            async for chunk in self._generate_mock_stream(prompt, config, system_prompt, messages):
                completion_text += chunk
                completion_tokens += 1
                yield chunk
        else:
            # Generate based on provider
            if config.provider == LLMProvider.OPENAI:
                async for chunk in self._generate_openai_stream(prompt, system_prompt, messages, config):
                    completion_text += chunk
                    completion_tokens += 1
                    yield chunk
            elif config.provider == LLMProvider.ANTHROPIC:
                async for chunk in self._generate_anthropic_stream(prompt, system_prompt, messages, config):
                    completion_text += chunk
                    completion_tokens += 1
                    yield chunk
            else:
                raise ValueError(f"Unsupported LLM provider: {config.provider}")
        
        # Track token usage if user_id is provided
        if user_id:
            # Estimate prompt tokens
            if messages:
                prompt_tokens = await token_manager.count_messages_tokens([msg.dict() for msg in messages])
            else:
                prompt_tokens = await token_manager.count_tokens(prompt)
                if system_prompt:
                    prompt_tokens += await token_manager.count_tokens(system_prompt)
            
            # Estimate completion tokens more accurately
            completion_tokens = await token_manager.count_tokens(completion_text)
            
            await token_manager.track_usage(
                user_id=user_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                correlation_id=correlation_id,
                session_id=session_id,
                model=config.model or self.default_completion_model,
                endpoint="generate_stream"
            )
    
    async def create_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> List[List[float]]:
        """
        Create embeddings for texts.
        
        Args:
            texts: List of texts to embed
            model: Optional embedding model
            user_id: Optional user ID for token tracking
            session_id: Optional session ID for token tracking
            correlation_id: Optional correlation ID for token tracking
            
        Returns:
            List of embeddings
        """
        # Use default model if not provided
        if model is None:
            model = self.default_embedding_model
        
        # Generate correlation ID if user_id is provided and correlation_id is not
        if user_id and not correlation_id:
            correlation_id = await token_manager.generate_correlation_id(user_id, session_id)
        
        # Check rate limit if user_id is provided
        if user_id:
            # Estimate token usage
            estimated_tokens = 0
            for text in texts:
                estimated_tokens += await token_manager.count_tokens(text)
            
            # Check rate limit
            within_limit = await token_manager.check_rate_limit(user_id, estimated_tokens)
            if not within_limit:
                raise ValueError(f"Rate limit exceeded for user {user_id}")
        
        # If using mock LLM, return mock embeddings
        if self.use_mock:
            embeddings = self._create_mock_embeddings(texts, model)
        else:
            # Create embeddings based on provider
            if self.default_provider == LLMProvider.OPENAI:
                embeddings = await self._create_openai_embeddings(texts, model)
            elif self.default_provider == LLMProvider.ANTHROPIC:
                # Anthropic doesn't have an embeddings API yet, fall back to OpenAI
                embeddings = await self._create_openai_embeddings(texts, model)
            else:
                raise ValueError(f"Unsupported LLM provider for embeddings: {self.default_provider}")
        
        # Track token usage if user_id is provided
        if user_id:
            # Calculate total tokens
            total_tokens = 0
            for text in texts:
                total_tokens += await token_manager.count_tokens(text)
            
            await token_manager.track_usage(
                user_id=user_id,
                prompt_tokens=total_tokens,
                completion_tokens=0,
                correlation_id=correlation_id,
                session_id=session_id,
                model=model,
                endpoint="create_embeddings"
            )
        
        return embeddings
    
    async def _generate_openai(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> LLMResponse:
        """
        Generate a response from OpenAI.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Returns:
            LLM response
        """
        # Use OpenAI client if available, otherwise use HTTP client
        if self.openai_client:
            return await self._generate_openai_with_client(prompt, system_prompt, messages, config)
        else:
            return await self._generate_openai_with_http(prompt, system_prompt, messages, config)
    
    async def _generate_openai_with_client(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> LLMResponse:
        """
        Generate a response from OpenAI using the OpenAI client.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Returns:
            LLM response
        """
        import openai
        
        # Prepare messages
        if messages:
            openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        else:
            openai_messages = []
            
            # Add system message if provided
            if system_prompt:
                openai_messages.append({"role": "system", "content": system_prompt})
            
            # Add user message
            openai_messages.append({"role": "user", "content": prompt})
        
        # Set model
        model = config.model or self.default_completion_model
        
        try:
            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                stop=config.stop_sequences
            )
            
            # Extract response
            content = response.choices[0].message.content
            
            # Create LLM response
            return LLMResponse(
                content=content,
                model=model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                finish_reason=response.choices[0].finish_reason
            )
        
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    async def _generate_openai_with_http(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> LLMResponse:
        """
        Generate a response from OpenAI using the HTTP client.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Returns:
            LLM response
        """
        # Prepare messages
        if messages:
            openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        else:
            openai_messages = []
            
            # Add system message if provided
            if system_prompt:
                openai_messages.append({"role": "system", "content": system_prompt})
            
            # Add user message
            openai_messages.append({"role": "user", "content": prompt})
        
        # Set model
        model = config.model or self.default_completion_model
        
        # Prepare request
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        data = {
            "model": model,
            "messages": openai_messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty
        }
        
        if config.max_tokens:
            data["max_tokens"] = config.max_tokens
        
        if config.stop_sequences:
            data["stop"] = config.stop_sequences
        
        try:
            # Call OpenAI API
            response = await self.http_client.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            # Extract response
            content = response_data["choices"][0]["message"]["content"]
            
            # Create LLM response
            return LLMResponse(
                content=content,
                model=model,
                usage=response_data["usage"],
                finish_reason=response_data["choices"][0]["finish_reason"]
            )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise
    
    async def _generate_openai_stream(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from OpenAI.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Yields:
            Response chunks
        """
        # Use OpenAI client if available, otherwise use HTTP client
        if self.openai_client:
            async for chunk in self._generate_openai_stream_with_client(prompt, system_prompt, messages, config):
                yield chunk
        else:
            async for chunk in self._generate_openai_stream_with_http(prompt, system_prompt, messages, config):
                yield chunk
    
    async def _generate_openai_stream_with_client(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from OpenAI using the OpenAI client.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Yields:
            Response chunks
        """
        import openai
        
        # Prepare messages
        if messages:
            openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        else:
            openai_messages = []
            
            # Add system message if provided
            if system_prompt:
                openai_messages.append({"role": "system", "content": system_prompt})
            
            # Add user message
            openai_messages.append({"role": "user", "content": prompt})
        
        # Set model
        model = config.model or self.default_completion_model
        
        try:
            # Call OpenAI API
            stream = await self.openai_client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                stop=config.stop_sequences,
                stream=True
            )
            
            # Process stream
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    async def _generate_openai_stream_with_http(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from OpenAI using the HTTP client.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Yields:
            Response chunks
        """
        # Prepare messages
        if messages:
            openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        else:
            openai_messages = []
            
            # Add system message if provided
            if system_prompt:
                openai_messages.append({"role": "system", "content": system_prompt})
            
            # Add user message
            openai_messages.append({"role": "user", "content": prompt})
        
        # Set model
        model = config.model or self.default_completion_model
        
        # Prepare request
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        data = {
            "model": model,
            "messages": openai_messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
            "stream": True
        }
        
        if config.max_tokens:
            data["max_tokens"] = config.max_tokens
        
        if config.stop_sequences:
            data["stop"] = config.stop_sequences
        
        try:
            # Call OpenAI API
            async with self.http_client.stream("POST", url, headers=headers, json=data) as response:
                response.raise_for_status()
                
                # Process stream
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                        json_str = line[6:]  # Remove "data: " prefix
                        try:
                            chunk = json.loads(json_str)
                            if chunk["choices"] and chunk["choices"][0]["delta"].get("content"):
                                yield chunk["choices"][0]["delta"]["content"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON: {json_str}")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise
    
    async def _generate_anthropic(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> LLMResponse:
        """
        Generate a response from Anthropic.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Returns:
            LLM response
        """
        # Use Anthropic client if available, otherwise use HTTP client
        if self.anthropic_client:
            return await self._generate_anthropic_with_client(prompt, system_prompt, messages, config)
        else:
            return await self._generate_anthropic_with_http(prompt, system_prompt, messages, config)
    
    async def _generate_anthropic_with_client(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> LLMResponse:
        """
        Generate a response from Anthropic using the Anthropic client.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Returns:
            LLM response
        """
        import anthropic
        
        # Prepare messages
        if messages:
            anthropic_messages = []
            for msg in messages:
                if msg.role == "system":
                    # Anthropic doesn't support system messages in the same way
                    # We'll handle this separately
                    continue
                elif msg.role == "user":
                    anthropic_messages.append({"role": "user", "content": msg.content})
                elif msg.role == "assistant":
                    anthropic_messages.append({"role": "assistant", "content": msg.content})
                else:
                    logger.warning(f"Unsupported message role for Anthropic: {msg.role}")
        else:
            anthropic_messages = [{"role": "user", "content": prompt}]
        
        # Set model
        model = config.model or "claude-3-opus-20240229"
        
        # Set system prompt
        system = system_prompt
        
        # Find system message in messages
        if messages and not system:
            for msg in messages:
                if msg.role == "system":
                    system = msg.content
                    break
        
        try:
            # Call Anthropic API
            response = await self.anthropic_client.messages.create(
                model=model,
                messages=anthropic_messages,
                system=system,
                temperature=config.temperature,
                max_tokens=config.max_tokens or 4096,
                top_p=config.top_p,
                stop_sequences=config.stop_sequences
            )
            
            # Extract response
            content = response.content[0].text
            
            # Create LLM response
            return LLMResponse(
                content=content,
                model=model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                finish_reason=response.stop_reason
            )
        
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise
    
    async def _generate_anthropic_with_http(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> LLMResponse:
        """
        Generate a response from Anthropic using the HTTP client.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Returns:
            LLM response
        """
        # Prepare messages
        if messages:
            anthropic_messages = []
            for msg in messages:
                if msg.role == "system":
                    # Anthropic doesn't support system messages in the same way
                    # We'll handle this separately
                    continue
                elif msg.role == "user":
                    anthropic_messages.append({"role": "user", "content": msg.content})
                elif msg.role == "assistant":
                    anthropic_messages.append({"role": "assistant", "content": msg.content})
                else:
                    logger.warning(f"Unsupported message role for Anthropic: {msg.role}")
        else:
            anthropic_messages = [{"role": "user", "content": prompt}]
        
        # Set model
        model = config.model or "claude-3-opus-20240229"
        
        # Set system prompt
        system = system_prompt
        
        # Find system message in messages
        if messages and not system:
            for msg in messages:
                if msg.role == "system":
                    system = msg.content
                    break
        
        # Prepare request
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens or 4096
        }
        
        if system:
            data["system"] = system
        
        if config.stop_sequences:
            data["stop_sequences"] = config.stop_sequences
        
        try:
            # Call Anthropic API
            response = await self.http_client.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            # Extract response
            content = response_data["content"][0]["text"]
            
            # Create LLM response
            return LLMResponse(
                content=content,
                model=model,
                usage={
                    "prompt_tokens": response_data["usage"]["input_tokens"],
                    "completion_tokens": response_data["usage"]["output_tokens"],
                    "total_tokens": response_data["usage"]["input_tokens"] + response_data["usage"]["output_tokens"]
                },
                finish_reason=response_data["stop_reason"]
            )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise
    
    async def _generate_anthropic_stream(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from Anthropic.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Yields:
            Response chunks
        """
        # Use Anthropic client if available, otherwise use HTTP client
        if self.anthropic_client:
            async for chunk in self._generate_anthropic_stream_with_client(prompt, system_prompt, messages, config):
                yield chunk
        else:
            async for chunk in self._generate_anthropic_stream_with_http(prompt, system_prompt, messages, config):
                yield chunk
    
    async def _generate_anthropic_stream_with_client(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from Anthropic using the Anthropic client.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Yields:
            Response chunks
        """
        import anthropic
        
        # Prepare messages
        if messages:
            anthropic_messages = []
            for msg in messages:
                if msg.role == "system":
                    # Anthropic doesn't support system messages in the same way
                    # We'll handle this separately
                    continue
                elif msg.role == "user":
                    anthropic_messages.append({"role": "user", "content": msg.content})
                elif msg.role == "assistant":
                    anthropic_messages.append({"role": "assistant", "content": msg.content})
                else:
                    logger.warning(f"Unsupported message role for Anthropic: {msg.role}")
        else:
            anthropic_messages = [{"role": "user", "content": prompt}]
        
        # Set model
        model = config.model or "claude-3-opus-20240229"
        
        # Set system prompt
        system = system_prompt
        
        # Find system message in messages
        if messages and not system:
            for msg in messages:
                if msg.role == "system":
                    system = msg.content
                    break
        
        try:
            # Call Anthropic API
            stream = await self.anthropic_client.messages.create(
                model=model,
                messages=anthropic_messages,
                system=system,
                temperature=config.temperature,
                max_tokens=config.max_tokens or 4096,
                top_p=config.top_p,
                stop_sequences=config.stop_sequences,
                stream=True
            )
            
            # Process stream
            async for chunk in stream:
                if hasattr(chunk, 'delta') and chunk.delta.text:
                    yield chunk.delta.text
        
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise
    
    async def _generate_anthropic_stream_with_http(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from Anthropic using the HTTP client.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Yields:
            Response chunks
        """
        # Prepare messages
        if messages:
            anthropic_messages = []
            for msg in messages:
                if msg.role == "system":
                    # Anthropic doesn't support system messages in the same way
                    # We'll handle this separately
                    continue
                elif msg.role == "user":
                    anthropic_messages.append({"role": "user", "content": msg.content})
                elif msg.role == "assistant":
                    anthropic_messages.append({"role": "assistant", "content": msg.content})
                else:
                    logger.warning(f"Unsupported message role for Anthropic: {msg.role}")
        else:
            anthropic_messages = [{"role": "user", "content": prompt}]
        
        # Set model
        model = config.model or "claude-3-opus-20240229"
        
        # Set system prompt
        system = system_prompt
        
        # Find system message in messages
        if messages and not system:
            for msg in messages:
                if msg.role == "system":
                    system = msg.content
                    break
        
        # Prepare request
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens or 4096,
            "stream": True
        }
        
        if system:
            data["system"] = system
        
        if config.stop_sequences:
            data["stop_sequences"] = config.stop_sequences
        
        try:
            # Call Anthropic API
            async with self.http_client.stream("POST", url, headers=headers, json=data) as response:
                response.raise_for_status()
                
                # Process stream
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                        json_str = line[6:]  # Remove "data: " prefix
                        try:
                            chunk = json.loads(json_str)
                            if chunk.get("type") == "content_block_delta" and chunk.get("delta", {}).get("text"):
                                yield chunk["delta"]["text"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON: {json_str}")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise
    
    async def _create_openai_embeddings(
        self,
        texts: List[str],
        model: str
    ) -> List[List[float]]:
        """
        Create embeddings using OpenAI.
        
        Args:
            texts: List of texts to embed
            model: Embedding model
            
        Returns:
            List of embeddings
        """
        # Use OpenAI client if available, otherwise use HTTP client
        if self.openai_client:
            return await self._create_openai_embeddings_with_client(texts, model)
        else:
            return await self._create_openai_embeddings_with_http(texts, model)
    
    async def _create_openai_embeddings_with_client(
        self,
        texts: List[str],
        model: str
    ) -> List[List[float]]:
        """
        Create embeddings using OpenAI with the OpenAI client.
        
        Args:
            texts: List of texts to embed
            model: Embedding model
            
        Returns:
            List of embeddings
        """
        import openai
        
        try:
            # Call OpenAI API
            response = await self.openai_client.embeddings.create(
                model=model,
                input=texts
            )
            
            # Extract embeddings
            embeddings = [data.embedding for data in response.data]
            
            return embeddings
        
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    async def _create_openai_embeddings_with_http(
        self,
        texts: List[str],
        model: str
    ) -> List[List[float]]:
        """
        Create embeddings using OpenAI with the HTTP client.
        
        Args:
            texts: List of texts to embed
            model: Embedding model
            
        Returns:
            List of embeddings
        """
        # Prepare request
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        data = {
            "model": model,
            "input": texts
        }
        
        try:
            # Call OpenAI API
            response = await self.http_client.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            # Extract embeddings
            embeddings = [data["embedding"] for data in response_data["data"]]
            
            return embeddings
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise
    
    async def _generate_mock_response(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> LLMResponse:
        """
        Generate a mock response for testing.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Returns:
            LLM response
        """
        # Create mock response
        if messages:
            # Find the last user message
            last_user_message = None
            for msg in reversed(messages):
                if msg.role == "user":
                    last_user_message = msg.content
                    break
            
            if last_user_message:
                response_content = f"This is a mock response to: {last_user_message[:50]}..."
            else:
                response_content = "This is a mock response."
        else:
            response_content = f"This is a mock response to: {prompt[:50]}..."
        
        # Add some delay to simulate processing time
        await asyncio.sleep(0.5)
        
        # Create LLM response
        return LLMResponse(
            content=response_content,
            model="mock-model",
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            },
            finish_reason="stop"
        )
    
    async def _generate_mock_stream(
        self,
        prompt: str,
        config: LLMConfig,
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a mock streaming response for testing.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: LLM configuration
            
        Yields:
            Response chunks
        """
        # Create mock response
        if messages:
            # Find the last user message
            last_user_message = None
            for msg in reversed(messages):
                if msg.role == "user":
                    last_user_message = msg.content
                    break
            
            if last_user_message:
                response_content = f"This is a mock response to: {last_user_message[:50]}..."
            else:
                response_content = "This is a mock response."
        else:
            response_content = f"This is a mock response to: {prompt[:50]}..."
        
        # Split response into chunks
        chunks = [response_content[i:i+5] for i in range(0, len(response_content), 5)]
        
        # Yield chunks with delay
        for chunk in chunks:
            await asyncio.sleep(0.1)
            yield chunk
    
    def _create_mock_embeddings(
        self,
        texts: List[str],
        model: str
    ) -> List[List[float]]:
        """
        Create mock embeddings for testing.
        
        Args:
            texts: List of texts to embed
            model: Embedding model
            
        Returns:
            List of embeddings
        """
        # Create mock embeddings
        embeddings = []
        for _ in texts:
            # Create a random embedding vector of length 1536 (same as OpenAI's text-embedding-ada-002)
            embedding = [0.0] * 1536
            embeddings.append(embedding)
        
        return embeddings


class StructuredLLMService(Generic[T]):
    """Service for structured LLM operations."""
    
    def __init__(self, llm_service: LLMService):
        """
        Initialize the structured LLM service.
        
        Args:
            llm_service: LLM service
        """
        self.llm_service = llm_service
    
    async def generate_structured(
        self,
        prompt: str,
        output_class: Type[T],
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None,
        config: Optional[LLMConfig] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
        max_retries: int = 2,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> T:
        """
        Generate a structured response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            output_class: Pydantic model class for the output
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: Optional LLM configuration
            examples: Optional list of example outputs
            max_retries: Maximum number of retries for parsing failures
            user_id: Optional user ID for token tracking
            session_id: Optional session ID for token tracking
            
        Returns:
            Structured response
        """
        # Generate correlation ID if user_id is provided
        correlation_id = None
        if user_id:
            correlation_id = await token_manager.generate_correlation_id(user_id, session_id)
        
        # Use output parser to generate structured output
        success, parsed_output, error_message = await output_parser.generate_structured_output(
            prompt=prompt,
            schema=output_class,
            examples=examples,
            max_retries=max_retries
        )
        
        if not success:
            raise ValueError(f"Failed to generate structured output: {error_message}")
        
        return parsed_output
        
    async def generate_structured_with_retry(
        self,
        prompt: str,
        output_class: Type[T],
        system_prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None,
        config: Optional[LLMConfig] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
        max_retries: int = 3,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Tuple[bool, Optional[T], Optional[str]]:
        """
        Generate a structured response from the LLM with retry logic.
        
        Args:
            prompt: The prompt to send to the LLM
            output_class: Pydantic model class for the output
            system_prompt: Optional system prompt
            messages: Optional list of messages for chat models
            config: Optional LLM configuration
            examples: Optional list of example outputs
            max_retries: Maximum number of retries
            user_id: Optional user ID for token tracking
            session_id: Optional session ID for token tracking
            
        Returns:
            Tuple of (success, parsed_output, error_message)
        """
        # Generate correlation ID if user_id is provided
        correlation_id = None
        if user_id:
            correlation_id = await token_manager.generate_correlation_id(user_id, session_id)
        
        # Use output parser to generate structured output
        return await output_parser.generate_structured_output(
            prompt=prompt,
            schema=output_class,
            examples=examples,
            max_retries=max_retries
        )

# Create singleton instances
llm_service = LLMService()
structured_llm_service = StructuredLLMService(llm_service)
structured_llm_service = StructuredLLMService(llm_service)