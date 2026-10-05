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
