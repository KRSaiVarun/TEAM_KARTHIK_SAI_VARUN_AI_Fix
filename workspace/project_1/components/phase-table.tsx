type Task = {
  name: string
  desc: string
  priority: "HIGH" | "MED" | "LOW"
  hours: string
  effort: number
}

type Phase = {
  title: string
  tasks: Task[]
}

const badgeStyles: Record<string, string> = {
  HIGH: "bg-accent-orange/15 text-accent-orange",
  MED: "bg-accent-purple/15 text-accent-purple",
  LOW: "bg-accent-green/12 text-accent-green",
}

const barStyles: Record<string, string> = {
  HIGH: "bg-accent-orange",
  MED: "bg-accent-purple",
  LOW: "bg-accent-green",
}

const phases: Phase[] = [
  {
    title: "// Phase 1 \u2014 Discovery & Architecture \u00a0\u00b7\u00a0 Weeks 1\u20133",
    tasks: [
      { name: "Requirements & stakeholder interviews", desc: "Map all 50+ issues to feature requirements", priority: "HIGH", hours: "40h", effort: 30 },
      { name: "System architecture design", desc: "Microservices, API contracts, data models", priority: "HIGH", hours: "80h", effort: 60 },
      { name: "Tech stack setup & PoC", desc: "Node.js + Express/Fastify backend, Git provider APIs, DB, auth, hosting setup", priority: "HIGH", hours: "40h", effort: 30 },
    ],
  },
  {
    title: "// Phase 2 \u2014 Core Infrastructure \u00a0\u00b7\u00a0 Weeks 4\u20138",
    tasks: [
      { name: "Repository scanner engine", desc: "Detect merge conflicts, large files, orphaned commits, pack issues", priority: "HIGH", hours: "160h", effort: 100 },
      { name: "Branch management module", desc: "Stale/orphaned/long-lived branch detection, naming enforcement", priority: "HIGH", hours: "120h", effort: 75 },
      { name: "Auth & access control layer", desc: "SSH key mgmt, token rotation, IP whitelisting, permission audits", priority: "HIGH", hours: "100h", effort: 63 },
      { name: "Node.js API & database foundation", desc: "Express/Fastify REST + GraphQL APIs, multi-repo ingestion pipeline, PostgreSQL/MongoDB", priority: "HIGH", hours: "120h", effort: 75 },
    ],
  },
  {
    title: "// Phase 3 \u2014 Security & Compliance \u00a0\u00b7\u00a0 Weeks 9\u201313",
    tasks: [
      { name: "Secret / credential scanner", desc: "Detect exposed passwords, API keys, tokens in commit history", priority: "HIGH", hours: "140h", effort: 88 },
      { name: "Dependency vulnerability analyzer", desc: "CVE matching, dependency confusion detection, SBOM generation", priority: "HIGH", hours: "120h", effort: 75 },
      { name: "GPG signature enforcement", desc: "Commit signing validation, missing/invalid signature alerts", priority: "MED", hours: "60h", effort: 38 },
      { name: "Protected branch enforcement", desc: "Force-push detection, bypass auditing, remediation flows", priority: "HIGH", hours: "80h", effort: 50 },
    ],
  },
  {
    title: "// Phase 4 \u2014 CI/CD, Hooks & Integrations \u00a0\u00b7\u00a0 Weeks 14\u201318",
    tasks: [
      { name: "Hook health monitor", desc: "Client/server hook status, permission checker, auto-fix suggestions", priority: "HIGH", hours: "100h", effort: 63 },
      { name: "CI/CD pipeline diagnostics", desc: "Build failure categorization, deployment issue tracking", priority: "HIGH", hours: "120h", effort: 75 },
      { name: "Third-party integrations", desc: "GitHub, GitLab, Bitbucket, Jira, Slack, IDE plugins", priority: "MED", hours: "140h", effort: 88 },
      { name: "Git LFS & performance optimizer", desc: "Large binary detection, gc/fsck scheduling, pack file repair", priority: "MED", hours: "80h", effort: 50 },
    ],
  },
  {
    title: "// Phase 5 \u2014 Dashboard, Reporting & Best Practices \u00a0\u00b7\u00a0 Weeks 19\u201322",
    tasks: [
      { name: "Health score dashboard", desc: "Per-repo scores across all 10 issue categories with drill-down", priority: "HIGH", hours: "120h", effort: 75 },
      { name: "Automated remediation playbooks", desc: "Step-by-step fix guides, one-click fixes where safe", priority: "MED", hours: "100h", effort: 63 },
      { name: "Policy engine & best practice checker", desc: ".gitignore enforcement, branching strategy rules, tag conventions", priority: "MED", hours: "80h", effort: 50 },
      { name: "Alerts, notifications & reporting", desc: "Scheduled reports, Slack/email alerts, PDF exports", priority: "LOW", hours: "60h", effort: 38 },
    ],
  },
  {
    title: "// Phase 6 \u2014 QA, Hardening & Launch \u00a0\u00b7\u00a0 Weeks 23\u201324",
    tasks: [
      { name: "Security penetration testing", desc: "External pen-test, remediation of findings", priority: "HIGH", hours: "80h", effort: 50 },
      { name: "Performance & load testing", desc: "Test at scale with 1000+ repo workloads", priority: "HIGH", hours: "60h", effort: 38 },
      { name: "Documentation & team training", desc: "User docs, API docs, onboarding guides", priority: "MED", hours: "40h", effort: 25 },
    ],
  },
]

