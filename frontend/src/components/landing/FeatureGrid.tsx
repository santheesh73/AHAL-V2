import {
  Boxes,
  FileArchive,
  FileText,
  FolderGit2,
  GitBranch,
  MessageCircleCode,
  Puzzle,
  TestTube2,
  UserRoundSearch,
} from "lucide-react"
import { motion } from "framer-motion"
import { GlassCard } from "../ui/GlassCard"
import { GlowBorder } from "../ui/GlowBorder"
import { ScrollReveal } from "../ui/ScrollReveal"
import { SectionHeader } from "../ui/SectionHeader"

const features = [
  { title: "Code Intelligence", icon: Boxes, detail: "Turn raw source files into architecture, module, and workflow insights." },
  { title: "Folder Analysis", icon: FileArchive, detail: "Upload ZIP archives to generate evidence-backed project summaries." },
  { title: "GitHub Repo Intelligence", icon: FolderGit2, detail: "Analyze full repositories with session-aware project intelligence." },
  { title: "Repo Chat", icon: MessageCircleCode, detail: "Ask grounded questions about APIs, risks, architecture, and intent." },
  { title: "PRD/PDF Reports", icon: FileText, detail: "Export professional documentation for product, onboarding, and reporting." },
  { title: "Architecture Diff", icon: GitBranch, detail: "Compare changes between scans to understand technical movement quickly." },
  { title: "Test Gap Detector", icon: TestTube2, detail: "Spot missing coverage in integration, workflow, and export surfaces." },
  { title: "Onboarding Report", icon: UserRoundSearch, detail: "Guide new contributors through the important areas of a codebase." },
  { title: "MCP Agent Tools", icon: Puzzle, detail: "Expose project intelligence to agent workflows without sacrificing evidence grounding." },
]

export function FeatureGrid() {
  return (
    <section className="px-4 py-20 md:px-8">
      <div className="mx-auto max-w-7xl space-y-10">
        <SectionHeader
          eyebrow="Core Capabilities"
          title="Purpose-built intelligence surfaces for engineering work"
          description="Each surface is designed to keep the output useful, defensible, and production-friendly."
        />
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <ScrollReveal key={feature.title} delay={index * 0.05}>
                <motion.div whileHover={{ y: -6 }} className="group h-full">
                  <GlowBorder>
                    <GlassCard className="h-full">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] transition duration-300 group-hover:border-cyan-300/30 group-hover:bg-cyan-300/10">
                        <Icon className="h-5 w-5 text-cyan-200 transition duration-300 group-hover:scale-110" />
                      </div>
                      <h3 className="mt-6 text-lg font-semibold text-white">{feature.title}</h3>
                      <p className="mt-3 text-sm leading-7 text-slate-400">{feature.detail}</p>
                    </GlassCard>
                  </GlowBorder>
                </motion.div>
              </ScrollReveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}
