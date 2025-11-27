/**
 * Custom hook for managing the file processing workflow
 */

import { useState, useCallback } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import * as api from '../api/client';
import type { ProcessingStage, ResultsResponse } from '../types/api';

interface ProcessingState {
  stage: ProcessingStage;
  sessionId: string | null;
  error: string | null;
  results: ResultsResponse | null;
}

export function useProcessing() {
  const [state, setState] = useState<ProcessingState>({
    stage: 'idle',
    sessionId: null,
    error: null,
    results: null,
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: api.uploadFiles,
    onMutate: () => {
      setState((prev) => ({ ...prev, stage: 'uploading', error: null }));
    },
    onSuccess: (data) => {
      setState((prev) => ({
        ...prev,
        stage: 'uploaded',
        sessionId: data.session_id,
      }));
    },
    onError: (error) => {
      setState((prev) => ({
        ...prev,
        stage: 'failed',
        error: error instanceof Error ? error.message : 'Upload failed',
      }));
    },
  });

  // Process mutation
  const processMutation = useMutation({
    mutationFn: api.processFiles,
    onMutate: () => {
      setState((prev) => ({ ...prev, stage: 'processing' }));
    },
    onSuccess: (data) => {
      if (data.status === 'completed') {
        setState((prev) => ({ ...prev, stage: 'completed' }));
      } else if (data.status === 'failed') {
        setState((prev) => ({
          ...prev,
          stage: 'failed',
          error: data.message,
        }));
      }
    },
    onError: (error) => {
      setState((prev) => ({
        ...prev,
        stage: 'failed',
        error: error instanceof Error ? error.message : 'Processing failed',
      }));
    },
  });

  // Results query - only enabled when processing is complete
  const resultsQuery = useQuery({
    queryKey: ['results', state.sessionId],
    queryFn: () => api.getResults(state.sessionId!),
    enabled: state.stage === 'completed' && !!state.sessionId,
    staleTime: Infinity,
  });

  // Update results when query succeeds
  if (resultsQuery.data && !state.results) {
    setState((prev) => ({ ...prev, results: resultsQuery.data }));
  }

  // Upload files and start processing
  const uploadAndProcess = useCallback(async (files: File[]) => {
    try {
      const uploadResult = await uploadMutation.mutateAsync(files);
      await processMutation.mutateAsync(uploadResult.session_id);
    } catch {
      // Errors are handled in mutation callbacks
    }
  }, [uploadMutation, processMutation]);

  // Reset to initial state
  const reset = useCallback(() => {
    setState({
      stage: 'idle',
      sessionId: null,
      error: null,
      results: null,
    });
  }, []);

  return {
    ...state,
    uploadAndProcess,
    reset,
    isLoading: uploadMutation.isPending || processMutation.isPending,
    results: state.results || resultsQuery.data || null,
  };
}

