import { useEffect, useState } from "react"
import { Download, FileJson2, FileText, FileType2, LoaderCircle, ShieldCheck } from "lucide-react"
import { downloadPrd, getHealth, getIntelligence, getStatus, isBackendConfigured } from "../../lib/ahal-api"
import { toFriendlyError } from "../../lib/errors"
import { normalizeDownloadError } from "../../lib/trust-adapter"
import type { IntelligenceData, StatusResponse } from "../../lib/types"
import { downloadBlob } from "../../lib/utils"
import { Badge } from "../ui/Badge"
import { Button } from "../ui/Button"
import { GlassCard } from "../ui/GlassCard"

const cards = [
  {
    format: "pdf" as const,
    title: "PDF Report",
    icon: Download,
    extension: ".pdf",
    description: "Client-ready project intelligence report.",
    useCase: "Best for product reviews and stakeholder sharing.",
  },
  {
    format: "markdown" as const,
    title: "Markdown",
    icon: FileText,
    extension: ".md",
    description: "Editable engineering handoff document.",
    useCase: "Best for internal docs and iteration.",
  },
  {
    format: "latex" as const,
    title: "LaTeX",
    icon: FileType2,
    extension: ".tex",
    description: "Academic/technical documentation source.",
    useCase: "Best for technical publishing workflows.",
  },
  {
    format: "json" as const,
    title: "JSON",
    icon: FileJson2,
    extension: ".json",
    description: "Raw structured intelligence output.",
    useCase: "Best for pipelines, tooling, and audits.",
  },
]

export function DownloadCenter({ sessionId }: { sessionId: string }) {
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [intelligence, setIntelligence] = useState<IntelligenceData | null>(null)
  const [healthStatus, setHealthStatus] = useState("Checking backend health...")
  const [loadingFormat, setLoadingFormat] = useState<string | null>(null)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [loadingMeta, setLoadingMeta] = useState(true)

  useEffect(() => {
    let active = true

    async function loadMeta() {
      setLoadingMeta(true)
      try {
        const [statusResult, healthResult] = await Promise.all([
          getStatus(sessionId),
          getHealth(),
        ])
        if (!active) {
          return
        }

        setStatus(statusResult.data)
        setHealthStatus(healthResult.demoMode ? "Demo backend" : healthResult.data.ok ? "Backend healthy" : "Backend responded")

        if (String(statusResult.data.status).toLowerCase() === "completed") {
          const intelligenceResult = await getIntelligence(sessionId)
          if (!active) {
            return
          }
          setIntelligence(intelligenceResult.data)
        }
      } catch (downloadError) {
        if (!active) {
          return
        }
        setError(toFriendlyError(downloadError))
      } finally {
        if (active) {
          setLoadingMeta(false)
        }
      }
    }

    void loadMeta()
    return () => {
      active = false
    }
  }, [sessionId])

  const reportsReady = !loadingMeta && (!status || String(status.status).toLowerCase() === "completed")

  async function handleDownload(format: "pdf" | "markdown" | "latex" | "json") {
    setLoadingFormat(format)
    setError("")
    setSuccess("")
    try {
      const result = await downloadPrd(sessionId, format)
      downloadBlob(result.content, result.filename, result.mimeType)
      setSuccess(`${cards.find((card) => card.format === format)?.title || "Report"} download started.`)
    } catch (downloadError) {
      setError(normalizeDownloadError(downloadError))
    } finally {
      setLoadingFormat(null)
    }
  }

  return (
    <div className="space-y-5">
      <GlassCard className="space-y-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">Report Preview</h3>
            <p className="mt-2 text-sm text-slate-400">
              {reportsReady
                ? "Evidence-backed exports are ready for this completed session."
                : "Reports are available after analysis completes."}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Badge className="border-white/10 bg-white/[0.04] text-slate-300">{healthStatus}</Badge>
            <Badge className="border-emerald-400/20 bg-emerald-400/10 text-emerald-200">Evidence-backed</Badge>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Report Title</p>
            <p className="mt-2 text-sm text-white">{intelligence?.projectName || "Project Intelligence Report"}</p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Project Type</p>
            <p className="mt-2 text-sm text-white">{intelligence?.projectType || "Unknown"}</p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Architecture Confidence</p>
            <p className="mt-2 text-sm text-white">{intelligence?.architectureConfidence || "Unknown"}</p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Purpose Confidence</p>
            <p className="mt-2 text-sm text-white">{intelligence?.productPurposeConfidence || "Unknown"}</p>
          </div>
        </div>
        <div className="flex items-start gap-3 rounded-3xl border border-cyan-400/15 bg-cyan-400/10 p-4 text-sm text-cyan-100">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
          <p>Truth notice: exports are generated from the same cleaned, evidence-backed session intelligence shown in the dashboard.</p>
        </div>
      </GlassCard>

      {error ? <div className="rounded-3xl border border-rose-400/20 bg-rose-500/10 p-4 text-sm text-rose-100/85">{error}</div> : null}
      {success ? <div className="rounded-3xl border border-emerald-400/20 bg-emerald-500/10 p-4 text-sm text-emerald-100/85">{success}</div> : null}

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon
          const loading = loadingFormat === card.format
          const disabled = !reportsReady || loading
          return (
            <GlassCard key={card.format} glow={card.format === "pdf"} className="group flex h-full flex-col justify-between">
              <div>
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] transition duration-300 group-hover:border-cyan-300/30 group-hover:bg-cyan-300/10">
                  {loading ? <LoaderCircle className="h-5 w-5 animate-spin text-cyan-200" /> : <Icon className="h-5 w-5 text-cyan-200" />}
                </div>
                <div className="mt-6 flex items-center justify-between gap-3">
                  <h3 className="text-lg font-semibold text-white">{card.title}</h3>
                  <Badge className="border-white/10 bg-white/[0.04] text-slate-300">{card.extension}</Badge>
                </div>
                <p className="mt-3 text-sm leading-7 text-slate-300">{card.description}</p>
                <p className="mt-2 text-sm text-slate-500">{card.useCase}</p>
                {!reportsReady ? <p className="mt-4 text-xs uppercase tracking-[0.24em] text-amber-200">Reports are available after analysis completes.</p> : null}
              </div>
              <div className="mt-6">
                <Button
                  variant={card.format === "pdf" ? "primary" : "secondary"}
                  onClick={() => void handleDownload(card.format)}
                  disabled={disabled}
                >
                  {loading ? "Preparing..." : `Download ${card.title}`}
                </Button>
              </div>
            </GlassCard>
          )
        })}
      </div>

      {!isBackendConfigured() ? (
        <p className="text-sm text-slate-500">Demo mode is active because no backend URL is configured. Mock exports are only used in that case.</p>
      ) : null}
    </div>
  )
}
