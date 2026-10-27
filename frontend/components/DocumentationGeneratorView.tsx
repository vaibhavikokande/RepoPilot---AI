"use client";

import { useState } from "react";
import {
  CodeFile,
  DocAudience,
  DocDetailLevel,
  DocGenerateResponse,
  DocType,
  generateDocumentation,
} from "@/lib/api";

interface DocumentationGeneratorViewProps {
  repositoryUrl: string;
  codeFiles?: CodeFile[];
}

const DOC_TYPES: { type: DocType; label: string; icon: string; desc: string }[] = [
  {
    type: "readme",
    label: "README",
    icon: "📖",
    desc: "Comprehensive project README with setup, stack, structure, and usage",
  },
  {
    type: "architecture",
    label: "Architecture",
    icon: "🏛️",
    desc: "System design, component flow, and Mermaid diagram",
  },
  {
    type: "api_reference",
    label: "API Reference",
    icon: "🔌",
    desc: "Discovered REST endpoints, handlers, and route tables",
  },
  {
    type: "setup_guide",
    label: "Setup Guide",
    icon: "⚙️",
    desc: "Prerequisites, installation, environment variables, and testing",
  },
  {
    type: "function_reference",
    label: "Function Reference",
    icon: "🧩",
    desc: "Function and class signatures, docstrings, and parameters",
  },
  {
    type: "module",
    label: "Module Reference",
    icon: "📦",
    desc: "Technical documentation for a specific file or directory",
  },
  {
    type: "project_overview",
    label: "Overview",
    icon: "📋",
    desc: "High-level summary of codebase purpose and statistics",
  },
];

