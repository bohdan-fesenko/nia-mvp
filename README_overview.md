# AI Project Assistant

A comprehensive platform for AI-assisted project management, document creation, and task tracking with real-time collaboration features.

## Project Structure

### Backend (FastAPI)

```
backend/
├── src/
│   └── app/
│       ├── api/                      # API endpoints and models
│       │   ├── middlewares/          # Middleware components
│       │   │   └── error_handler.py  # Global error handling
│       │   ├── models/               # API data models
│       │   │   ├── auth.py           # Authentication models
│       │   │   ├── documents.py      # Document models
│       │   │   ├── folders.py        # Folder models
│       │   │   └── projects.py       # Project models
│       │   └── routes/               # API route definitions
│       │       ├── agent.py          # Agent interaction endpoints
│       │       ├── auth.py           # Authentication endpoints
│       │       ├── document_processing.py # Document processing endpoints
│       │       ├── documents.py      # Document CRUD endpoints
│       │       ├── events.py         # Event streaming endpoints
│       │       ├── message.py        # Messaging endpoints
│       │       ├── projects.py       # Project management endpoints
│       │       └── task_management.py # Task management endpoints
│       ├── db/                       # Database connections and models
│       │   ├── init_db.py            # Database initialization
│       │   ├── models.py             # Database models
│       │   ├── neo4j_client.py       # Neo4j graph database client
│       │   ├── prisma_client.py      # Prisma ORM client
│       │   ├── qdrant_client.py      # Qdrant vector database client
│       │   └── redis_client.py       # Redis client for caching and pub/sub
│       ├── models/                   # Domain models
│       │   ├── agent.py              # Agent models
│       │   ├── document_processing.py # Document processing models
│       │   ├── task_management.py    # Task management models
│       │   └── user.py               # User models
│       ├── repositories/             # Data access layer
│       │   ├── agent_repository.py   # Agent data access
│       │   ├── base_repository.py    # Base repository pattern
│       │   ├── document_repository.py # Document data access
│       │   ├── document_version_repository.py # Version history
│       │   ├── event_repository.py   # Event data access
│       │   ├── folder_repository.py  # Folder data access
│       │   ├── neo4j_repository.py   # Neo4j specific repository
│       │   ├── project_repository.py # Project data access
│       │   └── task_management_repository.py # Task data access
│       ├── services/                 # Business logic layer
│       │   ├── cache_service.py      # Caching service
│       │   ├── conversation_agent_service.py # Conversation agent
│       │   ├── diff_service.py       # Document diff service
│       │   ├── document_processing_service.py # Document processing
│       │   ├── event_service.py      # Event handling service
│       │   ├── execution_agent_service.py # Execution agent
│       │   ├── llm_service.py        # Language model service
│       │   ├── output_parser.py      # LLM output parsing
│       │   ├── polling_service.py    # Event polling service
│       │   ├── pubsub_service.py     # Pub/sub messaging
│       │   ├── rate_limit_service.py # Rate limiting
│       │   ├── session_service.py    # Session management
│       │   ├── task_management_service.py # Task management
│       │   └── token_manager.py      # Token management for LLMs
│       ├── utils/                    # Utility functions
│       │   ├── auth.py               # Authentication utilities
│       │   ├── create_sample_data.py # Sample data generation
│       │   └── generate_dev_token.py # Development token generation
│       ├── config.py                 # Application configuration
│       └── main.py                   # Application entry point
├── tests/                            # Test suite
├── .env                              # Environment variables
├── .env.example                      # Example environment variables
├── docker-compose.yml                # Docker configuration
├── Dockerfile                        # Docker build configuration
├── requirements.txt                  # Python dependencies
└── setup_env.sh                      # Environment setup script
```

### Frontend (Next.js)

