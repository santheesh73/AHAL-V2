import { AnimatePresence, motion } from "framer-motion"
import { useSearchParams } from "react-router-dom"
import { CodeAnalyzer } from "./CodeAnalyzer"
import { FolderUploader } from "./FolderUploader"
import { RepoAnalyzer } from "./RepoAnalyzer"
import { cn } from "../../lib/utils"

const tabs = [
  { id: "code", label: "Code Session" },
  { id: "folder", label: "Folder Session" },
  { id: "repo", label: "Repo Session" },
]

export function AnalyzeTabs() {
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedTab = searchParams.get("tab")
  const activeTab = requestedTab && tabs.some((tab) => tab.id === requestedTab) ? requestedTab : "code"

  function updateTab(tabId: string) {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set("tab", tabId)
    setSearchParams(nextParams, { replace: true })
  }

  return (
    <div className="space-y-8">
      <div className="inline-flex rounded-2xl border border-white/10 bg-white/[0.04] p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => updateTab(tab.id)}
            className={cn(
              "relative rounded-2xl px-5 py-3 text-sm font-medium text-slate-400 transition",
              activeTab === tab.id && "text-white",
            )}
          >
            {activeTab === tab.id ? (
              <motion.span
                layoutId="active-tab"
                className="absolute inset-0 rounded-2xl bg-white/[0.08]"
                transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
              />
            ) : null}
            <span className="relative">{tab.label}</span>
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        >
          {activeTab === "code" ? <CodeAnalyzer /> : null}
          {activeTab === "folder" ? <FolderUploader /> : null}
          {activeTab === "repo" ? <RepoAnalyzer /> : null}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
