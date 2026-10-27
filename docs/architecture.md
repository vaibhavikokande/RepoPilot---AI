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
  - Interactive Unit Test Generator UI with AST entity pickers, test descriptions, syntax verification badges, copy, and `.py` download
  - Interactive Test Execution & Coverage Dashboard with review-then-run action, test outcome metrics, statement coverage bar, uncovered lines indicators, and runner console logs
  - Interactive Code Review Dashboard with multi-focus analysis, severity & category filtering, verified code evidence, and read-only improvement suggestions
  - Interactive AI Debugging Workspace with stack trace parsing, error explanations, ranked causes, code context viewer, and suggested fixes
  - Interactive AI Documentation Generator Workspace with 7 archetypes, target entity selection, audience & detail controls, formatted preview & raw Markdown views, and client-side copy and `.md` export
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
  - `POST /api/v1/repositories/generate-tests` — AI-powered unit test generation with AST context and syntax validation
  - `POST /api/v1/repositories/run-tests` — Safe test execution inside container sandbox with coverage analysis
  - `GET /api/v1/test-runs/{run_id}` — Test run outcome, summary, and coverage retrieval
  - `GET /api/v1/repositories/sandbox-status` — Container sandbox availability and security diagnostics
  - `POST /api/v1/repositories/review-code` — AI-powered code review and actionable recommendations
  - `POST /api/v1/repositories/debug` — AI debugging assistant analyzing errors and stack traces
  - `POST /api/v1/repositories/generate-docs` — Multi-archetype technical documentation generation
  - `GET /api/v1/documentation/{document_id}` — Generated technical documentation retrieval
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

### Unit Test Generation Engine & Dashboard [Implemented]

- **Purpose**: Autonomously synthesize grounded `pytest` unit test suites for functions and methods in ingested Python repositories without hallucinating imports, classes, or signatures.
- **Tech**: Python Standard Library AST, Next.js / TypeScript / Tailwind CSS, Multi-Provider LLM (`OpenAI` with `MockLLMGenerator` deterministic fallback).
- **Architecture & Pipeline**:
  - **AST Context Builder (`context_builder.py`)**:
    - Discovers target functions or class methods using Python's standard library `ast.parse`.
    - Extracts precise source lines, signatures, and docstrings.
    - Inspects enclosing class definition (e.g. `__init__`, attributes) for methods.
    - Collects module-level imports and relative imports for accurate test mocking and namespace resolution.
    - Enforces safety: validates file paths against workspace root to prevent path traversal; limits context payload to 8,000 characters.
  - **Prompt Engineering & Grounding (`prompt_builder.py`)**:
    - Wraps retrieved source code inside strict `<UNTRUSTED_CODE_DATA>` boundaries to neutralize prompt injection attacks.
    - Directs the LLM to write tests using `pytest` and `unittest.mock` covering happy paths, boundary conditions, edge cases, and error handling.
    - Demands strict structured JSON output containing `test_framework`, `test_code`, `test_cases`, and `suggested_file_name`.
  - **Deterministic Fallback Generator**:
    - When running offline or when LLM API keys are unavailable, generates high-quality syntactic `pytest` test templates directly derived from the target entity's AST signature, parameters, and class context.
  - **AST Syntax & Structure Validator (`validator.py`)**:
    - Statically validates generated test code using `ast.parse(test_code)`.
    - Discovers and counts valid `test_*` functions and class methods.
    - Returns structured warnings if test cases are missing, while marking `execution_status: "not_run"`.
    - **Zero Execution Safety Rule**: Generated test code is never executed directly on the host machine.
  - **Interactive Next.js Dashboard (`TestGenerationView.tsx`)**:
    - Automatically populates dropdown with Python files and callable entities discovered during AST code intelligence.
    - Manual fallback inputs allowing custom file and entity specification.
    - Real-time syntax validity status badge, test function count pill, and safety disclaimers.
    - Structured test case breakdown displaying test name and purpose.
    - Monospace test suite code viewer with one-click "Copy Code" and `.py` file download.

### Safe Test Execution & Coverage Engine [Implemented]

