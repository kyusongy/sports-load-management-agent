/**
 * API type definitions for the Sports Load Management Agent
 */

export interface UploadResponse {
  session_id: string;
  uploaded_files: string[];
  message: string;
}

export interface ProcessResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface StatusResponse {
  session_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'uploaded';
  current_stage?: string;
  error_message?: string;
}

export interface TokenUsage {
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface ResultsResponse {
  session_id: string;
  status: string;
  report_markdown?: string;
  visualization_files: string[];
  processed_csv_path?: string;
  processed_excel_path?: string;
  token_usage: TokenUsage;
  error_message?: string;
}

export interface TokenStats {
  tracker_name: string;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  call_count: number;
  created_at: string;
  last_updated_at: string;
  by_model: Record<string, {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    call_count: number;
  }>;
}

export type ProcessingStage = 
  | 'idle'
  | 'uploading'
  | 'uploaded'
  | 'processing'
  | 'data_ingest'
  | 'data_process'
  | 'visualization'
  | 'report_generation'
  | 'completed'
  | 'failed';

// Chat types
export interface ChatRequest {
  message: string;
}

export interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  result: string;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  tool_calls: ToolCall[];
  generated_files: string[];
  error?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  tool_calls?: ToolCall[];
}

export interface ChatHistoryResponse {
  session_id: string;
  history: ChatMessage[];
}

