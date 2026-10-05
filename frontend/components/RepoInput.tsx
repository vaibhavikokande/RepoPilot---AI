"use client";

import { useState } from "react";

export default function RepoInput() {
  const [repoUrl, setRepoUrl] = useState("");
  const [isHovered, setIsHovered] = useState(false);

  const handleAnalyze = () => {
    // Placeholder — will be connected to backend in a future phase
    if (repoUrl.trim()) {
      alert(`Repository analysis is coming soon!\n\nURL: ${repoUrl}`);
    }
  };

  return (
    <section id="repo-input" className="relative px-6 pb-16">
      <div className="max-w-2xl mx-auto">
        <label
          htmlFor="repo-url-input"
          className="block text-sm font-medium text-muted mb-3 text-center"
        >
          Repository URL
        </label>

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
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/owner/repository"
                className="w-full bg-surface border border-border rounded-lg py-3 pl-11 pr-4 text-foreground placeholder:text-muted/60 focus:outline-none focus:border-primary/50 transition-colors"
              />
            </div>

            <button
              id="analyze-button"
              onClick={handleAnalyze}
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
              className="relative px-8 py-3 rounded-lg font-semibold text-white overflow-hidden transition-all duration-300 cursor-pointer whitespace-nowrap"
              style={{
                background: isHovered
                  ? "linear-gradient(135deg, #818cf8 0%, #22d3ee 100%)"
                  : "linear-gradient(135deg, #6366f1 0%, #22d3ee 100%)",
                boxShadow: isHovered
                  ? "0 0 30px rgba(99, 102, 241, 0.4)"
                  : "0 0 20px rgba(99, 102, 241, 0.2)",
              }}
            >
              Analyze Repository
            </button>
          </div>
        </div>

        <p className="text-xs text-muted/60 text-center mt-3">
          Paste any public GitHub repository URL to get started
        </p>
      </div>
    </section>
  );
}
