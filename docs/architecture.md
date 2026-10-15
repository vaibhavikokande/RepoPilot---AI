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
│  Ingestion   │  │ Intelligence │  │ Orchestrator │
│[Implemented] │  │[Implemented] │  │  [Planned]   │
│              │  │              │  │              │
│ • URL checks │  │ • Python AST │  │ • LangGraph  │
│ • Clone repos│  │ • Tree-sitter│  │ • Multi-agent│
│ • File tree  │  │ • Code map   │  │ • Workflows  │
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
  - Interactive Code Search UI (lexical, semantic, and hybrid modes)
  - Interactive "Ask RepoPilot" RAG question-answering with verified source citations
  - Repository Health Dashboard with letter grade, sub-scores, findings filters, and file quality metrics
  - Static Security Analysis Dashboard with severity badges, category pills, CWE mapping, and remediation guidance
  - Responsive dark theme design
- **Planned Features**:
  - Real-time streaming output
  - Code diff viewer
  - Automated PR reviews

### Backend API (FastAPI) [Implemented]

- **Purpose**: REST API gateway and service orchestration
- **Tech**: FastAPI, Pydantic, Uvicorn
- **Current Endpoints**:
  - `GET /api/v1/health` — Service health check
  - `POST /api/v1/repositories/analyze` — Repository ingestion, statistics, and AST code intelligence
  - `POST /api/v1/repositories/search` — Lexical, AST-metadata, semantic, and hybrid code search
  - `POST /api/v1/repositories/index` — Embeddings generation and ChromaDB vector indexing
  - `POST /api/v1/repositories/ask` — RAG-based code understanding with citations
  - `POST /api/v1/repositories/quality` — Code quality analysis, smell detection, and health scoring
  - `POST /api/v1/repositories/analyze-security` — Static security analysis, risk detection, and CWE reporting
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

### Code Intelligence Engine [Implemented]

The AST-based parsing and structural comprehension layer:

```
User
 ↓
Next.js Frontend
 ↓
FastAPI Backend
 ↓
Repository Ingestion
 ↓
Repository Scanner
 ↓
Code Intelligence Engine
 ├── Language Detection
 ├── AST Parser (Python AST, Tree-sitter JS/TS/TSX)
 ├── Entity Extraction (Classes, Methods, Functions, Signatures, Line Info)
 ├── Dependency Analysis (Intra-repo vs External Imports)
 └── Codebase Map (Directory → File → Class → Methods / Functions)
 ↓
Future RAG Layer [Planned]
```

- **Purpose**: Parse source code into rich structural representations without code execution
- **Tech**: Python `ast`, `tree-sitter`, `tree-sitter-javascript`, `tree-sitter-typescript`
- **Components**:
  - `PythonParser`: Standard library AST parser extracting classes, methods, top-level functions, decorators, type hints, docstrings, imports, and variables.
  - `JavaScriptTypeScriptParser`: Tree-sitter grammar parser extracting classes, methods, functions, arrow functions, interfaces, type aliases, and imports.
  - `CodebaseTreeBuilder`: Builds a hierarchical structural map connecting files to their internal entities.
  - `CodeIntelligenceAnalyzer`: Orchestrates multi-file parsing, maps intra-repo dependencies, computes quantitative summaries, and isolates syntax errors.
- **Output**: Structured entities with 1-indexed `start_line` / `end_line` ranges, dependency maps, and codebase trees.

### Code Chunking Engine [Implemented]

- **Purpose**: Deconstructs parsed files into discrete, semantically bounded code units (`CodeChunk`) for search and vector retrieval.
- **Components**:
  - `CodeChunker`:
    - Slices raw code text according to exact AST entity line boundaries (`start_line` to `end_line`).
    - Synthesizes informative `context_header` lines combining repository file path, enclosing classes, entity types, signatures, and line numbers.
    - Computes token heuristic estimates (`tokens_estimate`) to prevent LLM context overflows in downstream RAG.
    - Generates fallback `file_module` chunks for configuration and procedural script files lacking AST entity declarations.

### Intelligent Code Search Engine [Implemented]

