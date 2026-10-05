import Hero from "@/components/Hero";
import RepoInput from "@/components/RepoInput";
import FeatureGrid from "@/components/FeatureGrid";

export default function Home() {
  return (
    <div className="flex flex-col flex-1 grid-pattern">
      {/* Navigation */}
      <nav id="navbar" className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-lg">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold gradient-text">RepoPilot</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary-hover font-medium border border-primary/20">
              AI
            </span>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              GitHub
            </a>
            <a
              href="/docs"
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              Docs
            </a>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1">
        <Hero />
        <RepoInput />
        <FeatureGrid />
      </main>

      {/* Footer */}
      <footer id="footer" className="border-t border-border py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted">
            © 2025 RepoPilot AI — Built with FastAPI & Next.js
          </p>
          <p className="text-xs text-muted/60">
            Developed incrementally as a production portfolio project
          </p>
        </div>
      </footer>
    </div>
  );
}