- **Purpose**: Run approved pytest test suites in an isolated, unprivileged container sandbox, capture passed/failed/skipped test outcomes, enforce strict resource and timeout limits, and compute code statement coverage.
- **Tech**: Docker container isolation, `pytest`, `coverage.py`, FastAPI, Next.js / TypeScript / Tailwind CSS.
- **Architecture & Security Components**:
  - **Container Isolation & Sandboxing (`sandbox.py`)**:
    - **Non-root user execution**: `--user 1000:1000` prevents privilege escalation.
    - **Zero network access**: `--network none` disables all inbound and outbound network sockets, preventing data exfiltration, command-and-control communication, or SSRF attacks.
    - **Linux capability stripping**: `--cap-drop=ALL` removes all kernel capabilities from the running container.
    - **No-new-privileges**: `--security-opt=no-new-privileges` prevents processes from gaining additional privileges via `setuid` binaries.
    - **Hardware resource limits**: Enforces `--memory=512m`, `--cpus=1.0`, and `--pids-limit=64` to prevent resource exhaustion, fork bombs, and memory leaks.
    - **Zero secrets inheritance**: Host environment variables (e.g. `OPENAI_API_KEY`, AWS credentials) are completely excluded from the execution environment.
    - **Automatic container lifecycle**: Ephemeral container created with `--rm` and destroyed immediately after run completion.
  - **Disposable Workspace Staging (`runner.py`)**:
    - Never executes tests in the original cloned repository workspace.
    - Copies source files to an isolated, temporary execution workspace.
    - Rejects absolute paths and path traversal (`..`) attempts.
    - Guarantees immediate cleanup of the disposable workspace in a `finally` block.
  - **Fixed Executable Construction**:
    - Never executes shell strings or uses `shell=True`.
    - Arguments are strictly constructed as fixed parameter vectors: `["pytest", test_file, "-v", "--tb=short", "--cov=..."]`.
  - **Coverage Analysis (`coverage.py`)**:
    - Automatically parses structured `coverage.json` generated by `pytest-cov`.
    - Measures total statements, covered statements, missing statements, and coverage percentage.
    - Identifies uncovered line numbers per analyzed source file.
    - If dependencies prevent coverage generation, reports coverage as unavailable rather than fabricating metrics.
  - **Server Diagnostic & Safety Fallback**:
    - Detects whether Docker runtime is available on host (`get_sandbox_status()`).
    - If Docker runtime is unavailable, real execution of untrusted code is blocked with a clear diagnostic explanation.
    - Provides a controlled mock sandbox implementation for offline testing, CI environments, and local verification without host compromise.
  - **Interactive Dashboard (`TestGenerationView.tsx`)**:
    - Real-time container sandbox status indicator.
    - Explicit user approval button with duplicate submission prevention.
    - Metric counters for Total, Passed, Failed, Skipped, and Error counts.
    - Statement coverage progress bar with per-file missing lines breakdown.
    - Monospace runner console output viewer with path and secret sanitization.

### AI-Powered Code Review Engine & Dashboard [Implemented]

- **Purpose**: Conduct automated, evidence-grounded code reviews of repository source files or specific entities (functions, methods, classes), categorizing issues across correctness, security, performance, maintainability, readability, and testing, while providing actionable, read-only improvement suggestions.
- **Tech**: Python Standard Library AST, Next.js / TypeScript / Tailwind CSS, Multi-Provider LLM (`OpenAI` with `MockLLMGenerator` deterministic fallback), Static Quality & Security Analyzers.
- **Architecture & Pipeline**:
  - **Evidence Collector (`collector.py`)**:
    - Safely resolves source file paths against repository boundaries, strictly rejecting path traversal (`..`) and absolute paths.
    - Targets specific functions or classes if specified, calculating exact line bounds.
    - Extracts numbered source code lines (` 15 | def foo():`) bounded by safety caps (600 lines, 24,000 characters).
    - Runs deterministic baseline checks from the Code Quality and Security Analysis engines, labeling findings with `source: "static_analysis"`.
  - **Prompt Hardening & Injection Defenses (`prompt_builder.py`)**:
    - Wraps untrusted source code and developer instructions inside strict `<UNTRUSTED_CODE_DATA>` XML-like delimiters.
    - Instructs the reviewer to never execute or treat the code content as instructions.
    - Enforces strict structured JSON schema output containing category, severity, confidence, start/end lines, problem description, verbatim code evidence, actionable recommendation, and optional suggested code changes.
  - **Grounding Validator & Secret Redaction (`grounding.py`)**:
    - Enforces line number validation: clamps out-of-range line indices and verifies line existence against actual source line counts.
    - Recovers line numbers by substring-searching verbatim evidence snippets in actual source lines if the LLM reported approximate bounds.
    - Flags findings where code evidence cannot be confirmed as `is_verified: False`.
    - Automatically sanitizes API tokens, AWS keys, GitHub credentials, and password strings (`[REDACTED_API_KEY]`, `[REDACTED_GITHUB_TOKEN]`).
  - **Review Orchestrator (`reviewer.py`)**:
    - Coordinates context collection, LLM synthesis, JSON parsing, grounding validation, and deduplication.
    - Merges deterministic static findings with AI-generated semantic findings into a unified, sorted findings list.
    - Computes aggregated summary metrics (critical, high, medium, low, info counts, category breakdown, static vs. AI counts).
    - Features a deterministic `MockLLMGenerator` fallback to guarantee reliable, offline execution without API keys.
  - **Read-Only Code Suggestions**:
    - Generates concrete, side-by-side suggested code fixes without modifying target files or executing patches on repository code.
  - **Interactive Next.js Review Dashboard (`CodeReviewView.tsx`)**:
    - File and entity pickers populated from AST code intelligence, with manual path override options.
    - Focus scope selector (`all`, `correctness`, `security`, `performance`, `maintainability`, `readability`, `testing`).
    - Optional developer guidance input.
    - Summary metrics bar with severity counts, static vs. AI breakdown, execution duration, and model metadata.
    - Multi-dimensional filtering: severity buttons, category pills, source toggles, and live search.
    - Expandable finding cards featuring verified line badges, code evidence viewers, actionable recommendations, and one-click copy suggested improvements.

