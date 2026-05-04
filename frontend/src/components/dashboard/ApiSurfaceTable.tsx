import type { ApiSurfaceItem } from "../../lib/types"
import { GlassCard } from "../ui/GlassCard"

export function ApiSurfaceTable({ items }: { items: ApiSurfaceItem[] }) {
  return (
    <GlassCard>
      <h3 className="text-lg font-semibold text-white">API Surface</h3>
      <div className="mt-5 overflow-hidden rounded-3xl border border-white/10">
        {items.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-[720px] w-full text-left text-sm">
              <thead className="bg-white/[0.05] text-slate-300">
                <tr>
                  <th className="px-4 py-3 font-medium">Method</th>
                  <th className="px-4 py-3 font-medium">Path</th>
                  <th className="px-4 py-3 font-medium">Purpose</th>
                  <th className="px-4 py-3 font-medium">Source</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={`${item.method}-${item.path}`} className="border-t border-white/10">
                    <td className="px-4 py-4 text-cyan-200">{item.method}</td>
                    <td className="px-4 py-4 text-white">{item.path}</td>
                    <td className="px-4 py-4 text-slate-300">{item.purpose}</td>
                    <td className="px-4 py-4 text-slate-400">{item.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="p-5 text-sm text-slate-400">No API endpoints were detected for this session.</p>}
      </div>
    </GlassCard>
  )
}
