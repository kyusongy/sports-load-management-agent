/**
 * API client for the Sports Load Management Agent backend
 */

import type {
  UploadResponse,
  ProcessResponse,
  StatusResponse,
  ResultsResponse,
  TokenStats,
  ChatRequest,
  ChatResponse,
  ChatHistoryResponse,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class APIError extends Error {
  status: number;
  
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'APIError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new APIError(response.status, text || response.statusText);
  }
  return response.json();
}

/**
 * Upload CSV files for processing
 */
export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<UploadResponse>(response);
}

/**
 * Start processing the uploaded files
 */
export async function processFiles(sessionId: string): Promise<ProcessResponse> {
  const response = await fetch(`${API_BASE_URL}/api/process/${sessionId}`, {
    method: 'POST',
  });

  return handleResponse<ProcessResponse>(response);
}

/**
 * Get the current processing status
 */
export async function getStatus(sessionId: string): Promise<StatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/status/${sessionId}`);
  return handleResponse<StatusResponse>(response);
}

/**
 * Get the processing results
 */
export async function getResults(sessionId: string): Promise<ResultsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/results/${sessionId}`);
  return handleResponse<ResultsResponse>(response);
}

/**
 * Get global token statistics
 */
export async function getTokenStats(): Promise<TokenStats> {
  const response = await fetch(`${API_BASE_URL}/api/token-stats`);
  return handleResponse<TokenStats>(response);
}

/**
 * Delete a session
 */
export async function deleteSession(sessionId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/session/${sessionId}`, {
    method: 'DELETE',
  });
  return handleResponse<{ message: string }>(response);
}

/**
 * Get the download URL for a file
 */
export function getDownloadUrl(path: string): string {
  // If path already starts with /api/, use it directly
  if (path.startsWith('/api/')) {
    return `${API_BASE_URL}${path}`;
  }
  return `${API_BASE_URL}${path}`;
}

// ============================================================================
// Chat API Functions
// ============================================================================

/**
 * Send a chat message and get a response
 */
export async function sendChatMessage(
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat/${sessionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message } as ChatRequest),
  });

  return handleResponse<ChatResponse>(response);
}

/**
 * Get chat history for a session
 */
export async function getChatHistory(sessionId: string): Promise<ChatHistoryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat/${sessionId}/history`);
  return handleResponse<ChatHistoryResponse>(response);
}

/**
 * Clear chat history for a session
 */
export async function clearChatHistory(sessionId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/chat/${sessionId}/history`, {
    method: 'DELETE',
  });
  return handleResponse<{ message: string }>(response);
}

export { APIError };

