/**
 * Sports Load Management Agent - Main Application
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FileUpload } from './components/FileUpload';
import { ProcessingStatus } from './components/ProcessingStatus';
import { Results } from './components/Results';
import { useProcessing } from './hooks/useProcessing';
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
    error,
    results,
    uploadAndProcess,
    reset,
    isLoading,
  } = useProcessing();

  const showUpload = stage === 'idle' || stage === 'failed';
  const showProcessing = !showUpload && stage !== 'completed';
  const showResults = stage === 'completed' && results;

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
      </header>

      <main className="main-content">
        {showUpload && (
          <div className="upload-section">
            <div className="section-header">
              <h2>Upload Training Data</h2>
              <p>
                Upload your athlete training data to calculate ACWR metrics,
                generate visualizations, and receive AI-powered insights.
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

        {showResults && results && (
          <Results results={results} onReset={reset} />
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
