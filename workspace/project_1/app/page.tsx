import { SummaryCards } from "@/components/summary-cards"
import { EstimateTabs } from "@/components/estimate-tabs"

export default function Page() {
  return (
    <main className="min-h-screen bg-bg pb-16">
      {/* Header */}
      <header className="relative overflow-hidden px-6 sm:px-10 pt-12 pb-8 border-b border-border">
        {/* Glow effect */}
        <div className="absolute -top-16 -right-16 w-72 h-72 bg-[radial-gradient(circle,rgba(0,229,160,0.12)_0%,transparent_70%)] pointer-events-none" />

        <div className="relative">
          <div className="font-mono text-[11px] text-accent-green tracking-[3px] uppercase">
            {"Project Estimate \u00b7 Software / Tech"}
          </div>
          <h1 className="text-[clamp(28px,4vw,48px)] font-extrabold leading-[1.1] mt-2 text-text text-balance">
            {"Git Health &"}
            <br />
            <span className="text-accent-green">Governance Platform</span>
          </h1>
          <div className="text-muted-color text-[15px] mt-1 font-mono">
            {"// Covering 10 issue categories \u00b7 50+ problem types"}
          </div>
        </div>
      </header>

      {/* Summary cards */}
      <SummaryCards />

      {/* Tab content */}
      <EstimateTabs />
    </main>
  )
}
