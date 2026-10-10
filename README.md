# 🤖 RepoPilot AI

**Autonomous AI Software Engineer**

> Understand, analyze, test, debug, and improve your codebase with AI.

---

## 📋 Overview

RepoPilot AI is an AI-powered developer agent that autonomously analyzes GitHub repositories, understands codebases, identifies bugs, generates tests, suggests fixes, creates documentation, and provides actionable repository-level insights.

Built as a production-grade portfolio project demonstrating modern AI engineering with agentic workflows, RAG pipelines, and code intelligence.

## 🎯 Problem Statement

Modern software development faces critical challenges:

- **Code reviews** are time-consuming and inconsistent
- **Bug detection** often happens too late in the development cycle
- **Test coverage** gaps go unnoticed until production failures
- **Documentation** frequently falls out of sync with code
- **Onboarding** new developers to large codebases is slow and painful

RepoPilot AI addresses these by providing an autonomous AI engineer that continuously analyzes and improves code quality.

## 🔮 Vision

To create an AI software engineer that can:

1. Clone and deeply understand any GitHub repository
2. Analyze code quality, patterns, and potential issues
3. Generate comprehensive test suites
4. Detect and suggest fixes for bugs
5. Auto-generate and maintain documentation
6. Provide a natural language interface for codebase queries

## ✅ Key Features

### Implemented (Day 1, Day 2, Day 3, Day 4 & Day 5)

- ✅ FastAPI backend with health monitoring API
- ✅ Next.js + TypeScript frontend with landing page
- ✅ GitHub repository URL validation (HTTPS enforcement, format checks)
- ✅ Safe shallow cloning into temporary workspace with automatic cleanup
- ✅ Repository scanner with ignored directories (.git, node_modules, venv, etc.)
- ✅ Programming language detection across 20+ languages
- ✅ Repository statistics (file count, directory count, total size, largest files)
- ✅ Code Intelligence Engine (Python standard library AST & Tree-sitter for JS/TS)
- ✅ Code entity extraction (classes, methods, functions, interfaces, types, signatures, line numbers)
- ✅ Dependency & import relationship analysis (internal and external)
- ✅ Hierarchical codebase structural map
- ✅ **Code Chunking Engine** with AST line slicing, context headers, and token estimation
- ✅ **Intelligent Code Search Engine** with lexical, identifier, and metadata-driven ranking
- ✅ **Vector Index & Embeddings** (ChromaDB persistent storage, local ONNX `all-MiniLM-L6-v2`, OpenAI support)
- ✅ **Semantic Code Search** with cosine vector similarity and natural language query understanding
- ✅ **Hybrid Search with Reciprocal Rank Fusion (RRF)** combining keyword and vector retrieval
- ✅ Conversational query normalization and software engineering synonym expansion
- ✅ Explainable search with human-readable match insights and criteria breakdown
- ✅ Interactive frontend with Search Mode toggle (`Semantic`, `Hybrid`, `Keyword`) and 1-click Vector Indexing
- ✅ API versioning (v1) and Pydantic schemas
- ✅ Automated test suite (58 unit and integration tests)
- ✅ Project documentation & architecture document



### Planned

- 📊 AI-powered code analysis
- 🔍 RAG-based codebase Q&A
- 🤖 Multi-agent workflow orchestration (LangGraph)
- 🧪 Automated test generation
- 🐛 Bug detection and fix suggestions
- 📝 Documentation generation
- 🏥 Repository health scoring
- 🔌 MCP integration

## 🏗️ Planned AI Architecture

```
User → Next.js Frontend → FastAPI Backend → Repository Ingestion
                                                    ↓
                                            Code Parser (Tree-sitter)
                                                    ↓
                                        Code Knowledge Layer (Embeddings)
                                                    ↓
                                         RAG / Vector Database (pgvector)
                                                    ↓
                                     Agent Orchestrator (LangGraph)
                                                    ↓
                               Specialized AI Agents (Analysis, Testing, Debugging, Docs)
                                                    ↓
                                          Results & Insights
```

