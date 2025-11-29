/**
 * Chat component for conversational interaction with the sports load agent
 */

import { useState, useRef, useEffect } from 'react';
import {
  Send,
  Loader2,
  Bot,
  User,
  Wrench,
  Image,
  Download,
  Trash2,
  Sparkles,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { useChat, getToolDescription } from '../hooks/useChat';
import { getDownloadUrl } from '../api/client';
import type { ChatMessage, ToolCall } from '../types/api';

interface ChatProps {
  sessionId: string;
}

export function Chat({ sessionId }: ChatProps) {
  const { messages, isLoading, error, generatedFiles, sendMessage, clearChat } =
    useChat(sessionId);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    const message = input;
    setInput('');
    await sendMessage(message);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
    inputRef.current?.focus();
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-header-title">
          <Sparkles size={20} className="chat-header-icon" />
          <h3>AI Analysis Assistant</h3>
        </div>
        <button className="chat-clear-btn" onClick={clearChat} title="Clear chat">
          <Trash2 size={16} />
        </button>
      </div>

      {/* Messages Area */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <WelcomeMessage onSuggestionClick={handleSuggestionClick} />
        ) : (
          <>
            {messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))}
            {isLoading && <LoadingIndicator />}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Generated Visualizations */}
      {generatedFiles.length > 0 && (
        <GeneratedVisualizations files={generatedFiles} />
      )}

      {/* Error Display */}
      {error && (
        <div className="chat-error">
          <span>{error}</span>
        </div>
      )}

      {/* Input Form */}
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="text"
          className="chat-input"
          placeholder="Ask about your training data..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="chat-send-btn"
          disabled={isLoading || !input.trim()}
        >
          {isLoading ? <Loader2 size={20} className="spinning" /> : <Send size={20} />}
        </button>
      </form>
    </div>
  );
}

/**
 * Welcome message with suggestions when chat is empty
 */
function WelcomeMessage({
  onSuggestionClick,
}: {
  onSuggestionClick: (suggestion: string) => void;
}) {
  const suggestions = [
    'Show me a summary of the training data',
    'Who has the highest injury risk?',
    'Plot the load trend for the top player',
    'Show me the load distribution chart',
    'List all players in the dataset',
  ];

  return (
    <div className="chat-welcome">
      <div className="chat-welcome-icon">
        <Bot size={32} />
      </div>
      <h4>How can I help you analyze your training data?</h4>
      <p>
        Ask me anything about your athletes' training load, injury risk, or request
        visualizations.
      </p>
      <div className="chat-suggestions">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            className="chat-suggestion"
            onClick={() => onSuggestionClick(suggestion)}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Individual message bubble
 */
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  // Extract generated image URLs from tool call results
  const generatedImages = extractImagesFromToolCalls(message.tool_calls);

  return (
    <div className={`chat-message ${isUser ? 'chat-message--user' : 'chat-message--assistant'}`}>
      <div className="chat-message-avatar">
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>
      <div className="chat-message-content">
        <div className="chat-message-text">
          {formatMessageContent(message.content)}
        </div>
        {/* Display generated visualizations inline */}
        {generatedImages.length > 0 && (
          <InlineVisualizations images={generatedImages} />
        )}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <ToolCallsList toolCalls={message.tool_calls} />
        )}
      </div>
    </div>
  );
}

/**
 * Extract image URLs from tool call results
 */
function extractImagesFromToolCalls(toolCalls?: ToolCall[]): string[] {
  if (!toolCalls) return [];

  const images: string[] = [];

  for (const toolCall of toolCalls) {
    // Tool results are stringified dicts - look for download_url
    const result = toolCall.result;
    if (!result) continue;

    // Try to extract download_url from the result string
    const downloadUrlMatch = result.match(/'download_url':\s*'([^']+)'/);
    if (downloadUrlMatch && downloadUrlMatch[1]) {
      images.push(downloadUrlMatch[1]);
    }

    // Also try JSON format
    const jsonDownloadMatch = result.match(/"download_url":\s*"([^"]+)"/);
    if (jsonDownloadMatch && jsonDownloadMatch[1]) {
      images.push(jsonDownloadMatch[1]);
    }
  }

  return images;
}

/**
 * Display visualizations inline in the message
 */
