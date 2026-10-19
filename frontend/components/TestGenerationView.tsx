"use client";

import { useState } from "react";
import {
  CodeFile,
  generateUnitTests,
  TestGenerationResponse,
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
              AI-Powered Unit Test Generation
            </h2>
            <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-medium">
              pytest
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Generate grounded, executable pytest unit tests with mock isolation for any Python function or method.
          </p>
        </div>
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

      {/* Results View */}
      {result && !isLoading && (
        <div className="space-y-4">
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
                  Review Required
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

            {/* Assumptions */}
            {result.assumptions.length > 0 && (
              <div className="pt-2 text-xs text-slate-400 border-t border-slate-800/60">
                <span className="text-slate-500 font-semibold">Assumptions: </span>
                {result.assumptions.join(" ")}
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

            <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed bg-slate-950/80 max-h-[450px]">
              {result.test_code}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
