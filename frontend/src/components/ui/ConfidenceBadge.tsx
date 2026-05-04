import { Badge } from "./Badge"

type ConfidenceBadgeProps = {
  value: string
}

const confidenceClasses = {
  High: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
  Medium: "border-cyan-400/20 bg-cyan-400/10 text-cyan-200",
  Low: "border-violet-400/20 bg-violet-400/10 text-violet-200",
  Unknown: "border-slate-400/20 bg-slate-400/10 text-slate-200",
}

export function ConfidenceBadge({ value }: ConfidenceBadgeProps) {
  const level = (value || "Unknown") as keyof typeof confidenceClasses
  return <Badge className={confidenceClasses[level] ?? confidenceClasses.Unknown}>{level}</Badge>
}
