import { useEffect, useState } from "react"
import { Badge } from "../ui/Badge"
import { getBackendUrl, getHealth, isBackendConfigured } from "../../lib/ahal-api"
import { toFriendlyError } from "../../lib/errors"

type ConnectionState = {
  label: string
  detail: string
  tone: string
  visible: boolean
}

export function ConnectionBanner() {
  const [state, setState] = useState<ConnectionState>(() =>
    isBackendConfigured()
      ? { label: "", detail: "", tone: "", visible: false }
      : {
          label: "Demo Mode",
          detail: "No backend URL is configured, so demo-safe fixtures are available.",
          tone: "border-violet-400/20 bg-violet-500/10 text-violet-200",
          visible: true,
        },
  )

  useEffect(() => {
    let active = true

    async function check() {
      if (!isBackendConfigured()) {
        return
      }

      try {
        const result = await getHealth()
        if (!active) {
          return
        }

        setState({
          label: result.demoMode ? "Demo Mode" : "",
          detail: result.demoMode
            ? "No backend URL is configured, so demo-safe fixtures are available."
            : "",
          tone: result.demoMode
            ? "border-violet-400/20 bg-violet-500/10 text-violet-200"
            : "",
          visible: result.demoMode,
        })
      } catch {
        if (!active) {
          return
        }

        setState({
          label: "Backend Unreachable",
          detail: `Cannot reach AHAL backend at ${getBackendUrl()}. Start FastAPI with python -m app.main.`,
          tone: "border-rose-400/20 bg-rose-500/10 text-rose-200",
          visible: true,
        })
      }
    }

    void check()
    return () => {
      active = false
    }
  }, [])

  if (!state.visible) {
    return null
  }

  return (
    <div className="sticky top-0 z-40 px-4 pt-4 md:px-8">
      <div className={`mx-auto max-w-[1600px] rounded-2xl border px-4 py-3 backdrop-blur-xl ${state.tone}`}>
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <Badge className={state.tone}>{state.label}</Badge>
            <p className="text-sm">{state.detail}</p>
          </div>
          {state.label === "Backend Unreachable" ? <p className="text-xs opacity-80">{toFriendlyError({ network: true })}</p> : null}
        </div>
      </div>
    </div>
  )
}
