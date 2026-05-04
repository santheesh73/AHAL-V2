import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { FolderGit2 } from "lucide-react"
import { analyzeRepo } from "../../lib/ahal-api"
import { DEMO_REPO_URL } from "../../lib/demo-fixtures"
import { toFriendlyError } from "../../lib/errors"
import { saveSession } from "../../lib/session-store"
import { Button } from "../ui/Button"
import { GlassCard } from "../ui/GlassCard"
import { Input } from "../ui/Input"

export function RepoAnalyzer() {
  const navigate = useNavigate()
  const [repoUrl, setRepoUrl] = useState(DEMO_REPO_URL)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit() {
    if (!repoUrl.startsWith("https://github.com/")) {
      setError("Please enter a valid GitHub repository URL.")
      return
    }

    setLoading(true)
    setError("")
    try {
      const result = await analyzeRepo(repoUrl)
      saveSession(result.data.sessionId, result.data.accessToken)
      navigate(`/dashboard/${result.data.sessionId}`)
    } catch (error) {
      setError(toFriendlyError(error))
    } finally {
      setLoading(false)
    }
  }

  return (
    <GlassCard className="space-y-5">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-400/10">
          <FolderGit2 className="h-5 w-5 text-emerald-200" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">Repo Session</h3>
          <p className="text-sm text-slate-400">Analyze a GitHub repository and land directly in the dashboard.</p>
        </div>
      </div>

      <Input aria-label="Repository URL" value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} placeholder="https://github.com/org/repo" />
      {error ? <p className="text-sm text-rose-300">{error}</p> : null}
      <Button onClick={handleSubmit} disabled={loading}>{loading ? "Analyzing..." : "Analyze Repo"}</Button>
    </GlassCard>
  )
}
