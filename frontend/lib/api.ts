/**
 * RepoPilot AI — API Client
 *
 * Centralized API utilities for communicating with the FastAPI backend.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Health check response from the backend */
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

/** Repository metadata */
export interface RepositoryInfo {
  name: string;
  owner: string;
  url: string;
  default_branch?: string | null;
}

/** Specific file information */
export interface FileInfo {
  path: string;
  size_bytes: number;
}

/** Repository statistics */
export interface RepositoryStatistics {
  total_files: number;
  total_directories: number;
  total_size_bytes: number;
  file_extensions: Record<string, number>;
  largest_files: FileInfo[];
}

/** Node in the file tree */
export interface FileTreeNode {
  name: string;
  type: "file" | "directory";
  path: string;
  size_bytes?: number | null;
  children?: FileTreeNode[] | null;
}

/** Full repository analysis response */
export interface RepositoryAnalyzeResponse {
  repository: RepositoryInfo;
  statistics: RepositoryStatistics;
  languages: Record<string, number>;
  file_tree: FileTreeNode[];
  status: string;
}

/** Code entity metadata (AST extraction) */
export interface CodeEntity {
  name: string;
  type: string; // 'class' | 'function' | 'method' | 'interface' | 'type_alias' | 'variable'
  file_path: string;
  start_line: number;
  end_line: number;
  signature?: string | null;
  docstring?: string | null;
  parent?: string | null;
  decorators?: string[];
  parameters?: string[];
  return_type?: string | null;
  visibility?: string | null;
}

/** Import statement */
export interface CodeImport {
  module: string;
  imported_names: string[];
  alias?: string | null;
  is_relative: boolean;
  line_number: number;
  source_file: string;
}

/** Analyzed source code file */
export interface CodeFile {
  path: string;
  language: string;
  size_bytes: number;
  lines: number;
  entities: CodeEntity[];
  imports: CodeImport[];
}

/** Dependency relationship */
export interface DependencyRelation {
  source_file: string;
  target_module: string;
  imported_symbols: string[];
  resolved_target_file?: string | null;
  is_internal: boolean;
}

/** Codebase quantitative summary */
export interface CodebaseSummary {
  files_analyzed: number;
  languages: Record<string, number>;
  classes: number;
  functions: number;
  methods: number;
  imports: number;
  interfaces: number;
  types: number;
  files_with_errors: number;
}

/** Hierarchical node in the codebase map */
export interface CodeStructureNode {
  name: string;
  type: string; // 'directory' | 'file' | 'class' | 'function' | 'interface' | 'method' | 'type_alias'
  path: string;
  line_info?: string | null;
  docstring?: string | null;
  children?: CodeStructureNode[] | null;
}

/** File parsing error */
export interface FileParseError {
  path: string;
  language: string;
  error_type: string;
  message: string;
}

/** Code intelligence analysis response */
export interface CodeAnalysisResponse {
  repository: RepositoryInfo;
  summary: CodebaseSummary;
  files: CodeFile[];
  entities: CodeEntity[];
  dependencies: DependencyRelation[];
  codebase_tree: CodeStructureNode[];
  errors: FileParseError[];
  status: string;
}

/**
 * Fetch the backend health status.
 */
