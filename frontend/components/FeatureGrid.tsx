"use client";

interface Feature {
  icon: string;
  title: string;
  description: string;
  status: "planned" | "coming-soon";
}

const features: Feature[] = [
  {
    icon: "🧠",
    title: "Codebase Understanding",
    description: "Deep semantic analysis of repository structure, dependencies, and architecture patterns.",
    status: "planned",
  },
  {
    icon: "🔍",
    title: "AI Code Analysis",
    description: "Intelligent code review powered by LLMs with context-aware insights and quality scoring.",
    status: "planned",
  },
  {
    icon: "🧪",
    title: "Test Generation",
    description: "Automated test suite creation with comprehensive coverage for functions and modules.",
    status: "planned",
  },
  {
    icon: "🐛",
    title: "Bug Detection",
    description: "Proactive identification of potential bugs, anti-patterns, and security vulnerabilities.",
    status: "planned",
  },
  {
    icon: "📝",
    title: "Documentation",
    description: "Auto-generate and maintain up-to-date documentation from your source code.",
    status: "planned",
  },
  {
    icon: "🏥",
    title: "Repository Health",
    description: "Comprehensive health scoring with actionable recommendations for improvement.",
    status: "planned",
  },
];

function StatusBadge({ status }: { status: Feature["status"] }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary-hover border border-primary/20">
      <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
      {status === "coming-soon" ? "Coming Soon" : "Planned"}
    </span>
  );
}

export default function FeatureGrid() {
  return (
    <section id="features" className="px-6 pb-24">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl font-bold text-center mb-2 text-foreground">
          AI-Powered Capabilities
        </h2>
        <p className="text-muted text-center mb-12 text-sm">
          Intelligent agents working together to improve your codebase
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="card-glow group relative bg-card border border-border rounded-xl p-6 hover:bg-card-hover hover:border-primary/20 transition-all duration-300"
            >
              <div className="flex items-start justify-between mb-4">
                <span className="text-3xl animate-float" style={{ animationDelay: `${Math.random() * 2}s` }}>
                  {feature.icon}
                </span>
                <StatusBadge status={feature.status} />
              </div>

              <h3 className="text-lg font-semibold text-foreground mb-2 group-hover:text-primary-hover transition-colors">
                {feature.title}
              </h3>

              <p className="text-sm text-muted leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