## 🛠️ Technology Stack

| Category | Technology |
|----------|------------|
| **Backend** | Python, FastAPI, Uvicorn, Pydantic |
| **Frontend** | Next.js, TypeScript, Tailwind CSS |
| **AI/ML** | LangGraph, LLMs (OpenAI/Anthropic), RAG |
| **Database** | PostgreSQL, pgvector |
| **Cache** | Redis |
| **Code Parsing** | Tree-sitter |
| **Integration** | GitHub API, MCP |
| **DevOps** | Docker, GitHub Actions |
| **Testing** | Pytest, Jest |

## 📁 Project Structure

```
RepoPilot-AI/
├── backend/                # FastAPI backend service
│   ├── app/
│   │   ├── api/v1/         # Versioned API endpoints
│   │   ├── core/           # Configuration & constants
│   │   ├── models/         # Data models
│   │   ├── services/       # Business logic
│   │   ├── utils/          # Utilities
│   │   └── main.py         # Application entry point
│   ├── tests/              # Backend tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # Next.js frontend
│   ├── app/                # App Router pages
│   ├── components/         # React components
│   ├── lib/                # Utilities & API client
│   └── .env.example
├── docs/                   # Project documentation
│   └── architecture.md
├── .gitignore
├── README.md
└── LICENSE
```

## 🚀 Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend runs at: http://localhost:8000

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend runs at: http://localhost:3000

## 📦 Repository Ingestion

RepoPilot AI accepts public GitHub repository URLs and processes them through an isolated, secure pipeline:

1. **URL Validation & Security Enforcement**:
   - Strictly enforces `https://github.com/owner/repository` formats.
   - Rejects non-HTTPS schemes, private credentials, and command injection characters.
2. **Safe Shallow Cloning**:
   - Clones with `--depth=1 --single-branch` into an ephemeral workspace directory.
   - Prevents path traversal outside the designated workspace.
   - Automatic cleanup using a Python context manager immediately after analysis.
3. **Smart Codebase Scanning**:
   - Recursively traverses repository while strictly skipping dependencies and metadata (`.git`, `node_modules`, `venv`, `__pycache__`, `.next`, `dist`, etc.).
   - Ignores binary files, media assets, compressed archives, and source maps.
4. **Language & Statistics Extraction**:
   - Maps file extensions and special filenames (e.g. `Dockerfile`, `Makefile`) to recognized languages.
   - Computes total files, directory counts, cumulative size, and identifies the largest files.
5. **Hierarchical File Tree Generation**:
   - Constructs a navigable file tree structure for intuitive frontend visualization.

## 🧠 Code Intelligence Engine

RepoPilot AI moves beyond raw file listings to statically comprehend codebase syntax and architecture:

1. **AST-Based Multi-Language Parsers**:
   - **Python**: Leverages Python's native `ast` library to extract classes, decorators, methods, top-level functions, type annotations, docstrings, and imports.
   - **JavaScript & TypeScript**: Integrates precompiled `tree-sitter` grammars (`tree-sitter-javascript`, `tree-sitter-typescript`, and TSX) to extract classes, methods, functions, arrow functions, interfaces, type aliases, and module import/export clauses.
2. **Entity Extraction with Precise Line Ranges**:
   - Every detected code entity (class, method, function, interface) captures exact 1-indexed `start_line` and `end_line` boundaries, signatures, docstrings, parameters, and return types.
   - Provides granular targeting required for future code search, retrieval, and RAG chunking.
3. **Dependency & Import Graph Mapping**:
   - Analyzes import declarations and resolves intra-repository relationships (e.g. `app.services.user_service` → `app/services/user_service.py`).
   - Distinguishes internal application modules from third-party external dependencies.
4. **Hierarchical Codebase Map**:
   - Generates an intuitive structural tree representing Directories → Files → Classes → Methods / Functions.
