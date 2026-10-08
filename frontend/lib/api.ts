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