function InlineVisualizations({ images }: { images: string[] }) {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  return (
    <>
      <div className="chat-inline-images">
        {images.map((imageUrl, index) => {
          const fullUrl = getDownloadUrl(imageUrl);
          return (
            <div key={index} className="chat-inline-image-container">
              <img
                src={fullUrl}
                alt={`Generated visualization ${index + 1}`}
                className="chat-inline-image"
                onClick={() => setSelectedImage(fullUrl)}
              />
              <div className="chat-inline-image-actions">
                <button
                  className="chat-inline-image-expand"
                  onClick={() => setSelectedImage(fullUrl)}
                  title="Expand"
                >
                  <Image size={14} />
                </button>
                <a
                  href={fullUrl}
                  download
                  className="chat-inline-image-download"
                  title="Download"
                >
                  <Download size={14} />
                </a>
              </div>
            </div>
          );
        })}
      </div>

      {/* Lightbox modal for expanded view */}
      {selectedImage && (
        <div className="chat-lightbox" onClick={() => setSelectedImage(null)}>
          <div className="chat-lightbox-content" onClick={(e) => e.stopPropagation()}>
            <img src={selectedImage} alt="Expanded visualization" />
            <div className="chat-lightbox-actions">
              <a href={selectedImage} download className="chat-lightbox-download">
                <Download size={18} />
                Download
              </a>
              <button
                className="chat-lightbox-close"
                onClick={() => setSelectedImage(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/**
 * Format message content with basic markdown support
 */
function formatMessageContent(content: string): React.ReactNode {
  // Split by code blocks first
  const parts = content.split(/(```[\s\S]*?```)/g);

  return parts.map((part, index) => {
    if (part.startsWith('```')) {
      // Code block
      const code = part.replace(/```\w*\n?/g, '').replace(/```$/g, '');
      return (
        <pre key={index} className="chat-code-block">
          <code>{code}</code>
        </pre>
      );
    }

    // Regular text with inline formatting
    return (
      <span key={index}>
        {part.split('\n').map((line, lineIndex) => (
          <span key={lineIndex}>
            {formatInlineMarkdown(line)}
            {lineIndex < part.split('\n').length - 1 && <br />}
          </span>
        ))}
      </span>
    );
  });
}

/**
 * Format inline markdown (bold, italic, inline code)
 */
function formatInlineMarkdown(text: string): React.ReactNode {
  // Very simple markdown parsing
  const formatted = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>');

  return <span dangerouslySetInnerHTML={{ __html: formatted }} />;
}

/**
 * List of tool calls made during response
 */
function ToolCallsList({ toolCalls }: { toolCalls: ToolCall[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="chat-tool-calls">
      <button
        className="chat-tool-calls-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        <Wrench size={14} />
        <span>{toolCalls.length} tool{toolCalls.length > 1 ? 's' : ''} used</span>
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>
      {expanded && (
        <div className="chat-tool-calls-list">
          {toolCalls.map((toolCall, index) => (
            <div key={index} className="chat-tool-call">
              <span className="chat-tool-call-name">
                {getToolDescription(toolCall)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Loading indicator while waiting for response
 */
function LoadingIndicator() {
  return (
    <div className="chat-message chat-message--assistant">
      <div className="chat-message-avatar">
        <Bot size={18} />
      </div>
      <div className="chat-message-content">
        <div className="chat-loading">
          <Loader2 size={16} className="spinning" />
          <span>Analyzing...</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Display generated visualizations
 */
function GeneratedVisualizations({ files }: { files: string[] }) {
  const [expanded, setExpanded] = useState(true);

  // Filter to only show image files
  const imageFiles = files.filter(
    (f) => f.endsWith('.png') || f.endsWith('.jpg') || f.endsWith('.jpeg')
  );

  if (imageFiles.length === 0) return null;

  return (
    <div className="chat-visualizations">
      <button
        className="chat-visualizations-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        <Image size={16} />
        <span>{imageFiles.length} visualization{imageFiles.length > 1 ? 's' : ''} generated</span>
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      {expanded && (
        <div className="chat-visualizations-grid">
          {imageFiles.map((file, index) => {
            const url = getDownloadUrl(file);
            const filename = file.split('/').pop() || 'chart';

            return (
              <div key={index} className="chat-visualization-item">
                <img src={url} alt={filename} />
                <a href={url} download className="chat-viz-download">
                  <Download size={14} />
                </a>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

