/**
 * Sports Load Management Agent - Main Application
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FileUpload } from './components/FileUpload';
import { ProcessingStatus } from './components/ProcessingStatus';
import { Chat } from './components/Chat';
import { useProcessing } from './hooks/useProcessing';
import { getDownloadUrl } from './api/client';
import { FileSpreadsheet, RefreshCw } from 'lucide-react';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30000,
    },
  },
});

function Dashboard() {
  const {
    stage,
    sessionId,
    error,
    results,
    uploadAndProcess,
    reset,
    isLoading,
  } = useProcessing();

  const showUpload = stage === 'idle' || stage === 'failed';
  const showProcessing = !showUpload && stage !== 'completed';
  const showResults = stage === 'completed';

  return (
    <div className="dashboard">
      <header className="header">
        <div className="logo">
          <span className="logo-icon">🏃</span>
          <div className="logo-text">
            <h1>Sports Load Manager</h1>
            <p>Training Load Analysis & ACWR Monitoring</p>
          </div>
        </div>
        {showResults && (
          <button className="header-reset-btn" onClick={reset}>
            <RefreshCw size={16} />
            New Analysis
          </button>
        )}
      </header>

      <main className="main-content">
        {showUpload && (
          <div className="upload-section">
            <div className="section-header">
              <h2>Upload Training Data</h2>
              <p>
                Upload your athlete training data to calculate ACWR metrics
                and chat with AI for insights and visualizations.
              </p>
            </div>
            <FileUpload
              onUpload={uploadAndProcess}
              isLoading={isLoading}
              disabled={isLoading}
            />
            {stage === 'failed' && error && (
              <button className="retry-btn" onClick={reset}>
                Try Again
              </button>
            )}
          </div>
        )}

        {showProcessing && (
          <ProcessingStatus stage={stage} error={error} />
        )}

        {showResults && sessionId && (
          <div className="analysis-layout">
            {/* Downloads Panel */}
            <div className="downloads-panel">
              <h3>📥 Processed Data</h3>
              <p className="downloads-description">
                Download your processed training data with ACWR metrics calculated.
              </p>
              <div className="download-buttons-vertical">
                {results?.processed_csv_path && (
                  <a
                    href={getDownloadUrl(results.processed_csv_path)}
                    className="download-btn"
                    download
                  >
                    <FileSpreadsheet size={18} />
                    Download CSV
                  </a>
                )}
                {results?.processed_excel_path && (
                  <a
                    href={getDownloadUrl(results.processed_excel_path)}
                    className="download-btn download-btn--excel"
                    download
                  >
                    <FileSpreadsheet size={18} />
                    Download Excel
                  </a>
                )}
              </div>
            </div>

            {/* Chat Panel */}
            <div className="chat-panel">
              <Chat sessionId={sessionId} />
            </div>
          </div>
        )}
      </main>

      <footer className="footer">
        <p>
          ACWR (Acute:Chronic Workload Ratio) helps monitor athlete training load.
          <br />
          <span className="legend">
            <span className="legend-item legend-high">High (&gt;1.5) = Injury Risk</span>
            <span className="legend-item legend-medium">Medium (0.67-1.5) = Optimal</span>
            <span className="legend-item legend-low">Low (&lt;0.67) = Undertraining</span>
          </span>
        </p>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  );
}
