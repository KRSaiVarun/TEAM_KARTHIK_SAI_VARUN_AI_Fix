type StackItem = { label: string; value: string }
type StackCategory = { title: string; colorClass: string; items: StackItem[] }

const stacks: StackCategory[] = [
  {
    title: "Backend \u2014 Node.js Core",
    colorClass: "text-accent-green",
    items: [
      { label: "Runtime", value: "Node.js 20 LTS" },
      { label: "Framework", value: "Fastify" },
      { label: "API style", value: "REST + GraphQL" },
      { label: "GraphQL server", value: "Apollo Server 4" },
      { label: "Auth", value: "Passport.js + JWT" },
      { label: "Job queues", value: "BullMQ (Redis)" },
      { label: "Git operations", value: "simple-git / nodegit" },
      { label: "Package manager", value: "pnpm workspaces" },
    ],
  },
  {
    title: "Data Layer",
    colorClass: "text-accent-purple",
    items: [
      { label: "Primary DB", value: "PostgreSQL 16" },
      { label: "ORM", value: "Prisma" },
      { label: "Cache / Queues", value: "Redis 7" },
      { label: "Search", value: "Elasticsearch" },
      { label: "Secrets storage", value: "HashiCorp Vault" },
      { label: "Time-series (metrics)", value: "InfluxDB" },
    ],
  },
  {
    title: "Frontend",
    colorClass: "text-warn",
    items: [
      { label: "Framework", value: "React 18 + Vite" },
      { label: "State management", value: "Zustand" },
      { label: "UI components", value: "shadcn/ui" },
      { label: "Charts / dashboards", value: "Recharts + D3" },
      { label: "API client", value: "TanStack Query" },
      { label: "Routing", value: "React Router v6" },
    ],
  },
  {
    title: "Security Tooling",
    colorClass: "text-accent-orange",
    items: [
      { label: "Secret scanning", value: "truffleHog (node wrapper)" },
      { label: "Dependency audit", value: "npm audit + Snyk SDK" },
      { label: "SAST", value: "Semgrep" },
      { label: "Auth hardening", value: "helmet.js + CSRF" },
      { label: "Rate limiting", value: "@fastify/rate-limit" },
    ],
  },
  {
    title: "DevOps & Infrastructure",
    colorClass: "text-accent-green",
    items: [
      { label: "Containerization", value: "Docker + Docker Compose" },
      { label: "Orchestration", value: "Kubernetes (EKS/GKE)" },
      { label: "CI/CD", value: "GitHub Actions" },
      { label: "IaC", value: "Terraform" },
      { label: "Monitoring", value: "Prometheus + Grafana" },
      { label: "Logging", value: "Pino (Node) + Loki" },
      { label: "Tracing", value: "OpenTelemetry" },
    ],
  },
  {
    title: "Testing",
    colorClass: "text-accent-purple",
    items: [
      { label: "Unit / integration", value: "Vitest" },
      { label: "API testing", value: "Supertest" },
      { label: "E2E", value: "Playwright" },
      { label: "Load testing", value: "k6" },
      { label: "Code coverage", value: "Istanbul / c8" },
      { label: "Linting", value: "ESLint + Prettier" },
    ],
  },
]

type NodeTask = {
  name: string
  desc: string
  phase: string
  hours: string
  priority: "HIGH" | "MED"
}

