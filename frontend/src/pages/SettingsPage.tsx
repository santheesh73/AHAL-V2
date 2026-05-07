import { useEffect, useState } from "react"
import { getBackendUrl, getHealth, getLlmStatus, isBackendConfigured } from "../lib/ahal-api"
import { toFriendlyError } from "../lib/errors"
import { clearSession, getBackendUrlOverride, getSession, setBackendUrlOverride } from "../lib/session-store"
import { truncateMiddle } from "../lib/utils"
import { AppShell } from "../components/layout/AppShell"
import { Button } from "../components/ui/Button"
import { GlassCard } from "../components/ui/GlassCard"
import { Input } from "../components/ui/Input"
import { SectionHeader } from "../components/ui/SectionHeader"

export function SettingsPage() {
  const session = getSession()
  const [backendUrl, setBackendUrl] = useState(getBackendUrlOverride() || getBackendUrl())
  const [message, setMessage] = useState("")
  const [healthStatus, setHealthStatus] = useState("Checking...")
  const [healthLoading, setHealthLoading] = useState(false)
  const [llmStatus, setLlmStatus] = useState("Checking...")
  const [llmDetail, setLlmDetail] = useState("")

  useEffect(() => {
    let active = true

    async function checkHealth() {
      setHealthLoading(true)
      if (!isBackendConfigured()) {
        if (active) {
          setHealthStatus("Demo Mode")
          setHealthLoading(false)
        }
        return
      }

      try {
        const result = await getHealth()
        if (active) {
          setHealthStatus(result.data.ok ? "Connected" : "Backend responded without healthy status")
        }
      } catch (error) {
        if (active) {
          setHealthStatus(toFriendlyError(error))
        }
      } finally {
        if (active) {
          setHealthLoading(false)
        }
      }
    }

    async function checkLlmStatus() {
      if (!isBackendConfigured()) {
        if (active) {
          setLlmStatus("Demo Mode")
          setLlmDetail("Gemma 4 26B status is available when a live backend is configured.")
        }
        return
      }

      try {
        const result = await getLlmStatus()
        if (active) {
          setLlmStatus(result.data.llm_enabled ? "Gemma 4 26B enabled" : "Fallback mode active")
          setLlmDetail(
            [
              `Chat polish ${result.data.chat_llm_enabled ? "enabled" : "disabled"}`,
              `Docs polish ${result.data.docs_llm_enabled ? "enabled" : "disabled"}`,
              `Last error ${result.data.last_error_type || "none"}`,
              `Fallbacks ${result.data.fallback_count ?? 0}`,
            ].join(" • "),
          )
        }
      } catch (error) {
        if (active) {
          setLlmStatus("Unavailable")
          setLlmDetail(toFriendlyError(error))
        }
      }
    }

    void checkHealth()
    void checkLlmStatus()
    return () => {
      active = false
    }
  }, [])

  function saveUrl() {
    setBackendUrlOverride(backendUrl)
    setMessage("Backend URL preference saved.")
  }

  function resetSession() {
    clearSession()
    setMessage("Session storage cleared.")
  }

  return (
    <AppShell
      title="Settings"
      subtitle="Manage backend connectivity, session state, and demo behavior."
      sessionId={session.sessionId ?? undefined}
      demoMode={!isBackendConfigured()}
    >
      <div className="space-y-8">
        <SectionHeader
          eyebrow="Environment"
          title="Frontend runtime configuration"
          description="Switch between live backend usage and demo-safe fallback behavior without exposing secrets."
        />

        <div className="grid gap-5 xl:grid-cols-2">
          <GlassCard className="space-y-5">
            <h3 className="text-lg font-semibold text-white">Backend URL</h3>
            <Input aria-label="Backend URL" value={backendUrl} onChange={(event) => setBackendUrl(event.target.value)} placeholder="http://localhost:8000" />
            <div className="flex flex-wrap gap-3">
              <Button onClick={saveUrl}>Save Backend URL</Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setBackendUrl("")
                  setBackendUrlOverride("")
                  setMessage("Using environment default or demo mode.")
                }}
              >
                Use Default
              </Button>
            </div>
            <p className="text-sm text-slate-400">Current mode: {!isBackendConfigured() ? "Demo Mode" : "Live backend configured"}</p>
          </GlassCard>

          <GlassCard className="space-y-5">
            <h3 className="text-lg font-semibold text-white">Session Status</h3>
            <div className="space-y-3 text-sm text-slate-300">
              <p>Health Check: {healthLoading ? "Checking..." : healthStatus}</p>
              <p>Session ID: {session.sessionId ? truncateMiddle(session.sessionId) : "No active session"}</p>
              <p>Token Status: {session.accessToken ? "Token saved (hidden)" : "No token saved"}</p>
              <p>Connection: {getBackendUrl() || "Demo mode fallback"}</p>
              <p>LLM Status: {llmStatus}</p>
              <p>LLM Detail: {llmDetail || "No LLM diagnostics yet."}</p>
            </div>
            <Button variant="secondary" onClick={resetSession}>Clear Session</Button>
          </GlassCard>
        </div>

        <GlassCard className="space-y-4">
          <h3 className="text-lg font-semibold text-white">About AHAL AI</h3>
          <p className="text-sm leading-7 text-slate-400">
            AHAL AI is a validated repository intelligence platform that turns code snippets, folders, and GitHub repositories into evidence-backed project understanding, chat workflows, and polished engineering reports.
          </p>
          {message ? <p className="text-sm text-cyan-200">{message}</p> : null}
        </GlassCard>
      </div>
    </AppShell>
  )
}
