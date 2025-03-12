"""
Create sample data for testing.
This script creates a sample project and document for testing.
"""
import asyncio
import uuid
from datetime import datetime

from ..repositories.project_repository import ProjectRepository
from ..repositories.document_repository import DocumentRepository
from ..db.neo4j_client import neo4j_client

async def create_sample_data():
    """
    Create sample data for testing.
    """
    print("Creating sample data...")
    
    # Connect to Neo4j
    await neo4j_client.connect_async()
    
    # Create repositories
    project_repository = ProjectRepository()
    document_repository = DocumentRepository()
    
    # Create a sample project
    project_id = str(uuid.uuid4())
    project_data = {
        "id": project_id,
        "name": "Sample Project",
        "description": "A sample project for testing",
        "created_by": "dev-user-id",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "status": "active",
        "owner_id": "dev-user-id"  # Add owner_id field
    }
    
    # Create the project
    await project_repository.create(project_data)
    print(f"Created project: {project_id}")
    # Create a sample document
    document_id = str(uuid.uuid4())  # Use UUID instead of fixed ID
    document_data = {
        "id": document_id,
        "name": "Sample Document",  # Use name instead of title
        "type": "markdown",
        "project_id": project_id,
        "folder_id": None,
        "created_by": "dev-user-id",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "status": "active",
        "owner_id": "dev-user-id",  # Add owner_id field
        "is_task": False  # Add is_task field
    }
    
    # Create the document
    document_content = "# Sample Document\n\nThis is a sample document for testing."
    await document_repository.create_document(document_data, document_content)
    print(f"Created document: {document_id}")
    
    # Create another sample document
    document_id2 = str(uuid.uuid4())  # Use UUID instead of fixed ID
    document_data2 = {
        "id": document_id2,
        "name": "Another Sample Document",  # Use name instead of title
        "type": "markdown",
        "project_id": project_id,
        "folder_id": None,
        "created_by": "dev-user-id",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "status": "active",
        "owner_id": "dev-user-id",  # Add owner_id field
        "is_task": False  # Add is_task field
    }
    
    # Create the document
    document_content2 = "# Another Sample Document\n\nThis is another sample document for testing."
    await document_repository.create_document(document_data2, document_content2)
    print(f"Created document: {document_id2}")
    
    # Close Neo4j connection
    await neo4j_client.close_async()
    
    print("Sample data creation complete!")

if __name__ == "__main__":
    asyncio.run(create_sample_data())