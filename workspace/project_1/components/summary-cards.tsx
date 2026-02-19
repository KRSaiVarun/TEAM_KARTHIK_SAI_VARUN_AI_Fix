const cards = [
  {
    label: "Total Duration",
    value: "24",
    sub: "weeks (6 months)",
    colorClass: "text-accent-green",
  },
  {
    label: "Total Hours",
    value: "2,640",
    sub: "across all phases",
    colorClass: "text-accent-orange",
  },
  {
    label: "Est. Budget",
    value: "$264K",
    sub: "at $100 avg/hr blended",
    colorClass: "text-accent-purple",
  },
  {
    label: "Team Size",
    value: "6\u20138",
    sub: "engineers + 1 PM",
    colorClass: "text-warn",
  },
]

export function SummaryCards() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-border border-b border-border">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-surface hover:bg-surface-hover transition-colors flex flex-col gap-1.5 px-8 py-7"
        >
          <span className="font-mono text-[10px] tracking-[2px] uppercase text-muted-color">
            {card.label}
          </span>
          <span className={`text-[32px] font-extrabold leading-none ${card.colorClass}`}>
            {card.value}
          </span>
          <span className="text-xs text-muted-color font-mono">{card.sub}</span>
        </div>
      ))}
    </div>
  )
}
