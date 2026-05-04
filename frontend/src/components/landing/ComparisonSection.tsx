import { Check, X } from "lucide-react"
import { GlassCard } from "../ui/GlassCard"
import { ScrollReveal } from "../ui/ScrollReveal"
import { SectionHeader } from "../ui/SectionHeader"

const comparison = [
  {
    label: "Evidence-backed outputs",
    traditional: false,
    ahal: true,
  },
  {
    label: "Conservative low-confidence summaries",
    traditional: false,
    ahal: true,
  },
  {
    label: "Repo chat with warnings and citations",
    traditional: false,
    ahal: true,
  },
  {
    label: "Professional export surfaces",
    traditional: true,
    ahal: true,
  },
]

export function ComparisonSection() {
  return (
    <section className="px-4 py-20 md:px-8">
      <div className="mx-auto max-w-7xl space-y-10">
        <SectionHeader
          eyebrow="Why AHAL"
          title="Built for teams that need credible engineering intelligence"
          description="The difference is not just prettier output. It is a safer and more defensible workflow."
        />

        <ScrollReveal>
          <GlassCard>
            <div className="grid gap-4 md:grid-cols-[1.2fr_0.4fr_0.4fr]">
              <div className="text-sm uppercase tracking-[0.28em] text-slate-500">Capability</div>
              <div className="text-sm uppercase tracking-[0.28em] text-slate-500">Typical Tools</div>
              <div className="text-sm uppercase tracking-[0.28em] text-slate-500">AHAL AI</div>
              {comparison.map((item) => [
                <div key={`${item.label}-label`} className="border-t border-white/8 py-4 text-white">{item.label}</div>,
                <div key={`${item.label}-traditional`} className="border-t border-white/8 py-4 text-slate-300">
                  {item.traditional ? <Check className="h-5 w-5 text-emerald-300" /> : <X className="h-5 w-5 text-rose-300" />}
                </div>,
                <div key={`${item.label}-ahal`} className="border-t border-white/8 py-4 text-slate-300">
                  {item.ahal ? <Check className="h-5 w-5 text-cyan-300" /> : <X className="h-5 w-5 text-rose-300" />}
                </div>,
              ])}
            </div>
          </GlassCard>
        </ScrollReveal>
      </div>
    </section>
  )
}
