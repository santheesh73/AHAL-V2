import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import {
  createRepoIndex,
  getIntelligence,
  getOnboarding,
  getPrdDiff,
  getStatus,
  getTestGaps,
  getTimeline,
  isBackendConfigured,
  runDeltaScan,
} from "../lib/ahal-api"
import { toFriendlyError } from "../lib/errors"
import { demoSessionId } from "../lib/mock-data"
import { safeText } from "../lib/presentation"
import { getToken } from "../lib/session-store"
import type { IntelligenceData, OnboardingReport, PrdDiffResult, StatusResponse, TestGapReport, TimelineItem } from "../lib/types"
import { AppShell } from "../components/layout/AppShell"
import { ApiSurfaceTable } from "../components/dashboard/ApiSurfaceTable"
import { EvidenceList } from "../components/dashboard/EvidenceList"
import { ProjectBriefGrid } from "../components/dashboard/ProjectBriefGrid"
import { RiskPanel } from "../components/dashboard/RiskPanel"
import { TechnicalGrid } from "../components/dashboard/TechnicalGrid"
import { TimelinePanel } from "../components/dashboard/TimelinePanel"
import { WorkflowPanel } from "../components/dashboard/WorkflowPanel"
import { ArchitectureDiffPanel } from "../components/reports/ArchitectureDiffPanel"
import { OnboardingPanel } from "../components/reports/OnboardingPanel"
import { TestGapPanel } from "../components/reports/TestGapPanel"
import { Badge } from "../components/ui/Badge"
import { Button } from "../components/ui/Button"
import { ErrorState } from "../components/ui/ErrorState"
import { GlassCard } from "../components/ui/GlassCard"
import { LoadingState } from "../components/ui/LoadingState"
import { ScrollReveal } from "../components/ui/ScrollReveal"
import { SectionHeader } from "../components/ui/SectionHeader"

const MAX_STATUS_ATTEMPTS = 60
const POLL_INTERVAL_MS = 1500

function getIndexStorageKey(sessionId: string) {
  return `ahal_index_id_${sessionId}`
}