export default function DocumentationGeneratorView({
  repositoryUrl,
  codeFiles = [],
}: DocumentationGeneratorViewProps) {
  const [docType, setDocType] = useState<DocType>("readme");
  const [audience, setAudience] = useState<DocAudience>("developer");
  const [detailLevel, setDetailLevel] = useState<DocDetailLevel>("standard");
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [customFile, setCustomFile] = useState<string>("");
  const [targetSymbol, setTargetSymbol] = useState<string>("");
  const [userInstructions, setUserInstructions] = useState<string>("");

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DocGenerateResponse | null>(null);
  const [viewMode, setViewMode] = useState<"rendered" | "raw">("rendered");
  const [copied, setCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const effectiveFile = customFile.trim() || selectedFile.trim();

  const handleGenerate = async () => {
    setIsLoading(true);
    setError(null);
    setCopied(false);

    try {
      const response = await generateDocumentation({
        repository_url: repositoryUrl,
        doc_type: docType,
        target_path: effectiveFile || undefined,
        target_symbol: targetSymbol.trim() || undefined,
        audience,
        detail_level: detailLevel,
        user_instructions: userInstructions.trim() || undefined,
      });
      setResult(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to generate documentation.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyMarkdown = async () => {
    if (!result?.content) return;
    try {
      await navigator.clipboard.writeText(result.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleDownload = () => {
    if (!result?.content) return;
    const filenameMap: Record<DocType, string> = {
      readme: "README.md",
      architecture: "ARCHITECTURE.md",
      api_reference: "API_REFERENCE.md",
      setup_guide: "SETUP_GUIDE.md",
      function_reference: "FUNCTION_REFERENCE.md",
      module: "MODULE_DOCUMENTATION.md",
      project_overview: "PROJECT_OVERVIEW.md",
    };
    const defaultName = filenameMap[result.doc_type] || "DOCUMENTATION.md";
    const blob = new Blob([result.content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = defaultName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mt-8 bg-surface/40 border border-border rounded-xl p-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-border">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/30">
              Day 13 • Documentation Generator
            </span>
            <span className="text-xs text-muted">
              Evidence-Grounded Technical Docs & Diagrams
            </span>
          </div>
          <h4 className="text-lg font-bold text-foreground">
            AI Technical Documentation Generator
          </h4>
          <p className="text-xs text-muted mt-0.5">
            Generate accurate READMEs, system architectures with Mermaid diagrams, API references,
            and setup guides directly from inspected repository code and manifests.
          </p>
        </div>
      </div>

      {/* Doc Type Selector Cards */}
      <div className="my-6">
        <label className="block text-xs font-medium text-foreground mb-2">
          Select Documentation Type <span className="text-red-400">*</span>
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
          {DOC_TYPES.map((dt) => (
            <button
              key={dt.type}
              onClick={() => setDocType(dt.type)}
              className={`p-3 rounded-lg border text-left transition-all cursor-pointer flex flex-col justify-between ${
                docType === dt.type
                  ? "bg-primary/10 border-primary shadow-sm"
                  : "bg-card border-border/80 hover:border-border hover:bg-surface"
              }`}
            >
              <div>
                <span className="text-base mb-1 block">{dt.icon}</span>
                <span
                  className={`text-xs font-semibold block ${
                    docType === dt.type ? "text-primary" : "text-foreground"
                  }`}
                >
                  {dt.label}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Configuration Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        {/* Target File */}
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">
            Target File / Path <span className="text-muted font-normal">(Optional)</span>
          </label>
          {codeFiles.length > 0 ? (
            <select
              value={selectedFile}
              onChange={(e) => {
                setSelectedFile(e.target.value);
                setCustomFile("");
              }}
              className="w-full text-xs bg-card border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary font-mono"
            >
              <option value="">Entire Repository</option>
              {codeFiles.map((f) => (
                <option key={f.path} value={f.path}>
                  {f.path}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              placeholder="e.g. app/api/v1/router.py"
              value={customFile}
              onChange={(e) => setCustomFile(e.target.value)}
              className="w-full text-xs bg-card border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary font-mono"
            />
          )}
        </div>

        {/* Target Symbol */}
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">
            Target Symbol <span className="text-muted font-normal">(Function / Class)</span>
          </label>
          <input
            type="text"
            placeholder="e.g. UserService or login"
            value={targetSymbol}
            onChange={(e) => setTargetSymbol(e.target.value)}
            className="w-full text-xs bg-card border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary font-mono"
          />
        </div>

        {/* Target Audience */}
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">
            Target Audience
          </label>
          <select
            value={audience}
            onChange={(e) => setAudience(e.target.value as DocAudience)}
            className="w-full text-xs bg-card border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary capitalize"
          >
            <option value="developer">Developer (Technical)</option>
            <option value="beginner">Beginner (Foundational)</option>
            <option value="maintainer">Maintainer (Architectural)</option>
          </select>
        </div>

        {/* Detail Level */}
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">
            Detail Level
          </label>
          <select
            value={detailLevel}
            onChange={(e) => setDetailLevel(e.target.value as DocDetailLevel)}
            className="w-full text-xs bg-card border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary capitalize"
          >
            <option value="standard">Standard</option>
            <option value="concise">Concise Summary</option>
            <option value="comprehensive">Comprehensive</option>
          </select>
        </div>
      </div>

      {/* User Instructions */}
      <div className="mb-6">
        <label className="block text-xs font-medium text-foreground mb-1.5">
          Custom Developer Guidance <span className="text-muted font-normal">(Optional focus instructions)</span>
        </label>
        <input
          type="text"
          placeholder="e.g. Highlight authentication endpoints, database models, and deployment prerequisites..."
          value={userInstructions}
          onChange={(e) => setUserInstructions(e.target.value)}
          className="w-full text-xs bg-card border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary"
        />
      </div>

      {/* Action Button & Safety */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <button
          onClick={handleGenerate}
          disabled={isLoading}
          className="px-5 py-2.5 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold transition-colors flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-sm"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>Analyzing Repo & Generating Documentation...</span>
            </>
          ) : (
            <>
              <span>✍️</span>
              <span>Generate Documentation</span>
            </>
          )}
        </button>

        <p className="text-[11px] text-muted font-mono">
          🛡️ Read-only preview: repository files are never overwritten automatically.
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mt-4 p-3.5 rounded-lg border border-red-500/30 bg-red-500/10 text-red-200 text-xs flex items-start gap-2.5">
          <span className="text-sm">⚠️</span>
          <div>
            <p className="font-semibold text-red-300">Documentation Generation Failed</p>
            <p className="mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Results View */}
      {result && (
        <div className="mt-8 space-y-6 animate-fade-in border-t border-border pt-6">
          {/* Metadata Banner */}
          <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/60">
              <div>
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/30 uppercase">
                    {result.doc_type}
                  </span>
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-surface text-muted border border-border capitalize">
                    {result.metadata.audience} Audience
                  </span>
                  <span className="text-xs text-muted font-mono">
                    ID: {result.document_id}
                  </span>
                </div>
                <h5 className="text-lg font-bold text-foreground">
                  {result.title}
                </h5>
                <p className="text-xs text-muted mt-1 leading-relaxed">
                  {result.summary}
                </p>
              </div>

              {/* Action Toolbar */}
              <div className="flex flex-wrap items-center gap-2">
                {/* View Mode Toggle */}
                <div className="flex items-center rounded-lg bg-surface p-1 border border-border text-xs">
                  <button
                    onClick={() => setViewMode("rendered")}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors cursor-pointer ${
                      viewMode === "rendered"
                        ? "bg-primary text-white"
                        : "text-muted hover:text-foreground"
                    }`}
                  >
                    Preview
                  </button>
                  <button
                    onClick={() => setViewMode("raw")}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors cursor-pointer ${
                      viewMode === "raw"
                        ? "bg-primary text-white"
                        : "text-muted hover:text-foreground"
                    }`}
                  >
                    Raw Markdown
                  </button>
                </div>

                {/* Copy Button */}
                <button
                  onClick={handleCopyMarkdown}
                  className="px-3 py-1.5 rounded-lg bg-surface hover:bg-surface/80 border border-border text-foreground text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  {copied ? (
                    <>
                      <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-emerald-400">Copied!</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-3.5 h-3.5 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                      </svg>
                      <span>Copy</span>
                    </>
                  )}
                </button>

                {/* Download Button */}
                <button
                  onClick={handleDownload}
                  className="px-3 py-1.5 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                    />
                  </svg>
                  <span>Download .md</span>
                </button>
              </div>
            </div>

            {/* Sub-meta */}
            <div className="flex flex-wrap items-center justify-between text-[11px] text-muted pt-3 font-mono">
              <span>
                Generated via {result.metadata.model} in {result.metadata.generation_time_seconds}s
              </span>
              <span>
                {result.source_files_used.length} repository files analyzed
              </span>
            </div>
          </div>

          {/* Unverified items / Missing info if present */}
          {(result.unverified_items.length > 0 || result.missing_information.length > 0) && (
            <div className="p-4 bg-amber-500/10 border border-amber-500/25 rounded-xl text-xs space-y-2">
              <h6 className="font-semibold text-amber-400 flex items-center gap-1.5">
                <span>⚠️</span>
                <span>Verification Notes & Codebase Limits</span>
              </h6>
              {result.unverified_items.length > 0 && (
                <p className="text-amber-200/90 text-[11px]">
                  <strong className="text-amber-300">Requires Confirmation:</strong>{" "}
                  {result.unverified_items.join("; ")}
                </p>
              )}
              {result.missing_information.length > 0 && (
                <p className="text-amber-200/80 text-[11px]">
                  <strong className="text-amber-300">Not Discovered in Repo:</strong>{" "}
                  {result.missing_information.join("; ")}
                </p>
              )}
            </div>
          )}

          {/* Markdown Content Viewer */}
          <div className="bg-card border border-border rounded-xl p-6 shadow-sm overflow-hidden">
            {viewMode === "raw" ? (
              <pre className="text-xs font-mono text-foreground overflow-x-auto whitespace-pre bg-surface/80 p-4 rounded-lg border border-border/60">
                {result.content}
              </pre>
            ) : (
              <div className="prose prose-invert max-w-none text-xs leading-relaxed space-y-4">
                <pre className="text-xs font-mono text-foreground overflow-x-auto whitespace-pre-wrap bg-surface/50 p-4 rounded-lg border border-border/50">
                  {result.content}
                </pre>
              </div>
            )}
          </div>

          {/* Analyzed Source Files Drawer */}
          {result.source_files_used.length > 0 && (
            <div className="bg-surface/30 border border-border rounded-xl p-4">
              <button
                onClick={() => setShowSources(!showSources)}
                className="w-full flex items-center justify-between text-xs font-medium text-foreground hover:text-primary transition-colors cursor-pointer"
              >
                <span className="flex items-center gap-2">
                  <span>📂</span>
                  <span>Analyzed Repository Files ({result.source_files_used.length})</span>
                </span>
                <span>{showSources ? "▲ Hide" : "▼ Show"}</span>
              </button>

              {showSources && (
                <div className="mt-3 flex flex-wrap gap-1.5 border-t border-border pt-3">
                  {result.source_files_used.map((file) => (
                    <span
                      key={file}
                      className="text-[11px] font-mono px-2 py-0.5 rounded bg-card border border-border text-foreground"
                    >
                      {file}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
