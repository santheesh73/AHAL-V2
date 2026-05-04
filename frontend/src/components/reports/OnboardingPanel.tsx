import type { OnboardingReport } from "../../lib/types"
import { Button } from "../ui/Button"
import { GlassCard } from "../ui/GlassCard"

type OnboardingPanelProps = {
  report: OnboardingReport | null
  loading?: boolean
  unavailable?: boolean
  onLoad?: () => void
}

export function OnboardingPanel({ report, loading = false, unavailable = false, onLoad }: OnboardingPanelProps) {
  return (
    <GlassCard>
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-lg font-semibold text-white">Onboarding Report</h3>
        {onLoad ? <Button variant="secondary" onClick={onLoad} disabled={loading}>{loading ? "Loading..." : "Load Report"}</Button> : null}
      </div>
      {unavailable ? <p className="mt-4 text-sm text-slate-400">Not available for this session.</p> : null}
      {report ? (
        <>
          <p className="mt-4 text-sm leading-7 text-slate-300">{report.summary}</p>
          <div className="mt-5 space-y-4">
            {report.steps.length ? report.steps.map((step) => (
              <div key={step.title} className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
                <p className="font-medium text-white">{step.title}</p>
                <p className="mt-2 text-sm text-slate-400">{step.detail}</p>
              </div>
            )) : <p className="text-sm text-slate-400">No onboarding steps were returned for this session.</p>}
          </div>
        </>
      ) : !unavailable ? <p className="mt-4 text-sm text-slate-400">No onboarding report has been loaded for this session yet.</p> : null}
    </GlassCard>
  )
}
