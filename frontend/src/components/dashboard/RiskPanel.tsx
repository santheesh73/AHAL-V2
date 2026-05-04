import type { RiskItem } from "../../lib/types"
import { GlassCard } from "../ui/GlassCard"

export function RiskPanel({ items }: { items: RiskItem[] }) {
  return (
    <GlassCard>
      <h3 className="text-lg font-semibold text-white">Risks and Gaps</h3>
      <div className="mt-5 overflow-hidden rounded-3xl border border-white/10">
        {items.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-[720px] w-full text-left text-sm">
              <thead className="bg-white/[0.05] text-slate-300">
                <tr>
                  <th className="px-4 py-3 font-medium">Severity</th>
                  <th className="px-4 py-3 font-medium">Issue</th>
                  <th className="px-4 py-3 font-medium">Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.issue} className="border-t border-white/10">
                    <td className="px-4 py-4 text-white">{item.severity}</td>
                    <td className="px-4 py-4 text-slate-300">{item.issue}</td>
                    <td className="px-4 py-4 text-slate-400">{item.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="p-5 text-sm text-slate-400">No risks were returned for this session.</p>}
      </div>
    </GlassCard>
  )
}
