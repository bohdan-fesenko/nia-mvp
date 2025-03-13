a#!/bin/bash

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
    echo "You can still use the API without Docker, but you'll need to set up Neo4j, Qdrant, and Redis separately."
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
    echo "You can still use the API without Docker, but you'll need to set up Neo4j, Qdrant, and Redis separately."
    echo "Environment setup completed (without database initialization)."
    echo "To activate the environment, run: source venv/bin/activate"
    echo "To start the API server, run: uvicorn src.app.main:app --reload"
    exit 0
fi

# Start Neo4j, Qdrant, and Redis containers
echo "Starting Neo4j, Qdrant, and Redis containers..."
$DOCKER_COMPOSE_CMD up -d neo4j qdrant redis

# Wait for Neo4j to be ready
echo "Waiting for Neo4j to be ready..."

# Function to check if Neo4j is ready
check_neo4j_ready() {
    # Try to connect to Neo4j's HTTP endpoint
    if curl -s -I http://localhost:7474 | grep -q "200 OK"; then
        return 0  # Success
    else
        return 1  # Not ready yet
    fi
}

# Wait for Neo4j with timeout
MAX_RETRIES=30
RETRY_COUNT=0
while ! check_neo4j_ready; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "Timed out waiting for Neo4j to start. Please check the Neo4j logs."
        echo "You can continue manually once Neo4j is ready by running: python -m src.app.db.init_db"
        exit 1
    fi
    echo "Waiting for Neo4j to be ready... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

echo "Neo4j is ready!"

# Initialize the database
echo "Initializing the database..."
python -m src.app.db.init_db

# Create sample data for testing
# echo "Creating sample data for testing..."
# python -m src.app.utils.create_sample_data # we don't need sample data

echo "Environment setup complete!"
echo "To activate the environment, run: source venv/bin/activate"
echo "To start the API server, run: uvicorn src.app.main:app --reload"