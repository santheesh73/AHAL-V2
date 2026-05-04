import { AlertTriangle } from "lucide-react"
import { Button } from "./Button"

type ErrorStateProps = {
  title?: string
  description: string
  onRetry?: () => void
}

export function ErrorState({
  title = "Something interrupted the workflow",
  description,
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="rounded-3xl border border-rose-400/20 bg-rose-500/10 p-8 text-slate-100">
      <div className="flex items-start gap-4">
        <AlertTriangle className="mt-1 h-5 w-5 text-rose-300" />
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">{title}</h3>
          <p className="max-w-2xl text-sm text-rose-100/80">{description}</p>
          {onRetry ? <Button variant="secondary" onClick={onRetry}>Try Again</Button> : null}
        </div>
      </div>
    </div>
  )
}
