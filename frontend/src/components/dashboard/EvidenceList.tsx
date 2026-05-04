import { useState } from "react"
import type { EvidenceItem } from "../../lib/types"
import { GlassCard } from "../ui/GlassCard"
import { Button } from "../ui/Button"

export function EvidenceList({ items }: { items: EvidenceItem[] }) {
  const [expanded, setExpanded] = useState(false)
  const visibleItems = expanded ? items.slice(0, 12) : items.slice(0, 6)

  return (
    <GlassCard>
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-lg font-semibold text-white">Evidence Appendix</h3>
        {items.length > 6 ? (
          <Button variant="secondary" size="sm" onClick={() => setExpanded((value) => !value)}>
            {expanded ? "Show less" : "Show more"}
          </Button>
        ) : null}
      </div>
      <div className="mt-5 space-y-4">
        {visibleItems.length ? visibleItems.map((item) => (
          <div key={item.label} className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
            <p className="break-words font-medium text-white">{item.label}</p>
            {item.detail ? <p className="mt-3 break-words text-sm leading-7 text-slate-400">{item.detail}</p> : null}
          </div>
        )) : <p className="text-sm text-slate-400">No evidence rows were returned for this session.</p>}
      </div>
      <p className="mt-5 text-sm text-slate-500">Additional evidence is available in the JSON report.</p>
      {items.length > 12 ? <p className="mt-2 text-xs text-slate-600">Only the first 12 normalized evidence items are shown here.</p> : null}
    </GlassCard>
  )
}
