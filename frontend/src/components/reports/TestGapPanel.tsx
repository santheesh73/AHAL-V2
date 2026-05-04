import type { TestGapReport } from "../../lib/types"
import { Button } from "../ui/Button"
import { GlassCard } from "../ui/GlassCard"

type TestGapPanelProps = {
  report: TestGapReport | null
  loading?: boolean
  unavailable?: boolean
  onLoad?: () => void
}

export function TestGapPanel({ report, loading = false, unavailable = false, onLoad }: TestGapPanelProps) {
  return (
    <GlassCard>
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-lg font-semibold text-white">Test Gap Report</h3>
        {onLoad ? <Button variant="secondary" onClick={onLoad} disabled={loading}>{loading ? "Loading..." : "Load Report"}</Button> : null}
      </div>
      {unavailable ? <p className="mt-4 text-sm text-slate-400">Not available for this session.</p> : null}
      {report ? (
        <>
          <p className="mt-4 text-sm leading-7 text-slate-300">{report.summary}</p>
          <div className="mt-5 space-y-4">
            {report.items.length ? report.items.map((item) => (
              <div key={item.area} className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
                <p className="font-medium text-white">{item.area}</p>
                <p className="mt-2 text-sm text-slate-300">{item.gap}</p>
                <p className="mt-2 text-sm text-slate-500">{item.impact}</p>
              </div>
            )) : <p className="text-sm text-slate-400">No detailed test gaps were returned for this session.</p>}
          </div>
        </>
      ) : !unavailable ? <p className="mt-4 text-sm text-slate-400">No test gap report has been loaded for this session yet.</p> : null}
    </GlassCard>
  )
}
