import { ArrowRight } from "lucide-react"
import { ScrollReveal } from "../ui/ScrollReveal"
import { SectionHeader } from "../ui/SectionHeader"

const steps = [
  "Code / Folder / Repo",
  "Extract Facts",
  "Validate Intelligence",
  "Generate Reports",
  "Chat / Diff / Test Gaps",
]

export function WorkflowSection() {
  return (
    <section className="px-4 py-20 md:px-8">
      <div className="mx-auto max-w-7xl">
        <SectionHeader
          eyebrow="Workflow"
          title="A clear path from raw code to usable engineering intelligence"
          description="The product flow is designed as a sequence of validation stages, not a black-box summarizer."
        />

        <div className="mt-12 grid gap-6 lg:grid-cols-5">
          {steps.map((step, index) => (
            <ScrollReveal key={step} delay={index * 0.08}>
              <div className="relative rounded-3xl border border-white/10 bg-white/[0.04] p-6">
                <p className="text-xs uppercase tracking-[0.28em] text-cyan-300/70">Step {index + 1}</p>
                <h3 className="mt-5 text-lg font-semibold text-white">{step}</h3>
                {index < steps.length - 1 ? (
                  <div className="pointer-events-none absolute -right-4 top-1/2 hidden -translate-y-1/2 lg:block">
                    <ArrowRight className="h-5 w-5 text-cyan-200/70" />
                  </div>
                ) : null}
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  )
}
