"""
Main application module.
This module initializes the FastAPI application.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import sys
from typing import List
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from loguru import logger
from .config import settings
from .api.middlewares.error_handler import add_error_handlers
from .api.routes import auth, projects, agent, document_processing, task_management, documents, message, events, test
from .db.neo4j_client import neo4j_client
from .db.qdrant_client import qdrant_client
from .db.redis_client import redis_client
from .services.event_service import event_publisher
from .services.llm_service import llm_service
from .services.conversation_agent_service import conversation_agent_service
from .services.execution_agent_service import execution_agent_service
from .services.cache_service import cache_service
from .services.pubsub_service import pubsub_service
from .services.session_service import session_service
from .services.rate_limit_service import rate_limit_service, RateLimitMiddleware

# Configure loguru
logger.remove()  # Remove default handler
log_level = "DEBUG" if settings.DEBUG else "INFO"
logger.add(
    sys.stderr,
    level=log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="1 week",
    level=log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Create FastAPI app
app = FastAPI(
    title="AI Project Assistant API",
    description="API for AI Project Assistant",
    version="1.0.0",
    docs_url="/api/v1/docs" if settings.DEBUG else None,
    redoc_url="/api/v1/redoc" if settings.DEBUG else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limit middleware
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        limit_type='api',
        exclude_paths=["/api/v1/health", "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json"],
    )
    logger.info("Added rate limit middleware")

# Add trusted host middleware in production
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.CORS_ORIGINS,
    )
    logger.info("Added trusted host middleware")

# Add error handlers
add_error_handlers(app)

# Health check endpoint
@app.get("/api/v1/health", tags=["health"])
async def health_check():
    """
    Health check endpoint to verify API is running
    """
    return {"status": "ok", "environment": settings.ENVIRONMENT}


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """
    Connect to databases and start services on startup
    """
    try:
        # Connect to Neo4j
        await neo4j_client.connect_async()
        logger.success("Connected to Neo4j database")
        
        # Connect to Qdrant
        qdrant_client.connect()
        logger.success("Connected to Qdrant database")
        # Connect to Redis (optional)
        redis_connected = False
        try:
            await redis_client.connect_async()
            logger.success("Connected to Redis database")
            redis_connected = True
        except Exception as redis_error:
            logger.warning(f"Redis connection failed, continuing without Redis: {str(redis_error)}")
            # Set Redis services to disabled mode
            if hasattr(cache_service, '_enabled'):
                cache_service._enabled = False
            if hasattr(pubsub_service, '_enabled'):
                pubsub_service._enabled = False
            if hasattr(session_service, '_enabled'):
                session_service._enabled = False
            if hasattr(rate_limit_service, '_enabled'):
                rate_limit_service._enabled = False
        # No duplicate code needed here
        
        # Initialize collections if needed
        if not qdrant_client.collection_exists():
            qdrant_client.create_collection(
                vector_size=settings.EMBEDDING_DIMENSION,
                distance="Cosine"
            )
            logger.success(f"Created Qdrant collection: {settings.QDRANT_COLLECTION}")
            
        # Start event publisher and pubsub service if Redis is available
        if redis_connected:
            try:
                await event_publisher.start()
                logger.success("Started event publisher")
                
                # Temporarily disable pubsub service to fix the error
                # await pubsub_service.start()
                # logger.success("Started pubsub service")
            except Exception as e:
                logger.warning(f"Failed to start event services, continuing without them: {str(e)}")
        
        # Initialize LLM service
        logger.info(f"Initializing LLM service with model: {settings.DEFAULT_LLM_MODEL}")
        
        # Initialize agent services
        await conversation_agent_service.initialize()
        await execution_agent_service.initialize()
        logger.success("Initialized agent services")
        
        # Clean up expired sessions if Redis is available
        if redis_connected:
            try:
                await session_service.cleanup_expired_sessions()
                logger.success("Cleaned up expired sessions")
            except Exception as e:
                logger.warning(f"Failed to clean up expired sessions: {str(e)}")
    except Exception as e:
        logger.error(f"Error connecting to databases: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Disconnect from databases and stop services on shutdown
    """
    try:
        # Stop Redis-dependent services if Redis is available
        if redis_connected:
            try:
                # Stop event publisher
                await event_publisher.stop()
                logger.success("Stopped event publisher")
                
                # Temporarily disable pubsub service to fix the error
                # await pubsub_service.stop()
                # logger.success("Stopped pubsub service")
                
                # Disconnect from Redis
                await redis_client.close_async()
                logger.success("Disconnected from Redis database")
            except Exception as e:
                logger.warning(f"Error stopping Redis-dependent services: {str(e)}")
        
        # Disconnect from Neo4j
        try:
            await neo4j_client.close_async()
            logger.success("Disconnected from Neo4j database")
        except Exception as e:
            logger.warning(f"Error disconnecting from Neo4j: {str(e)}")
        
        # Disconnect from Qdrant
        try:
            qdrant_client.close()
            logger.success("Disconnected from Qdrant database")
        except Exception as e:
            logger.warning(f"Error disconnecting from Qdrant: {str(e)}")
    except Exception as e:
        logger.error(f"Error disconnecting from databases: {str(e)}")


# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
app.include_router(message.router, prefix="/api/v1", tags=["message"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(agent.router, prefix="/api/v1", tags=["agents"])
app.include_router(document_processing.router, prefix="/api/v1", tags=["document-processing"])
app.include_router(events.router, prefix="/api/v1", tags=["events"])
app.include_router(test.router, prefix="/api/v1", tags=["test"])

# These will be uncommented as we implement them
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
# app.include_router(folders.router, prefix="/api/v1", tags=["folders"])
app.include_router(task_management.router, prefix="/api/v1", tags=["tasks"])

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "src.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )