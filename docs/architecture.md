# RepoPilot AI — Architecture

## Overview

This document describes the high-level architecture of RepoPilot AI. Components are labeled as **[Implemented]** or **[Planned]** to reflect the current project state.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER (Developer)                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                FRONTEND [Implemented]                            │
│             Next.js + TypeScript + Tailwind CSS                  │
│                                                                  │
│  • Landing page with repository URL input                       │
│  • Dashboard for analysis results (planned)                     │
│  • Real-time streaming interface (planned)                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 BACKEND [Implemented]                            │
│                FastAPI + Python 3.10+                             │
│                                                                  │
│  • API Gateway with versioning (v1)                             │
│  • Health monitoring endpoint                                    │
│  • Request validation (Pydantic)                                │
│  • CORS middleware                                               │
│  • Authentication & authorization (planned)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Repository  │  │     Code     │  │    Agent     │
│  Ingestion   │  │  Knowledge   │  │ Orchestrator │
│[Implemented] │  │   [Planned]  │  │  [Planned]   │
│              │  │              │  │              │
│ • URL checks │  │ • Tree-sitter│  │ • LangGraph  │
│ • Clone repos│  │ • Embeddings │  │ • Multi-agent│
│ • File tree  │  │ • pgvector   │  │ • Workflows  │
└──────────────┘  └──────────────┘  └──────┬───────┘
                                           │
                              ┌────────────┼────────────┐
                              ▼            ▼            ▼
                      ┌────────────┐┌────────────┐┌────────────┐
                      │  Analysis  ││   Testing  ││  Debugging │
                      │   Agent    ││   Agent    ││   Agent    │
                      │ [Planned]  ││ [Planned]  ││ [Planned]  │
                      └────────────┘└────────────┘└────────────┘
```

## Component Details

### Frontend (Next.js) [Implemented]

- **Purpose**: User interface for interacting with RepoPilot AI
- **Tech**: Next.js 14+, TypeScript, Tailwind CSS
- **Current Features**:
  - Repository URL input with analyze button
  - Feature overview grid
  - Responsive dark theme design
- **Planned Features**:
  - Analysis results dashboard
  - Real-time streaming output
  - Code diff viewer
  - Repository health score display

### Backend API (FastAPI) [Implemented]

- **Purpose**: REST API gateway and service orchestration
- **Tech**: FastAPI, Pydantic, Uvicorn
- **Current Endpoints**:
  - `GET /api/v1/health` — Service health check
- **Architecture Patterns**:
  - Application factory (`create_app()`)
  - Versioned API routing
  - Pydantic settings management
  - Dependency injection ready

### Repository Ingestion Service [Implemented]

The foundation for future code understanding and RAG pipelines:

```
User
 ↓
Next.js Frontend
 ↓
FastAPI Backend
 ↓
Repository Ingestion Service
 ↓
GitHub Repository
 ↓
Repository Scanner
 ↓
Repository Metadata & File Tree
```

- **Purpose**: Validate, shallow-clone, scan, and extract metrics from public repositories
- **Tech**: GitPython, Python pathlib/os, Pydantic v2
- **Components**:
  - `GitHubService`: Strict HTTPS URL validation, owner/repo validation, injection rejection
  - `RepositoryService`: Shallow cloning (`--depth=1 --single-branch`) into ephemeral workspaces with auto-cleanup context manager
  - `ScannerService`: Directory filtering, binary filtering, multi-language detection, metric aggregation, and file tree builder
- **Responsibilities**:
  - Validate GitHub repository HTTPS URLs
  - Clone repositories safely to isolated workspace directories
  - Extract structured file trees and metadata
  - Detect 20+ programming languages
  - Compute file counts, directory counts, size metrics, and largest files
  - Immediate workspace cleanup preventing disk retention

### Code Parser [Planned]

- **Purpose**: Parse source code into structured representations
- **Tech**: Tree-sitter
- **Output**: AST nodes, function signatures, class hierarchies, import graphs

### Code Knowledge Layer [Planned]

- **Purpose**: Create searchable knowledge base from parsed code
- **Tech**: Embedding models, chunking strategies
- **Output**: Code embeddings, semantic code representations

### Vector Database [Planned]

- **Purpose**: Store and retrieve code embeddings for RAG
- **Tech**: PostgreSQL + pgvector
- **Operations**: Similarity search, filtered retrieval, metadata queries

### RAG Pipeline [Planned]

- **Purpose**: Retrieve relevant code context for AI queries
- **Tech**: LangChain/LangGraph, embedding models
- **Flow**: Query → Embed → Search → Retrieve → Augment → Generate

### Agent Orchestrator [Planned]

- **Purpose**: Coordinate specialized AI agents using graph-based workflows
- **Tech**: LangGraph
- **Agents**:
  - **Code Analysis Agent** — Quality analysis, pattern detection
  - **Test Generation Agent** — Automated test suite creation
  - **Bug Detection Agent** — Proactive bug and vulnerability detection
  - **Documentation Agent** — Auto-generate documentation
  - **Code Fix Agent** — Suggest and apply code fixes

### Cache Layer [Planned]

- **Purpose**: Cache analysis results, embeddings, and API responses
- **Tech**: Redis
- **Benefits**: Faster repeated analyses, reduced LLM API costs

### MCP Integration [Planned]

- **Purpose**: Model Context Protocol for enhanced tool use
- **Tech**: MCP SDK

## Data Flow

1. **User** submits a GitHub repository URL via the frontend
2. **Backend** receives the request and validates the URL
3. **Repository Ingestion** clones the repository and extracts files
4. **Code Parser** processes source files into AST representations
5. **Embeddings** are generated from code chunks
6. **Vector Database** stores the embeddings for semantic search
7. **Agent Orchestrator** dispatches specialized agents based on the task
8. Each **Agent** queries the RAG pipeline for relevant code context
9. Agents produce **analysis, tests, fixes, and documentation**
10. Results are **aggregated** and returned to the user via the API
11. Results are **cached** in Redis for subsequent queries

## API Design Principles

- **Versioned**: All endpoints under `/api/v1/` prefix for backward compatibility
- **RESTful**: Standard HTTP methods and status codes
- **Typed**: Pydantic models for all request/response schemas
- **Documented**: Auto-generated OpenAPI/Swagger documentation at `/docs`
- **Async**: Async endpoints for non-blocking I/O operations

## Security Considerations

### Implemented Safeguards
- **HTTPS Only**: Only secure `https://github.com/` URLs permitted; credentials in URLs rejected.
- **Strict Input Validation**: Regex-enforced repository paths prevent command injection and malformed requests.
- **Zero Code Execution**: Repository code is strictly scanned as static text; no packages, scripts, or executables are run.
- **Path Traversal Prevention**: Target directories are resolved and verified against the designated workspace boundary.
- **Ephemeral Workspaces**: Repositories are cloned to isolated directories and removed immediately upon analysis completion.
- **Git Protection**: Cloned files, dependencies, and environment files are excluded via `.gitignore`.

### Planned Safeguards
- API key authentication and rate limiting for backend services
- Sandboxed code execution environment (for future test execution phases)
- Enterprise repository access tokens and secrets vault
- File size and clone depth quotas in production deployment
