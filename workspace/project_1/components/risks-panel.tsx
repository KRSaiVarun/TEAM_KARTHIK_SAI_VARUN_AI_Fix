type Risk = {
  level: "high" | "med" | "low"
  title: string
  desc: string
}

const dotStyles: Record<string, string> = {
  high: "bg-accent-orange shadow-[0_0_8px_rgba(255,107,53,0.5)]",
  med: "bg-warn shadow-[0_0_8px_rgba(240,180,41,0.5)]",
  low: "bg-accent-green shadow-[0_0_8px_rgba(0,229,160,0.5)]",
}

const risks: Risk[] = [
  {
    level: "high",
    title: "Git provider API rate limits & breaking changes",
    desc: "GitHub/GitLab APIs can throttle or change without notice. Mitigation: build an abstraction layer, cache aggressively, maintain versioned API adapters.",
  },
  {
    level: "high",
    title: "Secret scanning false positives / negatives",
    desc: "Credential detection is high-stakes. False negatives expose secrets; false positives cause alert fatigue. Mitigation: use allowlist/denylist, confidence scoring, regular model updates.",
  },
  {
    level: "high",
    title: "Performance at scale with large monorepos",
    desc: "Scanning repos with 10+ years of history can be slow. Mitigation: incremental scanning, background jobs, Git shallow clones where appropriate.",
  },
  {
    level: "med",
    title: "Scope creep across 50+ issue types",
    desc: "Each issue category can expand into a product on its own. Mitigation: strict MVP scoping, ruthless prioritization, phased feature flags.",
  },
  {
    level: "med",
    title: "Multi-cloud & on-prem Git hosting complexity",
    desc: "Self-hosted GitLab, Bitbucket Server behave differently. Mitigation: modular connector architecture, prioritize cloud-hosted first.",
  },
  {
    level: "med",
    title: "Security of the platform itself",
    desc: "This tool will have read access to customer codebases \u2014 a valuable target. Mitigation: zero-trust design, regular audits, SOC 2 from day one.",
  },
  {
    level: "low",
    title: "Team ramp-up on Git internals",
    desc: "Deep Git knowledge (pack files, plumbing commands) is rare. Mitigation: hire one Git expert early, invest in internal knowledge sharing.",
  },
  {
    level: "low",
    title: "User adoption & behavior change",
    desc: "Developers resist new tooling. Mitigation: IDE integrations, frictionless onboarding, gamified health scores.",
  },
]

export function RisksPanel() {
  return (
    <div>
      <div className="bg-accent-green/5 border border-accent-green/20 rounded-sm p-4 px-5 text-[13px] font-mono text-muted-color leading-relaxed mb-8">
        <strong className="text-accent-green">Risk register.</strong> Identified early risks with mitigation strategies.
      </div>

      <div className="flex flex-col gap-3">
        {risks.map((risk) => (
          <div
            key={risk.title}
            className="flex gap-4 items-start bg-surface border border-border rounded-sm px-5 py-4"
          >
            <div
              className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${dotStyles[risk.level]}`}
            />
            <div>
              <div className="font-semibold text-sm text-text mb-1">{risk.title}</div>
              <div className="text-xs text-muted-color font-mono">{risk.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
