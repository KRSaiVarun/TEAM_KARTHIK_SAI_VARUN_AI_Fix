type TimelineItem = {
  weeks: string
  phase: string
  phaseColor: string
  dotColor: string
  chips: string[]
}

const items: TimelineItem[] = [
  {
    weeks: "WEEKS 1\u20133",
    phase: "Phase 1 \u2014 Discovery & Architecture",
    phaseColor: "text-accent-orange",
    dotColor: "bg-accent-orange",
    chips: ["Requirements gathering", "System design", "PoC / tech selection", "Kickoff"],
  },
  {
    weeks: "WEEKS 4\u20138",
    phase: "Phase 2 \u2014 Core Infrastructure",
    phaseColor: "text-accent-purple",
    dotColor: "bg-accent-purple",
    chips: ["Repo scanner engine", "Branch management module", "Auth & access control", "API foundation"],
  },
  {
    weeks: "WEEKS 9\u201313",
    phase: "Phase 3 \u2014 Security & Compliance",
    phaseColor: "text-accent-orange",
    dotColor: "bg-accent-orange",
    chips: ["Secret scanner", "Dependency analyzer", "GPG signing", "Branch protection"],
  },
  {
    weeks: "WEEKS 14\u201318",
    phase: "Phase 4 \u2014 CI/CD, Hooks & Integrations",
    phaseColor: "text-accent-green",
    dotColor: "bg-accent-green",
    chips: ["Hook monitor", "CI/CD diagnostics", "3rd-party integrations", "Git LFS optimizer"],
  },
  {
    weeks: "WEEKS 19\u201322",
    phase: "Phase 5 \u2014 Dashboard & Best Practices",
    phaseColor: "text-warn",
    dotColor: "bg-warn",
    chips: ["Health score dashboard", "Remediation playbooks", "Policy engine", "Alerting & reports"],
  },
  {
    weeks: "WEEKS 23\u201324",
    phase: "Phase 6 \u2014 QA, Hardening & Launch",
    phaseColor: "text-accent-green",
    dotColor: "bg-accent-green",
    chips: ["Pen testing", "Load testing", "Documentation", "Go-live"],
  },
]

export function TimelinePanel() {
  return (
    <div>
      <div className="bg-accent-green/5 border border-accent-green/20 rounded-sm p-4 px-5 text-[13px] font-mono text-muted-color leading-relaxed mb-8">
        <strong className="text-accent-green">24-week delivery plan.</strong> Phases overlap slightly for efficiency. Adjust based on your team{"'"}s capacity.
      </div>

      <div className="relative pl-7">
        {/* Vertical line */}
        <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-border" />

        {items.map((item, i) => (
          <div key={i} className="relative mb-8">
            {/* Dot */}
            <div
              className={`absolute -left-5 top-1 w-3.5 h-3.5 rounded-full border-2 border-bg ${item.dotColor}`}
              style={{ boxShadow: `0 0 8px currentColor` }}
            />

            <div className="font-mono text-[10px] text-muted-color tracking-[2px] mb-1">
              {item.weeks}
            </div>
            <div className={`text-base font-bold mb-1.5 ${item.phaseColor}`}>
              {item.phase}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {item.chips.map((chip) => (
                <span
                  key={chip}
                  className="text-[11px] font-mono px-2.5 py-1 rounded-sm bg-border text-muted-color"
                >
                  {chip}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
