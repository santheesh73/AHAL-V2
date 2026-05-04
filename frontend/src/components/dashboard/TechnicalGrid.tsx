import type { IntelligenceData } from "../../lib/types"
import { GlassCard } from "../ui/GlassCard"

export function TechnicalGrid({ intelligence }: { intelligence: IntelligenceData }) {
  const stackSections = [
    { category: "Languages", items: intelligence.techStack.languages },
    { category: "Frameworks", items: intelligence.techStack.frameworks },
    { category: "Databases / Storage", items: intelligence.techStack.databases },
    { category: "Tools", items: intelligence.techStack.tools },
  ]

  return (
    <div className="grid gap-5">
      <GlassCard>
        <h3 className="text-lg font-semibold text-white">Tech Stack</h3>
        <div className="mt-5 grid gap-4">
          {stackSections.map((stack) => (
            <div key={stack.category} className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
              <p className="text-sm font-medium text-white">{stack.category}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {(stack.items.length ? stack.items : ["Not detected"]).map((item) => (
                  <span key={`${stack.category}-${item}`} className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-sm text-slate-300">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  )
}