- **Purpose**: Provides high-precision keyword, identifier, and metadata-driven search across indexed codebase chunks without requiring an active LLM.
- **Components**:
  - `CodeSearchEngine`:
    - **Query Normalization**: Strips conversational question prefixes (`"Where is"`, `"how to"`, `"handled"`, `"find"`) and generic English stopwords while preserving technical tokens.
    - **Identifier Tokenization**: Deconstructs CamelCase, PascalCase, and snake_case identifiers (`UserService` → `['user', 'service']`, `auth_token` → `['auth', 'token']`).
    - **Domain Synonym Expansion**: Expands software engineering concepts (`auth` ↔ `authentication`, `login`; `db` ↔ `database`; `repo` ↔ `repository`).
    - **Multi-Factor Weighted Scoring**:
      - Exact entity name match: 10.0
      - Split identifier tokens: 5.0 per term
      - Enclosing class / scope match: 4.0
      - File path & directory matches: 3.5
      - Signature parameters & types: 3.0
      - Docstring & comments: 2.5
      - Decorators: 2.0
      - Body code terms: 1.0
    - **Match Reason & Insight Generation**: Compiles human-readable explanations explaining *why* a chunk was retrieved.
    - **Type Filtering**: Supports filtering by `class`, `function`, `method`, `interface`.

### Vector Database & Embeddings [Implemented]

- **Purpose**: Persist dense code chunk embeddings and perform semantic similarity queries with repository-level isolation.
- **Tech**: ChromaDB with persistent local storage, ONNX `all-MiniLM-L6-v2` (384 dimensions) for local execution, and optional hosted OpenAI `text-embedding-3-small` (1536 dimensions).
- **Features**:
  - Deterministic repository namespaces (`repo_<hash>`) ensuring zero inter-repository data contamination.
  - Model and dimension mismatch guard protecting vector index integrity.
  - Batched upserts with comprehensive chunk metadata (line ranges, signatures, docstrings, scopes).
  - Cosine distance and similarity score computation.
  - Hybrid Search via Reciprocal Rank Fusion (RRF) integrating lexical and semantic rank orders.



### RAG Pipeline [Implemented]

- **Purpose**: Answer natural language questions about codebases strictly grounded in retrieved code evidence
- **Tech**: FastAPI, ChromaDB, httpx, OpenAI `gpt-4o-mini`, deterministic Mock fallback generator
- **Architecture & Security**:
  - **Prompt Injection Defense**: All retrieved code chunks are encapsulated in delimited untrusted data blocks. The system prompt commands the model to treat all comments, docstrings, and strings strictly as code data to analyze, never as instructions to follow.
  - **Context Budget Manager**: Sources are dynamically formatted and capped at ~12,000 characters to prevent token limit overflow.
  - **Citation Verification**: Every factual statement is required to cite its source inline (`[S1]`, `[S2]`). The pipeline extracts citation tags via regex and validates them strictly against the retrieved sources, filtering out any hallucinated source references.
  - **Graceful Insufficient-Evidence Handling**: If no relevant code chunks are retrieved or evidence is lacking, the pipeline outputs: `"I couldn't find enough relevant code in the repository to answer this question confidently."`
- **Flow**: User Question → Hybrid/Vector Retrieval → Context Assembly & Injection Safeguard → LLM Generation → Citation Verification → Grounded Answer with Source References

### Code Quality Analysis Engine & Repository Health Dashboard [Implemented]

- **Purpose**: Provide deterministic, evidence-based code quality diagnostics, cyclomatic complexity calculations, smell detection, and repository health grading.
- **Tech**: Python AST, Regular Expressions, Pydantic, Next.js / Tailwind CSS.
- **Components**:
  - **Metrics Computation (`metrics.py`)**:
    - Lines of code: total, physical code, comments, and blank lines.
    - Cyclomatic Complexity: McCabe cyclomatic complexity calculation on Python AST nodes (`If`, `For`, `While`, `ExceptHandler`, `With`, `Assert`, boolean operators `And`/`Or`) and JS/TS branching keywords.
    - Nesting Depth: Maximum indentation and AST statement block nesting.
    - Duplicate Code Detection: Rolling token hash windowing (minimum 6 matching normalized lines) across all indexed files.
  - **Quality Rules Engine (`rules.py`)**:
    - Evaluates 9 deterministic rules across 5 categories (`maintainability`, `complexity`, `documentation`, `reliability`, `duplication`):
      - `FUNCTION_TOO_LONG`: >50 lines (medium), >100 lines (high)
      - `FILE_TOO_LARGE`: >400 lines (medium), >800 lines (high)
      - `EXCESSIVE_NESTING`: >3 levels (medium), >4 levels (high)
      - `HIGH_CYCLOMATIC_COMPLEXITY`: >10 (high), >15 (critical)
      - `TOO_MANY_PARAMETERS`: >5 parameters (medium)
      - `MISSING_DOCSTRING`: Public functions/classes lacking docstrings (low)
      - `BROAD_EXCEPTION`: Catching broad `Exception`/`BaseException` or empty catch blocks (medium)
      - `POTENTIALLY_UNUSED_IMPORT`: Top-level imports not referenced in file body (low)
      - `DUPLICATE_CODE_BLOCK`: Repeated blocks of 6+ identical non-trivial lines (medium)
  - **Scoring & Health Grading (`scoring.py`)**:
    - Calculates 4 weighted sub-scores normalized per KLOC (1,000 lines of code):
      - Maintainability (40% weight)
      - Complexity (25% weight)
      - Documentation (20% weight)
      - Reliability (15% weight)
    - Computes composite 0–100 overall score and standard letter grades: A ($\ge 90$), B ($\ge 80$), C ($\ge 70$), D ($\ge 60$), F ($< 60$).
    - Computes individual file-level health scores for targeted refactoring.
  - **Interactive Health Dashboard (`RepositoryHealthDashboard.tsx`)**:
    - Visual health score card with animated progress bars for each dimension.
    - Metrics overview grid displaying LOC, comments, complexity, and duplicate counts.
    - Searchable and filterable findings list (by severity and category) with actionable suggestions.
    - File quality breakdown table with sorting and direct source line inspection.

