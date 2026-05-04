import type { HTMLAttributes } from "react"
import { cn } from "../../lib/utils"

type GlassCardProps = HTMLAttributes<HTMLDivElement> & {
  glow?: boolean
}

export function GlassCard({ className, glow = false, ...props }: GlassCardProps) {
  return (
    <div
      className={cn(
        "glass-card rounded-3xl border border-white/12 bg-white/[0.06] p-6 shadow-[0_20px_80px_rgba(4,10,30,0.45)] backdrop-blur-xl",
        glow && "shadow-[0_0_0_1px_rgba(103,232,249,0.12),0_20px_80px_rgba(4,10,30,0.55),0_0_60px_rgba(99,102,241,0.12)]",
        className,
      )}
      {...props}
    />
  )
}
