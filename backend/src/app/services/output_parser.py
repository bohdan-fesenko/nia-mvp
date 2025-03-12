"""
Output Parser for the AI Project Assistant.
This module provides functionality for parsing and validating structured outputs from LLMs.
"""
from typing import Dict, List, Any, Optional, Union, Type, TypeVar, Generic, Tuple
import json
import re
from pydantic import BaseModel, ValidationError, create_model, Field
from loguru import logger

from ..config import settings
# Remove direct import of llm_service to break circular dependency

T = TypeVar('T', bound=BaseModel)

class OutputParser(Generic[T]):
    """Service for parsing and validating structured outputs from LLMs."""
    
    def __init__(self):
        """Initialize the output parser."""
        # llm_service will be set later to avoid circular imports
        self.llm_service = None
    
    def set_llm_service(self, llm_service):
        """Set the LLM service instance."""
        self.llm_service = llm_service
    """Service for parsing and validating structured outputs from LLMs."""
    
    async def parse_structured_output(
        self,
        output: str,
        schema: Type[T]
    ) -> Tuple[bool, Optional[T], Optional[str]]:
        """
        Parse a structured output from the LLM.
        
        Args:
            output: The output from the LLM
            schema: The Pydantic model class to parse into
            
        Returns:
            Tuple of (success, parsed_output, error_message)
        """
        # Extract JSON from output
        json_str = self._extract_json(output)
        
        try:
            # Parse JSON
            data = json.loads(json_str)
            
            # Validate against schema
            parsed_output = schema.model_validate(data)
            
            return True, parsed_output, None
        
        except json.JSONDecodeError as e:
            error_message = f"Failed to parse JSON: {str(e)}"
            logger.error(f"{error_message}\nJSON string: {json_str}")
            return False, None, error_message
        
        except ValidationError as e:
            error_message = f"Failed to validate data: {str(e)}"
            logger.error(f"{error_message}\nData: {json_str}")
            return False, None, error_message
        
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            logger.error(f"{error_message}\nOutput: {output}")
            return False, None, error_message
    
    async def format_prompt_for_structured_output(
        self,
        prompt: str,
        schema: Type[BaseModel],
        examples: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Format a prompt to request structured output from the LLM.
        
        Args:
            prompt: The base prompt
            schema: The Pydantic model class for the output
            examples: Optional list of example outputs
            
        Returns:
            Formatted prompt
        """
        # Get model definition
        model_definition = self._get_model_definition(schema)
        
        # Create system prompt
        system_prompt = f"""
You are an AI assistant that generates structured data.
Your task is to generate a valid JSON object that conforms to the following Pydantic model:

```python
{model_definition}
```

Ensure that your response is a valid JSON object and follows the schema exactly.
Do not include any explanations or markdown formatting in your response, just the JSON object.
"""

        # Add examples if provided
        if examples and len(examples) > 0:
            system_prompt += "\n\nHere are some examples of valid outputs:\n\n"
            for i, example in enumerate(examples):
                system_prompt += f"Example {i+1}:\n```json\n{json.dumps(example, indent=2)}\n```\n\n"
        
        # Combine with user prompt
        formatted_prompt = f"{prompt}\n\nRespond with a valid JSON object that matches the specified schema."
        
        return formatted_prompt, system_prompt
    
    async def generate_structured_output(
        self,
        prompt: str,
        schema: Type[T],
        examples: Optional[List[Dict[str, Any]]] = None,
        max_retries: int = 2
    ) -> Tuple[bool, Optional[T], Optional[str]]:
        """
        Generate a structured output from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            schema: The Pydantic model class for the output
            examples: Optional list of example outputs
            max_retries: Maximum number of retries for parsing failures
            
        Returns:
            Tuple of (success, parsed_output, error_message)
        """
        # Format prompt for structured output
        formatted_prompt, system_prompt = await self.format_prompt_for_structured_output(
            prompt=prompt,
            schema=schema,
            examples=examples
        )
        
        # Try to generate and parse output
        for attempt in range(max_retries + 1):
            try:
                # Generate response
                if not self.llm_service:
                    raise ValueError("LLM service not set. Call set_llm_service() first.")
                
                response = await self.llm_service.generate(
                    prompt=formatted_prompt,
                    system_prompt=system_prompt
                )
                
                # Parse response
                success, parsed_output, error_message = await self.parse_structured_output(
                    output=response.content,
                    schema=schema
                )
                
                if success:
                    return True, parsed_output, None
                
                # If parsing failed and we have retries left, try again with error feedback
                if attempt < max_retries:
                    logger.warning(f"Parsing attempt {attempt+1} failed: {error_message}. Retrying...")
                    
                    # Add error feedback to prompt
                    formatted_prompt = f"""
{formatted_prompt}

Your previous response could not be parsed correctly. The error was:
{error_message}

Please try again and ensure your response is a valid JSON object that matches the specified schema.
"""
                else:
                    # No more retries
                    return False, None, error_message
            
            except Exception as e:
                error_message = f"Error generating structured output: {str(e)}"
                logger.error(error_message)
                return False, None, error_message
        
        # This should never be reached
        return False, None, "Maximum retries exceeded"
    
    async def validate_output(
        self,
        output: Any,
        schema: Type[BaseModel]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate an output against a schema.
        
        Args:
            output: The output to validate
            schema: The Pydantic model class to validate against
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Validate against schema
            schema.model_validate(output)
            return True, None
        
        except ValidationError as e:
            error_message = f"Validation error: {str(e)}"
            return False, error_message
        
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            return False, error_message
    
    def _get_model_definition(self, model_class: Type[BaseModel]) -> str:
        """
        Get the definition of a Pydantic model.
        
        Args:
            model_class: Pydantic model class
            
        Returns:
            Model definition as a string
        """
        # Get model schema
        schema = model_class.model_json_schema()
        
        # Create model definition
        definition = f"class {model_class.__name__}(BaseModel):\n"
        
        # Add fields
        for field_name, field_info in schema.get("properties", {}).items():
            field_type = field_info.get("type", "Any")
            
            if field_type == "array":
                items_type = field_info.get("items", {}).get("type", "Any")
                field_type = f"List[{items_type.capitalize()}]"
            elif field_type == "object":
                field_type = "Dict[str, Any]"
            elif field_type == "integer":
                field_type = "int"
            elif field_type == "number":
                field_type = "float"
            elif field_type == "boolean":
                field_type = "bool"
            else:
                field_type = field_type.capitalize()
            
            # Check if field is required
            required = field_name in schema.get("required", [])
            
            # Get description if available
            description = field_info.get("description", "")
            description_str = f'  # {description}' if description else ""
            
            if required:
                definition += f"    {field_name}: {field_type}{description_str}\n"
            else:
                definition += f"    {field_name}: Optional[{field_type}] = None{description_str}\n"
        
        return definition
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from text.
        
        Args:
            text: Text containing JSON
            
        Returns:
            JSON string
        """
        # Check if text is already valid JSON
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code block
        json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(json_pattern, text)
        
        if match:
            return match.group(1)
        
        # If no code block, try to find JSON object
        json_pattern = r"\{[\s\S]*\}"
        match = re.search(json_pattern, text)
        
        if match:
            return match.group(0)
        
        # If no JSON object found, return original text
        return text


# Create a singleton instance
output_parser = OutputParser()