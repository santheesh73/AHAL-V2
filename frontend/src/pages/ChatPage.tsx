import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { ChatPanel } from "../components/chat/ChatPanel"
import { AppShell } from "../components/layout/AppShell"
import { ScrollReveal } from "../components/ui/ScrollReveal"
import { SectionHeader } from "../components/ui/SectionHeader"
import { getIntelligence, isBackendConfigured } from "../lib/ahal-api"
import { demoSessionId } from "../lib/mock-data"
import type { IntelligenceData } from "../lib/types"

export function ChatPage() {
  const { sessionId } = useParams()
  const resolvedSessionId = sessionId ?? demoSessionId
  const usingDemoSession = !sessionId || sessionId === demoSessionId
  const [intelligence, setIntelligence] = useState<IntelligenceData | null>(null)

  useEffect(() => {
    let active = true
    void getIntelligence(resolvedSessionId)
      .then((result) => {
        if (active) {
          setIntelligence(result.data)
        }
      })
      .catch(() => {
        if (active) {
          setIntelligence(null)
        }
      })
    return () => {
      active = false
    }
  }, [resolvedSessionId])

  return (
    <AppShell
      title="Repo Chat"
      subtitle="Ask grounded questions about the analyzed project with cleaned evidence references."
      sessionId={resolvedSessionId}
      demoMode={usingDemoSession || !isBackendConfigured()}
    >
      <div className="space-y-8">
        <ScrollReveal>
          <SectionHeader
            eyebrow="Conversational Analysis"
            title="Repo chat with structured answers, grounded evidence, and follow-up guidance"
            description="Use the same validated session context from the dashboard, onboarding, test-gap, and report flows for deeper repository questions."
          />
        </ScrollReveal>
        <ScrollReveal delay={0.06}>
          <ChatPanel sessionId={resolvedSessionId} intelligence={intelligence} />
        </ScrollReveal>
      </div>
    </AppShell>
  )
}
