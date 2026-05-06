import { useParams } from "react-router-dom"
import { DownloadCenter } from "../components/downloads/DownloadCenter"
import { AppShell } from "../components/layout/AppShell"
import { ScrollReveal } from "../components/ui/ScrollReveal"
import { SectionHeader } from "../components/ui/SectionHeader"
import { isBackendConfigured } from "../lib/ahal-api"
import { demoSessionId } from "../lib/mock-data"

export function DownloadsPage() {
  const { sessionId } = useParams()
  const resolvedSessionId = sessionId ?? demoSessionId
  const usingDemoSession = !sessionId || sessionId === demoSessionId

  return (
    <AppShell
      title="Downloads"
      subtitle="Export the same intelligence as PDF, Markdown, LaTeX, or JSON."
      sessionId={resolvedSessionId}
      demoMode={usingDemoSession || !isBackendConfigured()}
    >
      <div className="space-y-8">
        <ScrollReveal>
          <SectionHeader
            eyebrow="Report Delivery"
            title="Professional exports for product, engineering, and onboarding workflows"
            description="The download center stays consistent with the same validated session intelligence shown in the dashboard."
          />
        </ScrollReveal>
        <ScrollReveal delay={0.06}>
          <DownloadCenter sessionId={resolvedSessionId} />
        </ScrollReveal>
      </div>
    </AppShell>
  )
}
