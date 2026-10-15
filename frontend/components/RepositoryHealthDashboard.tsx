"use client";

import { useState } from "react";
import {
  analyzeCodeQuality,
  CodeQualityResponse,
  FindingCategory,
  FindingSeverity,
  QualityFinding,
} from "@/lib/api";

interface RepositoryHealthDashboardProps {
  repositoryUrl: string;
}

export default function RepositoryHealthDashboard({
  repositoryUrl,
}: RepositoryHealthDashboardProps) {
  const [data, setData] = useState<CodeQualityResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [activeTab, setActiveTab] = useState<"findings" | "files">("findings");

  const handleRunAudit = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await analyzeCodeQuality(repositoryUrl);
      setData(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to analyze code quality.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case "A":
        return "text-emerald-400 bg-emerald-500/10 border-emerald-500/30 ring-emerald-500/20";
      case "B":
        return "text-blue-400 bg-blue-500/10 border-blue-500/30 ring-blue-500/20";
      case "C":
        return "text-amber-400 bg-amber-500/10 border-amber-500/30 ring-amber-500/20";
      case "D":
        return "text-orange-400 bg-orange-500/10 border-orange-500/30 ring-orange-500/20";
      default:
        return "text-red-400 bg-red-500/10 border-red-500/30 ring-red-500/20";
    }
  };

  const getSeverityBadge = (severity: FindingSeverity) => {
    switch (severity) {
      case "critical":
        return "bg-rose-500/15 text-rose-400 border-rose-500/30";
      case "error":
        return "bg-red-500/15 text-red-400 border-red-500/30";
      case "warning":
        return "bg-amber-500/15 text-amber-400 border-amber-500/30";
      case "info":
        return "bg-blue-500/15 text-blue-400 border-blue-500/30";
      default:
        return "bg-surface text-muted border-border";
    }
  };

  // Filter findings
  const filteredFindings = data?.findings.filter((f) => {
    if (selectedSeverity !== "all" && f.severity !== selectedSeverity) return false;
    if (selectedCategory !== "all" && f.category !== selectedCategory) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const inMsg = f.message.toLowerCase().includes(q);
      const inFile = f.file_path.toLowerCase().includes(q);
      const inRule = f.rule_name.toLowerCase().includes(q);
      const inEntity = f.entity_name ? f.entity_name.toLowerCase().includes(q) : false;
      return inMsg || inFile || inRule || inEntity;
    }
    return true;
  }) || [];

  return (
    <div className="mt-8 bg-card border border-border rounded-xl p-6 sm:p-8 shadow-xl transition-all">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🩺</span>
            <h3 className="text-lg font-bold text-foreground">
              Repository Health & Code Quality
            </h3>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              Static Code Audit
            </span>
          </div>
          <p className="text-xs text-muted mt-1">
            Analyze code complexity, functions length, documentation coverage, exception handling, and maintainability.
          </p>
        </div>

        <button
          type="button"
          onClick={handleRunAudit}
          disabled={isLoading}
          className="px-4 py-2 bg-primary hover:bg-primary-hover text-primary-foreground font-medium text-xs rounded-lg shadow-md transition-all disabled:opacity-50 flex items-center gap-2 cursor-pointer self-start sm:self-auto"
        >
          {isLoading ? (
            <>
              <div className="w-3.5 h-3.5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
              <span>Analyzing Code Quality...</span>
            </>
          ) : (
            <>
              <span>{data ? "Re-run Audit" : "Run Quality Audit"}</span>
              <span>⚡</span>
            </>
          )}
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="mt-4 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-200 text-xs flex items-start gap-3">
          <span className="text-base">⚠️</span>
          <div className="flex-1">
            <p className="font-semibold text-red-300">Code Quality Audit Error</p>
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

      {/* Empty State before audit */}
      {!data && !isLoading && !error && (
        <div className="py-12 text-center text-muted">
          <div className="text-4xl mb-3">📊</div>
          <p className="text-sm font-medium text-foreground">
            No Quality Audit Run Yet
          </p>
          <p className="text-xs text-muted max-w-md mx-auto mt-1">
            Click &quot;Run Quality Audit&quot; above to inspect cyclomatic complexity, nesting depth, code smells, and documentation coverage across this repository.
          </p>
        </div>
      )}

      {/* Audit Results */}
      {data && (
        <div className="mt-6 space-y-6 animate-fade-in">
          {/* Top Health Grade & Sub-scores Banner */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 bg-surface/50 border border-border rounded-xl p-5 shadow-inner items-center">
            {/* Grade Display */}
            <div className="flex items-center gap-5 md:border-r border-border/60 pr-4">
              <div
                className={`w-20 h-20 rounded-2xl flex flex-col items-center justify-center border ring-4 font-black shadow-lg ${getGradeColor(
                  data.health.letter_grade
                )}`}
              >
                <span className="text-3xl leading-none">{data.health.letter_grade}</span>
                <span className="text-[10px] uppercase tracking-wider font-semibold opacity-80 mt-1">
                  Grade
                </span>
              </div>
              <div>
                <span className="text-[11px] uppercase tracking-wider font-bold text-muted">
                  Overall Health Score
                </span>
                <div className="text-2xl font-bold text-foreground flex items-baseline gap-1 mt-0.5">
                  <span>{data.health.overall_score}</span>
                  <span className="text-xs text-muted font-normal">/ 100</span>
                </div>
                <p className="text-xs text-muted mt-1">
                  {data.metrics.files_with_issues === 0
                    ? "Exceptional code quality with no significant smells."
                    : `${data.metrics.files_with_issues} files contain areas for refactoring.`}
                </p>
              </div>
            </div>

            {/* Sub-Scores (2 columns span) */}
            <div className="md:col-span-2 grid grid-cols-2 gap-x-6 gap-y-3 text-xs">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-muted">Maintainability</span>
                  <span className="font-semibold text-foreground">
                    {data.health.maintainability_score}%
                  </span>
                </div>
                <div className="w-full bg-border rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-primary h-1.5 rounded-full"
                    style={{ width: `${data.health.maintainability_score}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-muted">Complexity Control</span>
                  <span className="font-semibold text-foreground">
                    {data.health.complexity_score}%
                  </span>
                </div>
                <div className="w-full bg-border rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-blue-400 h-1.5 rounded-full"
                    style={{ width: `${data.health.complexity_score}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-muted">Documentation Coverage</span>
                  <span className="font-semibold text-foreground">
                    {data.health.documentation_score}%
                  </span>
                </div>
                <div className="w-full bg-border rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-emerald-400 h-1.5 rounded-full"
                    style={{ width: `${data.health.documentation_score}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-muted">Reliability & Safety</span>
                  <span className="font-semibold text-foreground">
                    {data.health.reliability_score}%
                  </span>
                </div>
                <div className="w-full bg-border rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-amber-400 h-1.5 rounded-full"
                    style={{ width: `${data.health.reliability_score}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-surface/40 border border-border rounded-lg p-3">
              <span className="text-[10px] uppercase text-muted font-bold tracking-wider block">
                Total Code Lines
              </span>
              <span className="text-base font-bold text-foreground mt-0.5 block">
                {data.metrics.code_lines.toLocaleString()}
              </span>
              <span className="text-[10px] text-muted">
                {data.metrics.comment_lines} comments
              </span>
            </div>

            <div className="bg-surface/40 border border-border rounded-lg p-3">
              <span className="text-[10px] uppercase text-muted font-bold tracking-wider block">
                Analyzed Files
              </span>
              <span className="text-base font-bold text-foreground mt-0.5 block">
                {data.metrics.total_files_analyzed}
              </span>
              <span className="text-[10px] text-muted">
                {data.metrics.files_with_issues} with issues
              </span>
            </div>

            <div className="bg-surface/40 border border-border rounded-lg p-3">
              <span className="text-[10px] uppercase text-muted font-bold tracking-wider block">
                Functions / Classes
              </span>
              <span className="text-base font-bold text-foreground mt-0.5 block">
                {data.metrics.total_functions} / {data.metrics.total_classes}
              </span>
              <span className="text-[10px] text-muted">
                ~{data.metrics.average_function_length} lines/func
              </span>
            </div>

            <div className="bg-surface/40 border border-border rounded-lg p-3">
              <span className="text-[10px] uppercase text-muted font-bold tracking-wider block">
                Avg Complexity
              </span>
              <span className="text-base font-bold text-foreground mt-0.5 block">
                {data.metrics.average_cyclomatic_complexity}
              </span>
              <span className="text-[10px] text-muted">
                Max complexity: {data.metrics.max_cyclomatic_complexity}
              </span>
            </div>

            <div className="bg-surface/40 border border-border rounded-lg p-3">
              <span className="text-[10px] uppercase text-muted font-bold tracking-wider block">
                Doc Coverage
              </span>
              <span className="text-base font-bold text-foreground mt-0.5 block">
                {data.metrics.docstring_coverage_percentage}%
              </span>
              <span className="text-[10px] text-muted">public entities</span>
            </div>

            <div className="bg-surface/40 border border-border rounded-lg p-3">
              <span className="text-[10px] uppercase text-muted font-bold tracking-wider block">
                Total Findings
              </span>
              <span className="text-base font-bold text-foreground mt-0.5 block">
                {data.findings.length}
              </span>
              <span className="text-[10px] text-muted">
                {data.metrics.duplicate_blocks_count} dup blocks
              </span>
            </div>
          </div>

          {/* Navigation Tabs (Findings vs Files) */}
          <div className="flex items-center justify-between border-b border-border pt-2">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setActiveTab("findings")}
                className={`px-4 py-2 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                  activeTab === "findings"
                    ? "border-primary text-primary"
                    : "border-transparent text-muted hover:text-foreground"
                }`}
              >
                Findings ({data.findings.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("files")}
                className={`px-4 py-2 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                  activeTab === "files"
                    ? "border-primary text-primary"
                    : "border-transparent text-muted hover:text-foreground"
                }`}
              >
                File Quality Breakdown ({data.file_summaries.length})
              </button>
            </div>
          </div>

          {/* TAB 1: FINDINGS EXPLORER */}
          {activeTab === "findings" && (
            <div className="space-y-4">
              {/* Filter controls */}
              <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
                {/* Search */}
                <div className="relative flex-1">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search findings by message, rule, or file path..."
                    className="w-full bg-surface border border-border rounded-lg px-3 py-1.5 text-xs text-foreground placeholder:text-muted/60 focus:outline-none focus:border-primary"
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery("")}
                      className="absolute right-2.5 top-2 text-muted hover:text-foreground text-xs"
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* Filters */}
                <div className="flex items-center gap-2">
                  <select
                    value={selectedSeverity}
                    onChange={(e) => setSelectedSeverity(e.target.value)}
                    className="bg-surface border border-border rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:border-primary"
                  >
                    <option value="all">All Severities</option>
                    <option value="critical">Critical</option>
                    <option value="error">Error</option>
                    <option value="warning">Warning</option>
                    <option value="info">Info</option>
                  </select>

                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="bg-surface border border-border rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:border-primary"
                  >
                    <option value="all">All Categories</option>
                    <option value="complexity">Complexity</option>
                    <option value="size">Size</option>
                    <option value="maintainability">Maintainability</option>
                    <option value="documentation">Documentation</option>
                    <option value="error_handling">Error Handling</option>
                    <option value="duplication">Duplication</option>
                  </select>
                </div>
              </div>

              {/* Severity Pills Shortcut */}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="text-[11px] text-muted">Quick Filter:</span>
                {Object.entries(data.severity_breakdown).map(([sev, count]) => (
                  <button
                    key={sev}
                    type="button"
                    onClick={() =>
                      setSelectedSeverity(selectedSeverity === sev ? "all" : sev)
                    }
                    className={`px-2.5 py-1 rounded-md text-[11px] font-mono border transition-all cursor-pointer ${
                      selectedSeverity === sev
                        ? "bg-primary/20 border-primary text-primary font-bold"
                        : "bg-surface border-border text-muted hover:text-foreground"
                    }`}
                  >
                    {sev.toUpperCase()}: {count}
                  </button>
                ))}
              </div>

              {/* Findings List */}
              {filteredFindings.length === 0 ? (
                <div className="py-10 text-center text-muted bg-surface/30 rounded-xl border border-border">
                  <p className="text-xs">No findings match the current filter criteria.</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
                  {filteredFindings.map((finding) => (
                    <div
                      key={finding.id}
                      className="bg-surface/50 hover:bg-surface border border-border rounded-xl p-4 transition-all"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getSeverityBadge(
                              finding.severity
                            )}`}
                          >
                            {finding.severity}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-card text-muted border border-border">
                            {finding.rule_id}
                          </span>
                          <span className="text-xs font-semibold text-foreground">
                            {finding.rule_name}
                          </span>
                        </div>

                        <div className="text-xs font-mono text-muted flex items-center gap-1.5">
                          <span>📄</span>
                          <span className="text-foreground font-medium">
                            {finding.file_path}
                          </span>
                          <span>:</span>
                          <span className="text-primary font-bold">
                            {finding.start_line === finding.end_line
                              ? finding.start_line
                              : `${finding.start_line}-${finding.end_line}`}
                          </span>
                        </div>
                      </div>

                      {/* Finding message */}
                      <p className="text-xs text-foreground/90 mt-1 leading-relaxed">
                        {finding.message}
                      </p>

                      {/* Entity info tag if available */}
                      {finding.entity_name && (
                        <div className="mt-2 text-[11px] font-mono text-muted flex items-center gap-1">
                          <span className="text-primary">Target:</span>
                          <span>
                            {finding.entity_type} <code className="text-foreground font-semibold">{finding.entity_name}</code>
                          </span>
                        </div>
                      )}

                      {/* Suggestion box */}
                      <div className="mt-3 p-2.5 rounded-lg bg-card/70 border border-border/70 text-[11px] text-muted leading-relaxed flex items-start gap-2">
                        <span className="text-xs">💡</span>
                        <div>
                          <strong className="text-foreground font-medium">Suggestion: </strong>
                          <span>{finding.suggestion}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: FILE QUALITY SUMMARY */}
          {activeTab === "files" && (
            <div className="overflow-x-auto rounded-xl border border-border">
              <table className="w-full text-left text-xs">
                <thead className="bg-surface/80 border-b border-border text-muted uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="py-2.5 px-3">File Path</th>
                    <th className="py-2.5 px-3">Lang</th>
                    <th className="py-2.5 px-3">Lines</th>
                    <th className="py-2.5 px-3">Avg Complexity</th>
                    <th className="py-2.5 px-3">Findings</th>
                    <th className="py-2.5 px-3 text-right">Health Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60 font-mono">
                  {data.file_summaries.map((f) => (
                    <tr key={f.file_path} className="hover:bg-surface/50 transition-colors">
                      <td className="py-2 px-3 text-foreground font-medium truncate max-w-xs">
                        {f.file_path}
                      </td>
                      <td className="py-2 px-3 text-muted">{f.language}</td>
                      <td className="py-2 px-3 text-muted">{f.total_lines}</td>
                      <td className="py-2 px-3 text-muted">
                        {f.average_complexity}
                        {f.max_complexity > 10 && (
                          <span className="text-[10px] text-amber-400 ml-1">
                            (max {f.max_complexity})
                          </span>
                        )}
                      </td>
                      <td className="py-2 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            f.findings_count > 0
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                              : "text-muted"
                          }`}
                        >
                          {f.findings_count}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right">
                        <span
                          className={`px-2 py-0.5 rounded font-bold text-xs border ${getGradeColor(
                            f.letter_grade
                          )}`}
                        >
                          {f.health_score}% ({f.letter_grade})
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
