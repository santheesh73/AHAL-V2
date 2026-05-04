import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Code2 } from "lucide-react"
import { analyzeCode } from "../../lib/ahal-api"
import { DEMO_CODE_SNIPPET } from "../../lib/demo-fixtures"
import { toFriendlyError } from "../../lib/errors"
import { saveSession } from "../../lib/session-store"
import { Button } from "../ui/Button"
import { GlassCard } from "../ui/GlassCard"
import { Input } from "../ui/Input"
import { Textarea } from "../ui/Textarea"

export function CodeAnalyzer() {
  const navigate = useNavigate()
  const [filename, setFilename] = useState("main.py")
  const [language, setLanguage] = useState("python")
  const [code, setCode] = useState("from fastapi import FastAPI\n\napp = FastAPI()\n")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  function useDemoCode() {
    setFilename("main.py")
    setLanguage("python")
    setCode(DEMO_CODE_SNIPPET)
    setError("")
  }

  async function handleAnalyze() {
    if (!filename.trim() || !language.trim() || !code.trim()) {
      setError("Please provide a filename, language, and code snippet.")
      return
    }

    setLoading(true)
    setError("")
    try {
      const result = await analyzeCode({ filename, language, code })
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
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10">
          <Code2 className="h-5 w-5 text-cyan-200" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">Code Session</h3>
          <p className="text-sm text-slate-400">Paste a focused snippet and create an analysis session immediately.</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <Button variant="secondary" onClick={useDemoCode}>Use Demo Code</Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Input aria-label="Filename" value={filename} onChange={(event) => setFilename(event.target.value)} placeholder="main.py" />
        <Input aria-label="Language" value={language} onChange={(event) => setLanguage(event.target.value)} placeholder="python" />
      </div>

      <Textarea aria-label="Code snippet" value={code} onChange={(event) => setCode(event.target.value)} placeholder="Paste code here..." className="min-h-[260px]" />
      {error ? <p className="text-sm text-rose-300">{error}</p> : null}
      <Button onClick={handleAnalyze} disabled={loading}>{loading ? "Analyzing..." : "Analyze Code"}</Button>
    </GlassCard>
  )
}
