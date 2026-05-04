import { Activity, CheckCircle2, Clock3 } from "lucide-react"
import { Badge } from "./Badge"

type StatusBadgeProps = {
  status: "completed" | "active" | "queued"
}

const statusMap = {
  completed: {
    label: "Completed",
    className: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
  },
  active: {
    label: "Active",
    className: "border-cyan-400/20 bg-cyan-400/10 text-cyan-200",
    icon: <Activity className="h-3.5 w-3.5 animate-pulse" />,
  },
  queued: {
    label: "Queued",
    className: "border-amber-400/20 bg-amber-400/10 text-amber-200",
    icon: <Clock3 className="h-3.5 w-3.5" />,
  },
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const item = statusMap[status]
  return <Badge className={item.className}>{item.icon}{item.label}</Badge>
}