```
web_app/
├── app/                              # Next.js App Router
│   ├── (auth)/                       # Authentication routes
│   │   ├── login/                    # Login page
│   │   └── signup/                   # Signup page
│   ├── api/                          # API routes
│   │   └── auth/                     # Auth API routes
│   │       └── [...nextauth]/        # NextAuth configuration
│   ├── auth-login/                   # Auth login page
│   ├── auth-profile/                 # Auth profile page
│   ├── profile/                      # User profile page
│   ├── session-test/                 # Session testing page
│   ├── settings/                     # User settings page
│   ├── simple-login/                 # Simple login page
│   ├── static/                       # Static content page
│   ├── test/                         # Test page
│   ├── auth-provider.tsx             # Auth provider component
│   └── layout.tsx                    # Root layout
├── components/                       # Reusable components
│   ├── demo-nav.tsx                  # Demo navigation
│   ├── document-diff-viewer.tsx      # Document diff viewer
│   ├── document-editor.tsx           # Document editor
│   ├── document-version-history.tsx  # Version history component
│   ├── markdown-preview.tsx          # Markdown preview
│   ├── ui/                           # UI components
│   └── user-avatar.tsx               # User avatar component
├── contexts/                         # React contexts
│   ├── app-provider.tsx              # Application provider
│   ├── document-context.tsx          # Document context
│   ├── polling-context.tsx           # Polling context
│   ├── project-context.tsx           # Project context
│   ├── task-context.tsx              # Task context
│   └── toast-context.tsx             # Toast notification context
├── hooks/                            # Custom React hooks
│   ├── use-auth.ts                   # Authentication hook
│   ├── use-events.ts                 # Events hook
│   └── use-toast.ts                  # Toast notification hook
├── lib/                              # Library code
│   ├── api-client.ts                 # API client
│   ├── auth-utils.ts                 # Authentication utilities
│   ├── diff-utils.ts                 # Diff utilities
│   ├── markdown-utils.ts             # Markdown utilities
│   ├── types.ts                      # TypeScript types
│   └── utils/                        # Utility functions
│       ├── date-utils.ts             # Date utilities
│       └── type-converters.ts        # Type conversion utilities
├── project_docs/                     # Project documentation
│   ├── adr/                          # Architecture Decision Records
│   ├── project/                      # Project documentation
│   │   ├── api_documentation.md      # API documentation
│   │   ├── architecture_design_document.md # Architecture design
│   │   └── coding_standards.md       # Coding standards
│   └── tasks/                        # Task documentation
│       ├── project_tasks_overview.md # Tasks overview
│       ├── TASK_009_next_auth_implementation.md # Auth implementation
│       └── TASK_010_api_frontend_type_conversion.md # Type conversion
├── public/                           # Static assets
├── services/                         # Frontend services
│   ├── document-service.ts           # Document service
│   └── project-service.ts            # Project service
├── styles/                           # Global styles
├── types/                            # TypeScript type definitions
│   ├── auth.ts                       # Auth types
│   ├── document.ts                   # Document types
│   └── next-auth.d.ts                # NextAuth type extensions
├── middleware.ts                     # Next.js middleware
├── next.config.js                    # Next.js configuration
├── package.json                      # Dependencies and scripts
└── tsconfig.json                     # TypeScript configuration
```

## Key Features

- **Document Management**: Create, edit, and version documents with Markdown and Mermaid diagram support
- **Project Organization**: Organize documents in projects and folders with hierarchical structure
- **Task Management**: Create and track tasks with status updates and relationships
- **Real-time Collaboration**: Real-time updates and notifications for collaborative editing
- **AI Integration**: LLM-powered assistance for document creation and task management
- **Authentication**: Secure authentication with NextAuth and Google OAuth
- **Type Safety**: Robust type conversion between API and frontend data models

## Technology Stack

- **Backend**: FastAPI, Neo4j, Redis, Qdrant, Prisma
- **Frontend**: Next.js 15.1.0, React, TypeScript, TailwindCSS
- **Authentication**: NextAuth with JWT and Google OAuth
- **Real-time**: Server-Sent Events (SSE) for real-time updates
- **AI**: Integration with Language Model providers