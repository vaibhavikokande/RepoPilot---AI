"use client";

import { useState } from "react";
import { CodeAnalysisResponse, CodeStructureNode } from "@/lib/api";

interface CodeIntelligenceViewProps {
  data: CodeAnalysisResponse;
}

function StructureTreeNode({
  node,
  depth = 0,
}: {
  node: CodeStructureNode;
  depth?: number;
}) {
  const isExpandable = Boolean(node.children && node.children.length > 0);
  const [isOpen, setIsOpen] = useState(depth < 2);

  const getIcon = (type: string) => {
    switch (type) {
      case "directory":
        return isOpen ? "📂" : "📁";
      case "file":
        return "📄";
      case "class":
        return "🏛️";
      case "method":
        return "🔹";
      case "function":
        return "⚡";
      case "interface":
        return "🧩";
      case "type_alias":
        return "🏷️";
      default:
        return "•";
    }
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
      case "type_alias":
        return "bg-purple-500/15 text-purple-300 border-purple-500/30";
      default:
        return "bg-surface text-muted border-border";
    }
  };

  return (
    <div className="select-none text-xs font-mono">
      <div
        onClick={() => isExpandable && setIsOpen(!isOpen)}
        className={`flex items-center gap-1.5 py-1 px-2 rounded hover:bg-surface/80 transition-colors ${
          isExpandable ? "cursor-pointer" : "cursor-default"
        } ${depth === 0 ? "font-semibold text-foreground" : "text-muted hover:text-foreground"}`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        <span className="text-sm shrink-0">{getIcon(node.type)}</span>
        <span
          className={
            node.type === "directory"
              ? "text-primary-hover font-semibold"
              : node.type === "class"
              ? "text-amber-200 font-semibold"
              : node.type === "function"
              ? "text-emerald-200"
              : node.type === "file"
              ? "text-foreground font-medium"
              : "text-foreground"
          }
        >
          {node.name}
        </span>

        {node.type !== "directory" && node.type !== "file" && (
          <span
            className={`ml-1.5 text-[10px] px-1.5 py-0.2 rounded border ${getTypeBadgeClass(
              node.type
            )}`}
          >
            {node.type}
          </span>
        )}

        {node.line_info && (
          <span className="ml-auto text-[10px] text-muted/60 font-mono">
            {node.line_info}
          </span>
        )}
      </div>

      {isExpandable && isOpen && node.children && (
        <div className="border-l border-border/40 ml-4">
          {node.children.map((child, idx) => (
            <StructureTreeNode
              key={`${child.path}-${child.name}-${idx}`}
              node={child}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function CodeIntelligenceView({ data }: CodeIntelligenceViewProps) {
  const { summary, codebase_tree, dependencies, errors } = data;
  const [activeTab, setActiveTab] = useState<"structure" | "dependencies">("structure");

  const internalDeps = dependencies.filter((d) => d.is_internal);
  const externalDeps = dependencies.filter((d) => !d.is_internal);

  return (
    <div className="mt-8 pt-8 border-t border-border">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🧠</span>
            <h3 className="text-xl font-bold text-foreground">
              Code Intelligence
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary-hover border border-primary/20 font-medium">
              AST Parsed
            </span>
          </div>
          <p className="text-xs text-muted mt-1">
            Static structural analysis, class definitions, function signatures, and dependency maps
          </p>
        </div>
      </div>

      {/* Codebase Metrics Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        <div className="bg-surface/60 border border-border rounded-lg p-3">
          <p className="text-[11px] text-muted font-medium">Files Analyzed</p>
          <p className="text-xl font-bold text-foreground mt-0.5">
            {summary.files_analyzed}
          </p>
        </div>
        <div className="bg-surface/60 border border-border rounded-lg p-3">
          <p className="text-[11px] text-muted font-medium">Classes</p>
          <p className="text-xl font-bold text-amber-400 mt-0.5">
            {summary.classes}
          </p>
        </div>
        <div className="bg-surface/60 border border-border rounded-lg p-3">
          <p className="text-[11px] text-muted font-medium">Functions</p>
          <p className="text-xl font-bold text-emerald-400 mt-0.5">
            {summary.functions}
          </p>
        </div>
        <div className="bg-surface/60 border border-border rounded-lg p-3">
          <p className="text-[11px] text-muted font-medium">Methods</p>
          <p className="text-xl font-bold text-sky-400 mt-0.5">
            {summary.methods}
          </p>
        </div>
        <div className="bg-surface/60 border border-border rounded-lg p-3">
          <p className="text-[11px] text-muted font-medium">Imports</p>
          <p className="text-xl font-bold text-purple-400 mt-0.5">
            {summary.imports}
          </p>
        </div>
        <div className="bg-surface/60 border border-border rounded-lg p-3">
          <p className="text-[11px] text-muted font-medium">Parse Errors</p>
          <p
            className={`text-xl font-bold mt-0.5 ${
              summary.files_with_errors > 0 ? "text-red-400" : "text-muted/60"
            }`}
          >
            {summary.files_with_errors}
          </p>
        </div>
      </div>

      {/* Language Breakdown */}
      {Object.keys(summary.languages).length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-6">
          <span className="text-xs text-muted font-medium mr-1">Analyzed Languages:</span>
          {Object.entries(summary.languages).map(([lang, count]) => (
            <span
              key={lang}
              className="text-xs px-2.5 py-1 rounded-md bg-surface border border-border text-foreground font-mono"
            >
              <strong className="text-primary-hover font-semibold">{lang}</strong>: {count}{" "}
              {count === 1 ? "file" : "files"}
            </span>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-border mb-4">
        <button
          onClick={() => setActiveTab("structure")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition-colors cursor-pointer ${
            activeTab === "structure"
              ? "border-primary text-primary-hover"
              : "border-transparent text-muted hover:text-foreground"
          }`}
        >
          Code Structure Map ({summary.classes + summary.functions + summary.methods} entities)
        </button>
        <button
          onClick={() => setActiveTab("dependencies")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition-colors cursor-pointer ${
            activeTab === "dependencies"
              ? "border-primary text-primary-hover"
              : "border-transparent text-muted hover:text-foreground"
          }`}
        >
          Dependencies ({dependencies.length})
        </button>
      </div>

      {/* Tab 1: Structure Map */}
      {activeTab === "structure" && (
        <div className="bg-surface/40 border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3 text-xs text-muted">
            <span>Expand folders and files to inspect classes, methods, and functions with line numbers</span>
            <span className="font-mono text-[11px]">📁 directories • 📄 files • 🏛️ classes • ⚡ functions</span>
          </div>

          <div className="max-h-96 overflow-y-auto pr-1 bg-card/60 rounded border border-border/60 p-2">
            {codebase_tree && codebase_tree.length > 0 ? (
              codebase_tree.map((node, idx) => (
                <StructureTreeNode
                  key={`${node.path}-${node.name}-${idx}`}
                  node={node}
                  depth={0}
                />
              ))
            ) : (
              <p className="text-xs text-muted p-4 text-center">
                No supported code files (Python, JavaScript, TypeScript) found in this repository.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Dependencies */}
      {activeTab === "dependencies" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Internal Dependencies */}
          <div className="bg-surface/40 border border-border rounded-lg p-4">
            <h4 className="text-xs font-semibold text-foreground mb-3 flex items-center justify-between">
              <span>Internal Dependencies</span>
              <span className="text-[11px] text-primary-hover font-mono">
                {internalDeps.length} intra-repo links
              </span>
            </h4>
            <div className="max-h-80 overflow-y-auto space-y-2 pr-1">
              {internalDeps.length > 0 ? (
                internalDeps.map((dep, idx) => (
                  <div
                    key={`${dep.source_file}-${dep.target_module}-${idx}`}
                    className="p-2.5 rounded bg-card/70 border border-border/60 text-xs font-mono"
                  >
                    <div className="text-foreground truncate">
                      📄 {dep.source_file}
                    </div>
                    <div className="text-primary-hover ml-3 mt-1 flex items-center gap-1.5">
                      <span>↳ imports</span>
                      <span className="bg-primary/10 px-1.5 py-0.5 rounded border border-primary/20 text-[11px]">
                        {dep.resolved_target_file || dep.target_module}
                      </span>
                    </div>
                    {dep.imported_symbols.length > 0 && (
                      <div className="text-[10px] text-muted mt-1 ml-6">
                        symbols: {dep.imported_symbols.join(", ")}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted p-3">No intra-repository imports detected.</p>
              )}
            </div>
          </div>

          {/* External Dependencies */}
          <div className="bg-surface/40 border border-border rounded-lg p-4">
            <h4 className="text-xs font-semibold text-foreground mb-3 flex items-center justify-between">
              <span>External Packages & Modules</span>
              <span className="text-[11px] text-muted font-mono">
                {externalDeps.length} imports
              </span>
            </h4>
            <div className="max-h-80 overflow-y-auto space-y-2 pr-1">
              {externalDeps.length > 0 ? (
                externalDeps.map((dep, idx) => (
                  <div
                    key={`${dep.source_file}-${dep.target_module}-${idx}`}
                    className="p-2 rounded bg-card/70 border border-border/60 text-xs font-mono flex items-center justify-between"
                  >
                    <span className="text-foreground font-semibold">
                      📦 {dep.target_module}
                    </span>
                    <span className="text-[10px] text-muted truncate max-w-[150px]">
                      in {dep.source_file}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted p-3">No external packages detected.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Parse Errors (if any) */}
      {errors && errors.length > 0 && (
        <div className="mt-4 p-4 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-200 text-xs">
          <p className="font-semibold mb-1">
            ⚠️ {errors.length} file{errors.length === 1 ? "" : "s"} skipped due to syntax/encoding issues:
          </p>
          <ul className="list-disc list-inside space-y-0.5 font-mono text-[11px]">
            {errors.map((err, idx) => (
              <li key={`${err.path}-${idx}`}>
                {err.path} ({err.language}) — {err.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
