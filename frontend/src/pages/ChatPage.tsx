import { Navigate, useParams } from "react-router-dom"
import { ChatPanel } from "../components/chat/ChatPanel"
import { AppShell } from "../components/layout/AppShell"
import { ScrollReveal } from "../components/ui/ScrollReveal"
import { SectionHeader } from "../components/ui/SectionHeader"
import { isBackendConfigured } from "../lib/ahal-api"

export function ChatPage() {
  const { sessionId } = useParams()

  if (!sessionId) {
    return <Navigate to="/analyze" replace />
  }

  return (
    <AppShell
      title="Repo Chat"
      subtitle="Ask grounded questions about the analyzed project with cleaned evidence references."
      sessionId={sessionId}
      demoMode={!isBackendConfigured()}
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
          <ChatPanel sessionId={sessionId} />
        </ScrollReveal>
      </div>
    </AppShell>
  )
}
