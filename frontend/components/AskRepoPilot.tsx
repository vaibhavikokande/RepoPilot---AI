"use client";

import { useState } from "react";
import {
  askRepositoryQuestion,
  CodeCitation,
  RAGResponse,
  RetrievedSource,
} from "@/lib/api";

interface AskRepoPilotProps {
  repositoryUrl: string;
}

const EXAMPLE_QUESTIONS = [
  "How does authentication work in this project?",
  "Where is error and exception handling configured?",
  "Explain the main entry point and request lifecycle.",
  "Which functions interact with the database or storage?",
  "How is configuration loaded from environment variables?",
];

export default function AskRepoPilot({ repositoryUrl }: AskRepoPilotProps) {
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<RAGResponse | null>(null);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [copiedAnswer, setCopiedAnswer] = useState(false);
  const [copiedChunkId, setCopiedChunkId] = useState<string | null>(null);

  const handleAsk = async (queryToAsk?: string) => {
    const q = (queryToAsk || question).trim();
    if (!q) return;

    if (queryToAsk) {
      setQuestion(queryToAsk);
    }

    setIsLoading(true);
    setError(null);
    setResponse(null);
    setSelectedSourceId(null);

    try {
      const res = await askRepositoryQuestion(repositoryUrl, q, topK);
      setResponse(res);
      if (res.sources && res.sources.length > 0) {
        setSelectedSourceId(res.sources[0].source_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to answer question.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyAnswer = () => {
    if (!response?.answer) return;
    navigator.clipboard.writeText(response.answer);
    setCopiedAnswer(true);
    setTimeout(() => setCopiedAnswer(false), 2000);
  };

  const handleCopyCode = (code: string, chunkId: string) => {
    navigator.clipboard.writeText(code);
    setCopiedChunkId(chunkId);
    setTimeout(() => setCopiedChunkId(null), 2000);
  };

  // Helper to render answer text with clickable citation chips
  const renderFormattedAnswer = (answerText: string) => {
    const parts = answerText.split(/(\[S\d+\])/g);
    return (
      <div className="text-sm leading-relaxed text-foreground whitespace-pre-wrap font-sans space-y-2">
        {parts.map((part, idx) => {
          const match = part.match(/\[(S\d+)\]/);
          if (match) {
            const sourceId = match[1];
            const isSelected = selectedSourceId === sourceId;
            return (
              <button
                key={idx}
                type="button"
                onClick={() => setSelectedSourceId(sourceId)}
                className={`inline-flex items-center px-1.5 py-0.5 mx-0.5 text-xs font-mono font-semibold rounded transition-all cursor-pointer ${
                  isSelected
                    ? "bg-primary text-primary-foreground shadow-sm ring-1 ring-primary-hover"
                    : "bg-primary/15 text-primary hover:bg-primary/25 border border-primary/30"
                }`}
                title={`Click to view source ${sourceId}`}
              >
                [{sourceId}]
              </button>
            );
          }
          return <span key={idx}>{part}</span>;
        })}
      </div>
    );
  };

  const activeSource = response?.sources?.find((s) => s.source_id === selectedSourceId);

  return (
    <div className="mt-8 bg-card border border-border rounded-xl p-6 sm:p-8 shadow-xl transition-all">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">✨</span>
            <h3 className="text-lg font-bold text-foreground">
              Ask RepoPilot
            </h3>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/30">
              RAG Code Understanding
            </span>
          </div>
          <p className="text-xs text-muted mt-1">
            Ask natural language questions about this codebase. Answers are strictly grounded in retrieved code with verified source citations.
          </p>
        </div>

        {/* Top-K Selector */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted">Evidence Chunks:</span>
          <select
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="bg-surface border border-border rounded px-2 py-1 text-foreground text-xs focus:outline-none focus:border-primary"
            disabled={isLoading}
          >
            <option value={3}>Top 3</option>
            <option value={5}>Top 5</option>
            <option value={8}>Top 8</option>
          </select>
        </div>
      </div>

      {/* Example Prompt Chips */}
      <div className="mt-4">
        <span className="text-[11px] font-semibold text-muted uppercase tracking-wider block mb-2">
          Suggested Questions:
        </span>
        <div className="flex flex-wrap gap-1.5">
          {EXAMPLE_QUESTIONS.map((eq, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleAsk(eq)}
              disabled={isLoading}
              className="text-xs bg-surface/80 hover:bg-surface border border-border/70 hover:border-primary/50 text-foreground/80 hover:text-foreground rounded-lg px-3 py-1.5 transition-all text-left disabled:opacity-50"
            >
              💬 {eq}
            </button>
          ))}
        </div>
      </div>

      {/* Question Input Form */}
      <div className="mt-4">
        <div className="relative">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAsk();
              }
            }}
            placeholder="Ask anything about the codebase (e.g. Where is database connectivity configured?)..."
            rows={2}
            disabled={isLoading}
            className="w-full bg-surface border border-border rounded-xl p-3.5 pr-28 text-sm text-foreground placeholder:text-muted/60 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all resize-none"
          />
          <button
            type="button"
            onClick={() => handleAsk()}
            disabled={isLoading || !question.trim()}
            className="absolute right-2.5 bottom-3.5 px-4 py-2 bg-primary hover:bg-primary-hover text-primary-foreground font-medium text-xs rounded-lg shadow-md transition-all disabled:opacity-50 flex items-center gap-1.5 cursor-pointer"
          >
            {isLoading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                <span>Thinking...</span>
              </>
            ) : (
              <>
                <span>Ask AI</span>
                <span>🚀</span>
              </>
            )}
          </button>
        </div>
        <div className="flex justify-between items-center mt-1 px-1 text-[11px] text-muted">
          <span>Press Enter to ask, Shift+Enter for new line</span>
          <span>Prompt injection protected</span>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mt-4 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-200 text-xs flex items-start gap-3">
          <span className="text-base">⚠️</span>
          <div className="flex-1">
            <p className="font-semibold text-red-300">Question Processing Error</p>
            <p className="mt-0.5">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-200 text-xs font-semibold px-2 py-0.5 rounded hover:bg-red-500/20"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Answer and Citations View */}
      {response && (
        <div className="mt-6 space-y-6 animate-fade-in">
          {/* Grounded Answer Card */}
          <div className="bg-surface/50 border border-border rounded-xl p-5 shadow-inner">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 mb-3 border-b border-border/60">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-foreground">
                  RepoPilot AI Answer
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-medium">
                  Grounded in {response.retrieved_chunks} sources
                </span>
                {response.citations.length > 0 && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-400 border border-blue-500/30 font-medium">
                    {response.citations.length} verified citations
                  </span>
                )}
              </div>

              <button
                type="button"
                onClick={handleCopyAnswer}
                className="text-xs text-muted hover:text-foreground flex items-center gap-1 px-2.5 py-1 rounded bg-card/60 hover:bg-card border border-border transition-colors self-start sm:self-auto"
              >
                {copiedAnswer ? "✓ Copied" : "📋 Copy Answer"}
              </button>
            </div>

            {/* Answer Content */}
            <div className="pt-1">
              {renderFormattedAnswer(response.answer)}
            </div>
          </div>

          {/* Citations & Source Evidence Inspector */}
          {response.sources && response.sources.length > 0 && (
            <div className="bg-surface/30 border border-border rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-2">
                  <span>Verified Source Evidence</span>
                  <span className="text-[10px] lowercase font-normal bg-card px-2 py-0.5 rounded border border-border">
                    click citation to view code
                  </span>
                </h4>
                <span className="text-[11px] text-muted">
                  {response.sources.length} sources retrieved
                </span>
              </div>

              {/* Source Tabs */}
              <div className="flex flex-wrap gap-2 mb-4">
                {response.sources.map((s) => {
                  const isSelected = selectedSourceId === s.source_id;
                  return (
                    <button
                      key={s.source_id}
                      type="button"
                      onClick={() => setSelectedSourceId(s.source_id)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium border transition-all cursor-pointer ${
                        isSelected
                          ? "bg-primary/20 border-primary text-primary shadow-sm ring-1 ring-primary/40"
                          : "bg-surface border-border hover:border-primary/40 text-muted hover:text-foreground"
                      }`}
                    >
                      <span className="font-bold">[{s.source_id}]</span>
                      <span className="truncate max-w-[140px] text-[11px]">
                        {s.entity_name || s.file_path.split("/").pop()}
                      </span>
                      <span className="text-[10px] opacity-70">
                        {Math.round(s.score * 100)}%
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Active Source Details */}
              {activeSource && (
                <div className="bg-card border border-border rounded-lg p-4 font-mono text-xs">
                  {/* Meta Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-2 mb-3 border-b border-border/60">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-primary">
                        [{activeSource.source_id}]
                      </span>
                      <span className="text-foreground font-semibold">
                        {activeSource.file_path}
                      </span>
                      <span className="text-muted text-[11px]">
                        Lines {activeSource.start_line}-{activeSource.end_line}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20">
                        {activeSource.entity_type}: {activeSource.entity_name}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-surface text-muted border border-border">
                        {activeSource.language}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopyCode(activeSource.code_content, activeSource.chunk_id)}
                        className="text-[11px] text-muted hover:text-foreground px-2 py-0.5 rounded hover:bg-surface border border-border/50"
                      >
                        {copiedChunkId === activeSource.chunk_id ? "✓ Copied" : "Copy"}
                      </button>
                    </div>
                  </div>

                  {/* Docstring if present */}
                  {activeSource.docstring && (
                    <div className="mb-3 p-2 bg-surface/60 rounded border border-border/40 text-[11px] text-muted italic">
                      💡 {activeSource.docstring}
                    </div>
                  )}

                  {/* Code Snippet */}
                  <div className="max-h-72 overflow-y-auto bg-black/40 rounded p-3 text-xs leading-relaxed border border-border/40 text-foreground/90">
                    <pre className="whitespace-pre overflow-x-auto">
                      <code>{activeSource.code_content}</code>
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
