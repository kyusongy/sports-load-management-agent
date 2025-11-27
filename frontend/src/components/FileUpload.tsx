/**
 * File upload component with drag-and-drop support
 */

import { useState, useCallback, useRef } from 'react';
import { Upload, FileSpreadsheet, X } from 'lucide-react';
import clsx from 'clsx';

interface FileUploadProps {
  onUpload: (files: File[]) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function FileUpload({ onUpload, isLoading, disabled }: FileUploadProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (file) => file.name.endsWith('.csv')
    );

    if (droppedFiles.length > 0) {
      setFiles((prev) => [...prev, ...droppedFiles]);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles((prev) => [...prev, ...selectedFiles]);
  }, []);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleSubmit = useCallback(() => {
    if (files.length > 0) {
      onUpload(files);
    }
  }, [files, onUpload]);

  return (
    <div className="upload-container">
      <div
        className={clsx('drop-zone', {
          'drop-zone--dragging': isDragging,
          'drop-zone--disabled': disabled || isLoading,
        })}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && !isLoading && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          multiple
          onChange={handleFileSelect}
          className="file-input"
          disabled={disabled || isLoading}
        />
        <Upload className="upload-icon" size={48} />
        <p className="upload-text">
          Drag & drop CSV files here, or click to browse
        </p>
        <p className="upload-hint">
          Supports training load data with player names, dates, and RPE/Time or Load values
        </p>
      </div>

      {files.length > 0 && (
        <div className="file-list">
          <h4>Selected Files ({files.length})</h4>
          {files.map((file, index) => (
            <div key={`${file.name}-${index}`} className="file-item">
              <FileSpreadsheet size={20} />
              <span className="file-name">{file.name}</span>
              <span className="file-size">
                {(file.size / 1024).toFixed(1)} KB
              </span>
              <button
                className="remove-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(index);
                }}
                disabled={isLoading}
              >
                <X size={16} />
              </button>
            </div>
          ))}
        </div>
      )}

      <button
        className="submit-btn"
        onClick={handleSubmit}
        disabled={files.length === 0 || isLoading || disabled}
      >
        {isLoading ? (
          <>
            <span className="spinner" />
            Processing...
          </>
        ) : (
          <>
            <Upload size={20} />
            Analyze Training Load
          </>
        )}
      </button>
    </div>
  );
}

