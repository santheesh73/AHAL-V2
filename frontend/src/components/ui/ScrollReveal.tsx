import type { ReactNode } from "react"
import { motion, useReducedMotion } from "framer-motion"

type ScrollRevealProps = {
  children: ReactNode
  delay?: number
  direction?: "up" | "down" | "left" | "right" | "none"
  className?: string
}

function getOffset(direction: ScrollRevealProps["direction"]) {
  switch (direction) {
    case "down":
      return { y: -18 }
    case "left":
      return { x: 18 }
    case "right":
      return { x: -18 }
    case "none":
      return {}
    case "up":
    default:
      return { y: 18 }
  }
}

export function ScrollReveal({
  children,
  delay = 0,
  direction = "up",
  className,
}: ScrollRevealProps) {
  const reduceMotion = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, ...getOffset(direction) }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: reduceMotion ? 0.2 : 0.45, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}
