"use client";

export default function Hero() {
  return (
    <section id="hero" className="relative pt-24 pb-12 px-6 text-center overflow-hidden">
      {/* Background glow orbs */}
      <div className="absolute top-20 left-1/4 w-72 h-72 bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-40 right-1/4 w-64 h-64 bg-accent/8 rounded-full blur-[100px] pointer-events-none" />

      <div className="relative z-10 max-w-4xl mx-auto">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-8 rounded-full border border-border bg-surface/80 text-sm text-muted backdrop-blur-sm">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
          </span>
          v0.1.0 — Foundation Release
        </div>

        {/* Main title */}
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight mb-6">
          <span className="gradient-text">RepoPilot</span>
          <span className="text-foreground"> AI</span>
        </h1>

        {/* Subtitle */}
        <p className="text-xl sm:text-2xl font-medium text-primary-hover mb-4">
          Autonomous AI Software Engineer
        </p>

        {/* Description */}
        <p className="text-lg text-muted max-w-2xl mx-auto leading-relaxed">
          Understand, analyze, test, debug, and improve your codebase with AI.
          Point RepoPilot at any GitHub repository and let it work.
        </p>
      </div>
    </section>
  );
}
