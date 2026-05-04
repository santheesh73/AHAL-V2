import { FloatingOrb } from "./FloatingOrb"

export function AnimatedBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,#0f1d52_0%,#050811_32%,#02040a_100%)]" />
      <div className="animated-grid absolute inset-0 opacity-30" />
      <FloatingOrb className="absolute left-[-10%] top-[8%] h-72 w-72 rounded-full bg-cyan-400/16 blur-[120px]" duration={24} />
      <FloatingOrb className="absolute right-[-6%] top-[18%] h-80 w-80 rounded-full bg-violet-500/18 blur-[140px]" duration={20} />
      <FloatingOrb className="absolute bottom-[-8%] left-[30%] h-72 w-72 rounded-full bg-emerald-400/12 blur-[120px]" duration={26} />
      <div className="noise-overlay absolute inset-0 opacity-[0.07]" />
    </div>
  )
}