### AI Debugging Assistant Engine & Dashboard [Implemented]

- **Purpose**: Analyze error messages and stack traces using repository source code, identify innermost failure frames, locate relevant code context, formulate ranked root cause hypotheses, and provide practical debugging steps and read-only fix recommendations.
- **Tech**: Python Regular Expressions, AST Parsing, Next.js / TypeScript / Tailwind CSS, Multi-Provider LLM (`OpenAI` with `MockLLMGenerator` deterministic fallback).
- **Architecture & Pipeline**:
  - **Error Parser (`error_parser.py`)**:
    - Robust parsing across Python tracebacks, JavaScript/Node.js stack traces, and raw log messages.
    - Extracts exception type, message, stack frames, line numbers, function names, and file paths.
    - Classifies stack frames as application code vs. standard library/vendor dependencies to prioritize relevant lines.
    - Imposes a strict 15,000-character safety limit and treats all error content as untrusted data.
  - **Context Locator (`context_locator.py`)**:
    - Resolves raw stack trace paths against repository boundaries, handling relative paths, container prefixes, and Windows separators.
    - Strictly prevents path traversal attacks (`..` and directory escaping).
    - Extracts context windows (15 lines padding or enclosing function/class via AST parsing).
    - Explicitly reports missing or external source files not found in the repository.
  - **Prompt Hardening & Injection Defenses (`prompt_builder.py`)**:
    - Encloses untrusted error inputs and code snippets within `<UNTRUSTED_ERROR_INPUT>`, `<UNTRUSTED_USER_CONTEXT>`, and `<UNTRUSTED_CODE_DATA>` XML-like blocks.
    - Enforces strict structured JSON schema output containing error summary, root cause, ranked causes, debugging steps, and optional suggested fix.
  - **Grounding Validator & Secret Redaction (`validator.py`)**:
    - Calibrates confidence: automatically downgrades confidence if repository source code for the failure line could not be retrieved.
    - Enforces mandatory confidence disclaimer note.
    - Filters related files against known repository files.
    - Automatically redacts API tokens, AWS keys, GitHub credentials, and passwords (`[REDACTED_API_KEY]`, `[REDACTED_GITHUB_TOKEN]`).
  - **Debug Orchestrator (`assistant.py`)**:
    - Coordinates parsing, context location, LLM synthesis, JSON parsing, validation, and assembly.
    - Features a deterministic fallback engine generating high-quality diagnoses derived from innermost frames and source lines for reliable offline operation.
  - **Read-Only Code Fix Recommendations**:
    - Proposes clean, minimal fix snippets without automatically applying patches, executing scripts, or modifying repository code.
  - **Interactive Next.js Debugging Dashboard (`DebugAssistantView.tsx`)**:
    - Stack trace textarea with character counter.
    - Optional reproduction steps, expected behavior, file focus, and language dropdowns.
    - Error summary card with error type pill, confidence badge, and disclaimer note.
    - Prominent primary root cause card.
    - Ranked possible causes with likelihood badges and evidence references.
    - Repository code evidence viewer with line numbers and relevance notes.
    - Actionable step-by-step debugging checklist.
    - Read-only suggested code fix preview with one-click copy button.
    - Collapsible stack frames inspector detailing application vs. vendor frames.

### AI Technical Documentation Generator & Workspace [Implemented]

