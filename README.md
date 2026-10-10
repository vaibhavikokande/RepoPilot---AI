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

### Implemented (Day 1, Day 2 & Day 3)

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
- ✅ Interactive frontend analysis & Code Intelligence dashboard
- ✅ API versioning (v1) and Pydantic schemas
- ✅ Automated test suite (30 unit and integration tests)
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

**Interactive API documentation**: http://localhost:8000/docs

## 🧪 Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v
```

## 📍 Development Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Foundation — Project setup, FastAPI, Next.js | ✅ Complete |
| **Phase 2** | Repository Ingestion — URL validation, safe clone, scan & metrics | ✅ Complete |
| **Phase 3** | Code Intelligence — Python AST & Tree-sitter JS/TS parsing | ✅ Complete |
| **Phase 4** | RAG Pipeline — Embeddings, pgvector, semantic search | 🔲 Planned |
| **Phase 5** | Agentic Workflow — LangGraph, agent orchestration | 🔲 Planned |
| **Phase 6** | Test Generation — AI-powered test creation | 🔲 Planned |
| **Phase 7** | Bug Detection & Fixes — Automated debugging | 🔲 Planned |
| **Phase 8** | MCP Integration — Model Context Protocol | 🔲 Planned |
| **Phase 9** | Evaluation — Benchmarks, quality metrics | 🔲 Planned |
| **Phase 10** | Deployment — Docker, CI/CD, cloud hosting | 🔲 Planned |

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
