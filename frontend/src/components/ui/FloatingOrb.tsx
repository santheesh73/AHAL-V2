import { motion, useReducedMotion } from "framer-motion"

type FloatingOrbProps = {
  className?: string
  duration?: number
}

export function FloatingOrb({ className, duration = 18 }: FloatingOrbProps) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      className={className}
      animate={
        reduceMotion
          ? { opacity: 0.65 }
          : {
              x: [0, 28, -18, 0],
              y: [0, -32, 18, 0],
              scale: [1, 1.05, 0.98, 1],
            }
      }
      transition={{
        duration,
        repeat: Number.POSITIVE_INFINITY,
        ease: "easeInOut",
      }}
    />
  )
}
