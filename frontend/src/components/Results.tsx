/**
 * Results display component showing report, visualizations, and downloads
 */

import { Download, FileSpreadsheet, RefreshCw } from 'lucide-react';
import type { ResultsResponse } from '../types/api';
import { getDownloadUrl } from '../api/client';

interface ResultsProps {
  results: ResultsResponse;
  onReset: () => void;
}

export function Results({ results, onReset }: ResultsProps) {
  const {
    report_markdown,
    visualization_files,
    processed_csv_path,
    processed_excel_path,
  } = results;

  return (
    <div className="results-container">
      <div className="results-header">
        <h2>📊 Analysis Results</h2>
        <button className="reset-btn" onClick={onReset}>
          <RefreshCw size={18} />
          New Analysis
        </button>
      </div>

      {/* Downloads Section */}
      <section className="results-section downloads-section">
        <h3>📥 Download Processed Data</h3>
        <div className="download-buttons">
          {processed_csv_path && (
            <a
              href={getDownloadUrl(processed_csv_path)}
              className="download-btn"
              download
            >
              <FileSpreadsheet size={20} />
              Download CSV
            </a>
          )}
          {processed_excel_path && (
            <a
              href={getDownloadUrl(processed_excel_path)}
              className="download-btn download-btn--excel"
              download
            >
              <FileSpreadsheet size={20} />
              Download Excel (Color-coded)
            </a>
          )}
        </div>
      </section>

      {/* Visualizations Section */}
      {visualization_files.length > 0 && (
        <section className="results-section visualizations-section">
          <h3>📈 Visualizations</h3>
          <div className="visualizations-grid">
            {visualization_files
              .filter((file) => {
                // Filter out empty/invalid entries
                if (!file || file.length === 0) return false;
                const filename = file.split('/').pop() || '';
                // Only include known chart types
                return (
                  filename.includes('top_players_load') ||
                  filename.includes('top_players_training') ||
                  filename.includes('load_distribution') ||
                  filename.includes('team_timeline') ||
                  filename.includes('player_heatmap')
                );
              })
              .map((file) => {
                const url = getDownloadUrl(file);
                const filename = file.split('/').pop() || '';
                
                // Extract chart type from filename - match the backend plot titles
                let title = 'Chart';
                if (filename.includes('top_players_load')) {
                  title = 'Top 5 Players by ACWR';
                } else if (filename.includes('top_players_training')) {
                  title = 'Top 5 Players by Training Load (sRPE)';
                } else if (filename.includes('load_distribution')) {
                  title = 'Load Quality Distribution';
                } else if (filename.includes('team_timeline')) {
                  title = 'Team Load Timeline';
                } else if (filename.includes('player_heatmap')) {
                  title = 'Player Load Heatmap (Weekly)';
                }

                return (
                  <div key={file} className="visualization-card">
                    <h4>{title}</h4>
                    <img src={url} alt={title} className="visualization-image" />
                    <a href={url} download className="viz-download-btn">
                      <Download size={16} />
                      Download
                    </a>
                  </div>
                );
              })}
          </div>
        </section>
      )}

      {/* Report Section */}
      {report_markdown && (
        <section className="results-section report-section">
          <h3>📝 Analysis Report</h3>
          <div
            className="report-content"
            dangerouslySetInnerHTML={{
              __html: markdownToHtml(report_markdown),
            }}
          />
        </section>
      )}

      {/* Token Usage - Hidden for cleaner UI */}
    </div>
  );
}

/**
 * Simple markdown to HTML converter
 */
function markdownToHtml(markdown: string): string {
  return markdown
    // Headers
    .replace(/^### (.*$)/gm, '<h4>$1</h4>')
    .replace(/^## (.*$)/gm, '<h3>$1</h3>')
    .replace(/^# (.*$)/gm, '<h2>$1</h2>')
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Lists
    .replace(/^\- (.*$)/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    // Tables (basic)
    .replace(/\|(.+)\|/g, (match) => {
      const cells = match.split('|').filter(Boolean);
      const row = cells.map((cell) => `<td>${cell.trim()}</td>`).join('');
      return `<tr>${row}</tr>`;
    })
    // Line breaks
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
    // Horizontal rules
    .replace(/^---$/gm, '<hr>')
    // Wrap in paragraph
    .replace(/^(.+)$/gm, (match) => {
      if (match.startsWith('<')) return match;
      return `<p>${match}</p>`;
    });
}

