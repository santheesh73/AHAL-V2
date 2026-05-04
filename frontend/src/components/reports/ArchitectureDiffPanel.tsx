import type { PrdDiffResult } from "../../lib/types"
import { GlassCard } from "../ui/GlassCard"

export function ArchitectureDiffPanel({ diff }: { diff: PrdDiffResult | null }) {
  return (
    <GlassCard>
      <h3 className="text-lg font-semibold text-white">Architecture Diff</h3>
      {diff ? (
        <>
          <p className="mt-4 text-sm leading-7 text-slate-300">{diff.summary}</p>
          <div className="mt-5 space-y-4">
            {diff.changes.length ? diff.changes.map((change) => (
              <div key={change.title} className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
                <p className="font-medium text-white">{change.title}</p>
                <p className="mt-2 text-sm text-slate-400">{change.detail}</p>
              </div>
            )) : <p className="text-sm text-slate-400">No diff changes were returned yet.</p>}
          </div>
        </>
      ) : <p className="mt-4 text-sm text-slate-400">Run a delta scan to generate a meaningful architecture diff for this session.</p>}
    </GlassCard>
  )
}
