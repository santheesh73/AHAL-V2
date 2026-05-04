import type { TimelineItem } from "../../lib/types"
import { formatDateTime } from "../../lib/utils"
import { GlassCard } from "../ui/GlassCard"
import { StatusBadge } from "../ui/StatusBadge"

export function TimelinePanel({ items }: { items: TimelineItem[] }) {
  return (
    <GlassCard>
      <h3 className="text-lg font-semibold text-white">Analysis Timeline</h3>
      <div className="mt-6 space-y-5">
        {items.length ? items.map((item) => (
          <div key={item.id} className="flex gap-4">
            <div className="mt-1 flex flex-col items-center">
              <span className="h-3 w-3 rounded-full bg-cyan-300" />
              <span className="mt-2 h-full w-px bg-white/10" />
            </div>
            <div className="flex-1 rounded-2xl border border-white/8 bg-white/[0.03] p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-medium text-white">{item.title}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.24em] text-slate-500">{formatDateTime(item.timestamp)}</p>
                </div>
                <StatusBadge status={item.status} />
              </div>
              <p className="mt-3 text-sm text-slate-400">{item.detail}</p>
            </div>
          </div>
        )) : <p className="text-sm text-slate-400">No timeline events were returned yet. Progress updates will appear here when the backend reports them.</p>}
      </div>
    </GlassCard>
  )
}