5. **Fault-Tolerant Parsing**:
   - Syntax errors or unsupported edge cases in individual files are captured as `FileParseError` records without halting codebase analysis.

## 🔍 Code Chunking & Intelligent Code Search

RepoPilot AI breaks down repositories into discrete, self-contained semantic code chunks and provides keyword, identifier, and AST metadata search:

1. **Semantic Code Chunking (`CodeChunker`)**:
   - Accurately slices source code lines using AST entity boundaries (`start_line` to `end_line`).
   - Builds contextual header strings (`File: ... | Scope: ... | Class/Method: ... | Lines: ...`) for retrieval.
   - Computes heuristic token estimates (`tokens_estimate`) to safeguard downstream LLM prompts.
   - Generates fallback `file_module` chunks for procedural scripts and configuration files without entity declarations.
2. **Lexical & Metadata Search Engine (`CodeSearchEngine`)**:
   - **Query Normalization**: Strips conversational prefixes (`"Where is"`, `"how to"`, `"handled"`, `"find"`) while preserving key engineering terms.
   - **Identifier Decomposition**: Automatically tokenizes CamelCase and snake_case identifiers (`UserService` → `['user', 'service']`, `auth_token` → `['auth', 'token']`).
   - **Domain Synonym Expansion**: Expands concepts across synonymous terms (`auth` ↔ `authentication`, `login`; `db` ↔ `database`; `user` ↔ `users`).
   - **Multi-Factor Weighted Scoring**: Rewards exact name matches, substring tokens, signatures, file paths, docstrings, decorators, and code bodies.
   - **Explainable Match Insights**: Returns a concise sentence explaining *why* each result matched (e.g., *"Method 'authenticate_user' in 'AuthService' matches 'user', 'authentication' via entity name and signature parameters."*).
   - **Granular Entity Filtering**: Allows targeted filtering by `function`, `class`, `method`, or `interface`.

## 🧠 Semantic Code Search & Vector Index

RepoPilot AI integrates deep vector representations to understand code meaning beyond exact token matches:

1. **Provider-Agnostic Embeddings Architecture (`backend/app/embeddings/`)**:
   - `BaseEmbeddingProvider`: Abstract interface for batch text embedding, query embedding, and vector dimension verification.
   - **Local ONNX Provider (`LocalChromaEmbeddingProvider`)**: Runs `all-MiniLM-L6-v2` (384 dimensions) natively via ONNX Runtime without external network or API key dependencies.
   - **Hosted Provider (`OpenAIEmbeddingProvider`)**: Connects to OpenAI embeddings API (`text-embedding-3-small`, 1536 dimensions) when API key is configured.
   - **Mock Provider (`MockEmbeddingProvider`)**: Deterministic unit-normalized vector generator for fast, isolated test runs.
   - `EmbeddingService`: Orchestrates chunk formatting (`File + Entity + Signature + Docstring + Code`), batched requests, exponential backoff retries, and dimension validation.
2. **Persistent Vector Store (`ChromaVectorStore`)**:
   - Persistent local ChromaDB storage under `backend/chroma_db/`.
   - **Repository-Level Collection Isolation**: Deterministic collection namespaces (`repo_<hash>`) ensure codebases never mix vectors.
   - **Model Mismatch Guard**: Detects if embedding model or dimension changed and safely rebuilds collection instead of mixing incompatible spaces.
   - Upserts vectors, identifiers, code documents, and comprehensive metadata in batches.
3. **Hybrid Search with Reciprocal Rank Fusion (RRF)**:
   - Combines lexical keyword scores with semantic vector cosine similarity using Reciprocal Rank Fusion:
     $$RRF(d) = \sum_{m \in \{lexical, semantic\}} \frac{w_m}{60 + rank_m(d)}$$
   - Seamlessly returns results in `semantic`, `hybrid`, or `lexical` search modes.

## 🔌 API



