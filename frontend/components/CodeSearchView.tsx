"use client";

import { useState } from "react";
import {
  CodeSearchResultItem,
  searchCode,
} from "@/lib/api";

interface CodeSearchViewProps {
  repositoryUrl: string;
}

export default function CodeSearchView({ repositoryUrl }: CodeSearchViewProps) {
  const [query, setQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<CodeSearchResultItem[] | null>(null);
  const [totalIndexed, setTotalIndexed] = useState<number | null>(null);
  const [searchedQuery, setSearchedQuery] = useState<string>("");
  const [expandedSnippets, setExpandedSnippets] = useState<Record<string, boolean>>({});

  const sampleQueries = [
    "Where is user authentication handled?",
    "database connection",
    "create user",
    "repository scanner",
    "parse AST",
  ];

  const handleSearch = async (overrideQuery?: string, overrideType?: string) => {
    const q = (overrideQuery ?? query).trim();
    if (!q) return;

    const t = overrideType ?? selectedType;
    const entityTypes = t === "all" ? undefined : [t];

    setIsLoading(true);
    setError(null);

    try {
      const res = await searchCode(repositoryUrl, q, 10, entityTypes);
      setResults(res.results);
      setTotalIndexed(res.total_chunks_indexed);
      setSearchedQuery(res.query);
      // Auto-expand the top result snippet for immediate preview
      if (res.results.length > 0) {
        setExpandedSnippets({ [res.results[0].chunk_id]: true });
      } else {
        setExpandedSnippets({});
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Search failed.";
      setError(msg);
      setResults(null);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleSnippet = (chunkId: string) => {
    setExpandedSnippets((prev) => ({
      ...prev,
      [chunkId]: !prev[chunkId],
    }));
  };

  const getTypeBadgeClass = (type: string) => {
    switch (type) {
      case "class":
        return "bg-amber-500/15 text-amber-300 border-amber-500/30";
      case "function":
        return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
      case "method":
        return "bg-sky-500/15 text-sky-300 border-sky-500/30";
      case "interface":
        return "bg-purple-500/15 text-purple-300 border-purple-500/30";
      default:
        return "bg-surface text-muted border-border";
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "class":
        return "🏛️";
      case "function":
        return "⚡";
      case "method":
        return "🔹";
      case "interface":
        return "🧩";
      case "file_module":
        return "📄";
      default:
        return "🔍";
    }
  };

  return (
    <div className="bg-surface/30 border border-border rounded-xl p-5 sm:p-6 mt-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg">🔍</span>
            <h4 className="text-base font-bold text-foreground">
              Intelligent Code Search
            </h4>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary-hover border border-primary/20 font-semibold uppercase tracking-wider">
              Lexical & Metadata
            </span>
          </div>
          <p className="text-xs text-muted mt-1">
            Search functions, classes, methods, and modules using natural query terms or code identifiers
          </p>
        </div>
      </div>

      {/* Search Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSearch();
        }}
        className="mb-3"
      >
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <svg
              className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Where is user authentication handled? or UserService"
              className="w-full bg-card border border-border rounded-lg py-2.5 pl-10 pr-4 text-xs font-mono text-foreground placeholder:text-muted/60 focus:outline-none focus:border-primary/50 transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="px-5 py-2.5 rounded-lg text-xs font-semibold text-white bg-primary hover:bg-primary-hover disabled:opacity-50 transition-colors flex items-center justify-center gap-2 cursor-pointer shrink-0"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Searching...</span>
              </>
            ) : (
              <span>Search Code</span>
            )}
          </button>
        </div>
      </form>

      {/* Filter Chips & Quick Examples */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-1 pb-3 text-xs border-b border-border/50">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] text-muted mr-1">Filter type:</span>
          {[
            { id: "all", label: "All" },
            { id: "function", label: "Functions" },
            { id: "class", label: "Classes" },
            { id: "method", label: "Methods" },
            { id: "interface", label: "Interfaces" },
          ].map((typeOption) => (
            <button
              key={typeOption.id}
              type="button"
              onClick={() => {
                setSelectedType(typeOption.id);
                if (results !== null && query.trim()) {
                  handleSearch(query, typeOption.id);
                }
              }}
              className={`px-2.5 py-1 rounded text-[11px] font-medium border transition-colors cursor-pointer ${
                selectedType === typeOption.id
                  ? "bg-primary/15 border-primary/40 text-primary-hover"
                  : "bg-card border-border text-muted hover:text-foreground"
              }`}
            >
              {typeOption.label}
            </button>
          ))}
        </div>

        {/* Quick Suggestion Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] text-muted">Try:</span>
          {sampleQueries.map((sample) => (
            <button
              key={sample}
              type="button"
              onClick={() => {
                setQuery(sample);
                handleSearch(sample, selectedType);
              }}
              className="text-[11px] px-2 py-0.5 rounded bg-surface border border-border/60 text-muted hover:text-primary-hover transition-colors cursor-pointer"
            >
              &quot;{sample}&quot;
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mt-4 p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-red-200 text-xs">
          <strong>Search Error:</strong> {error}
        </div>
      )}

      {/* Results Header */}
      {results !== null && (
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs text-muted mb-3">
            <span>
              Query: <strong className="text-foreground">&quot;{searchedQuery}&quot;</strong> • Found{" "}
              <strong className="text-primary-hover">{results.length}</strong> match
              {results.length === 1 ? "" : "es"}
              {totalIndexed !== null && (
                <span className="text-muted/70"> (out of {totalIndexed} indexed chunks)</span>
              )}
            </span>
          </div>

          {/* Results List */}
          {results.length === 0 ? (
            <div className="p-6 text-center bg-card/60 rounded-lg border border-border/60">
              <p className="text-sm text-foreground font-semibold">No matches found</p>
              <p className="text-xs text-muted mt-1">
                Try broader keywords, identifier names, or removing specific type filters.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((hit) => {
                const isExpanded = Boolean(expandedSnippets[hit.chunk_id]);
                return (
                  <div
                    key={hit.chunk_id}
                    className="bg-card border border-border rounded-xl p-4 transition-all hover:border-primary/40 shadow-sm"
                  >
                    {/* Header Row */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border/50">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-base">{getTypeIcon(hit.entity_type)}</span>
                        <span className="text-sm font-bold text-foreground font-mono">
                          {hit.entity_name}
                        </span>
                        {hit.parent && (
                          <span className="text-xs text-muted font-mono">
                            in <strong className="text-foreground">{hit.parent}</strong>
                          </span>
                        )}
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded border ${getTypeBadgeClass(
                            hit.entity_type
                          )}`}
                        >
                          {hit.entity_type}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-mono font-semibold">
                          Score: {hit.score}
                        </span>
                        <span className="text-[10px] text-muted/60 font-mono">
                          ~{hit.tokens_estimate} tokens
                        </span>
                      </div>
                    </div>

                    {/* File Path & Line Numbers */}
                    <div className="mt-2.5 flex items-center justify-between text-xs font-mono">
                      <div className="text-primary-hover flex items-center gap-1.5 truncate">
                        <span>📄</span>
                        <span className="truncate">{hit.file_path}</span>
                        <span className="text-muted/80 shrink-0">
                          :L{hit.start_line}-L{hit.end_line}
                        </span>
                      </div>
                      <span className="text-[11px] text-muted shrink-0 capitalize">
                        {hit.language}
                      </span>
                    </div>

                    {/* Human Explanation Box */}
                    <div className="mt-2.5 p-2.5 rounded-lg bg-surface/70 border border-border/60 text-xs">
                      <p className="text-foreground leading-relaxed">
                        <strong className="text-primary-hover font-semibold">Match Insight: </strong>
                        {hit.explanation}
                      </p>
                    </div>

                    {/* Match Reasons Chips */}
                    {hit.match_reasons && hit.match_reasons.length > 0 && (
                      <div className="mt-2.5 flex flex-wrap gap-1.5 items-center">
                        <span className="text-[10px] text-muted font-medium mr-1">Criteria:</span>
                        {hit.match_reasons.map((reason, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] px-2 py-0.5 rounded bg-surface border border-border/70 text-muted font-mono"
                          >
                            ✓ {reason}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Signature if available */}
                    {hit.signature && (
                      <div className="mt-2.5 text-xs font-mono bg-background/60 p-2 rounded border border-border/40 text-muted/90 truncate">
                        <span className="text-muted/50 select-none mr-2">sig:</span>
                        <code>{hit.signature}</code>
                      </div>
                    )}

                    {/* Code Snippet Toggle */}
                    <div className="mt-3 pt-2.5 border-t border-border/40 flex items-center justify-between">
                      <button
                        type="button"
                        onClick={() => toggleSnippet(hit.chunk_id)}
                        className="text-xs text-primary-hover hover:underline flex items-center gap-1 font-semibold cursor-pointer"
                      >
                        <span>{isExpanded ? "▾ Hide Code Snippet" : "▸ View Code Snippet"}</span>
                        <span className="text-[10px] text-muted font-normal">
                          ({hit.end_line - hit.start_line + 1} lines)
                        </span>
                      </button>
                    </div>

                    {/* Expandable Snippet Area */}
                    {isExpanded && (
                      <div className="mt-2 relative rounded-lg bg-background border border-border/80 overflow-hidden font-mono text-xs">
                        <div className="flex items-center justify-between px-3 py-1.5 bg-surface/80 border-b border-border/60 text-[10px] text-muted">
                          <span>{hit.context_header}</span>
                          <button
                            type="button"
                            onClick={() => navigator.clipboard?.writeText(hit.code_snippet)}
                            className="hover:text-foreground text-[10px] cursor-pointer"
                          >
                            Copy Code
                          </button>
                        </div>
                        <pre className="p-3 overflow-x-auto text-[11px] text-foreground leading-relaxed">
                          <code>{hit.code_snippet}</code>
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
