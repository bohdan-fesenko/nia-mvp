# AI Project Assistant Backend

This is the backend API for the AI Project Assistant project, built with FastAPI, Neo4j, and Qdrant.

## Features

- FastAPI application with proper project structure
- Neo4j database integration for graph data
- Qdrant vector database for embeddings and semantic search
- JWT authentication with role-based access control
- WebSocket infrastructure for real-time updates
- Event-based notification system
- Error handling middleware
- API versioning
- OpenAI integration with pydantic-ai for LLM operations
- Docker setup for development environment

## Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Neo4j (run via Docker)
- Qdrant (run via Docker)
- OpenAI API key (for LLM features)

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-directory>/backend
```

### 2. Run the setup script

```bash
chmod +x setup_env.sh
./setup_env.sh
```

This script will:
- Create a Python virtual environment
- Install dependencies
- Create necessary directories
- Copy environment variables template
- Start Neo4j and Qdrant containers
- Initialize the database

### 3. Update environment variables

Edit the `.env` file to set your configuration values, especially:
- `JWT_SECRET`
- `NEO4J_PASSWORD`
- `OPENAI_API_KEY`

## Running the application

### Development mode

```bash
source venv/bin/activate  # Activate the virtual environment
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000/api/v1

### Using Docker

To run the entire stack with Docker:

```bash
docker-compose up -d
```

## API Documentation

When running in development mode, the API documentation is available at:

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Project Structure

```
backend/
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Docker configuration
├── requirements.txt        # Python dependencies
├── setup_env.sh            # Setup script
├── .env.example            # Environment variables template
├── src/                    # Source code
    └── app/                # Application code
        ├── main.py         # FastAPI application
        ├── config.py       # Configuration
        ├── api/            # API endpoints
        │   ├── models/     # Pydantic models
        │   ├── routes/     # API routes
        │   └── middlewares/# Middleware components
        ├── db/             # Database modules
        │   ├── neo4j_client.py  # Neo4j client
        │   ├── qdrant_client.py # Qdrant client
        │   ├── models.py   # Database models
        │   └── init_db.py  # Database initialization
        ├── repositories/   # Repository pattern implementations
        │   ├── base_repository.py    # Base repository interface
        │   ├── neo4j_repository.py   # Neo4j repository implementation
        │   ├── project_repository.py # Project repository
        │   ├── folder_repository.py  # Folder repository
        │   └── document_repository.py # Document repository
        ├── services/       # Business logic
        │   ├── llm_service.py     # LLM service
        │   ├── websocket_service.py # WebSocket service
        │   └── event_service.py   # Event handling service
        └── utils/          # Utility functions
            └── auth.py     # Authentication utilities
```

## Authentication

The API uses JWT tokens for authentication. To authenticate:

1. Register a user: `POST /api/v1/auth/register`
2. Login to get tokens: `POST /api/v1/auth/login`
3. Use the access token in the Authorization header: `Authorization: Bearer <token>`
4. Refresh tokens when they expire: `POST /api/v1/auth/refresh`

## Database

### Neo4j

Neo4j is used as the primary database for storing structured data in a graph format. This allows for complex relationships between entities like users, projects, documents, etc.

### Qdrant

Qdrant is used as a vector database for storing embeddings. This enables semantic search and similarity matching for documents and content.

## WebSocket Infrastructure

The backend implements a WebSocket infrastructure for real-time updates and notifications:

### WebSocket Connection

- Endpoint: `ws://localhost:8000/api/v1/ws`
- Authentication: JWT token passed as a query parameter (`?token=<jwt_token>`)
- Connection management with automatic reconnection handling

### Event System

The WebSocket system uses an event-based architecture:

- **Event Types**: Predefined event types for different update categories
- **Event Publishing**: Services publish events to notify clients of changes
- **Event Subscription**: Clients subscribe to specific event types
- **Event Filtering**: Events can be filtered by project, document, or chat session

### Key Event Types

- `document:updated`: When a document is created, updated, or deleted
- `folder:updated`: When folder structure changes
- `ai:typing`: When AI is generating a response
- `ai:response`: When AI completes a response
- `task:status`: When a task status changes
- `agent:task:created`: When a new agent task is created
- `agent:task:updated`: When an agent task status is updated
- `agent:task:progress`: Real-time progress updates for a task
- `agent:task:completed`: When an agent task is completed
- `agent:task:failed`: When an agent task fails

### Client Reconnection

- Automatic reconnection with exponential backoff
- State synchronization after reconnection
- Missed events handling during disconnection

### Usage Example

```python
# Server-side event publishing
async def update_document(document_id: str, content: str):
    # Update document in database
    document = await document_repository.update(document_id, {"content": content})
    
    # Publish event to notify clients
    await event_service.publish_event(
        event_type="document:updated",
        data={
            "id": document_id,
            "content": content,
            "updated_at": document.updated_at
        }
    )
```

## LLM Integration

The backend integrates with OpenAI's API for:
- Text generation
- Embeddings generation
- Structured data extraction using pydantic-ai

## Development

### Adding a new API endpoint

1. Create a new route file in `src/app/api/routes/`
2. Define your endpoint using FastAPI router
3. Add any required models in `src/app/api/models/`
4. Import and include your router in `src/app/main.py`

### Database operations

The project uses the Repository Pattern for database operations:

- Base repositories provide a consistent interface for CRUD operations
- Entity-specific repositories implement business logic for each entity type
- Repositories abstract the database implementation details from the API layer
- Use the Neo4j client for direct graph database operations when needed
- Use the Qdrant client for vector operations

## Testing

Run tests with pytest:

```bash
pytest
```

## Deployment

For production deployment:

1. Update the `.env` file with production settings
2. Build the Docker image: `docker build -t ai-project-assistant-api .`
3. Deploy using Docker Compose or your preferred container orchestration system

# Don't change this SECTION !!!
(venv) (base) admin@MacBook-Pro backend % python -m src.app.utils.generate_dev_token

Development JWT Token:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXZfdXNlciIsIm5hbWUiOiJEZXZlbG9wbWVudCBVc2VyIiwiZW1haWwiOiJkZXZAZXhhbXBsZS5jb20iLCJyb2xlcyI6WyJ1c2VyIiwiYWRtaW4iXSwiZXhwIjoxNzQ0MzUyMjY0fQ.N4BKkg_031dT5QqBPNljJjkKPGBEiENFilqS1TyRRZ8

This token will be valid for 30 days.
Add this token to your frontend WebSocket context for development purposes.