### Health Check

```bash
GET /api/v1/health
```

Response:

```json
{
  "status": "healthy",
  "service": "RepoPilot AI",
  "version": "0.1.0",
  "timestamp": "2026-10-08T09:00:00.000000+00:00"
}
```

### Analyze Repository

```bash
POST /api/v1/repositories/analyze
```

Request payload:

```json
{
  "repository_url": "https://github.com/octocat/Hello-World"
}
```

Response:

```json
{
  "repository": {
    "name": "Hello-World",
    "owner": "octocat",
    "url": "https://github.com/octocat/Hello-World",
    "default_branch": "master"
  },
  "statistics": {
    "total_files": 1,
    "total_directories": 0,
    "total_size_bytes": 13,
    "file_extensions": {
      "(no extension)": 1
    },
    "largest_files": [
      {
        "path": "README",
        "size_bytes": 13
      }
    ]
  },
  "languages": {},
  "file_tree": [
    {
      "name": "README",
      "type": "file",
      "path": "README",
      "size_bytes": 13,
      "children": null
    }
  ],
  "status": "success"
}
```

### Analyze Code Intelligence

```bash
POST /api/v1/repositories/analyze-code
```

Request payload:

```json
{
  "repository_url": "https://github.com/octocat/Hello-World"
}
```

Response:

```json
{
  "repository": {
    "name": "Hello-World",
    "owner": "octocat",
    "url": "https://github.com/octocat/Hello-World",
    "default_branch": "master"
  },
  "summary": {
    "files_analyzed": 1,
    "languages": {
      "Python": 1
    },
    "classes": 1,
    "functions": 2,
    "methods": 3,
    "imports": 4,
    "interfaces": 0,
    "types": 0,
    "files_with_errors": 0
  },
  "files": [],
  "entities": [],
  "dependencies": [],
  "codebase_tree": [],
  "errors": [],
  "status": "success"
}
```

### Search Repository Code

```bash
POST /api/v1/repositories/search-code
```

Request payload:

```json
{
  "repository_url": "https://github.com/my-org/my-service",
  "query": "Where is user authentication handled?",
  "limit": 5,
  "entity_types": ["function", "class", "method"]
}
```

Response:

```json
{
  "repository": {
    "name": "my-service",
    "owner": "my-org",
    "url": "https://github.com/my-org/my-service",
    "default_branch": "main"
  },
  "query": "Where is user authentication handled?",
  "total_chunks_indexed": 38,
  "total_results": 2,
  "results": [
    {
      "chunk_id": "app/services.py#UserService.create_user#L50-L53",
      "file_path": "app/services.py",
      "entity_name": "create_user",
      "entity_type": "method",
      "language": "Python",
      "start_line": 50,
      "end_line": 53,
      "signature": "def create_user(self, name: str) -> dict",
      "docstring": null,
      "parent": "UserService",
      "parameters": ["self", "name"],
      "return_type": "dict",
      "code_snippet": "    def create_user(self, name: str) -> dict:\n        return {\"name\": name}\n",
      "context_header": "File: app/services.py | Scope: UserService | Method: create_user | Lines: 50-53 | Signature: def create_user(self, name: str) -> dict",
      "tokens_estimate": 18,
      "score": 14.5,
      "match_reasons": [
        "Identifier parts matched: user",
        "Enclosing class 'UserService' matches: user"
      ],
      "explanation": "Method 'create_user' in 'UserService' [app/services.py:50-53] matches query: Identifier parts matched: user."
    }
  ],
  "status": "success"
}
```

### Index Repository (Vector Embeddings)

```bash
POST /api/v1/repositories/index
```

Request payload:

```json
{
  "repository_url": "https://github.com/my-org/my-service",
  "force_reindex": false
}
```

Response:

