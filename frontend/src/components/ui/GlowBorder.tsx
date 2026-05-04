import type { ReactNode } from "react"

export function GlowBorder({ children }: { children: ReactNode }) {
  return (
    <div className="relative">
      <div className="pointer-events-none absolute inset-0 rounded-[inherit] bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.22),transparent_48%),radial-gradient(circle_at_bottom,rgba(139,92,246,0.18),transparent_44%)] opacity-0 transition duration-300 group-hover:opacity-100" />
      <div className="relative">{children}</div>
    </div>
  )
}
