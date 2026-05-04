import type { ReactNode } from "react"
import { motion, type HTMLMotionProps } from "framer-motion"
import { cn } from "../../lib/utils"

type ButtonProps = HTMLMotionProps<"button"> & {
  children?: ReactNode
  variant?: "primary" | "secondary" | "ghost"
  size?: "sm" | "md" | "lg"
  icon?: ReactNode
}

const sizeClasses = {
  sm: "h-10 px-4 text-sm",
  md: "h-11 px-5 text-sm",
  lg: "h-12 px-6 text-base",
}

const variantClasses = {
  primary:
    "bg-gradient-to-r from-cyan-400 via-blue-500 to-violet-500 text-slate-950 shadow-[0_12px_32px_rgba(56,189,248,0.28)] hover:brightness-110",
  secondary:
    "border border-white/15 bg-white/8 text-white hover:bg-white/12",
  ghost:
    "border border-transparent bg-transparent text-slate-300 hover:border-white/10 hover:bg-white/5",
}

export function Button({
  children,
  className,
  variant = "primary",
  size = "md",
  icon,
  ...props
}: ButtonProps) {
  return (
    <motion.button
      whileHover={{ y: -1.5 }}
      whileTap={{ scale: 0.985 }}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-2xl font-medium transition duration-300 focus:outline-none focus:ring-2 focus:ring-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-60",
        sizeClasses[size],
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {icon}
      {children}
    </motion.button>
  )
}
