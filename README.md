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

### Implemented (Day 1 – Day 9)

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
- ✅ **RAG-Based Code Understanding** (`POST /api/v1/repositories/ask`)
- ✅ **Strict Code Grounding & Verified Source Citations** (`[S1]`, `[S2]`, file paths, line ranges)
- ✅ **Prompt Injection Defenses & Untrusted Code Boundaries**
- ✅ **Multi-Provider LLM Engine** (OpenAI `gpt-4o-mini` with deterministic `MockLLMGenerator` fallback)
- ✅ **Interactive "Ask RepoPilot" UI** with suggested questions, citation badge links, and code inspector
- ✅ **Code Quality Analysis Engine** (cyclomatic complexity, nesting depth, function/file size thresholds, parameter count, docstring coverage, broad exceptions, unused imports, duplicate code block detection)
- ✅ **Repository Health Dashboard & Scoring** (composite 0–100 score, maintainability/complexity/documentation/reliability sub-scores, letter grades A–F, severity & category filtering, actionable suggestions)
- ✅ **Static Security Analysis Engine (SAST)** (hardcoded credentials, dynamic execution eval/exec, insecure subprocess/shell injection, SQL injection indicators, unsafe deserialization pickle/yaml, weak cryptography, disabled TLS verification)
- ✅ **Security Risk Dashboard & Privacy Protections** (complete secret redaction, confidence & severity classification, CWE mappings, human-review guardrails, optional AI executive summary)
- ✅ **AI-Powered Unit Test Generation** (`POST /api/v1/repositories/generate-tests`)
- ✅ **AST Context Extraction** (target signature, docstrings, enclosing classes, imports, helper snippets)
- ✅ **Pytest Test Suite Synthesis & Strict Grounding** (happy path, boundary conditions, edge cases, error handling, mock dependencies)
- ✅ **AST Syntax & Structure Validation** (zero hallucinated syntax, test discovery verification, isolated execution markers)
- ✅ **Interactive Test Generator UI** (file/entity pickers, test descriptions, syntax verification badges, copy & `.py` download)
- ✅ Conversational query normalization and software engineering synonym expansion
- ✅ Explainable search with human-readable match insights and criteria breakdown
- ✅ API versioning (v1) and Pydantic schemas
- ✅ Automated test suite (144 unit and integration tests passing in <1s)
- ✅ Project documentation & architecture document

### Planned

- 📊 Deep AI-powered code analysis
- 🤖 Multi-agent workflow orchestration (LangGraph)
- 🐛 Bug detection and fix suggestions
- 📝 Documentation generation
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

## 🏥 Code Quality Analysis & Repository Health Dashboard

RepoPilot AI statically inspects codebase structure and computes transparent, actionable health metrics:

1. **Static Quality Rules Engine (`backend/app/code_quality/`)**:
   - **Structural Complexity**: Measures McCabe cyclomatic complexity (branch points) for Python AST and JavaScript/TypeScript regex tokens. Flags methods and functions exceeding threshold limits.
   - **Nesting Depth**: Evaluates AST statement depth (loops, conditionals, exception handlers) and nested brace indentation (>3/4 depth).
   - **Size Violations**: Identifies oversized functions (>50/100 lines) and bloated source files (>400/800 lines).
   - **Parameter Overload**: Flags methods taking excessive parameters (>5 arguments).
   - **Documentation Coverage**: Verifies presence of docstrings on public classes, methods, and functions.
   - **Reliability Smells**: Detects broad exception clauses (`except Exception: pass`, empty `catch {}`), and potentially unused imported modules.
   - **Duplication Detection**: Employs rolling hash windowing over normalized non-comment tokens to identify duplicate or near-duplicate code blocks (6+ lines).
2. **Deterministic Repository Health Scoring**:
   - Computes KLOC-normalized penalties across 4 key dimensions:
     - **Maintainability** (40% weight): Function/file sizes, nesting depth, and duplicate code blocks.
     - **Complexity** (25% weight): Average and peak cyclomatic complexity.
     - **Documentation** (20% weight): Docstring coverage on public API symbols.
     - **Reliability** (15% weight): Broad exception handling and unused imports.
   - Generates overall composite score (0–100) and letter grades: `A` ($\ge 90$), `B` ($\ge 80$), `C` ($\ge 70$), `D` ($\ge 60$), `F` ($< 60$).
