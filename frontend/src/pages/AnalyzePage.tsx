import { useSearchParams } from "react-router-dom"
import { AppShell } from "../components/layout/AppShell"
import { AnalyzeTabs } from "../components/analyze/AnalyzeTabs"
import { GlassCard } from "../components/ui/GlassCard"
import { ScrollReveal } from "../components/ui/ScrollReveal"
import { SectionHeader } from "../components/ui/SectionHeader"
import { isBackendConfigured } from "../lib/ahal-api"
import { DEMO_REPO_URL } from "../lib/demo-fixtures"

export function AnalyzePage() {
  const [searchParams] = useSearchParams()
  const demoRequested = searchParams.get("demo") === "1"

  return (
    <AppShell
      title="Analyze Project"
      subtitle="Create a session from code, a ZIP archive, or a GitHub repository."
      demoMode={!isBackendConfigured()}
    >
      <div className="space-y-8">
        <ScrollReveal>
          <SectionHeader
            eyebrow="New Session"
            title="Start the intelligence workflow"
            description="Every session feeds the dashboard, chat, reports, and export surfaces with a shared analysis context."
          />
        </ScrollReveal>
        {demoRequested ? (
          <ScrollReveal delay={0.04}>
            <GlassCard className="space-y-3">
              <p className="text-xs uppercase tracking-[0.28em] text-cyan-300/70">Public Demo</p>
              <h3 className="text-lg font-semibold text-white">Recommended live demo path</h3>
              <p className="text-sm leading-7 text-slate-400">
                Use the prefilled repo session to exercise the full dashboard flow, including chat, downloads, test gaps,
                onboarding, repository indexing, and delta scanning.
              </p>
              <p className="break-all text-sm text-cyan-100">{DEMO_REPO_URL}</p>
            </GlassCard>
          </ScrollReveal>
        ) : null}
        <ScrollReveal delay={0.08}>
          <AnalyzeTabs />
        </ScrollReveal>
      </div>
    </AppShell>
  )
}
