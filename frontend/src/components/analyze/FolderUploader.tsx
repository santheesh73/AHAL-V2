import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { UploadCloud } from "lucide-react"
import { analyzeFolder } from "../../lib/ahal-api"
import { toFriendlyError } from "../../lib/errors"
import { saveSession } from "../../lib/session-store"
import { Button } from "../ui/Button"
import { GlassCard } from "../ui/GlassCard"

export function FolderUploader() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function submit() {
    if (!file) {
      setError("Please choose a ZIP archive to continue.")
      return
    }
    if (!file.name.toLowerCase().endsWith(".zip")) {
      setError("Please upload a .zip archive for folder analysis.")
      return
    }

    setLoading(true)
    setError("")
    try {
      const result = await analyzeFolder(file)
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
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-violet-400/20 bg-violet-400/10">
          <UploadCloud className="h-5 w-5 text-violet-200" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">Folder Session</h3>
          <p className="text-sm text-slate-400">Upload a ZIP archive and let AHAL build a structured project view.</p>
        </div>
      </div>

      <label
        className={`block rounded-[28px] border border-dashed px-6 py-12 text-center transition ${
          dragActive ? "border-cyan-300/50 bg-cyan-300/10" : "border-white/12 bg-white/[0.03]"
        }`}
        onDragEnter={() => setDragActive(true)}
        onDragLeave={() => setDragActive(false)}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault()
          setDragActive(false)
          setFile(event.dataTransfer.files[0] ?? null)
        }}
      >
        <input
          type="file"
          aria-label="Upload ZIP archive"
          accept=".zip"
          className="hidden"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <p className="text-lg font-medium text-white">{file ? file.name : "Drop a ZIP archive here or click to browse"}</p>
        <p className="mt-2 text-sm text-slate-400">The upload flow supports repository scans without exposing raw filesystem details.</p>
      </label>

      {error ? <p className="text-sm text-rose-300">{error}</p> : null}
      <Button onClick={submit} disabled={loading}>{loading ? "Uploading..." : "Analyze Folder"}</Button>
    </GlassCard>
  )
}