3. **Interactive Repository Health Dashboard**:
   - Health score grade badge with color indicators and animated progress bars.
   - Overview metrics: total files, lines of code, comment lines, complexity, and duplicate blocks.
   - Severity filtering (`critical`, `high`, `medium`, `low`, `info`) and category filtering (`maintainability`, `complexity`, `documentation`, `reliability`, `duplication`).
   - Actionable remediation advice and exact source location links.

## 🛡️ Static Security Analysis & Risk Detection Engine

RepoPilot AI incorporates a lightweight Static Application Security Testing (SAST) engine designed to detect common security anti-patterns, hardcoded credentials, and injection risks without executing untrusted code:

1. **Modular Security Rules & CWE Mappings (`backend/app/security_analysis/`)**:
   - **Hardcoded Credentials (`CWE-798`)**: Identifies suspicious assignments to credential-like identifiers (`password`, `api_key`, `secret`, `token`, etc.) while ignoring common dummy placeholders (`CHANGE_ME`, `TODO`, `dummy`, `test`). Classifies recognized live token formats (e.g. `sk-`, `ghp_`, `AKIA`) as `critical` severity.
   - **Dangerous Dynamic Execution (`CWE-95`)**: Detects Python `eval()`, `exec()`, and JavaScript `eval()`, distinguishing dynamic expressions from static constants.
   - **Insecure Subprocess Execution (`CWE-78`)**: Flags `shell=True` and `os.system()` with dynamic arguments while recognizing safe argument-list invocations (`subprocess.run(["cmd", arg])`).
   - **SQL Injection Indicators (`CWE-89`)**: Detects string-built SQL queries (using f-strings, `%`, or `.format()`) passed to database `execute()` functions, while passing safe parameterized queries.
   - **Unsafe Deserialization (`CWE-502`)**: Detects untrusted deserialization via Python `pickle.loads()`, `marshal`, and unsafe `yaml.load()` missing `SafeLoader`.
   - **Weak Cryptographic Algorithms (`CWE-328` / `CWE-327`)**: Detects legacy hashing functions (`MD5`, `SHA-1`) while permitting non-security checksums that explicitly declare `usedforsecurity=False`.
   - **Insecure TLS Verification (`CWE-295`)**: Flags explicit certificate bypasses such as `verify=False` in HTTP clients and `ssl._create_unverified_context()`.
   - **Broad Exception Handling (`CWE-391`)**: Flags broad error silencing (`except Exception: pass`) inside security-sensitive authentication/authorization functions.
2. **Strict Privacy & Secret-Redaction Safeguards**:
   - **Zero Secret Exposure**: Suspected secrets are redacted before presentation (`sk-***[REDACTED length 32]`). Raw secrets are **never** logged, stored in finding summaries, or forwarded to external LLMs.
   - **Safe Sandbox Execution**: The engine is purely static. Repository code is never executed, dependencies are never installed, and no exploitation attempts are made.
3. **Severity & Confidence Classifications**:
   - **Severity**: `Critical` (immediate exploitable pattern / live key), `High` (dangerous primitives with dynamic input), `Medium` (static shell / weak algorithms), `Low` / `Informational` (maintainability and defense-in-depth).
   - **Confidence**: `High` (syntactically unambiguous AST nodes), `Medium` (pattern matches requiring data-flow context), `Low` (heuristics).
4. **Interactive Security Dashboard**:
   - Overview metrics: Scanned files, findings breakdown, and severity badges.
   - Severity & category filter pills, CWE links, and search bar.
   - Actionable remediation advice and exact source file locations (`file_path:line`).
   - Clear human review guardrail indicating static findings require developer confirmation.

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

### 4. RAG Code Understanding (`POST /api/v1/repositories/ask`)

Ask natural language questions about the codebase and receive grounded answers with verified source citations:

```json
{
  "repository_url": "https://github.com/octocat/Hello-World",
  "question": "How does authentication work in this project?",
  "top_k": 5
}
```

**Example Response:**
```json
{
  "repository": {
    "name": "Hello-World",
    "owner": "octocat",
    "url": "https://github.com/octocat/Hello-World",
    "default_branch": "main"
  },
  "question": "How does authentication work in this project?",
  "answer": "Based on the codebase analysis, authentication is handled in [S1] via `verify_token` in `app/auth.py`. User sessions are managed by `SessionManager` in [S2].",
  "citations": [
    {
      "source_id": "S1",
      "file_path": "app/auth.py",
      "start_line": 15,
      "end_line": 42,
      "entity_name": "verify_token",
      "entity_type": "function",
      "score": 0.892
    },
    {
      "source_id": "S2",
      "file_path": "app/session.py",
      "start_line": 1,
      "end_line": 35,
      "entity_name": "SessionManager",
      "entity_type": "class",
      "score": 0.841
    }
  ],
  "sources": [
    {
      "source_id": "S1",
      "chunk_id": "chunk_auth_verify",
      "file_path": "app/auth.py",
      "start_line": 15,
      "end_line": 42,
      "entity_name": "verify_token",
      "entity_type": "function",
      "language": "python",
      "code_content": "def verify_token(token: str) -> bool:\n    ...",
      "score": 0.892
    }
  ],
  "retrieved_chunks": 2,
  "status": "success"
}
```

