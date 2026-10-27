"use client";

import { useState } from "react";
import {
  CodeFile,
  DebugRequest,
  DebugResponse,
  debugError,
} from "@/lib/api";

interface DebugAssistantViewProps {
  repositoryUrl: string;
  codeFiles?: CodeFile[];
}

export default function DebugAssistantView({
  repositoryUrl,
  codeFiles = [],
}: DebugAssistantViewProps) {
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [reproductionSteps, setReproductionSteps] = useState<string>("");
  const [expectedBehavior, setExpectedBehavior] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [customFile, setCustomFile] = useState<string>("");
  const [language, setLanguage] = useState<string>("");

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DebugResponse | null>(null);
  const [copiedFix, setCopiedFix] = useState(false);
  const [showFrames, setShowFrames] = useState(false);

  const effectiveFile = customFile.trim() || selectedFile.trim();

  const handleAnalyze = async () => {
    if (!errorMessage.trim()) {
      setError("Please paste an error message or stack trace to analyze.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setCopiedFix(false);

    try {
      const response = await debugError({
        repository_url: repositoryUrl,
        error_message: errorMessage.trim(),
        reproduction_steps: reproductionSteps.trim() || undefined,
        expected_behavior: expectedBehavior.trim() || undefined,
        file_path: effectiveFile || undefined,
        language: language.trim() || undefined,
      });
      setResult(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to analyze error.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyFix = async () => {
    if (!result?.suggested_fix) return;
    try {
      await navigator.clipboard.writeText(result.suggested_fix);
      setCopiedFix(true);
      setTimeout(() => setCopiedFix(false), 2000);
    } catch {
      // Fallback
    }
  };

  const getConfidenceBadge = (confidence: string) => {
    switch (confidence.toLowerCase()) {
      case "high":
        return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
      case "medium":
        return "bg-amber-500/15 text-amber-400 border-amber-500/30";
      case "low":
      default:
        return "bg-slate-500/15 text-slate-300 border-slate-500/30";
    }
  };

  return (
    <div className="mt-8 bg-surface/40 border border-border rounded-xl p-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-border">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/30">
              Day 12 • AI Debugging Assistant
            </span>
            <span className="text-xs text-muted">
              Root Cause Analysis & Evidence Grounding
            </span>
          </div>
          <h4 className="text-lg font-bold text-foreground">
            AI-Powered Debugging Assistant
          </h4>
          <p className="text-xs text-muted mt-0.5">
            Paste an error message or stack trace. The assistant will locate matching source files,
            diagnose the most likely root causes, and provide practical debugging steps without executing code.
          </p>
        </div>
      </div>

      {/* Input Workspace */}
      <div className="my-6 space-y-4">
        {/* Error / Stack Trace Input */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-medium text-foreground">
              Error Message or Stack Trace <span className="text-red-400">*</span>
            </label>
            <span className="text-[11px] text-muted font-mono">
              {errorMessage.length}/15,000 chars
            </span>
          </div>
          <textarea
            rows={6}
            placeholder={`Paste error output or traceback here, for example:
Traceback (most recent call last):
  File "app/services/calculator.py", line 5, in divide
    return a / b
ZeroDivisionError: float division by zero`}
            value={errorMessage}
            onChange={(e) => setErrorMessage(e.target.value)}
            className="w-full text-xs font-mono bg-card border border-border rounded-lg p-3 text-foreground focus:outline-none focus:border-primary placeholder:text-muted/60"
          />
        </div>

        {/* Optional Context Inputs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* File Selector */}
          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">
              Focus File <span className="text-muted font-normal">(Optional)</span>
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
                <option value="">Auto-detect from trace</option>
                {codeFiles.map((f) => (
                  <option key={f.path} value={f.path}>
                    {f.path}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                placeholder="e.g. app/services/calculator.py"
                value={customFile}
                onChange={(e) => setCustomFile(e.target.value)}
                className="w-full text-xs bg-card border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary font-mono"
              />
            )}
            {codeFiles.length > 0 && (
              <input
                type="text"
                placeholder="Or custom path..."
                value={customFile}
                onChange={(e) => setCustomFile(e.target.value)}
                className="mt-1.5 w-full text-[11px] bg-card/60 border border-border rounded px-2 py-1 text-foreground focus:outline-none font-mono"
              />
            )}
          </div>

          {/* Reproduction Steps */}
          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">
              Steps to Reproduce <span className="text-muted font-normal">(Optional)</span>
            </label>
            <input
              type="text"
              placeholder="e.g. Called divide(10.0, 0.0) from CLI"
              value={reproductionSteps}
              onChange={(e) => setReproductionSteps(e.target.value)}
              className="w-full text-xs bg-card border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary"
            />
          </div>

          {/* Expected Behavior & Language */}
          <div>
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="block text-xs font-medium text-foreground mb-1.5">
                  Expected Behavior <span className="text-muted font-normal">(Opt)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Should return 0.0 or raise ValueError"
                  value={expectedBehavior}
                  onChange={(e) => setExpectedBehavior(e.target.value)}
                  className="w-full text-xs bg-card border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary"
                />
              </div>

              <div className="w-28">
                <label className="block text-xs font-medium text-foreground mb-1.5">
                  Language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full text-xs bg-card border border-border rounded-lg px-2 py-2 text-foreground focus:outline-none focus:border-primary"
                >
                  <option value="">Auto</option>
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="typescript">TypeScript</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Action Button & Disclaimer */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
          <button
            onClick={handleAnalyze}
            disabled={isLoading || !errorMessage.trim()}
            className="px-5 py-2.5 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold transition-colors flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-sm"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Analyzing Error & Sourcing Evidence...</span>
              </>
            ) : (
              <>
                <span>🩺</span>
                <span>Analyze Error & Root Cause</span>
              </>
            )}
          </button>

          <p className="text-[11px] text-muted">
            🛡️ Analysis-only: code and suggested fixes are never executed automatically.
          </p>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="p-3.5 rounded-lg border border-red-500/30 bg-red-500/10 text-red-200 text-xs flex items-start gap-2.5">
            <span className="text-sm">⚠️</span>
            <div>
              <p className="font-semibold text-red-300">Debugging Analysis Failed</p>
              <p className="mt-0.5">{error}</p>
            </div>
          </div>
        )}
      </div>

      {/* Results Workspace */}
      {result && (
        <div className="mt-8 space-y-6 animate-fade-in border-t border-border pt-6">
          {/* Summary Banner */}
          <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pb-4 border-b border-border/60">
              <div>
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  {result.error_type && (
                    <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30 font-mono">
                      {result.error_type}
                    </span>
                  )}
                  <span
                    className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border capitalize ${getConfidenceBadge(
                      result.confidence
                    )}`}
                  >
                    {result.confidence} Confidence
                  </span>
                  <span className="text-xs text-muted font-mono">
                    ID: {result.debug_id}
                  </span>
                </div>
                <h5 className="text-base font-semibold text-foreground">
                  {result.error_summary}
                </h5>
              </div>

              {result.evidence.length > 0 && (
                <div className="text-xs font-mono px-3 py-1 rounded bg-surface border border-border text-muted">
                  {result.evidence.length} Source {result.evidence.length === 1 ? "Snippet" : "Snippets"} Found
                </div>
              )}
            </div>

            {/* Confidence Disclaimer */}
            <p className="text-[11px] text-muted italic mt-3">
              ℹ️ {result.confidence_note}
            </p>
          </div>

          {/* Root Cause Card */}
          <div className="bg-primary/5 border border-primary/25 rounded-xl p-5">
            <h5 className="text-xs font-bold uppercase tracking-wider text-primary mb-2 flex items-center gap-1.5">
              <span>🎯</span>
              <span>Primary Root Cause</span>
            </h5>
            <p className="text-xs text-foreground/95 leading-relaxed font-normal">
              {result.root_cause}
            </p>
          </div>

          {/* Ranked Possible Causes */}
          {result.possible_causes.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-5">
              <h5 className="text-xs font-bold uppercase tracking-wider text-foreground mb-3 flex items-center gap-1.5">
                <span>🔍</span>
                <span>Hypothesized Causes (Ranked by Likelihood)</span>
              </h5>
              <div className="space-y-3">
                {result.possible_causes.map((cause) => (
                  <div
                    key={cause.rank}
                    className="p-3.5 bg-surface/50 border border-border/70 rounded-lg text-xs"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="font-semibold text-foreground flex items-center gap-1.5">
                        <span className="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">
                          {cause.rank}
                        </span>
                        {cause.title}
                      </span>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border capitalize ${getConfidenceBadge(
                          cause.confidence
                        )}`}
                      >
                        {cause.confidence}
                      </span>
                    </div>
                    <p className="text-foreground/90 leading-relaxed">
                      {cause.explanation}
                    </p>
                    {cause.supporting_evidence.length > 0 && (
                      <div className="mt-2 text-[11px] text-muted font-mono flex items-center gap-1.5">
                        <span>Supporting:</span>
                        <span>{cause.supporting_evidence.join(", ")}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Source Code Evidence */}
          {result.evidence.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-5">
              <h5 className="text-xs font-bold uppercase tracking-wider text-foreground mb-3 flex items-center gap-1.5">
                <span>📄</span>
                <span>Repository Source Code Evidence</span>
              </h5>
              <div className="space-y-4">
                {result.evidence.map((ev, idx) => (
                  <div
                    key={`${ev.file_path}-${ev.start_line}-${idx}`}
                    className="bg-surface/60 border border-border rounded-lg p-3.5"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs mb-2">
                      <div className="flex items-center gap-2 font-mono">
                        <span className="font-semibold text-primary">
                          {ev.file_path}:{ev.start_line}-{ev.end_line}
                        </span>
                        {ev.entity_name && (
                          <span className="text-muted">({ev.entity_name})</span>
                        )}
                      </div>
                      <span className="text-[11px] text-muted italic">
                        {ev.relevance}
                      </span>
                    </div>
                    <pre className="text-xs font-mono text-foreground overflow-x-auto whitespace-pre bg-card/90 p-3 rounded border border-border/50">
                      {ev.code_snippet}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Debugging Steps */}
          {result.recommended_steps.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-5">
              <h5 className="text-xs font-bold uppercase tracking-wider text-foreground mb-3 flex items-center gap-1.5">
                <span>🛠️</span>
                <span>Actionable Debugging Steps</span>
              </h5>
              <ul className="space-y-2 text-xs text-foreground/90">
                {result.recommended_steps.map((step, idx) => (
                  <li
                    key={idx}
                    className="p-2.5 rounded bg-surface/50 border border-border/50 flex items-start gap-2"
                  >
                    <span className="text-primary font-bold">›</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Read-Only Suggested Fix */}
          {result.suggested_fix && (
            <div className="bg-card border border-emerald-500/30 rounded-xl p-5">
              <div className="flex items-center justify-between mb-2">
                <h5 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                  <span>✨</span>
                  <span>Suggested Code Fix (Read-Only • Not Automatically Applied)</span>
                </h5>
                <button
                  onClick={handleCopyFix}
                  className="text-xs px-2.5 py-1 rounded bg-surface hover:bg-surface/80 border border-border text-foreground font-mono transition-colors flex items-center gap-1 cursor-pointer"
                >
                  {copiedFix ? (
                    <>
                      <svg className="w-3 h-3 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-emerald-400">Copied!</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-3 h-3 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                      </svg>
                      <span>Copy Fix</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="text-xs font-mono text-emerald-200/95 overflow-x-auto whitespace-pre bg-card/90 p-3.5 rounded border border-emerald-500/20">
                {result.suggested_fix}
              </pre>
            </div>
          )}

          {/* Missing Information & Limitations */}
          {(result.missing_information.length > 0 || result.limitations.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              {result.missing_information.length > 0 && (
                <div className="bg-surface/40 border border-border rounded-xl p-4">
                  <h6 className="font-semibold text-foreground mb-2 flex items-center gap-1.5">
                    <span>📋</span>
                    <span>Missing Information for Full Diagnosis</span>
                  </h6>
                  <ul className="list-disc list-inside space-y-1 text-muted text-[11px]">
                    {result.missing_information.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {result.limitations.length > 0 && (
                <div className="bg-surface/40 border border-border rounded-xl p-4">
                  <h6 className="font-semibold text-foreground mb-2 flex items-center gap-1.5">
                    <span>⚠️</span>
                    <span>Static Analysis Limitations</span>
                  </h6>
                  <ul className="list-disc list-inside space-y-1 text-muted text-[11px]">
                    {result.limitations.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Parsed Stack Frames (Collapsible) */}
          {result.parsed_error.frames.length > 0 && (
            <div className="bg-surface/30 border border-border rounded-xl p-4">
              <button
                onClick={() => setShowFrames(!showFrames)}
                className="w-full flex items-center justify-between text-xs font-medium text-foreground hover:text-primary transition-colors cursor-pointer"
              >
                <span className="flex items-center gap-2">
                  <span>📜</span>
                  <span>Extracted Stack Frames ({result.parsed_error.frames.length})</span>
                </span>
                <span>{showFrames ? "▲ Hide" : "▼ Show"}</span>
              </button>

              {showFrames && (
                <div className="mt-3 space-y-2 border-t border-border pt-3">
                  {result.parsed_error.frames.map((frame, idx) => (
                    <div
                      key={idx}
                      className="text-[11px] font-mono p-2 rounded bg-card/60 border border-border/50 flex flex-col sm:flex-row sm:items-center justify-between gap-1"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-muted font-bold">#{idx + 1}</span>
                        <span className="text-foreground">{frame.file_path || "unknown"}</span>
                        {frame.line_number && (
                          <span className="text-primary font-bold">:{frame.line_number}</span>
                        )}
                        {frame.function_name && (
                          <span className="text-muted">in {frame.function_name}()</span>
                        )}
                      </div>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded self-start sm:self-auto ${
                          frame.is_application_code
                            ? "bg-primary/10 text-primary border border-primary/20"
                            : "bg-surface text-muted border border-border"
                        }`}
                      >
                        {frame.is_application_code ? "Application" : "Vendor/Stdlib"}
                      </span>
                    </div>
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
