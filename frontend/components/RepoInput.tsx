"use client";

import { FormEvent, useState } from "react";
import { analyzeRepository, RepositoryAnalyzeResponse } from "@/lib/api";
import RepoResults from "./RepoResults";

export default function RepoInput() {
  const [repoUrl, setRepoUrl] = useState("");
  const [isHovered, setIsHovered] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RepositoryAnalyzeResponse | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = repoUrl.trim();

    if (!trimmed) {
      setError("Please enter a GitHub repository URL.");
      return;
    }

    if (!trimmed.startsWith("https://github.com/")) {
      setError("Please enter a valid GitHub HTTPS URL starting with 'https://github.com/'.");
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      const data = await analyzeRepository(trimmed);
      setResult(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to analyze repository.";
      setError(message);
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  const setExampleUrl = (example: string) => {
    setRepoUrl(example);
    setError(null);
  };

  return (
    <section id="repo-input" className="relative px-6 pb-16">
      <div className="max-w-3xl mx-auto">
        <label
          htmlFor="repo-url-input"
          className="block text-sm font-medium text-muted mb-3 text-center"
        >
          Repository URL
        </label>

        <form onSubmit={handleSubmit}>
          <div className="gradient-border p-1">
            <div className="flex flex-col sm:flex-row gap-3 p-3 bg-card rounded-[10px]">
              <div className="relative flex-1">
                <svg
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m9.924-4.253a4.5 4.5 0 00-1.242-7.244l-4.5-4.5a4.5 4.5 0 00-6.364 6.364L4.34 8.684"
                    transform="translate(0, 2)"
                  />
                </svg>
                <input
                  id="repo-url-input"
                  type="url"
                  value={repoUrl}
                  onChange={(e) => {
                    setRepoUrl(e.target.value);
                    if (error) setError(null);
                  }}
                  disabled={isLoading}
                  placeholder="https://github.com/owner/repository"
                  className="w-full bg-surface border border-border rounded-lg py-3 pl-11 pr-4 text-foreground placeholder:text-muted/60 focus:outline-none focus:border-primary/50 transition-colors disabled:opacity-60"
                />
              </div>

              <button
                id="analyze-button"
                type="submit"
                disabled={isLoading}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
                className="relative px-8 py-3 rounded-lg font-semibold text-white overflow-hidden transition-all duration-300 cursor-pointer whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-70 flex items-center justify-center gap-2"
                style={{
                  background: isHovered && !isLoading
                    ? "linear-gradient(135deg, #818cf8 0%, #22d3ee 100%)"
                    : "linear-gradient(135deg, #6366f1 0%, #22d3ee 100%)",
                  boxShadow: isHovered && !isLoading
                    ? "0 0 30px rgba(99, 102, 241, 0.4)"
                    : "0 0 20px rgba(99, 102, 241, 0.2)",
                }}
              >
                {isLoading ? (
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
                    Analyzing...
                  </>
                ) : (
                  "Analyze Repository"
                )}
              </button>
            </div>
          </div>
        </form>

        {/* Quick try examples */}
        {!result && (
          <div className="flex items-center justify-center gap-2 mt-3 text-xs text-muted">
            <span>Try example:</span>
            <button
              type="button"
              onClick={() => setExampleUrl("https://github.com/octocat/Hello-World")}
              className="text-primary-hover hover:underline cursor-pointer"
            >
              octocat/Hello-World
            </button>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="mt-4 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-200 text-sm flex items-start gap-3">
            <svg
              className="w-5 h-5 text-red-400 shrink-0 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="flex-1">
              <p className="font-medium text-red-300">Analysis Error</p>
              <p className="mt-0.5 text-xs text-red-200/90 leading-relaxed">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-red-200 text-xs cursor-pointer ml-auto"
            >
              ✕
            </button>
          </div>
        )}

        {/* Analysis Results */}
        {result && <RepoResults data={result} onReset={handleReset} />}
      </div>
    </section>
  );
}