- **Purpose**: Autonomously generate accurate, repository-grounded technical documentation across 7 archetypes (`readme`, `project_overview`, `architecture` with valid Mermaid diagrams, `module`, `api_reference`, `function_reference`, `setup_guide`), reflecting actual repository source code, AST entities, discovered API routes, package manifests, and configuration files.
- **Tech**: Python Regular Expressions, AST Parsing, Next.js / TypeScript / Tailwind CSS, Multi-Provider LLM (`OpenAI` with `MockLLMGenerator` deterministic fallback).
- **Architecture & Pipeline**:
  - **Context Collector (`context_collector.py`)**:
    - Discovers manifests (`requirements.txt`, `pyproject.toml`, `package.json`, `setup.py`, `Pipfile`) to determine real dependencies.
    - Scans existing documentation files (`README.md`, `docs/`) to respect established project naming and layout conventions.
    - Generates directory tree representations with automatic filtering of build/dependency noise.
    - Discovers API routes via static analysis across Python decorators (`@router.get`, `@app.post`, etc.) and JavaScript/TypeScript Express routing.
    - Extracts Python AST symbols (classes, functions, methods, parameter signatures, and docstrings).
    - Detects environment variables from `.env.example` and configuration files.
    - Identifies configured test runners (`pytest`, `jest`, `unittest`).
    - Enforces strict path traversal defenses, rejecting any relative sequences (`..`) or paths that escape repository boundaries.
  - **Prompt Hardening & Injection Defenses (`prompt_builder.py`)**:
    - Wraps all untrusted codebase context inside `<UNTRUSTED_REPO_DATA>` XML-like blocks.
    - Instructs LLMs to treat all repository data strictly as text to be documented and ignore embedded instructions.
    - Enforces Mermaid diagram constraints: requires valid `graph TD` flowcharts referencing verified modules and components.
    - Forbids inventing nonexistent dependencies, routes, environment variables, or CLI commands.
  - **Grounding Validator & Secret Redaction (`validator.py`)**:
    - Scans generated markdown for sensitive tokens, AWS keys, GitHub credentials, and passwords, replacing them with `[REDACTED_...]` placeholders.
    - Parses Markdown H1 and H2 headers into structured, queryable `DocSection` objects for navigation.
    - Extracts concise executive summaries.
    - Tracks and tags unverified claims with `[Requires Confirmation]`.
  - **Generator Orchestrator & Deterministic Fallback (`generator.py`)**:
    - Coordinates context gathering, prompt preparation, LLM synthesis, validation, and storage.
    - Features a full deterministic fallback engine that synthesizes complete, structured documentation for all 7 archetypes from collected context even when external LLM services are offline or unconfigured.
    - Generates valid Mermaid architecture diagrams dynamically mapping discovered repository directories and API endpoints.
  - **Document Store (`store.py`)**:
    - Thread-safe in-memory store for saving and retrieving generated documents via unique IDs (`doc_...`).
  - **Read-Only Safety & Client-Side Export**:
    - Generated previews are completely read-only until the user explicitly chooses to copy or download.
    - Client-side `.md` file download via Blob URL guarantees that original repository files remain completely untouched.
  - **Interactive Next.js Documentation Workspace (`DocumentationGeneratorView.tsx`)**:
    - Document archetype selector cards (`README`, `Overview`, `Architecture`, `Module`, `API Reference`, `Function Reference`, `Setup Guide`).
    - Target file and symbol pickers populated from AST analysis.
    - Target audience selector (`developer`, `beginner`, `maintainer`) and detail level selector (`concise`, `standard`, `comprehensive`).
    - Custom developer instructions input.
    - Summary status banner with analyzed file count, discovered route/symbol counts, and generation method.
    - Formatted Markdown preview vs. raw source code toggle.
    - One-click "Copy Markdown" and "Download .md" buttons.
    - Collapsible drawer listing all analyzed repository source files.

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
- **Zero Raw Host Code Execution**: Repository code is strictly scanned as static text during ingestion; test execution is strictly isolated in a container sandbox.
- **Container Sandbox Isolation**: Untrusted tests execute inside an isolated Docker container with non-root UID 1000, zero network access (`--network none`), all capabilities dropped (`--cap-drop=ALL`), no-new-privileges, and memory/CPU/PID limits.
- **Zero Secrets Inheritance**: Host credentials, API keys, and environment variables are never passed to the runner container.
- **Path Traversal Prevention**: Target directories and test files are resolved and verified against the designated workspace boundary (`..` and absolute paths strictly rejected).
- **Disposable Workspaces**: Repositories are cloned to isolated directories, and tests execute in temporary copies, leaving original repository files completely untouched. All temporary workspaces are automatically cleaned up immediately.
- **Git Protection**: Cloned files, dependencies, and environment files are excluded via `.gitignore`.

### Planned Safeguards
- API key authentication and rate limiting for backend services
- Multi-language container runners (Node.js, Go, Rust)
- Enterprise repository access tokens and secrets vault
- File size and clone depth quotas in production deployment
