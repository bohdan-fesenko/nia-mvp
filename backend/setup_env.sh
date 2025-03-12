#!/bin/bash

# Create a Python virtual environment
# python -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads

# Copy environment variables if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from .env.example. Please update with your actual values."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker before proceeding with database setup."
    echo "You can still use the API without Docker, but you'll need to set up Neo4j and Qdrant separately."
    echo "Environment setup completed (without database initialization)."
    echo "To activate the environment, run: source venv/bin/activate"
    echo "To start the API server, run: uvicorn src.app.main:app --reload"
    exit 0
fi

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo "Neither docker-compose nor docker compose is available. Please install Docker Compose."
    echo "You can still use the API without Docker, but you'll need to set up Neo4j and Qdrant separately."
    echo "Environment setup completed (without database initialization)."
    echo "To activate the environment, run: source venv/bin/activate"
    echo "To start the API server, run: uvicorn src.app.main:app --reload"
    exit 0
fi

# Start Neo4j and Qdrant containers
echo "Starting Neo4j and Qdrant containers..."
$DOCKER_COMPOSE_CMD up -d neo4j qdrant

# Wait for Neo4j to be ready
echo "Waiting for Neo4j to be ready..."
sleep 10

# Initialize the database
echo "Initializing the database..."
python -m src.app.db.init_db

echo "Environment setup complete!"
echo "To activate the environment, run: source venv/bin/activate"
echo "To start the API server, run: uvicorn src.app.main:app --reload"