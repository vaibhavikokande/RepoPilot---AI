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

