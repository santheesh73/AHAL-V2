import type { ReactNode } from "react"
import { Sidebar } from "./Sidebar"
import { Topbar } from "./Topbar"

type AppShellProps = {
  title: string
  subtitle: string
  children: ReactNode
  sessionId?: string
  demoMode?: boolean
  headerMeta?: ReactNode
}

export function AppShell({ title, subtitle, children, sessionId, demoMode, headerMeta }: AppShellProps) {
  return (
    <div className="relative min-h-screen text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        <Sidebar sessionId={sessionId} />
        <div className="flex min-h-screen flex-1 flex-col">
          <Topbar title={title} subtitle={subtitle} sessionId={sessionId} demoMode={demoMode} headerMeta={headerMeta} />
          <main className="flex-1 px-4 py-6 pb-24 md:px-8 md:py-8 lg:pb-8">{children}</main>
        </div>
      </div>
    </div>
  )
}
