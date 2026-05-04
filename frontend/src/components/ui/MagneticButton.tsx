import type { ReactNode } from "react"
import { useRef } from "react"
import { motion, useReducedMotion } from "framer-motion"
import { cn } from "../../lib/utils"

export function MagneticButton({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  const buttonRef = useRef<HTMLDivElement | null>(null)
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      ref={buttonRef}
      onMouseMove={(event) => {
        if (reduceMotion || !buttonRef.current) {
          return
        }

        const bounds = buttonRef.current.getBoundingClientRect()
        const x = event.clientX - bounds.left - bounds.width / 2
        const y = event.clientY - bounds.top - bounds.height / 2
        buttonRef.current.style.transform = `translate(${x * 0.06}px, ${y * 0.06}px)`
      }}
      onMouseLeave={() => {
        if (!buttonRef.current) {
          return
        }

        buttonRef.current.style.transform = "translate(0px, 0px)"
      }}
      className={cn("transition-transform duration-300", className)}
    >
      {children}
    </motion.div>
  )
}