### 5. Code Quality & Health Analysis (`POST /api/v1/repositories/quality`)

Analyze codebase health, detect static code smells, compute cyclomatic complexity, and calculate maintainability scores:

```bash
POST /api/v1/repositories/quality
```

Request payload:
```json
{
  "repository_url": "https://github.com/octocat/Hello-World",
  "max_files": 200
}
```

**Example Response:**
```json
{
  "repository": {
    "name": "Hello-World",
    "owner": "octocat",
    "url": "https://github.com/octocat/Hello-World",
    "default_branch": "master"
  },
  "overall_health_score": 92.5,
  "health_grade": "A",
  "score_breakdown": {
    "maintainability_score": 94.0,
    "complexity_score": 90.0,
    "documentation_score": 88.0,
    "reliability_score": 98.0
  },
  "metrics": {
    "total_files_analyzed": 12,
    "total_lines_of_code": 1420,
    "total_comment_lines": 310,
    "total_blank_lines": 250,
    "average_file_length": 118.3,
    "average_function_length": 18.2,
    "average_cyclomatic_complexity": 2.4,
    "max_cyclomatic_complexity": 7,
    "docstring_coverage_percentage": 82.5,
    "duplicate_block_count": 0
  },
  "findings_summary": {
    "critical": 0,
    "high": 1,
    "medium": 3,
    "low": 4,
    "info": 2,
    "total": 10
  },
  "findings": [
    {
      "id": "finding_1_high",
      "rule_id": "HIGH_CYCLOMATIC_COMPLEXITY",
      "severity": "high",
      "category": "complexity",
      "title": "High cyclomatic complexity in 'process_records'",
      "description": "Function 'process_records' has a cyclomatic complexity of 12 (threshold is 10).",
      "file_path": "backend/app/services/processor.py",
      "start_line": 45,
      "end_line": 95,
      "entity_name": "process_records",
      "entity_type": "function",
      "metric_name": "cyclomatic_complexity",
      "metric_value": 12.0,
      "threshold_value": 10.0,
      "suggestion": "Refactor complex branching into smaller helper functions or lookup tables."
    }
  ],
  "file_summaries": [
    {
      "file_path": "backend/app/services/processor.py",
      "language": "python",
      "lines_total": 140,
      "lines_code": 110,
      "complexity_average": 4.2,
      "complexity_max": 12,
      "findings_count": 2,
      "health_score": 84.0
    }
  ],
  "status": "success"
}
```

### 6. Security Analysis & Risk Detection (`POST /api/v1/repositories/analyze-security`)

Statically inspect repository code for security anti-patterns, hardcoded credentials, and injection risks:

```bash
POST /api/v1/repositories/analyze-security
```

Request payload:
```json
{
  "repository_url": "https://github.com/octocat/Hello-World",
  "explain_with_llm": false
}
```

