"use client"

import { useState } from "react"

const phaseRows = [
  { label: "Phase 1 \u2014 Discovery", hours: 160 },
  { label: "Phase 2 \u2014 Core Infrastructure", hours: 500 },
  { label: "Phase 3 \u2014 Security & Compliance", hours: 400 },
  { label: "Phase 4 \u2014 CI/CD & Integrations", hours: 440 },
  { label: "Phase 5 \u2014 Dashboard & Reporting", hours: 360 },
  { label: "Phase 6 \u2014 QA & Launch", hours: 180 },
  { label: "Buffer (15%)", hours: 396, isBuffer: true },
]

const roleRows = [
  { label: "Backend Engineers (\u00d73)", amount: "~$120K" },
  { label: "Frontend Engineer (\u00d71)", amount: "~$40K" },
  { label: "Security Engineer (\u00d71)", amount: "~$44K" },
  { label: "QA Engineer (\u00d71)", amount: "~$22K" },
  { label: "DevOps / Infra (\u00d71)", amount: "~$38K" },
  { label: "Project Manager (\u00d71)", amount: "~$39.6K" },
]

function formatCurrency(val: number) {
  return "$" + val.toLocaleString()
}

export function BudgetPanel() {
  const [rate, setRate] = useState(100)

  const total = phaseRows.reduce((sum, row) => sum + row.hours * rate, 0)

  return (
    <div>
      <div className="bg-accent-green/5 border border-accent-green/20 rounded-sm p-4 px-5 text-[13px] font-mono text-muted-color leading-relaxed mb-8">
        <strong className="text-accent-green">Adjust your hourly rate:</strong> Use the slider to see how budget changes across team configurations.
      </div>

      <div className="mb-8">
        <label className="font-mono text-xs tracking-[2px] uppercase text-muted-color">
          {"BLENDED HOURLY RATE: "}
          <span className="text-accent-green">${rate}</span>/hr
        </label>
        <br />
        <input
          type="range"
          min={60}
          max={200}
          step={10}
          value={rate}
          onChange={(e) => setRate(parseInt(e.target.value))}
          className="w-80 max-w-full mt-4"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
        <div className="bg-surface border border-border rounded-sm p-7">
          <h3 className="text-[13px] font-semibold font-mono text-muted-color tracking-[2px] uppercase mb-5">
            By Phase
          </h3>
          {phaseRows.map((row) => (
            <div
              key={row.label}
              className="flex justify-between items-center py-2.5 border-b border-surface-hover last:border-0 text-sm"
            >
              <span className="text-text">{row.label}</span>
              <span className={`font-mono font-bold ${row.isBuffer ? "text-warn" : "text-text"}`}>
                {formatCurrency(row.hours * rate)}
              </span>
            </div>
          ))}
          <div className="flex justify-between mt-4 pt-4 border-t-2 border-accent-green text-lg font-extrabold">
            <span className="text-text">TOTAL</span>
            <span className="text-accent-green font-mono">{formatCurrency(total)}</span>
          </div>
        </div>

        <div className="bg-surface border border-border rounded-sm p-7">
          <h3 className="text-[13px] font-semibold font-mono text-muted-color tracking-[2px] uppercase mb-5">
            By Role
          </h3>
          {roleRows.map((row) => (
            <div
              key={row.label}
              className="flex justify-between items-center py-2.5 border-b border-surface-hover last:border-0 text-sm"
            >
              <span className="text-text">{row.label}</span>
              <span className="font-mono font-bold text-accent-purple">{row.amount}</span>
            </div>
          ))}
          <div className="mt-4 pt-2 text-xs text-muted-color font-mono leading-relaxed">
            * Role budgets are indicative.<br />
            Blended rate slider applies to phase breakdown.
          </div>
        </div>
      </div>
    </div>
  )
}
