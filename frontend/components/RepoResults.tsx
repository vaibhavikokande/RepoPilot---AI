"use client";

import { useState } from "react";
import {
  analyzeCodeIntelligence,
  CodeAnalysisResponse,
  FileTreeNode,
  RepositoryAnalyzeResponse,
} from "@/lib/api";
import CodeIntelligenceView from "./CodeIntelligenceView";
import CodeSearchView from "./CodeSearchView";


interface RepoResultsProps {
  data: RepositoryAnalyzeResponse;
  onReset?: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function FileTreeItem({
  node,
  depth = 0,
}: {
  node: FileTreeNode;
  depth?: number;
}) {
  const [isOpen, setIsOpen] = useState(depth < 2);
  const isDirectory = node.type === "directory";

  return (
    <div className="select-none text-xs font-mono">
      <div
        onClick={() => isDirectory && setIsOpen(!isOpen)}
        className={`flex items-center gap-1.5 py-1 px-2 rounded hover:bg-surface/80 cursor-pointer transition-colors ${
          depth === 0 ? "font-medium text-foreground" : "text-muted hover:text-foreground"
        }`}
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
      >
        <span className="text-sm">
          {isDirectory ? (isOpen ? "📂" : "📁") : "📄"}
        </span>
        <span className={isDirectory ? "text-primary-hover font-semibold" : "text-foreground"}>
          {node.name}
        </span>
        {!isDirectory && node.size_bytes !== null && node.size_bytes !== undefined && (
          <span className="ml-auto text-[10px] text-muted/60">
            {formatBytes(node.size_bytes)}
          </span>
        )}
      </div>

      {isDirectory && isOpen && node.children && node.children.length > 0 && (
        <div className="border-l border-border/40 ml-4">
          {node.children.map((child) => (
            <FileTreeItem
              key={`${child.path}-${child.name}`}
              node={child}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function RepoResults({ data, onReset }: RepoResultsProps) {
  const { repository, statistics, languages, file_tree } = data;
  const totalLangFiles = Object.values(languages).reduce((a, b) => a + b, 0);

  const [codeData, setCodeData] = useState<CodeAnalysisResponse | null>(null);
  const [isCodeLoading, setIsCodeLoading] = useState(false);
  const [codeError, setCodeError] = useState<string | null>(null);

  const handleRunCodeIntelligence = async () => {
    setIsCodeLoading(true);
    setCodeError(null);
    try {
      const response = await analyzeCodeIntelligence(repository.url);
      setCodeData(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to analyze code intelligence.";
      setCodeError(msg);
    } finally {
      setIsCodeLoading(false);
    }
  };

  return (
    <div className="mt-8 bg-card border border-border rounded-xl p-6 sm:p-8 animate-fade-in shadow-xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-success/15 text-success border border-success/30">
              Analysis Complete
            </span>
            {repository.default_branch && (
              <span className="text-xs px-2 py-0.5 rounded bg-surface text-muted border border-border font-mono">
                branch: {repository.default_branch}
              </span>
            )}
          </div>
          <h3 className="text-2xl font-bold text-foreground">
            {repository.name}
          </h3>
          <a
            href={repository.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-primary-hover hover:underline inline-flex items-center gap-1 mt-0.5"
          >
            <span>{repository.owner}/{repository.name}</span>
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto">
          {!codeData && (
            <button
              onClick={handleRunCodeIntelligence}
              disabled={isCodeLoading}
              className="text-xs px-3.5 py-1.5 rounded-lg border border-primary/40 bg-primary/10 hover:bg-primary/20 text-primary-hover font-semibold transition-colors flex items-center gap-1.5 disabled:opacity-60 cursor-pointer"
            >
              {isCodeLoading ? (
                <>
                  <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Parsing AST...</span>
                </>
              ) : (
                <>
                  <span>🧠</span>
                  <span>Extract Code Intelligence</span>
                </>
              )}
            </button>
          )}

          {onReset && (
            <button
              onClick={onReset}
              className="text-xs px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-card-hover text-muted hover:text-foreground transition-colors cursor-pointer"
            >
              Analyze Another
            </button>
          )}
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 my-6">
        <div className="bg-surface/60 border border-border rounded-lg p-4">
          <p className="text-xs text-muted mb-1 font-medium">Total Files</p>
          <p className="text-2xl font-bold text-foreground">
            {statistics.total_files.toLocaleString()}
          </p>
        </div>
        <div className="bg-surface/60 border border-border rounded-lg p-4">
          <p className="text-xs text-muted mb-1 font-medium">Directories</p>
          <p className="text-2xl font-bold text-foreground">
            {statistics.total_directories.toLocaleString()}
          </p>
        </div>
        <div className="bg-surface/60 border border-border rounded-lg p-4 col-span-2 sm:col-span-1">
          <p className="text-xs text-muted mb-1 font-medium">Scanned Size</p>
          <p className="text-2xl font-bold text-foreground">
            {formatBytes(statistics.total_size_bytes)}
          </p>
        </div>
      </div>

      {/* Languages & File Tree Side-by-Side or Stacked */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Languages section */}
        <div className="bg-surface/40 border border-border rounded-lg p-5">
          <h4 className="text-sm font-semibold text-foreground mb-4 flex items-center justify-between">
            <span>Detected Languages</span>
            <span className="text-xs font-normal text-muted">
              {Object.keys(languages).length} languages
            </span>
          </h4>

          {Object.keys(languages).length === 0 ? (
            <p className="text-xs text-muted">No recognized programming languages detected.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(languages).map(([lang, count]) => {
                const percentage =
                  totalLangFiles > 0
                    ? Math.round((count / totalLangFiles) * 100)
                    : 0;
                return (
                  <div key={lang} className="text-xs">
                    <div className="flex justify-between mb-1">
                      <span className="font-medium text-foreground">{lang}</span>
                      <span className="text-muted">
                        {count} {count === 1 ? "file" : "files"} ({percentage}%)
                      </span>
                    </div>
                    <div className="w-full bg-border rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-primary h-1.5 rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(percentage, 3)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Structure / File Tree section */}
        <div className="bg-surface/40 border border-border rounded-lg p-5 flex flex-col">
          <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center justify-between">
            <span>Repository Structure</span>
            <span className="text-[11px] font-normal text-muted">
              Click folders to expand/collapse
            </span>
          </h4>

          <div className="max-h-80 overflow-y-auto pr-1 bg-card/60 rounded border border-border/60 p-2">
            <div className="text-xs font-mono font-semibold text-primary mb-1 px-2 py-0.5">
              📦 {repository.name}/
            </div>
            {file_tree && file_tree.length > 0 ? (
              file_tree.map((node) => (
                <FileTreeItem
                  key={`${node.path}-${node.name}`}
                  node={node}
                  depth={0}
                />
              ))
            ) : (
              <p className="text-xs text-muted p-2">Empty repository.</p>
            )}
          </div>
        </div>
      </div>

      {/* Code Search Section */}
      <CodeSearchView repositoryUrl={repository.url} />

      {/* Code Intelligence Error if any */}
      {codeError && (
        <div className="mt-6 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-200 text-xs flex items-start gap-3">
          <span className="text-sm">⚠️</span>
          <div>
            <p className="font-semibold text-red-300">Code Intelligence Error</p>
            <p className="mt-0.5">{codeError}</p>
          </div>
        </div>
      )}

      {/* Code Intelligence View */}
      {codeData && <CodeIntelligenceView data={codeData} />}
    </div>
  );
}
