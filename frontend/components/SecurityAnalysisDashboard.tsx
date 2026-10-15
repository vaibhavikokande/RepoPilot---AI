"use client";

import { useState } from "react";
import {
  analyzeSecurity,
  SecurityAnalysisResponse,
  SecurityFinding,
} from "@/lib/api";

interface SecurityAnalysisDashboardProps {
  repositoryUrl: string;
}

export default function SecurityAnalysisDashboard({
  repositoryUrl,
}: SecurityAnalysisDashboardProps) {
  const [data, setData] = useState<SecurityAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [explainWithLLM, setExplainWithLLM] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [expandedFindingId, setExpandedFindingId] = useState<string | null>(null);

  const handleRunScan = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await analyzeSecurity(repositoryUrl, explainWithLLM);
      setData(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to run security analysis.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return "text-red-400 bg-red-500/10 border-red-500/30";
      case "high":
        return "text-orange-400 bg-orange-500/10 border-orange-500/30";
      case "medium":
        return "text-amber-400 bg-amber-500/10 border-amber-500/30";
      case "low":
        return "text-blue-400 bg-blue-500/10 border-blue-500/30";
      default:
        return "text-gray-400 bg-gray-500/10 border-gray-500/30";
    }
  };

  const getConfidenceBadge = (confidence: string) => {
    switch (confidence.toLowerCase()) {
      case "high":
        return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
      case "medium":
        return "text-cyan-400 bg-cyan-500/10 border-cyan-500/20";
      default:
        return "text-gray-400 bg-gray-500/10 border-gray-500/20";
    }
  };

  const toggleExpand = (findingId: string) => {
    setExpandedFindingId((prev) => (prev === findingId ? null : findingId));
  };

  // Filter findings
  const filteredFindings = data
    ? data.findings.filter((f) => {
        if (selectedSeverity !== "all" && f.severity !== selectedSeverity) {
          return false;
        }
        if (selectedCategory !== "all" && f.category !== selectedCategory) {
          return false;
        }
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchesTitle = f.title.toLowerCase().includes(q);
          const matchesFile = f.file_path.toLowerCase().includes(q);
          const matchesRule = f.rule_id.toLowerCase().includes(q);
          const matchesEntity = f.entity_name ? f.entity_name.toLowerCase().includes(q) : false;
          const matchesCwe = f.cwe_id ? f.cwe_id.toLowerCase().includes(q) : false;
          return matchesTitle || matchesFile || matchesRule || matchesEntity || matchesCwe;
        }
        return true;
      })
    : [];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🛡️</span>
            <h2 className="text-xl font-bold text-slate-100">
              Security Analysis & Risk Detection
            </h2>
            <span className="text-xs bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-full font-medium">
              Static SAST
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Statically inspects source code for hardcoded secrets, dangerous dynamic execution,
            insecure subprocesses, SQL injection patterns, unsafe deserialization, and disabled TLS.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={explainWithLLM}
              onChange={(e) => setExplainWithLLM(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0"
            />
            AI Summary
          </label>

          <button
            onClick={handleRunScan}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 disabled:from-slate-700 disabled:to-slate-700 text-white font-medium rounded-lg text-sm transition-all shadow-lg shadow-red-900/20 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Scanning AST...
              </>
            ) : (
              <>
                <span>🔍</span>
                {data ? "Re-scan Security" : "Run Security Analysis"}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-500/30 rounded-lg text-sm text-red-300 flex items-start gap-3">
          <span className="text-red-400 text-lg">⚠️</span>
          <div>
            <div className="font-semibold">Security scan failed</div>
            <div className="text-xs text-red-400/90 mt-0.5">{error}</div>
          </div>
        </div>
      )}

      {/* Initial state */}
      {!data && !isLoading && !error && (
        <div className="text-center py-12 px-4 bg-slate-950/40 rounded-xl border border-slate-800/80">
          <div className="w-16 h-16 bg-slate-800/60 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl">
            🔒
          </div>
          <h3 className="text-base font-semibold text-slate-200">
            Ready for Static Security Audit
          </h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto mt-1 mb-6">
            RepoPilot will clone the repository into an isolated sandbox and evaluate AST rules
            to identify common vulnerabilities, unredacted tokens, and risky coding anti-patterns.
          </p>
          <button
            onClick={handleRunScan}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors inline-flex items-center gap-2"
          >
            <span>🚀</span>
            Start Security Analysis
          </button>
        </div>
      )}

      {/* Loading state */}
      {isLoading && !data && (
        <div className="py-16 text-center space-y-4">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-slate-700 border-t-red-500"></div>
          <div className="text-slate-300 font-medium">Scanning Codebase for Security Risks...</div>
          <div className="text-xs text-slate-500">
            Checking AST trees for eval/exec, command injection, hardcoded credentials, and TLS configs
          </div>
        </div>
      )}

      {/* Main Results View */}
      {data && (
        <div className="space-y-6">
          {/* Human Review Disclaimer Banner */}
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg flex items-center gap-3 text-xs text-amber-300">
            <span className="text-base">⚠️</span>
            <div>
              <span className="font-semibold">Human Review Notice:</span> Static security analysis identifies
              code patterns for developer inspection. Findings represent potential risks and review items,
              not confirmed exploitable vulnerabilities.
            </div>
          </div>

          {/* Metric Overview Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-lg">
              <div className="text-xs font-medium text-slate-400">Total Findings</div>
              <div className="text-2xl font-bold text-slate-100 mt-1">
                {data.summary.total}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                {data.analysis.files_analyzed} files scanned
              </div>
            </div>

            <div className="bg-slate-950/60 border border-red-500/20 p-4 rounded-lg">
              <div className="text-xs font-medium text-red-400">Critical Severity</div>
              <div className="text-2xl font-bold text-red-400 mt-1">
                {data.summary.critical}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">Known live tokens / RCE</div>
            </div>

            <div className="bg-slate-950/60 border border-orange-500/20 p-4 rounded-lg">
              <div className="text-xs font-medium text-orange-400">High Severity</div>
              <div className="text-2xl font-bold text-orange-400 mt-1">
                {data.summary.high}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">Shell / SQL / Deserialization</div>
            </div>

            <div className="bg-slate-950/60 border border-amber-500/20 p-4 rounded-lg">
              <div className="text-xs font-medium text-amber-400">Medium Severity</div>
              <div className="text-2xl font-bold text-amber-400 mt-1">
                {data.summary.medium}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">Weak crypto / Static shell</div>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-lg col-span-2 md:col-span-1">
              <div className="text-xs font-medium text-blue-400">Low / Informational</div>
              <div className="text-2xl font-bold text-blue-400 mt-1">
                {data.summary.low + data.summary.informational}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">Error handling / Checksums</div>
            </div>
          </div>

          {/* Executive Summary Card */}
          {data.llm_summary && (
            <div className="p-4 bg-slate-950/50 border border-slate-800 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm">📋</span>
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Security Posture Summary
                </h4>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
                {data.llm_summary}
              </p>
            </div>
          )}

          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
            {/* Severity Filters */}
            <div className="flex flex-wrap items-center gap-1.5">
              {[
                { id: "all", label: `All (${data.summary.total})` },
                { id: "critical", label: `Critical (${data.summary.critical})` },
                { id: "high", label: `High (${data.summary.high})` },
                { id: "medium", label: `Medium (${data.summary.medium})` },
                { id: "low", label: `Low (${data.summary.low})` },
              ].map((pill) => (
                <button
                  key={pill.id}
                  onClick={() => setSelectedSeverity(pill.id)}
                  className={`text-xs px-2.5 py-1 rounded-full font-medium transition-all ${
                    selectedSeverity === pill.id
                      ? "bg-slate-100 text-slate-900"
                      : "bg-slate-800/80 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {pill.label}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative">
              <input
                type="text"
                placeholder="Search findings, files, CWE..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:border-slate-700 w-full sm:w-64"
              />
              <span className="absolute left-2.5 top-2 text-slate-500 text-xs">🔍</span>
            </div>
          </div>

          {/* Category Filter Pills */}
          {Object.keys(data.category_summary).length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
              <span className="text-slate-500">Category:</span>
              <button
                onClick={() => setSelectedCategory("all")}
                className={`px-2 py-0.5 rounded text-[11px] ${
                  selectedCategory === "all"
                    ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/40"
                    : "bg-slate-800/40 text-slate-400 hover:text-slate-200"
                }`}
              >
                All
              </button>
              {Object.entries(data.category_summary).map(([cat, count]) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-2 py-0.5 rounded text-[11px] ${
                    selectedCategory === cat
                      ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/40"
                      : "bg-slate-800/40 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {cat.replace("_", " ")} ({count})
                </button>
              ))}
            </div>
          )}

          {/* Findings List */}
          {filteredFindings.length === 0 ? (
            <div className="text-center py-12 bg-slate-950/40 rounded-lg border border-slate-800/80">
              <div className="text-3xl mb-2">🎉</div>
              <div className="text-sm font-semibold text-slate-200">
                No matching findings
              </div>
              <div className="text-xs text-slate-400 mt-1">
                {data.summary.total === 0
                  ? "Zero security anti-patterns or hardcoded credential indicators were detected in this repository."
                  : "No findings matched your active filters or search terms."}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredFindings.map((finding: SecurityFinding) => {
                const isExpanded = expandedFindingId === finding.finding_id;

                return (
                  <div
                    key={finding.finding_id}
                    className="bg-slate-950/70 border border-slate-800 rounded-lg p-4 transition-all hover:border-slate-700/80"
                  >
                    {/* Header Row */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center flex-wrap gap-2">
                        <span
                          className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${getSeverityBadge(
                            finding.severity
                          )}`}
                        >
                          {finding.severity}
                        </span>

                        <span
                          className={`text-[10px] uppercase px-2 py-0.5 rounded-full border ${getConfidenceBadge(
                            finding.confidence
                          )}`}
                        >
                          {finding.confidence} Conf.
                        </span>

                        {finding.cwe_id && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                            {finding.cwe_id}
                          </span>
                        )}

                        <span className="text-xs font-semibold text-slate-200">
                          {finding.title}
                        </span>
                      </div>

                      <div className="text-xs text-slate-400 font-mono flex items-center gap-1.5">
                        <span>📄 {finding.file_path}:{finding.start_line}</span>
                        {finding.entity_name && (
                          <span className="text-slate-500">({finding.entity_name})</span>
                        )}
                      </div>
                    </div>

                    {/* Description */}
                    <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                      {finding.description}
                    </p>

                    {/* Evidence summary & Toggle */}
                    <div className="mt-3 flex items-center justify-between pt-2 border-t border-slate-800/80">
                      <div className="text-xs text-slate-400 flex items-center gap-1.5">
                        <span className="text-slate-500">Evidence:</span>
                        <code className="text-slate-300 bg-slate-900 px-1.5 py-0.5 rounded text-[11px]">
                          {finding.evidence_summary}
                        </code>
                      </div>

                      <button
                        onClick={() => toggleExpand(finding.finding_id)}
                        className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
                      >
                        {isExpanded ? "Hide Remediation ▲" : "View Remediation ▼"}
                      </button>
                    </div>

                    {/* Expanded Remediation Box */}
                    {isExpanded && (
                      <div className="mt-3 p-3 bg-indigo-950/20 border border-indigo-500/20 rounded-lg text-xs space-y-2">
                        <div className="font-semibold text-indigo-300 flex items-center gap-1.5">
                          <span>💡</span> Actionable Remediation Guidance
                        </div>
                        <p className="text-slate-300 leading-relaxed">
                          {finding.remediation}
                        </p>
                        <div className="text-[11px] text-slate-400 pt-1 flex items-center gap-4">
                          <span>Rule ID: <code className="text-slate-300">{finding.rule_id}</code></span>
                          <span>Category: <span className="text-slate-300 capitalize">{finding.category.replace("_", " ")}</span></span>
                        </div>
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
