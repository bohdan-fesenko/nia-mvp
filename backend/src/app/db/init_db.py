"""
Database initialization script.
This script initializes the Neo4j database with the necessary constraints and indexes.
"""
import logging
import asyncio
from datetime import datetime
import uuid

from ..db.neo4j_client import neo4j_client
from ..db.qdrant_client import qdrant_client
from ..config import settings
from ..utils.auth import get_password_hash

logger = logging.getLogger(__name__)

# Neo4j Cypher queries for database initialization
INIT_QUERIES = [
    # Create constraints for User model
    """
    CREATE CONSTRAINT user_id_unique IF NOT EXISTS
    FOR (u:User) REQUIRE u.id IS UNIQUE
    """,
    
    """
    CREATE CONSTRAINT user_email_unique IF NOT EXISTS
    FOR (u:User) REQUIRE u.email IS UNIQUE
    """,
    
    # Create constraints for Project model
    """
    CREATE CONSTRAINT project_id_unique IF NOT EXISTS
    FOR (p:Project) REQUIRE p.id IS UNIQUE
    """,
    
    # Create constraints for Document model
    """
    CREATE CONSTRAINT document_id_unique IF NOT EXISTS
    FOR (d:Document) REQUIRE d.id IS UNIQUE
    """,
    
    # Create constraints for Folder model
    """
    CREATE CONSTRAINT folder_id_unique IF NOT EXISTS
    FOR (f:Folder) REQUIRE f.id IS UNIQUE
    """,
    
    # Create constraints for DocumentVersion model
    """
    CREATE CONSTRAINT document_version_id_unique IF NOT EXISTS
    FOR (dv:DocumentVersion) REQUIRE dv.id IS UNIQUE
    """,
    
    # Create constraints for DocumentChunk model
    """
    CREATE CONSTRAINT document_chunk_id_unique IF NOT EXISTS
    FOR (dc:DocumentChunk) REQUIRE dc.id IS UNIQUE
    """,
    
    # Create constraints for VectorEmbedding model
    """
    CREATE CONSTRAINT vector_embedding_id_unique IF NOT EXISTS
    FOR (ve:VectorEmbedding) REQUIRE ve.id IS UNIQUE
    """,
    
    # Create constraints for Agent model
    """
    CREATE CONSTRAINT agent_id_unique IF NOT EXISTS
    FOR (a:Agent) REQUIRE a.id IS UNIQUE
    """,
    
    # Create constraints for AgentTask model
    """
    CREATE CONSTRAINT agent_task_id_unique IF NOT EXISTS
    FOR (at:AgentTask) REQUIRE at.id IS UNIQUE
    """,
    
    # Create constraints for ChatSession model
    """
    CREATE CONSTRAINT chat_session_id_unique IF NOT EXISTS
    FOR (cs:ChatSession) REQUIRE cs.id IS UNIQUE
    """,
    
    # Create constraints for ChatMessage model
    """
    CREATE CONSTRAINT chat_message_id_unique IF NOT EXISTS
    FOR (cm:ChatMessage) REQUIRE cm.id IS UNIQUE
    """,
    
    # Create constraints for Notepad model
    """
    CREATE CONSTRAINT notepad_id_unique IF NOT EXISTS
    FOR (n:Notepad) REQUIRE n.id IS UNIQUE
    """,
    
    # Create constraints for NotepadEntry model
    """
    CREATE CONSTRAINT notepad_entry_id_unique IF NOT EXISTS
    FOR (ne:NotepadEntry) REQUIRE ne.id IS UNIQUE
    """,
    
    # Create indexes for common queries
    """
    CREATE INDEX document_type_idx IF NOT EXISTS
    FOR (d:Document) ON (d.type)
    """,
    
    """
    CREATE INDEX document_is_task_idx IF NOT EXISTS
    FOR (d:Document) ON (d.is_task)
    """,
    
    """
    CREATE INDEX document_status_idx IF NOT EXISTS
    FOR (d:Document) ON (d.status)
    """,
    
    """
    CREATE INDEX agent_task_status_idx IF NOT EXISTS
    FOR (at:AgentTask) ON (at.status)
    """,
    
    """
    CREATE INDEX agent_type_idx IF NOT EXISTS
    FOR (a:Agent) ON (a.type)
    """,
    
    # Create indexes for OAuth authentication
    """
    CREATE INDEX user_provider_idx IF NOT EXISTS
    FOR (u:User) ON (u.provider)
    """,
    
    """
    CREATE INDEX user_provider_user_id_idx IF NOT EXISTS
    FOR (u:User) ON (u.provider, u.provider_user_id)
    """
]


async def init_neo4j_database():
    """
    Initialize the Neo4j database with constraints and indexes.
    """
    logger.info("Initializing Neo4j database...")
    
    try:
        # Execute initialization queries
        for query in INIT_QUERIES:
            await neo4j_client.execute_query_async(query)
        
        logger.info("Neo4j database initialization completed successfully")
        
        # Check if admin user exists, create if not
        admin_exists_query = """
        MATCH (u:User {email: $email}) 
        RETURN u
        """
        
        admin_exists = await neo4j_client.execute_query_async(
            admin_exists_query,
            {"email": "admin@example.com"}
        )
        
        if not admin_exists:
            # Create admin user
            create_admin_query = """
            CREATE (u:User {
                id: $id,
                email: $email,
                name: $name,
                password: $password,
                created_at: datetime(),
                updated_at: datetime(),
                provider: 'local',
                provider_user_id: $id,
                email_verified: false,
                locale: 'en'
            })
            RETURN u
            """
            
            await neo4j_client.execute_query_async(
                create_admin_query,
                {
                    "id": str(uuid.uuid4()),
                    "email": "admin@example.com",
                    "name": "Admin User",
                    "password": get_password_hash("password123")
                }
            )
            logger.info("Created admin user")
    
    except Exception as e:
        logger.error(f"Error initializing Neo4j database: {str(e)}")
        raise


async def init_qdrant_database():
    """
    Initialize the Qdrant database.
    """
    logger.info("Initializing Qdrant database...")
    
    try:
        # Check if collection exists, create if not
        if not qdrant_client.collection_exists():
            qdrant_client.create_collection(
                vector_size=settings.EMBEDDING_DIMENSION,
                distance="Cosine"
            )
            logger.info(f"Created Qdrant collection: {settings.QDRANT_COLLECTION}")
        else:
            logger.info(f"Qdrant collection {settings.QDRANT_COLLECTION} already exists")
    
    except Exception as e:
        logger.error(f"Error initializing Qdrant database: {str(e)}")
        raise


async def init_database():
    """
    Initialize all databases.
    """
    try:
        await init_neo4j_database()
        await init_qdrant_database()
        logger.info("All databases initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing databases: {str(e)}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_database())