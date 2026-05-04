import type { ReactNode } from "react"
import { Link } from "react-router-dom"
import { ChevronRight, DatabaseZap } from "lucide-react"
import { Badge } from "../ui/Badge"
import { Button } from "../ui/Button"
import { truncateMiddle } from "../../lib/utils"

type TopbarProps = {
  title: string
  subtitle: string
  demoMode?: boolean
  sessionId?: string
  headerMeta?: ReactNode
}

export function Topbar({ title, subtitle, demoMode = false, sessionId, headerMeta }: TopbarProps) {
  return (
    <div className="sticky top-0 z-20 flex flex-col gap-4 border-b border-white/8 bg-slate-950/65 px-4 py-4 backdrop-blur-xl md:px-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.28em] text-slate-500">
            <span>Workspace</span>
            <ChevronRight className="h-3.5 w-3.5" />
            <span>{title}</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">{title}</h1>
          <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {demoMode ? <Badge className="border-violet-400/20 bg-violet-500/10 text-violet-200">Demo Mode</Badge> : null}
          {headerMeta}
          {sessionId ? (
            <Badge className="border-white/10 bg-white/[0.04] text-slate-300">
              <DatabaseZap className="h-3.5 w-3.5" />
              Session {truncateMiddle(sessionId)}
            </Badge>
          ) : null}
          <Link to="/analyze">
            <Button variant="secondary">New Analysis</Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