const nodeTasks: NodeTask[] = [
  { name: "Node.js project scaffolding & monorepo setup", desc: "pnpm workspaces, tsconfig, ESLint, shared packages", phase: "Phase 1", hours: "24h", priority: "HIGH" },
  { name: "Fastify API server with plugin architecture", desc: "Route organization, middleware, error handling, OpenAPI docs", phase: "Phase 2", hours: "40h", priority: "HIGH" },
  { name: "BullMQ job queue workers", desc: "Async repo scanning jobs, retry logic, dead letter queues", phase: "Phase 2", hours: "32h", priority: "HIGH" },
  { name: "simple-git integration layer", desc: "Wrap Git CLI operations safely in Node.js for scanning, log parsing, ref walking", phase: "Phase 2", hours: "48h", priority: "HIGH" },
  { name: "npm audit + Snyk integration", desc: "Programmatic dependency scanning using Node.js npm audit API and Snyk SDK", phase: "Phase 3", hours: "40h", priority: "HIGH" },
  { name: "Node.js webhook receiver service", desc: "GitHub/GitLab webhook ingestion, signature verification, event routing", phase: "Phase 4", hours: "32h", priority: "MED" },
  { name: "Pino structured logging + OpenTelemetry tracing", desc: "Production observability for all Node.js services", phase: "Phase 4", hours: "24h", priority: "MED" },
  { name: "Vitest + Supertest test suite", desc: "Unit and integration tests for all Node.js services, CI coverage gates", phase: "Phase 6", hours: "40h", priority: "HIGH" },
]

const badgeStyles: Record<string, string> = {
  HIGH: "bg-accent-orange/15 text-accent-orange",
  MED: "bg-accent-purple/15 text-accent-purple",
}

export function TechStackPanel() {
  return (
    <div>
      <div className="bg-accent-green/5 border border-accent-green/20 rounded-sm p-4 px-5 text-[13px] font-mono text-muted-color leading-relaxed mb-8">
        <strong className="text-accent-green">Node.js-first stack.</strong> All backend services run on Node.js. Selected for its async I/O performance (ideal for Git API calls), rich npm ecosystem, and team familiarity across full-stack engineers.
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-10">
        {stacks.map((cat) => (
          <div key={cat.title} className="bg-surface border border-border rounded-sm p-7">
            <h3 className="text-[13px] font-semibold font-mono text-muted-color tracking-[2px] uppercase mb-5">
              {cat.title}
            </h3>
            {cat.items.map((item) => (
              <div key={item.label} className="flex justify-between items-center py-2.5 border-b border-surface-hover last:border-0 text-sm">
                <span className="text-text">{item.label}</span>
                <span className={`font-mono font-bold ${cat.colorClass}`}>{item.value}</span>
              </div>
            ))}
          </div>
        ))}
      </div>

      <h2 className="text-xl font-extrabold mb-5 text-text">Node.js-Specific Work Items</h2>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse mb-10">
          <thead>
            <tr>
              <th className="font-mono text-[10px] tracking-[2px] text-muted-color uppercase text-left px-4 py-2.5 border-b border-border">Task</th>
              <th className="font-mono text-[10px] tracking-[2px] text-muted-color uppercase text-left px-4 py-2.5 border-b border-border">Phase</th>
              <th className="font-mono text-[10px] tracking-[2px] text-muted-color uppercase text-left px-4 py-2.5 border-b border-border">Hours</th>
              <th className="font-mono text-[10px] tracking-[2px] text-muted-color uppercase text-left px-4 py-2.5 border-b border-border">Priority</th>
            </tr>
          </thead>
          <tbody>
            {nodeTasks.map((task) => (
              <tr key={task.name} className="hover:bg-[#141720] transition-colors">
                <td className="px-4 py-3.5 text-sm border-b border-surface-hover align-middle">
                  <div className="font-semibold text-text">{task.name}</div>
                  <div className="text-xs text-muted-color font-mono mt-0.5">{task.desc}</div>
                </td>
                <td className="px-4 py-3.5 text-sm border-b border-surface-hover align-middle font-mono text-xs text-muted-color">
                  {task.phase}
                </td>
                <td className="px-4 py-3.5 text-sm border-b border-surface-hover align-middle font-mono text-[13px] text-text">
                  {task.hours}
                </td>
                <td className="px-4 py-3.5 text-sm border-b border-surface-hover align-middle">
                  <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-mono tracking-[1px] font-bold ${badgeStyles[task.priority]}`}>
                    {task.priority}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