**Example Response:**
```json
{
  "repository": {
    "name": "Hello-World",
    "owner": "octocat",
    "url": "https://github.com/octocat/Hello-World",
    "default_branch": "master"
  },
  "analysis": {
    "files_discovered": 40,
    "files_analyzed": 38,
    "files_skipped": 2
  },
  "summary": {
    "critical": 0,
    "high": 2,
    "medium": 3,
    "low": 1,
    "informational": 0,
    "total": 6
  },
  "findings": [
    {
      "finding_id": "sec_python_dangerous_eval_a1b2c3d4",
      "rule_id": "PYTHON_DANGEROUS_EVAL",
      "title": "Dynamic Code Execution (eval)",
      "description": "The code calls 'eval()' to dynamically execute code. Evaluating untrusted input leads to Remote Code Execution (RCE).",
      "severity": "high",
      "confidence": "high",
      "file_path": "app/utils/parser.py",
      "start_line": 24,
      "end_line": 24,
      "entity_name": "parse_user_expression",
      "evidence_summary": "Call to eval() executes dynamic code expressions.",
      "remediation": "Avoid dynamic execution. Use ast.literal_eval() for safely parsing Python literals, or an explicit dispatch table.",
      "cwe_id": "CWE-95",
      "category": "code_execution"
    },
    {
      "finding_id": "sec_python_hardcoded_credential_e5f6g7h8",
      "rule_id": "PYTHON_HARDCODED_CREDENTIAL",
      "title": "Hardcoded Credential in 'api_key'",
      "description": "Variable 'api_key' is assigned a hardcoded string literal that appears to be a sensitive credential.",
      "severity": "high",
      "confidence": "medium",
      "file_path": "app/config.py",
      "start_line": 12,
      "end_line": 12,
      "entity_name": null,
      "evidence_summary": "Variable 'api_key' assigned a hardcoded literal string (32 characters).",
      "remediation": "Store secrets in environment variables or use a secrets manager. Never commit API keys directly to source control.",
      "cwe_id": "CWE-798",
      "category": "credentials"
    }
  ],
  "category_summary": {
    "code_execution": 1,
    "credentials": 1,
    "command_injection": 1,
    "sql_injection": 1,
    "deserialization": 1,
    "cryptography": 1
  },
  "status": "completed",
  "llm_summary": "Static security scan for 'Hello-World' identified 6 findings requiring review. Primary areas of concern include: code execution (1), credentials (1), command injection (1)."
}
```

### 7. AI-Powered Unit Test Generation (`POST /api/v1/repositories/generate-tests`)

Extract grounded AST context for a function or method and synthesize a complete `pytest` test suite:

```bash
POST /api/v1/repositories/generate-tests
```

Request payload:
```json
{
  "repository_url": "https://github.com/octocat/Hello-World",
  "file_path": "app/services/calculator.py",
  "entity_name": "divide_numbers"
}
```

**Example Response:**
```json
{
  "repository": {
    "name": "Hello-World",
    "owner": "octocat",
    "url": "https://github.com/octocat/Hello-World",
    "default_branch": "master"
  },
  "target": {
    "file_path": "app/services/calculator.py",
    "entity_name": "divide_numbers",
    "entity_type": "function",
    "start_line": 15,
    "end_line": 25,
    "class_name": null,
    "signature": "def divide_numbers(a: float, b: float) -> float:",
    "docstring": "Divide two numbers and return the quotient. Raises ZeroDivisionError if b is 0."
  },
  "test_framework": "pytest",
  "test_code": "import pytest\nfrom app.services.calculator import divide_numbers\n\ndef test_divide_numbers_happy_path():\n    assert divide_numbers(10.0, 2.0) == 5.0\n\ndef test_divide_numbers_zero_division():\n    with pytest.raises(ZeroDivisionError):\n        divide_numbers(10.0, 0.0)\n",
  "test_cases": [
    {
      "name": "test_divide_numbers_happy_path",
      "purpose": "Verify correct quotient for positive floats"
    },
    {
      "name": "test_divide_numbers_zero_division",
      "purpose": "Verify ZeroDivisionError when denominator is zero"
    }
  ],
  "validation": {
    "syntax_valid": true,
    "structure_valid": true,
    "test_functions_found": 2,
    "syntax_error": null,
    "warnings": [],
    "execution_status": "not_run"
  },
  "suggested_file_name": "test_calculator_divide_numbers.py",
  "status": "completed"
}
```

**Interactive API documentation**: http://localhost:8000/docs

## 🧪 Running Tests

```bash
# Backend tests (144 tests covering ingestion, AST parsing, chunking, embeddings, Chroma vector store, search, RAG pipeline, code quality, security analysis, and test generation)
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
| **Phase 6** | RAG-Based Code Understanding — Evidence grounding, prompt injection defenses & verified citations | ✅ Complete |
| **Phase 7** | Code Quality & Health Dashboard — AST metrics, complexity, code smells, duplication & health scoring | ✅ Complete |
| **Phase 8** | Security Analysis & Risk Detection — SAST rules, secret redaction, CWE mapping & security dashboard | ✅ Complete |
| **Phase 9** | AI-Powered Unit Test Generation — AST context extraction, pytest generation, syntax validation & dashboard | ✅ Complete |
| **Phase 10** | Agentic Workflow — LangGraph, multi-agent orchestration | 🔲 Planned |
| **Phase 11** | Bug Detection & Fixes — Automated debugging and code repair | 🔲 Planned |
| **Phase 12** | Production Deployment — Docker, CI/CD, cloud hosting | 🔲 Planned |



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
