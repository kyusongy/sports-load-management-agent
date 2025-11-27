/**
 * Processing status indicator component
 */

import { CheckCircle, Circle, Loader, XCircle } from 'lucide-react';
import clsx from 'clsx';
import type { ProcessingStage } from '../types/api';

interface ProcessingStatusProps {
  stage: ProcessingStage;
  error?: string | null;
}

const stages = [
  { key: 'uploading', label: 'Uploading Files' },
  { key: 'data_ingest', label: 'Data Ingestion' },
  { key: 'data_process', label: 'Calculating Metrics' },
  { key: 'visualization', label: 'Generating Charts' },
  { key: 'report_generation', label: 'Creating Report' },
] as const;

function getStageIndex(stage: ProcessingStage): number {
  if (stage === 'idle') return -1;
  if (stage === 'uploading') return 0;
  if (stage === 'uploaded' || stage === 'processing') return 1;
  if (stage === 'data_ingest') return 1;
  if (stage === 'data_process') return 2;
  if (stage === 'visualization') return 3;
  if (stage === 'report_generation') return 4;
  if (stage === 'completed') return 5;
  if (stage === 'failed') return -2;
  return -1;
}

export function ProcessingStatus({ stage, error }: ProcessingStatusProps) {
  const currentIndex = getStageIndex(stage);
  const isFailed = stage === 'failed';
  const isComplete = stage === 'completed';

  if (stage === 'idle') return null;

  return (
    <div className="processing-status">
      <h3 className="status-title">
        {isComplete ? '✅ Analysis Complete' : isFailed ? '❌ Processing Failed' : '⏳ Processing...'}
      </h3>

      {error && (
        <div className="error-message">
          <XCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      <div className="stages-list">
        {stages.map((s, index) => {
          const isActive = currentIndex === index;
          const isDone = currentIndex > index || isComplete;
          const isPending = currentIndex < index && !isFailed;

          return (
            <div
              key={s.key}
              className={clsx('stage-item', {
                'stage-item--active': isActive,
                'stage-item--done': isDone,
                'stage-item--pending': isPending,
                'stage-item--failed': isFailed && isActive,
              })}
            >
              <div className="stage-icon">
                {isDone ? (
                  <CheckCircle size={24} className="icon-done" />
                ) : isActive ? (
                  isFailed ? (
                    <XCircle size={24} className="icon-failed" />
                  ) : (
                    <Loader size={24} className="icon-loading" />
                  )
                ) : (
                  <Circle size={24} className="icon-pending" />
                )}
              </div>
              <span className="stage-label">{s.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