### Security Analysis Engine & Risk Detection Dashboard [Implemented]

- **Purpose**: Statically inspect repository source code for common security vulnerabilities, hardcoded credentials, and injection risks without code execution.
- **Tech**: Python AST, Regular Expressions, Pydantic, Next.js / Tailwind CSS, optional OpenAI LLM explanation layer.
- **Components**:
  - **Modular SAST Engine (`backend/app/security_analysis/`)**:
    - **AST & Token Analysis**: Operates strictly on parsed ASTs (Python) and comment-stripped token lines (JS/TS). Ignores comments and docstrings to prevent avoidable false positives.
    - **Credential Detection & Redaction**: Detects sensitive assignments to credential-like variable names (`password`, `api_key`, `secret`, `access_token`, etc.) while filtering obvious dummy placeholders. Automatically redacts all discovered secrets (`[REDACTED]`) before generating findings or logs.
  - **Implemented Detection Rules & CWE Mappings**:
    - `PYTHON_HARDCODED_CREDENTIAL` / `JS_HARDCODED_CREDENTIAL` (`CWE-798`): Hardcoded tokens, API keys, and passwords.
    - `PYTHON_DANGEROUS_EVAL` / `PYTHON_DANGEROUS_EXEC` / `JS_DANGEROUS_EVAL` (`CWE-95`): Dynamic evaluation of untrusted code expressions.
    - `PYTHON_INSECURE_SUBPROCESS` (`CWE-78`): Subprocess execution with `shell=True` and dynamic arguments or `os.system()` invocations.
    - `PYTHON_SQL_INJECTION` (`CWE-89`): Dynamically concatenated or formatted SQL queries passed to database execution methods.
    - `PYTHON_UNSAFE_DESERIALIZATION` (`CWE-502`): Arbitrary object deserialization via `pickle.loads()`, `marshal`, or unsafe `yaml.load()`.
    - `PYTHON_WEAK_CRYPTO` / `JS_WEAK_CRYPTO` (`CWE-328` / `CWE-327`): Usage of collision-vulnerable hash algorithms (`MD5`, `SHA-1`) or broken ciphers.
    - `PYTHON_INSECURE_TLS` / `JS_INSECURE_TLS` (`CWE-295`): Disabled TLS/SSL certificate verification (`verify=False`, `ssl._create_unverified_context()`).
    - `PYTHON_BROAD_EXCEPTION_SECURITY` (`CWE-391`): Silencing errors via broad exceptions (`except Exception: pass`) inside authentication or cryptographic functions.
  - **Severity & Confidence Scoring**:
    - **Severity**: `Critical`, `High`, `Medium`, `Low`, `Informational`.
    - **Confidence**: `High`, `Medium`, `Low`.
  - **Privacy & Safety Safeguards**:
    - Purely static analysis; never executes repository scripts or installs dependencies.
    - Zero secret exposure: Suspected secret values are never included in API responses or sent to LLMs.
    - Context-budgeted, optional AI summary that treats repository content strictly as untrusted data.
  - **Interactive Security Dashboard (`SecurityAnalysisDashboard.tsx`)**:
    - Severity breakdown cards (Critical, High, Medium, Low, Informational).
    - Severity and category filtering pills, full-text search, and expandable remediation cards.
    - Prominent human-review guardrail clarifying that findings represent static review items.

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
