import { LoaderCircle } from "lucide-react"

export function LoadingState({ label = "Loading project intelligence..." }: { label?: string }) {
  return (
    <div className="flex min-h-[220px] flex-col items-center justify-center gap-4 rounded-3xl border border-white/10 bg-white/[0.04] text-center text-slate-300">
      <LoaderCircle className="h-10 w-10 animate-spin text-cyan-300" />
      <p className="text-sm text-slate-400">{label}</p>
    </div>
  )
}