```json
{
  "repository": {
    "name": "my-service",
    "owner": "my-org",
    "url": "https://github.com/my-org/my-service",
    "default_branch": "main"
  },
  "status": "success",
  "files_processed": 14,
  "chunks_indexed": 38,
  "chunks_skipped": 0,
  "embedding_model": "all-MiniLM-L6-v2",
  "dimension": 384,
  "total_vectors_in_index": 38,
  "message": "Repository successfully indexed into persistent vector store."
}
```

### Semantic & Hybrid Search

```bash
POST /api/v1/repositories/semantic-search
```

Request payload:

```json
{
  "repository_url": "https://github.com/my-org/my-service",
  "query": "Where does the application validate user login credentials?",
  "limit": 5,
  "mode": "semantic",
  "entity_types": ["function", "class", "method"]
}
```

Response:

```json
{
  "repository": {
    "name": "my-service",
    "owner": "my-org",
    "url": "https://github.com/my-org/my-service",
    "default_branch": "main"
  },
  "query": "Where does the application validate user login credentials?",
  "search_mode": "semantic",
  "total_results": 1,
  "results": [
    {
      "chunk_id": "app/services/auth.py#AuthService.login#L15-L35",
      "file_path": "app/services/auth.py",
      "entity_name": "login",
      "entity_type": "method",
      "language": "Python",
      "start_line": 15,
      "end_line": 35,
      "signature": "def login(username: str, token: str) -> bool",
      "docstring": "Validate credentials token against database.",
      "parent": "AuthService",
      "code_snippet": "    def login(username: str, token: str) -> bool:\n        return self.verify(token)\n",
      "context_header": "File: app/services/auth.py | Scope: AuthService | Method: login | Lines: 15-35",
      "tokens_estimate": 24,
      "score": 0.8421,
      "search_mode": "semantic",
      "match_reasons": [
        "Semantic similarity: 0.84",
        "Embedding cosine distance: 0.158"
      ],
      "explanation": "Method 'login' in app/services/auth.py semantically aligns with query (similarity 0.84)."
    }
  ],
  "status": "success"
}
```

**Interactive API documentation**: http://localhost:8000/docs

## 🧪 Running Tests

```bash
# Backend tests (58 tests covering ingestion, AST parsing, chunking, embeddings, Chroma vector store, and search)
cd backend
pytest tests/ -v
```

## 📍 Development Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Foundation — Project setup, FastAPI, Next.js | ✅ Complete |
| **Phase 2** | Repository Ingestion — URL validation, safe clone, scan & metrics | ✅ Complete |
| **Phase 3** | Code Intelligence — Python AST & Tree-sitter JS/TS parsing | ✅ Complete |
| **Phase 4** | Code Chunking & Intelligent Search — Lexical, AST metadata & explanations | ✅ Complete |
| **Phase 5** | Vector Embeddings & Semantic Search — ChromaDB, ONNX all-MiniLM-L6-v2 & RRF Hybrid Retrieval | ✅ Complete |
| **Phase 6** | Agentic Workflow — LangGraph, multi-agent orchestration | 🔲 Planned |
| **Phase 7** | Automated Test Generation — AI-powered test suite creation | 🔲 Planned |
| **Phase 8** | Bug Detection & Fixes — Automated debugging and code repair | 🔲 Planned |
| **Phase 9** | MCP Integration — Model Context Protocol tools & sidecars | 🔲 Planned |
| **Phase 10** | Production Deployment — Docker, CI/CD, cloud hosting | 🔲 Planned |



> This project is being developed incrementally. Each day adds meaningful functionality while maintaining production-quality code standards.

## 🔮 Future Features

- Real-time repository analysis streaming
- Multi-language support (Python, JavaScript, TypeScript, Go, Rust)
- PR review automation
- Code refactoring suggestions
- Dependency vulnerability scanning
- Performance profiling insights
- Team collaboration dashboard
- VS Code extension
- CLI tool

## 🤝 Contributing

This project is in active incremental development. Contributions, suggestions, and feedback are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ using FastAPI, Next.js, and AI**
