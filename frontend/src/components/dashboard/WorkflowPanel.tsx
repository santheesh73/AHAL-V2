import type { WorkflowStep } from "../../lib/types"
import { GlassCard } from "../ui/GlassCard"

export function WorkflowPanel({ steps }: { steps: WorkflowStep[] }) {
  return (
    <GlassCard>
      <h3 className="text-lg font-semibold text-white">Workflow</h3>
      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {steps.length ? steps.map((step, index) => (
          <div key={step.title} className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
            <p className="text-xs uppercase tracking-[0.28em] text-cyan-300/70">Step {index + 1}</p>
            <p className="mt-4 break-words text-base font-medium text-white">{step.title}</p>
            <p className="mt-3 break-words text-sm leading-7 text-slate-400">{step.description}</p>
          </div>
        )) : <p className="text-sm text-slate-400">No workflow was detected for this session.</p>}
      </div>
    </GlassCard>
  )
}