export function DashboardPage() {
  const { sessionId } = useParams()
  const resolvedSessionId = sessionId ?? demoSessionId
  const usingDemoSession = !sessionId || sessionId === demoSessionId
  const [intelligence, setIntelligence] = useState<IntelligenceData | null>(null)
  const [timeline, setTimeline] = useState<TimelineItem[]>([])
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [demoMode, setDemoMode] = useState(usingDemoSession || !isBackendConfigured())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [testGaps, setTestGaps] = useState<TestGapReport | null>(null)
  const [testGapsLoading, setTestGapsLoading] = useState(false)
  const [testGapsUnavailable, setTestGapsUnavailable] = useState(false)
  const [onboarding, setOnboarding] = useState<OnboardingReport | null>(null)
  const [onboardingLoading, setOnboardingLoading] = useState(false)
  const [onboardingUnavailable, setOnboardingUnavailable] = useState(false)
  const [diff, setDiff] = useState<PrdDiffResult | null>(null)
  const [indexId, setIndexId] = useState(() => localStorage.getItem(getIndexStorageKey(resolvedSessionId || "pending")) ?? "")
  const [indexLoading, setIndexLoading] = useState(false)
  const [deltaLoading, setDeltaLoading] = useState(false)
  const [deltaMessage, setDeltaMessage] = useState("")
  const [actionMessage, setActionMessage] = useState("")

  useEffect(() => {
    let active = true
    let attempts = 0
    let timeoutId: number | undefined
    let finalized = false

    async function finalizeSession() {
      if (finalized) {
        return
      }
      finalized = true
      const [intelligenceResult, timelineResult] = await Promise.all([
        getIntelligence(resolvedSessionId),
        getTimeline(resolvedSessionId),
      ])
      if (!active) {
        return
      }

      setIntelligence(intelligenceResult.data)
      setTimeline(timelineResult.data)
      setDemoMode(intelligenceResult.demoMode || timelineResult.demoMode)
      setLoading(false)
    }

    async function poll() {
      try {
        const [statusResult, timelineResult] = await Promise.all([getStatus(resolvedSessionId), getTimeline(resolvedSessionId)])
        if (!active) {
          return
        }

        setStatus(statusResult.data)
        setTimeline(timelineResult.data)
        setDemoMode(statusResult.demoMode || timelineResult.demoMode)

        const currentStatus = String(statusResult.data.status || "").toLowerCase()
        if (currentStatus === "completed") {
          await finalizeSession()
          return
        }

        if (currentStatus === "failed") {
          setError(statusResult.data.error || statusResult.data.message || "This analysis session failed before intelligence could be generated.")
          setLoading(false)
          return
        }

        attempts += 1
        if (attempts >= MAX_STATUS_ATTEMPTS) {
          setError("The analysis is taking longer than expected. Please refresh the dashboard in a moment.")
          setLoading(false)
          return
        }

        timeoutId = window.setTimeout(() => {
          void poll()
        }, POLL_INTERVAL_MS)
      } catch (error) {
        if (!active) {
          return
        }
        if ((error as { status?: number })?.status === 401 && !getToken()) {
          setError("This session requires authorization. Start a new analysis.")
        } else {
          setError(toFriendlyError(error))
        }
        setLoading(false)
      }
    }

    if (usingDemoSession || !isBackendConfigured()) {
      void finalizeSession()
    } else {
      void poll()
    }

    return () => {
      active = false
      if (timeoutId) {
        window.clearTimeout(timeoutId)
      }
    }
  }, [resolvedSessionId, usingDemoSession])

  async function loadTestGaps() {
    setTestGapsLoading(true)
    setTestGapsUnavailable(false)
    setActionMessage("")
    try {
      const result = await getTestGaps(resolvedSessionId)
      setTestGaps(result.data)
      setActionMessage("Test gap report loaded.")
    } catch (error) {
      if ((error as { status?: number })?.status === 404) {
        setTestGapsUnavailable(true)
      } else {
        setError(toFriendlyError(error))
      }
    } finally {
      setTestGapsLoading(false)
    }
  }

  async function loadOnboarding() {
    setOnboardingLoading(true)
    setOnboardingUnavailable(false)
    setActionMessage("")
    try {
      const result = await getOnboarding(resolvedSessionId)
      setOnboarding(result.data)
      setActionMessage("Onboarding report loaded.")
    } catch (error) {
      if ((error as { status?: number })?.status === 404) {
        setOnboardingUnavailable(true)
      } else {
        setError(toFriendlyError(error))
      }
    } finally {
      setOnboardingLoading(false)
    }
  }

  async function handleCreateIndex() {
    setIndexLoading(true)
    setDeltaMessage("")
    setActionMessage("")
    try {
      const result = await createRepoIndex(resolvedSessionId)
      const newIndexId = result.data.index_id
      localStorage.setItem(getIndexStorageKey(resolvedSessionId), newIndexId)
      setIndexId(newIndexId)
      setDeltaMessage(`Repository index created: ${newIndexId}`)
      setActionMessage("Repository index created successfully.")
    } catch (error) {
      setError(toFriendlyError(error))
    } finally {
      setIndexLoading(false)
    }
  }

  async function handleDeltaScan() {
    if (!indexId) {
      return
    }

    setDeltaLoading(true)
    setDeltaMessage("")
    setActionMessage("")
    try {
      const deltaResult = await runDeltaScan(indexId, {})
      const newSessionId = deltaResult.data.new_session_id
      setDeltaMessage(deltaResult.data.summary || "Delta scan completed.")
      setActionMessage("Delta scan completed.")
      if (newSessionId) {
        const diffResult = await getPrdDiff(resolvedSessionId, newSessionId)
        setDiff(diffResult.data)
      }
    } catch (error) {
      const message = toFriendlyError(error)
      if ((error as { status?: number })?.status === 400) {
        setDeltaMessage("Delta scan needs changed files or a newer indexed version.")
      } else {
        setError(message)
      }
    } finally {
      setDeltaLoading(false)
    }
  }

  if (loading) {
    return (
      <AppShell
        title="Dashboard"
        subtitle="Analysis is running."
        sessionId={resolvedSessionId}
        demoMode={demoMode}
      >
        <div className="space-y-6">
          <LoadingState
            label={
              status
                ? `Status: ${status.status}${typeof status.progress === "number" ? ` (${status.progress}%)` : ""}`
                : "Waiting for the backend to complete analysis..."
            }
          />
          <TimelinePanel items={timeline} />
        </div>
      </AppShell>
    )
  }

  if (error) {
    return (
      <AppShell title="Dashboard" subtitle="Project intelligence could not be loaded." sessionId={resolvedSessionId} demoMode={demoMode}>
        <div className="space-y-4">
          <ErrorState description={error} onRetry={() => window.location.reload()} />
          <div className="flex flex-wrap gap-3">
            <Link to="/analyze"><Button variant="secondary">Start New Analysis</Button></Link>
          </div>
        </div>
      </AppShell>
    )
  }

  if (!intelligence) {
    return (
      <AppShell title="Dashboard" subtitle="No intelligence is available yet." sessionId={resolvedSessionId} demoMode={demoMode}>
        <ErrorState description="The dashboard did not receive project intelligence for this session." />
      </AppShell>
    )
  }

  const repoType = String(intelligence.repoType || intelligence.projectType).toLowerCase()
  const isDocumentationRepo = ["documentation", "curriculum", "knowledge_base"].includes(repoType)
  const isPackageRepo = ["python_package", "npm_package", "component_library", "sdk"].includes(repoType)
  const isDatasetRepo = repoType === "dataset"
  const workflowTitle = isDocumentationRepo ? "Repository Structure" : "Workflow"
  const apiTitle = isDatasetRepo ? "Dataset Overview" : isPackageRepo ? "Package/API Surface" : "API Surface"
  const apiEmptyMessage = isDatasetRepo
    ? "No dataset records were detected for this session."
    : isPackageRepo
      ? "No HTTP API endpoints were detected. This repository appears to expose package/library APIs instead."
      : "No API endpoints were detected for this session."
  const showApiSurface = !isDocumentationRepo || intelligence.apiSurface.length > 0 || isPackageRepo || isDatasetRepo

  return (
    <AppShell
      title={intelligence.projectName}
      subtitle={
        intelligence.productPurposeConfidence === "Low"
          ? "Exact product purpose is not fully specified from analyzed evidence."
          : intelligence.productPurposeConfidence === "Medium"
            ? "Product purpose is partially inferred from available code and metadata."
          : safeText(intelligence.projectSummary, "Project intelligence is available for this session.")
      }
      sessionId={resolvedSessionId}
      demoMode={demoMode}
      headerMeta={
        intelligence.dataQuality.normalized ? (
          <Badge
            className="border-cyan-400/20 bg-cyan-400/10 text-cyan-100"
            title="Raw evidence was cleaned, deduplicated, and grouped for readability."
          >
            Normalized for presentation
          </Badge>
        ) : undefined
      }
    >
      <div className="space-y-6">
        <ScrollReveal>
          <SectionHeader
            eyebrow="Project Intelligence"
            title="Validated summary, architecture, and action surfaces"
            description="Confidence, evidence, and follow-up reports stay visible together so the product story remains grounded and readable."
            action={
              <div className="flex flex-wrap gap-3">
                <Link to={`/chat/${resolvedSessionId}`}><Button variant="secondary">Chat with Project</Button></Link>
                <Link to={`/downloads/${resolvedSessionId}`}><Button>Download Reports</Button></Link>
              </div>
            }
          />
        </ScrollReveal>

        <ScrollReveal delay={0.04}><ProjectBriefGrid intelligence={intelligence} /></ScrollReveal>
        <ScrollReveal delay={0.08}><TechnicalGrid intelligence={intelligence} /></ScrollReveal>
        {showApiSurface ? (
          <ScrollReveal delay={0.1}><ApiSurfaceTable items={intelligence.apiSurface} title={apiTitle} emptyMessage={apiEmptyMessage} /></ScrollReveal>
        ) : null}
        <ScrollReveal delay={0.12}><WorkflowPanel steps={intelligence.workflow} title={workflowTitle} /></ScrollReveal>
        <ScrollReveal delay={0.14}><TimelinePanel items={timeline} /></ScrollReveal>
        <ScrollReveal delay={0.16}><RiskPanel items={intelligence.issues.map((item) => ({
          severity: item.severity === "Unknown" || item.severity === "Neutral" ? "Low" : item.severity as "High" | "Medium" | "Low",
          issue: item.title,
          recommendation: item.recommendation,
        }))} /></ScrollReveal>

        <div className="grid gap-5 xl:grid-cols-3">
        <ScrollReveal delay={0.18}>
            <TestGapPanel
              report={testGaps}
              loading={testGapsLoading}
              unavailable={testGapsUnavailable}
              onLoad={() => void loadTestGaps()}
            />
          </ScrollReveal>
          <ScrollReveal delay={0.2}>
            <OnboardingPanel
              report={onboarding}
              loading={onboardingLoading}
              unavailable={onboardingUnavailable}
              onLoad={() => void loadOnboarding()}
            />
          </ScrollReveal>
          <ScrollReveal delay={0.22}><ArchitectureDiffPanel diff={diff} /></ScrollReveal>
        </div>

        <ScrollReveal delay={0.24}><EvidenceList items={intelligence.evidence} /></ScrollReveal>

        <ScrollReveal delay={0.26}>
          <GlassCard className="space-y-4">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">Action Center</h3>
                <p className="mt-2 text-sm text-slate-400">
                  Trigger more outputs from the same session without restarting the workflow.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link to={`/chat/${resolvedSessionId}`}><Button>Open Repo Chat</Button></Link>
                <Link to={`/downloads/${resolvedSessionId}`}><Button variant="secondary">Download Reports</Button></Link>
                <Button variant="secondary" onClick={() => void loadTestGaps()} disabled={testGapsLoading}>
                  {testGapsLoading ? "Loading Test Gaps..." : "Load Test Gaps"}
                </Button>
                <Button variant="secondary" onClick={() => void loadOnboarding()} disabled={onboardingLoading}>
                  {onboardingLoading ? "Generating Onboarding..." : "Generate Onboarding Report"}
                </Button>
                <Button variant="secondary" onClick={handleCreateIndex} disabled={indexLoading}>
                  {indexLoading ? "Creating Index..." : "Create Repo Index"}
                </Button>
                <Button variant="secondary" onClick={handleDeltaScan} disabled={!indexId || deltaLoading}>
                  {deltaLoading ? "Running Delta..." : "Run Delta Scan"}
                </Button>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-300">
                Repository Index: {indexId || "Not created yet"}
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-300">
                {deltaMessage || "Create an index before running delta scan comparisons."}
              </div>
            </div>
            {actionMessage ? <p className="text-sm text-cyan-200">{actionMessage}</p> : null}
          </GlassCard>
        </ScrollReveal>
      </div>
    </AppShell>
  )
}
