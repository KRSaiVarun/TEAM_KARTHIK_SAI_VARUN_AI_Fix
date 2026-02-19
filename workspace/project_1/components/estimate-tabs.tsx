"use client"

import { useState } from "react"
import { PhasesPanel } from "./phase-table"
import { TechStackPanel } from "./tech-stack-panel"
import { BudgetPanel } from "./budget-panel"
import { TimelinePanel } from "./timeline-panel"
import { RisksPanel } from "./risks-panel"

const tabs = [
  { id: "phases", label: "Phases & Tasks" },
  { id: "techstack", label: "Tech Stack" },
  { id: "budget", label: "Budget" },
  { id: "timeline", label: "Timeline" },
  { id: "risks", label: "Risks" },
] as const

type TabId = (typeof tabs)[number]["id"]

export function EstimateTabs() {
  const [activeTab, setActiveTab] = useState<TabId>("phases")

  return (
    <div className="p-6 sm:p-10">
      {/* Tab bar */}
      <div className="flex gap-1 mb-8 border-b border-border overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`font-mono text-xs tracking-[1px] px-5 py-2.5 border-b-2 transition-colors uppercase whitespace-nowrap cursor-pointer ${
              activeTab === tab.id
                ? "text-accent-green border-accent-green"
                : "text-muted-color border-transparent hover:text-text"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Panel content */}
      {activeTab === "phases" && <PhasesPanel />}
      {activeTab === "techstack" && <TechStackPanel />}
      {activeTab === "budget" && <BudgetPanel />}
      {activeTab === "timeline" && <TimelinePanel />}
      {activeTab === "risks" && <RisksPanel />}
    </div>
  )
}
