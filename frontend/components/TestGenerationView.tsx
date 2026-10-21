"use client";

import { useEffect, useState } from "react";
import {
  CodeFile,
  generateUnitTests,
  getSandboxStatus,
  runTests,
  SandboxStatus,
  TestGenerationResponse,
  TestRunResponse,
} from "@/lib/api";

interface TestGenerationViewProps {
  repositoryUrl: string;
  codeFiles?: CodeFile[];
}

export default function TestGenerationView({
  repositoryUrl,
  codeFiles = [],
}: TestGenerationViewProps) {
  // Filter python files from code intelligence
  const pythonFiles = codeFiles.filter(
    (f) => f.path.endsWith(".py") || f.language.toLowerCase() === "python"
  );

  const [selectedFile, setSelectedFile] = useState<string>(
    pythonFiles[0]?.path || ""
  );
  const [selectedEntity, setSelectedEntity] = useState<string>("");
  const [customFile, setCustomFile] = useState<string>("");
  const [customEntity, setCustomEntity] = useState<string>("");

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TestGenerationResponse | null>(null);
  const [copied, setCopied] = useState(false);

  // Sandbox & Execution state
  const [sandboxStatus, setSandboxStatus] = useState<SandboxStatus | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [testRunResult, setTestRunResult] = useState<TestRunResponse | null>(null);
  const [enableCoverage, setEnableCoverage] = useState(true);
  const [allowMockExecution, setAllowMockExecution] = useState(true);
  const [showLogs, setShowLogs] = useState(false);

  // Fetch sandbox status on mount
  useEffect(() => {
    getSandboxStatus()
      .then((status) => {
        setSandboxStatus(status);
        if (!status.available) {
          setAllowMockExecution(true);
        }
      })
      .catch(() => {
        setSandboxStatus({
          available: false,
          sandbox_type: "docker",
          configured: false,
          message: "Unable to connect to sandbox diagnostic service.",
          requirements: ["Docker engine required for container isolation"],
        });
        setAllowMockExecution(true);
      });
  }, []);

  // Available entities in the selected file
  const currentFileModel = pythonFiles.find((f) => f.path === selectedFile);
  const availableEntities = currentFileModel
    ? currentFileModel.entities.filter(
        (e) => e.type === "function" || e.type === "method"
      )
    : [];

  const effectiveFile = selectedFile || customFile;
  const effectiveEntity = selectedEntity || customEntity;

  const handleGenerate = async () => {
    if (!effectiveFile.trim() || !effectiveEntity.trim()) {
      setError("Please specify both a file path and a function or method name.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setCopied(false);
    setTestRunResult(null);
    setExecutionError(null);

    try {
      const response = await generateUnitTests({
        repository_url: repositoryUrl,
        file_path: effectiveFile.trim(),
        entity_name: effectiveEntity.trim(),
      });
      setResult(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to generate tests.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunTests = async () => {
    if (!result?.test_code && !effectiveFile) return;

    setIsExecuting(true);
    setExecutionError(null);
    setTestRunResult(null);

    try {
      const testFileRel = result?.file_name
        ? `tests/${result.file_name}`
        : `tests/test_${effectiveEntity}.py`;

      const response = await runTests({
        repository_url: repositoryUrl,
        test_file: testFileRel,
        test_code: result?.test_code || null,
        target_file: effectiveFile || null,
        coverage: enableCoverage,
        timeout_seconds: 30,
        allow_mock: allowMockExecution || !sandboxStatus?.available,
      });

      setTestRunResult(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to run tests.";
      setExecutionError(msg);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleCopyCode = async () => {
    if (!result?.test_code) return;
    try {
      await navigator.clipboard.writeText(result.test_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard fallback
    }
  };

  const handleDownload = () => {
    if (!result?.test_code) return;
    const blob = new Blob([result.test_code], { type: "text/x-python" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = result.file_name || `test_${effectiveEntity}.py`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🧪</span>
            <h2 className="text-xl font-bold text-slate-100">
              AI-Powered Unit Test Generation & Safe Execution
            </h2>
            <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-medium">
              pytest + coverage
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Generate grounded pytest unit tests, review code, and execute safely in an isolated sandbox with coverage analysis.
          </p>
        </div>

        {/* Sandbox Diagnostic Pill */}
        {sandboxStatus && (
          <div className="flex items-center gap-2 self-start md:self-auto">
            {sandboxStatus.available ? (
              <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                Docker Sandbox Ready
              </span>
            ) : (
              <span className="text-xs px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 font-medium flex items-center gap-1.5" title={sandboxStatus.message}>
                <span>🔒</span>
                Container Sandbox Offline (Simulation Mode)
              </span>
            )}
          </div>
        )}
      </div>

      {/* Target Selection Form */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-4 space-y-4">
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Target Function Selection
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* File Selector */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">
              Select Python Source File
            </label>
            {pythonFiles.length > 0 ? (
              <select
                value={selectedFile}
                onChange={(e) => {
                  setSelectedFile(e.target.value);
                  setSelectedEntity("");
                }}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                {pythonFiles.map((f) => (
                  <option key={f.path} value={f.path}>
                    {f.path} ({f.entities.length} entities)
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                placeholder="e.g. app/services/user_service.py"
                value={customFile}
                onChange={(e) => setCustomFile(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              />
            )}
          </div>

          {/* Function Selector */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">
              Select Function or Method
            </label>
            {availableEntities.length > 0 ? (
              <select
                value={selectedEntity}
                onChange={(e) => setSelectedEntity(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              >
                <option value="">-- Choose Function / Method --</option>
                {availableEntities.map((ent) => (
                  <option key={`${ent.file_path}-${ent.name}`} value={ent.name}>
                    {ent.parent ? `${ent.parent}.${ent.name}` : ent.name} ({ent.type}, lines {ent.start_line}-{ent.end_line})
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                placeholder="e.g. validate_email"
                value={customEntity}
                onChange={(e) => setSelectedEntity(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              />
            )}
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={handleGenerate}
            disabled={isLoading || (!selectedEntity && !customEntity)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:from-slate-700 disabled:to-slate-700 text-white font-medium rounded-lg text-sm transition-all shadow-lg shadow-emerald-900/20 disabled:cursor-not-allowed"
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
                Generating pytest suite...
              </>
            ) : (
              <>
                <span>⚡</span>
                Generate Unit Tests
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
            <div className="font-semibold">Test Generation Failed</div>
            <div className="text-xs text-red-400/90 mt-0.5">{error}</div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="py-12 text-center space-y-3">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-700 border-t-emerald-500"></div>
          <div className="text-slate-300 text-sm font-medium">
            Extracting AST context & synthesizing tests...
          </div>
          <div className="text-xs text-slate-500">
            Grounding test inputs, mocking dependencies, and validating syntax
          </div>
        </div>
      )}

      {/* Generated Results & Test Runner Workflow */}
      {result && !isLoading && (
        <div className="space-y-6">
          {/* Metadata Card */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-mono font-bold text-slate-100 bg-slate-800 px-2.5 py-1 rounded">
                  {result.target.entity_name}()
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  {result.target.file_path}:{result.target.start_line}-{result.target.end_line}
                </span>
                {result.target.parent_class && (
                  <span className="text-[11px] text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 px-2 py-0.5 rounded">
                    class {result.target.parent_class}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                {result.validation.syntax_valid ? (
                  <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded font-medium flex items-center gap-1">
                    ✓ Syntax Valid
                  </span>
                ) : (
                  <span className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 px-2 py-0.5 rounded font-medium flex items-center gap-1">
                    ✗ Syntax Invalid
                  </span>
                )}

                <span className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded font-medium">
                  Review Required Before Execution
                </span>
              </div>
            </div>

            {/* Test Cases Summary */}
            {result.test_cases.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
                  Generated Test Cases ({result.test_cases.length})
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {result.test_cases.map((tc, idx) => (
                    <div
                      key={idx}
                      className="bg-slate-900/80 border border-slate-800/80 rounded p-2.5 text-xs"
                    >
                      <div className="font-mono text-emerald-400 font-semibold">
                        {tc.name}
                      </div>
                      <div className="text-slate-400 mt-0.5">{tc.purpose}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Test Code Viewer */}
          <div className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-slate-900/80 border-b border-slate-800 text-xs">
              <span className="font-mono text-slate-400">
                📁 {result.file_name}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyCode}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs transition-colors font-medium flex items-center gap-1"
                >
                  {copied ? "✓ Copied" : "📋 Copy Code"}
                </button>
                <button
                  onClick={handleDownload}
                  className="px-2.5 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded text-xs transition-colors font-medium flex items-center gap-1"
                >
                  ⬇ Download .py
                </button>
              </div>
            </div>

            <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed bg-slate-950/80 max-h-[400px]">
              {result.test_code}
            </pre>
          </div>

          {/* =============================================================== */}
          {/* DAY 10: Safe Test Execution & Coverage Section                   */}
          {/* =============================================================== */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg">🛡️</span>
                  <h3 className="text-base font-bold text-slate-100">
                    Safe Test Execution & Coverage Runner
                  </h3>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Execute the reviewed pytest suite inside an isolated disposable environment. Zero host secrets, network disabled.
                </p>
              </div>

              {/* Execution Options */}
              <div className="flex items-center gap-4 text-xs text-slate-300 flex-wrap">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enableCoverage}
                    onChange={(e) => setEnableCoverage(e.target.checked)}
                    className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                  />
                  <span>Analyze Statement Coverage</span>
                </label>

                {!sandboxStatus?.available && (
                  <label className="flex items-center gap-1.5 cursor-pointer text-amber-400">
                    <input
                      type="checkbox"
                      checked={allowMockExecution}
                      onChange={(e) => setAllowMockExecution(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0"
                    />
                    <span>Allow Simulation (Mock Sandbox)</span>
                  </label>
                )}
              </div>
            </div>

            {/* Sandbox Offline Warning Banner */}
            {!sandboxStatus?.available && !allowMockExecution && (
              <div className="p-3.5 bg-amber-950/30 border border-amber-500/30 rounded-lg text-xs text-amber-200 space-y-1">
                <div className="font-semibold flex items-center gap-1.5 text-amber-300">
                  <span>🔒</span>
                  <span>Container Execution Unavailable</span>
                </div>
                <p className="text-amber-300/80">
                  Docker container runtime is not detected on the server. Executing untrusted code directly on the host is disabled to prevent security vulnerabilities. Check &quot;Allow Simulation&quot; to test the execution flow and report parsing.
                </p>
              </div>
            )}

            {/* Run Button Action */}
            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-slate-500">
                Target: <span className="font-mono text-slate-400">tests/{result.file_name}</span>
              </span>

              <button
                onClick={handleRunTests}
                disabled={isExecuting || (!sandboxStatus?.available && !allowMockExecution)}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-semibold rounded-lg text-xs transition-all shadow-lg shadow-indigo-950/40 disabled:cursor-not-allowed cursor-pointer"
              >
                {isExecuting ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
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
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    <span>Running in isolated sandbox...</span>
                  </>
                ) : (
                  <>
                    <span>▶</span>
                    <span>Run Approved Tests</span>
                  </>
                )}
              </button>
            </div>

            {/* Execution Error */}
            {executionError && (
              <div className="p-3.5 bg-red-900/20 border border-red-500/30 rounded-lg text-xs text-red-300 flex items-start gap-2.5">
                <span className="text-red-400">⚠️</span>
                <div>
                  <div className="font-semibold text-red-200">Execution Error</div>
                  <div className="text-red-300/80 mt-0.5">{executionError}</div>
                </div>
              </div>
            )}

            {/* Test Run Report Dashboard */}
            {testRunResult && (
              <div className="space-y-4 pt-4 border-t border-slate-800">
                {/* Status Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/90 border border-slate-800 rounded-lg p-3.5">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span
                      className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                        testRunResult.status === "completed" && testRunResult.summary.failed === 0 && testRunResult.summary.errors === 0
                          ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                          : testRunResult.status === "completed"
                          ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                          : "bg-red-500/15 text-red-400 border-red-500/30"
                      }`}
                    >
                      {testRunResult.status === "completed" && testRunResult.summary.failed === 0 && testRunResult.summary.errors === 0
                        ? "✓ All Tests Passed"
                        : testRunResult.status === "completed"
                        ? "⚠️ Tests Completed with Failures"
                        : `✗ Execution ${testRunResult.status.toUpperCase()}`}
                    </span>

                    <span className="text-xs font-mono text-slate-400">
                      Duration: {testRunResult.duration_seconds}s
                    </span>

                    {testRunResult.exit_code !== null && testRunResult.exit_code !== undefined && (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        Exit code: {testRunResult.exit_code}
                      </span>
                    )}
                  </div>

                  {/* Execution Type Pill */}
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                      Run ID: {testRunResult.run_id.slice(0, 8)}
                    </span>
                    {testRunResult.execution_type === "mocked" && (
                      <span className="text-[11px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 font-medium">
                        Simulated Mock
                      </span>
                    )}
                  </div>
                </div>

                {/* Warnings / Notices */}
                {testRunResult.warnings.length > 0 && (
                  <div className="space-y-1">
                    {testRunResult.warnings.map((w, idx) => (
                      <div
                        key={idx}
                        className="text-xs px-3 py-2 rounded bg-amber-950/20 border border-amber-500/20 text-amber-300 flex items-center gap-2"
                      >
                        <span>ℹ️</span>
                        <span>{w}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Summary Metric Counters */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
                    <div className="text-[11px] text-slate-400 font-medium">Total Tests</div>
                    <div className="text-xl font-bold text-slate-100 mt-1">
                      {testRunResult.summary.total}
                    </div>
                  </div>

                  <div className="bg-emerald-950/20 border border-emerald-500/20 rounded-lg p-3 text-center">
                    <div className="text-[11px] text-emerald-400 font-medium">Passed</div>
                    <div className="text-xl font-bold text-emerald-300 mt-1">
                      {testRunResult.summary.passed}
                    </div>
                  </div>

                  <div className="bg-red-950/20 border border-red-500/20 rounded-lg p-3 text-center">
                    <div className="text-[11px] text-red-400 font-medium">Failed</div>
                    <div className="text-xl font-bold text-red-300 mt-1">
                      {testRunResult.summary.failed}
                    </div>
                  </div>

                  <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
                    <div className="text-[11px] text-slate-400 font-medium">Skipped</div>
                    <div className="text-xl font-bold text-slate-300 mt-1">
                      {testRunResult.summary.skipped}
                    </div>
                  </div>

                  <div className="bg-purple-950/20 border border-purple-500/20 rounded-lg p-3 text-center col-span-2 sm:col-span-1">
                    <div className="text-[11px] text-purple-400 font-medium">Errors</div>
                    <div className="text-xl font-bold text-purple-300 mt-1">
                      {testRunResult.summary.errors}
                    </div>
                  </div>
                </div>

                {/* Individual Test Results List */}
                {testRunResult.test_results.length > 0 && (
                  <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3.5 space-y-2">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Individual Test Cases
                    </h4>
                    <div className="space-y-1.5 max-h-60 overflow-y-auto">
                      {testRunResult.test_results.map((tr, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 rounded bg-slate-950/60 border border-slate-800/80 text-xs font-mono"
                        >
                          <span className="text-slate-200">{tr.name}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-semibold uppercase ${
                              tr.status === "passed"
                                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                                : tr.status === "failed"
                                ? "bg-red-500/15 text-red-400 border border-red-500/30"
                                : "bg-slate-800 text-slate-400 border border-slate-700"
                            }`}
                          >
                            {tr.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Coverage Analysis Card */}
                {testRunResult.coverage && (
                  <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-base">📊</span>
                        <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
                          Statement Coverage Analysis
                        </h4>
                      </div>

                      {testRunResult.coverage.is_available ? (
                        <span className="text-sm font-bold font-mono text-indigo-400">
                          {testRunResult.coverage.coverage_percent}% Covered
                        </span>
                      ) : (
                        <span className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded">
                          Coverage Unavailable
                        </span>
                      )}
                    </div>

                    {testRunResult.coverage.is_available ? (
                      <div className="space-y-3">
                        {/* Progress Bar */}
                        <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                          <div
                            className={`h-full transition-all duration-500 ${
                              testRunResult.coverage.coverage_percent >= 80
                                ? "bg-emerald-500"
                                : testRunResult.coverage.coverage_percent >= 50
                                ? "bg-amber-500"
                                : "bg-red-500"
                            }`}
                            style={{ width: `${Math.max(testRunResult.coverage.coverage_percent, 2)}%` }}
                          />
                        </div>

                        {/* Totals */}
                        <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                          <span>
                            Total: <strong className="text-slate-200">{testRunResult.coverage.total_statements}</strong> statements
                          </span>
                          <span>
                            Covered: <strong className="text-emerald-400">{testRunResult.coverage.covered_statements}</strong>
                          </span>
                          <span>
                            Missing: <strong className="text-red-400">{testRunResult.coverage.missing_statements}</strong>
                          </span>
                        </div>

                        {/* File Breakdown */}
                        {testRunResult.coverage.files.length > 0 && (
                          <div className="space-y-2 pt-2 border-t border-slate-800">
                            {testRunResult.coverage.files.map((fc, idx) => (
                              <div
                                key={idx}
                                className="bg-slate-950/80 border border-slate-800/80 rounded p-2.5 text-xs space-y-1.5"
                              >
                                <div className="flex items-center justify-between font-mono">
                                  <span className="text-slate-200 font-medium truncate max-w-[70%]">
                                    {fc.file_path}
                                  </span>
                                  <span className="text-indigo-400 font-bold">
                                    {fc.coverage_percent}%
                                  </span>
                                </div>

                                {fc.missing_lines.length > 0 && (
                                  <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5 flex-wrap">
                                    <span className="text-red-400 font-semibold">Uncovered lines:</span>
                                    <span className="bg-red-950/40 text-red-300 border border-red-500/20 px-1.5 py-0.5 rounded">
                                      {fc.missing_lines.slice(0, 15).join(", ")}
                                      {fc.missing_lines.length > 15 ? ` (+${fc.missing_lines.length - 15} more)` : ""}
                                    </span>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400">
                        {testRunResult.coverage.reason || "Coverage metrics could not be collected for this execution."}
                      </p>
                    )}
                  </div>
                )}

                {/* Console Output Viewer */}
                <div className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden">
                  <div
                    onClick={() => setShowLogs(!showLogs)}
                    className="flex items-center justify-between px-3.5 py-2 bg-slate-900/80 border-b border-slate-800 text-xs cursor-pointer hover:bg-slate-850"
                  >
                    <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                      <span>💻</span>
                      <span>Runner Console Output ({testRunResult.stdout ? "stdout" : "empty"})</span>
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {showLogs ? "Hide Logs ▲" : "View Logs ▼"}
                    </span>
                  </div>

                  {showLogs && (
                    <div className="p-3.5 text-xs font-mono text-slate-300 space-y-2 bg-slate-950 max-h-72 overflow-y-auto">
                      {testRunResult.stdout && (
                        <div>
                          <div className="text-[11px] text-slate-500 mb-1 font-semibold">STDOUT:</div>
                          <pre className="whitespace-pre-wrap leading-relaxed text-slate-300">
                            {testRunResult.stdout}
                          </pre>
                        </div>
                      )}

                      {testRunResult.stderr && (
                        <div className="pt-2 border-t border-slate-800/80 text-red-300">
                          <div className="text-[11px] text-red-400 mb-1 font-semibold">STDERR:</div>
                          <pre className="whitespace-pre-wrap leading-relaxed">
                            {testRunResult.stderr}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