export function PhasesPanel() {
  return (
    <div>
      <div className="bg-accent-green/5 border border-accent-green/20 rounded-sm p-4 px-5 text-[13px] font-mono text-muted-color leading-relaxed mb-8">
        <strong className="text-accent-green">Rate assumption:</strong> Blended team rate of $100/hr. Adjust in Budget tab. Priorities:{" "}
        <strong className="text-accent-orange">High</strong> = must-have{" \u00b7 "}
        <strong className="text-accent-purple">Med</strong> = important{" \u00b7 "}
        <strong className="text-accent-green">Low</strong> = nice-to-have
      </div>

      {phases.map((phase) => (
        <div key={phase.title} className="mb-10">
          <div className="text-[11px] font-mono tracking-[3px] text-muted-color uppercase mb-3 pl-1">
            {phase.title}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="font-mono text-[10px] tracking-[2px] text-muted-color uppercase text-left px-4 py-2.5 border-b border-border">Task</th>
                  <th className="font-mono text-[10px] tracking-[2px] text-muted-color uppercase text-left px-4 py-2.5 border-b border-border">Priority</th>
                  <th className="font-mono text-[10px] tracking-[2px] text-muted-color uppercase text-left px-4 py-2.5 border-b border-border">Hours</th>
                  <th className="font-mono text-[10px] tracking-[2px] text-muted-color uppercase text-left px-4 py-2.5 border-b border-border">% Effort</th>
                </tr>
              </thead>
              <tbody>
                {phase.tasks.map((task) => (
                  <tr key={task.name} className="hover:bg-[#141720] transition-colors">
                    <td className="px-4 py-3.5 text-sm border-b border-surface-hover align-middle">
                      <div className="font-semibold text-text">{task.name}</div>
                      <div className="text-xs text-muted-color font-mono mt-0.5">{task.desc}</div>
                    </td>
                    <td className="px-4 py-3.5 text-sm border-b border-surface-hover align-middle">
                      <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-mono tracking-[1px] font-bold ${badgeStyles[task.priority]}`}>
                        {task.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-sm border-b border-surface-hover align-middle font-mono text-[13px] text-text">
                      {task.hours}
                    </td>
                    <td className="px-4 py-3.5 text-sm border-b border-surface-hover align-middle">
                      <div className="h-1 bg-border rounded min-w-20">
                        <div
                          className={`h-full rounded ${barStyles[task.priority]}`}
                          style={{ width: `${task.effort}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  )
}