export async function healthCheck(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Send a public GitHub repository URL to be cloned and analyzed.
 */
export async function analyzeRepository(
  repositoryUrl: string
): Promise<RepositoryAnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/repositories/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ repository_url: repositoryUrl }),
  });

  if (!response.ok) {
    let errorMessage = "Failed to analyze repository.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      errorMessage = `Server returned status ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

/**
 * Perform static code intelligence analysis on a public GitHub repository.
 */
export async function analyzeCodeIntelligence(
  repositoryUrl: string
): Promise<CodeAnalysisResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/repositories/analyze-code`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ repository_url: repositoryUrl }),
  });

  if (!response.ok) {
    let errorMessage = "Failed to analyze repository code.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      errorMessage = `Server returned status ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

/** An individual search result hit representing a matched code chunk */
export interface CodeSearchResultItem {
  chunk_id: string;
  file_path: string;
  entity_name: string;
  entity_type: string;
  language: string;
  start_line: number;
  end_line: number;
  signature?: string | null;
  docstring?: string | null;
  parent?: string | null;
  parameters?: string[];
  return_type?: string | null;
  code_snippet: string;
  context_header: string;
  tokens_estimate: number;
  score: number;
  match_reasons: string[];
  explanation: string;
}

/** Response from the code search API */
export interface CodeSearchResponse {
  repository: RepositoryInfo;
  query: string;
  total_chunks_indexed: number;
  total_results: number;
  results: CodeSearchResultItem[];
  status: string;
}

/**
 * Search repository code using lexical analysis, AST metadata, and keyword matching.
 */
export async function searchCode(
  repositoryUrl: string,
  query: string,
  limit: number = 10,
  entityTypes?: string[]
): Promise<CodeSearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/repositories/search-code`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      repository_url: repositoryUrl,
      query,
      limit,
      entity_types: entityTypes && entityTypes.length > 0 ? entityTypes : undefined,
    }),
  });

  if (!response.ok) {
    let errorMessage = "Failed to search repository code.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      errorMessage = `Server returned status ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

/** Response from repository vector indexing */
export interface RepositoryIndexResponse {
  repository: RepositoryInfo;
  status: string;
  files_processed: number;
  chunks_indexed: number;
  chunks_skipped: number;
  embedding_model: string;
  dimension: number;
  total_vectors_in_index: number;
  message: string;
}

/** Hit returned from semantic or hybrid retrieval */
export interface SemanticSearchResultItem {
  chunk_id: string;
  file_path: string;
  entity_name: string;
  entity_type: string;
  language: string;
  start_line: number;
  end_line: number;
  signature?: string | null;
  docstring?: string | null;
  parent?: string | null;
  code_snippet: string;
  context_header: string;
  tokens_estimate: number;
  score: number;
  search_mode: string;
  match_reasons: string[];
  explanation: string;
}

/** Full response from semantic or hybrid search */
export interface SemanticSearchResponse {
  repository: RepositoryInfo;
  query: string;
  search_mode: string;
  total_results: number;
  results: SemanticSearchResultItem[];
  status: string;
}

/**
 * Trigger vector indexing for a repository.
 */
export async function indexRepository(
  repositoryUrl: string,
  forceReindex: boolean = false
): Promise<RepositoryIndexResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/repositories/index`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      repository_url: repositoryUrl,
      force_reindex: forceReindex,
    }),
  });

  if (!response.ok) {
    let errorMessage = "Failed to index repository.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      errorMessage = `Server returned status ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

/**
 * Execute semantic, lexical, or hybrid code search.
 */
export async function semanticSearch(
  repositoryUrl: string,
  query: string,
  limit: number = 10,
  entityTypes?: string[],
  mode: string = "semantic"
): Promise<SemanticSearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/repositories/semantic-search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      repository_url: repositoryUrl,
      query,
      limit,
      entity_types: entityTypes && entityTypes.length > 0 ? entityTypes : undefined,
      mode,
    }),
  });

  if (!response.ok) {
    let errorMessage = "Failed to perform semantic search.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      errorMessage = `Server returned status ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

/** A verified source citation referencing a code chunk in the generated answer */
export interface CodeCitation {
  source_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
  entity_name: string;
  entity_type: string;
  score: number;
}

/** A code chunk retrieved from the repository and provided as context */
export interface RetrievedSource {
  source_id: string;
  chunk_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
  entity_name: string;
  entity_type: string;
  language: string;
  signature?: string | null;
  docstring?: string | null;
  code_content: string;
  score: number;
}

/** Request payload for asking natural language questions about a repository */
export interface RAGRequest {
  repository_url: string;
  question: string;
  top_k?: number;
}

/** Response payload containing grounded answer and verified code citations */
export interface RAGResponse {
  repository: RepositoryInfo;
  question: string;
  answer: string;
  citations: CodeCitation[];
  sources: RetrievedSource[];
  retrieved_chunks: number;
  status: string;
}

/**
 * Ask a natural language question about an indexed repository using grounded RAG.
 */
export async function askRepositoryQuestion(
  repositoryUrl: string,
  question: string,
  topK: number = 5
): Promise<RAGResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/repositories/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      repository_url: repositoryUrl,
      question: question.trim(),
      top_k: topK,
    }),
  });

  if (!response.ok) {
    let errorMessage = "Failed to process question.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      errorMessage = `Server returned status ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

/** Finding severity level */
export type FindingSeverity = "critical" | "error" | "warning" | "info";

/** Finding category */
export type FindingCategory =
  | "complexity"
  | "size"
  | "maintainability"
  | "documentation"
  | "error_handling"
  | "style"
  | "duplication";

/** Quality finding model */
export interface QualityFinding {
  id: string;
  rule_id: string;
  rule_name: string;
  category: FindingCategory;
  severity: FindingSeverity;
  file_path: string;
  start_line: number;
  end_line: number;
  entity_name?: string | null;
  entity_type?: string | null;
  message: string;
  suggestion: string;
  metric_value?: number | null;
  threshold?: number | null;
}

/** File quality summary */
export interface FileQualitySummary {
  file_path: string;
  language: string;
  total_lines: number;
  code_lines: number;
  comment_lines: number;
  blank_lines: number;
  functions_count: number;
  classes_count: number;
  average_complexity: number;
  max_complexity: number;
  findings_count: number;
  health_score: number;
  letter_grade: string;
}

/** Repository quality metrics */
export interface RepositoryQualityMetrics {
  total_lines: number;
  code_lines: number;
  comment_lines: number;
  blank_lines: number;
  total_files_analyzed: number;
  files_with_issues: number;
  total_functions: number;
  total_classes: number;
  average_function_length: number;
  average_cyclomatic_complexity: number;
  max_cyclomatic_complexity: number;
  docstring_coverage_percentage: number;
  duplicate_blocks_count: number;
}

/** Health scores breakdown */
export interface HealthScoreBreakdown {
  maintainability_score: number;
  complexity_score: number;
  documentation_score: number;
  reliability_score: number;
  overall_score: number;
  letter_grade: string;
}

/** Full code quality response */
export interface CodeQualityResponse {
  repository: RepositoryInfo;
  health: HealthScoreBreakdown;
  metrics: RepositoryQualityMetrics;
  findings: QualityFinding[];
  file_summaries: FileQualitySummary[];
  category_breakdown: Record<string, number>;
  severity_breakdown: Record<string, number>;
  parsing_errors: FileParseError[];
  status: string;
}

/**
 * Perform comprehensive code quality analysis and repository health scoring.
 */
export async function analyzeCodeQuality(
  repositoryUrl: string
): Promise<CodeQualityResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/repositories/quality`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      repository_url: repositoryUrl,
    }),
  });

  if (!response.ok) {
    let errorMessage = "Failed to analyze code quality.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      errorMessage = `Server returned status ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

/** Security finding interface */
export interface SecurityFinding {
  finding_id: string;
  rule_id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "informational";
  confidence: "high" | "medium" | "low";
  file_path: string;
  start_line: number;
  end_line: number;
  entity_name?: string | null;
  evidence_summary: string;
  remediation: string;
  cwe_id?: string | null;
  category: string;
}

/** Security findings summary by severity */
export interface SecuritySummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  informational: number;
  total: number;
}

/** Security analysis file coverage statistics */
export interface SecurityAnalysisStats {
  files_discovered: number;
  files_analyzed: number;
  files_skipped: number;
}

/** Full security analysis response */
export interface SecurityAnalysisResponse {
  repository: RepositoryInfo;
  analysis: SecurityAnalysisStats;
  summary: SecuritySummary;
  findings: SecurityFinding[];
  category_summary: Record<string, number>;
  status: string;
  llm_summary?: string | null;
}

/**
 * Perform static security analysis and risk detection on a repository.
 */
export async function analyzeSecurity(
  repositoryUrl: string,
  explainWithLLM: boolean = false
): Promise<SecurityAnalysisResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/repositories/analyze-security`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        repository_url: repositoryUrl,
        explain_with_llm: explainWithLLM,
      }),
    }
  );

  if (!response.ok) {
    let errorMessage = "Failed to analyze repository security.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      errorMessage = `Server returned status ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}



