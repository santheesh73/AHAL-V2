import { BarChart3, Download, MessageCircleCode, Radar } from "lucide-react"
import { GlassCard } from "../ui/GlassCard"
import { ScrollReveal } from "../ui/ScrollReveal"
import { SectionHeader } from "../ui/SectionHeader"

export function ProductShowcase() {
  return (
    <section className="px-4 py-20 md:px-8">
      <div className="mx-auto max-w-7xl space-y-10">
        <SectionHeader
          eyebrow="Dashboard"
          title="A premium command center for validated project understanding"
          description="The interface keeps confidence, evidence, actions, and reports close together so teams can move quickly without losing grounding."
        />

        <ScrollReveal>
          <GlassCard glow className="overflow-hidden p-0">
            <div className="grid gap-px bg-white/10 lg:grid-cols-[1.3fr_0.7fr]">
              <div className="space-y-6 bg-slate-950/80 p-6">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
                    <Radar className="h-5 w-5 text-cyan-200" />
                    <p className="mt-5 text-sm text-slate-400">Architecture Confidence</p>
                    <p className="mt-2 text-2xl font-semibold text-white">High</p>
                  </div>
                  <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
                    <MessageCircleCode className="h-5 w-5 text-violet-200" />
                    <p className="mt-5 text-sm text-slate-400">Repo Chat</p>
                    <p className="mt-2 text-2xl font-semibold text-white">Grounded</p>
                  </div>
                  <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
                    <Download className="h-5 w-5 text-emerald-200" />
                    <p className="mt-5 text-sm text-slate-400">Exports</p>
                    <p className="mt-2 text-2xl font-semibold text-white">PDF / MD / LaTeX</p>
                  </div>
                </div>
                <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-6">
                  <p className="text-sm text-slate-400">Project Goal</p>
                  <p className="mt-3 text-xl font-semibold text-white">
                    Turn repository evidence into validated technical intelligence, not generic narrative.
                  </p>
                  <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400">
                    Product purpose, risks, workflow, APIs, and report generation remain visible in one place with clear confidence and evidence.
                  </p>
                </div>
              </div>
              <div className="space-y-4 bg-white/[0.04] p-6">
                <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-5">
                  <p className="text-sm text-slate-400">Timeline</p>
                  <div className="mt-4 space-y-4">
                    {["Session created", "Evidence extracted", "Summary validated"].map((item) => (
                      <div key={item} className="flex items-center gap-3">
                        <span className="h-2.5 w-2.5 rounded-full bg-cyan-300" />
                        <span className="text-sm text-slate-200">{item}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-5">
                  <BarChart3 className="h-5 w-5 text-cyan-200" />
                  <p className="mt-5 text-sm text-slate-400">Evidence-backed overview</p>
                  <p className="mt-3 text-sm leading-7 text-slate-300">
                    Separate architecture certainty from product-purpose certainty so teams can trust what is known and see what remains uncertain.
                  </p>
                </div>
              </div>
            </div>
          </GlassCard>
        </ScrollReveal>
      </div>
    </section>
  )
}
