"""
Error handling middleware.
This module provides middleware for handling errors in the API.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
from neo4j.exceptions import Neo4jError
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class APIError(Exception):
    """
    Base class for API errors.
    """
    def __init__(
        self, 
        status_code: int, 
        message: str, 
        error_code: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(message)


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Handle APIError exceptions.
    """
    error_response = {
        "error": {
            "message": exc.message,
            "status_code": exc.status_code,
        }
    }
    
    if exc.error_code:
        error_response["error"]["code"] = exc.error_code
    
    if exc.details:
        error_response["error"]["details"] = exc.details
    
    logger.error(f"API Error: {error_response}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def validation_error_handler(request: Request, exc: Union[RequestValidationError, ValidationError]) -> JSONResponse:
    """
    Handle validation errors.
    """
    error_details = []
    for error in exc.errors():
        error_details.append({
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", "")
        })
    
    error_response = {
        "error": {
            "message": "Validation error",
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "code": "VALIDATION_ERROR",
            "details": error_details
        }
    }
    
    logger.error(f"Validation Error: {error_response}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


async def neo4j_error_handler(request: Request, exc: Neo4jError) -> JSONResponse:
    """
    Handle Neo4j errors.
    """
    error_response = {
        "error": {
            "message": "Database error",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "code": "DATABASE_ERROR",
            "details": {
                "neo4j_code": exc.code,
                "neo4j_message": str(exc)
            }
        }
    }
    
    logger.error(f"Neo4j Error: {error_response}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle general exceptions.
    """
    error_response = {
        "error": {
            "message": "Internal server error",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "code": "INTERNAL_SERVER_ERROR",
            "details": {
                "type": type(exc).__name__,
                "message": str(exc)
            }
        }
    }
    
    logger.error(f"Unhandled Exception: {type(exc).__name__}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


def add_error_handlers(app: FastAPI) -> None:
    """
    Add error handlers to the FastAPI application.
    """
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(Neo4jError, neo4j_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)