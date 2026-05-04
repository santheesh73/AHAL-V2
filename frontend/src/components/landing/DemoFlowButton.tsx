import { useNavigate } from "react-router-dom"
import { isBackendConfigured } from "../../lib/ahal-api"
import { getSession } from "../../lib/session-store"
import { Button } from "../ui/Button"

type DemoFlowButtonProps = {
  variant?: "primary" | "secondary" | "ghost"
  size?: "sm" | "md" | "lg"
  className?: string
  children: string
}

export function DemoFlowButton({ variant = "secondary", size = "lg", className, children }: DemoFlowButtonProps) {
  const navigate = useNavigate()

  function handleClick() {
    const { sessionId } = getSession()

    if (isBackendConfigured()) {
      if (sessionId) {
        navigate(`/dashboard/${sessionId}`)
        return
      }

      navigate("/analyze?tab=repo&demo=1")
      return
    }

    navigate("/dashboard/demo-ahal-session")
  }

  return (
    <Button
      variant={variant}
      size={size}
      className={className}
      onClick={handleClick}
      aria-label="Open the AHAL demo flow"
    >
      {children}
    </Button>
  )
}
