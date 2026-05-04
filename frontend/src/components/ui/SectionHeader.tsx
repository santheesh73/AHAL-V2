import type { ReactNode } from "react"
import { cn } from "../../lib/utils"

export function SectionHeader({
  eyebrow,
  title,
  description,
  action,
  className,
}: {
  eyebrow?: string
  title: string
  description?: string
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex flex-col gap-4 md:flex-row md:items-end md:justify-between", className)}>
      <div className="space-y-2">
        {eyebrow ? <p className="text-xs uppercase tracking-[0.32em] text-cyan-300/80">{eyebrow}</p> : null}
        <h2 className="text-2xl font-semibold tracking-tight text-white md:text-3xl">{title}</h2>
        {description ? <p className="max-w-2xl text-sm text-slate-400 md:text-base">{description}</p> : null}
      </div>
      {action}
    </div>
  )
}
