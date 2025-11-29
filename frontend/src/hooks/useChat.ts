/**
 * Custom hook for managing chat state with the conversational agent
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import * as api from '../api/client';
import type { ChatMessage, ToolCall } from '../types/api';

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  generatedFiles: string[];
}

export function useChat(sessionId: string | null) {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    error: null,
    generatedFiles: [],
  });

  // Track all generated files across messages
  const allGeneratedFiles = useRef<Set<string>>(new Set());

  // Send message mutation
  const sendMutation = useMutation({
    mutationFn: ({ sessionId, message }: { sessionId: string; message: string }) =>
      api.sendChatMessage(sessionId, message),
    onMutate: ({ message }) => {
      // Add user message optimistically
      setState((prev) => ({
        ...prev,
        isLoading: true,
        error: null,
        messages: [
          ...prev.messages,
          { role: 'user', content: message },
        ],
      }));
    },
    onSuccess: (data) => {
      // Add generated files to tracking
      data.generated_files.forEach((file) => allGeneratedFiles.current.add(file));

      // Add assistant message
      setState((prev) => ({
        ...prev,
        isLoading: false,
        messages: [
          ...prev.messages,
          {
            role: 'assistant',
            content: data.response,
            tool_calls: data.tool_calls,
          },
        ],
        generatedFiles: Array.from(allGeneratedFiles.current),
        error: data.error || null,
      }));
    },
    onError: (error) => {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to send message',
      }));
    },
  });

  // Send a message
  const sendMessage = useCallback(
    async (message: string) => {
      if (!sessionId || !message.trim()) return;
      await sendMutation.mutateAsync({ sessionId, message: message.trim() });
    },
    [sessionId, sendMutation]
  );

  // Clear chat
  const clearChat = useCallback(async () => {
    if (!sessionId) return;
    try {
      await api.clearChatHistory(sessionId);
      setState({
        messages: [],
        isLoading: false,
        error: null,
        generatedFiles: [],
      });
      allGeneratedFiles.current.clear();
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to clear chat',
      }));
    }
  }, [sessionId]);

  // Reset state when session changes
  useEffect(() => {
    setState({
      messages: [],
      isLoading: false,
      error: null,
      generatedFiles: [],
    });
    allGeneratedFiles.current.clear();
  }, [sessionId]);

  return {
    ...state,
    sendMessage,
    clearChat,
  };
}

/**
 * Parse tool result string to extract useful data
 */
export function parseToolResult(result: string): Record<string, unknown> | null {
  try {
    // Try to parse as JSON (tool results are often stringified dicts)
    return JSON.parse(result.replace(/'/g, '"'));
  } catch {
    return null;
  }
}

/**
 * Get a human-readable description of a tool call
 */
export function getToolDescription(toolCall: ToolCall): string {
  const toolNames: Record<string, string> = {
    get_data_summary: 'Retrieved data summary',
    get_high_risk_players: 'Identified high-risk players',
    get_player_load_data: 'Retrieved player load data',
    list_all_players: 'Listed all players',
    plot_player_load_trend: 'Generated load trend chart',
    plot_top_players: 'Generated top players chart',
    plot_load_distribution: 'Generated load distribution chart',
    plot_team_timeline: 'Generated team timeline chart',
  };

  return toolNames[toolCall.tool] || `Used ${toolCall.tool}`;
}

