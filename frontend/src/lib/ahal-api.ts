import {
  buildDemoDownload,
  buildDemoSession,
  demoChatResponse,
  demoDiff,
  demoIntelligence,
  demoOnboarding,
  demoTestGaps,
  demoTimeline,
} from "./mock-data"
import {
  humanizeCapability,
  sanitizeEvidenceDetail,
  sanitizePath,
  safeText,
} from "./presentation"
import { getBackendUrlOverride, getToken } from "./session-store"
import {
  normalizeChatResponse as normalizeTrustedChatResponse,
  normalizeIntelligence as normalizeTrustedIntelligence,
  normalizeTimeline as normalizeTrustedTimeline,
  summarizeSessionForFilename,
} from "./trust-adapter"
import type {
  AnalyzeCodePayload,
  AnalyzeResponse,
  ApiResult,
  BackendChatResponse,
  ChatResponse,
  DeltaScanResponse,
  HealthResponse,
  IntelligenceData,
  IntelligenceResponse,
  OnboardingReport,
  OnboardingResponse,
  PrdDiffResponse,
  PrdDiffResult,
  RepoIndexResponse,
  SessionResponse,
  StatusResponse,
  TestGapReport,
  TestGapResponse,
  TimelineEvent,
  TimelineResponse,
} from "./types"

const envApiUrl = import.meta.env.VITE_AHAL_API_URL?.trim() ?? ""
const networkHint =
  "Cannot reach AHAL backend. Make sure FastAPI is running at http://localhost:8000 and CORS allows http://localhost:5173."

export class APIError extends Error {
  status?: number
  code?: string
  network: boolean

  constructor(message: string, options?: { status?: number; code?: string; network?: boolean }) {
    super(message)
    this.name = "APIError"
    this.status = options?.status
    this.code = options?.code
    this.network = options?.network ?? false
  }
}

function trimTrailingSlash(value: string) {
  return value.replace(/\/+$/, "")
}

export function getBackendUrl() {
  const override = getBackendUrlOverride()
  return trimTrailingSlash(override || envApiUrl)
}

export function isBackendConfigured() {
  return Boolean(getBackendUrl())
}

function buildHeaders(extra?: HeadersInit) {
  const token = getToken()
  return {
    ...(token ? { "X-Session-Token": token } : {}),
    ...extra,
  }
}

function friendlyMessage(status: number) {
  switch (status) {
    case 202:
      return "Analysis is still running. Please wait."
    case 400:
      return "The request could not be processed. Please review the input and try again."
    case 401:
      return "Session authorization failed. Start a new analysis."
    case 404:
      return "Session not found. The analysis may have expired."
    case 500:
      return "AHAL backend returned an internal error. Try again or check the backend logs."
    default:
      return "The backend returned an unexpected response."
  }
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") || ""
  if (contentType.includes("application/json")) {
    return response.json()
  }
  return response.text()
}

function extractErrorMessage(body: unknown, status: number) {
  if (body && typeof body === "object") {
    const detail = (body as { detail?: unknown }).detail
    if (typeof detail === "string" && detail.trim()) {
      return detail
    }
    if (detail && typeof detail === "object") {
      const message = (detail as { message?: unknown }).message
      if (typeof message === "string" && message.trim()) {
        return message
      }
    }
  }
  if (typeof body === "string" && body.trim()) {
    return body
  }
  return friendlyMessage(status)
}

async function requestJson<T>(path: string, options: RequestInit, demoFallback: T): Promise<ApiResult<T>> {
  const backendUrl = getBackendUrl()
  if (!backendUrl) {
    return { data: demoFallback, demoMode: true }
  }

  let response: Response
  try {
    response = await fetch(`${backendUrl}${path}`, options)
  } catch {
    throw new APIError(networkHint, { network: true })
  }

  if (!response.ok) {
    const body = await parseResponseBody(response)
    throw new APIError(extractErrorMessage(body, response.status), { status: response.status })
  }

  const data = (await parseResponseBody(response)) as T
  return { data, demoMode: false }
}

async function requestBlob(path: string, format: "pdf" | "markdown" | "latex" | "json", sessionId: string) {
  const shortSessionId = summarizeSessionForFilename(sessionId) || sessionId
  const backendUrl = getBackendUrl()
  if (!backendUrl) {
    const demo = buildDemoDownload(format)
    const extensionMap = {
      pdf: "pdf",
      markdown: "md",
      latex: "tex",
      json: "json",
    }
    return {
      ...demo,
      filename: `ahal-report-${shortSessionId}.${extensionMap[format]}`,
    }
  }

  let response: Response
  try {
    response = await fetch(`${backendUrl}${path}`, {
      headers: buildHeaders(),
    })
  } catch {
    throw new APIError(networkHint, { network: true })
  }

  if (!response.ok) {
    const body = await parseResponseBody(response)
    throw new APIError(extractErrorMessage(body, response.status), { status: response.status })
  }

  const blob = await response.blob()
  const extensionMap = {
    pdf: "pdf",
    markdown: "md",
    latex: "tex",
    json: "json",
  }
  const mimeMap = {
    pdf: "application/pdf",
    markdown: "text/markdown",
    latex: "application/x-tex",
    json: "application/json",
  }

  return {
    content: blob,
    filename: `ahal-report-${shortSessionId}.${extensionMap[format]}`,
    mimeType: blob.type || mimeMap[format],
    demoMode: false,
  }
}

function toArray(value: unknown) {
  return Array.isArray(value) ? value : []
}

function toText(value: unknown, fallback = "") {
  return safeText(value, fallback)
}

function normalizeIntelligence(raw: IntelligenceResponse, fallbackSessionId: string): IntelligenceData {
  return {
    ...normalizeTrustedIntelligence(raw),
    sessionId: toText(raw.session_id, fallbackSessionId),
  }
}

function normalizeChatResponse(raw: BackendChatResponse): ChatResponse {
  return { ...normalizeTrustedChatResponse(raw), demoMode: false }
}

function normalizeTestGapReport(raw: TestGapResponse): TestGapReport {
  const items = toArray(raw.gaps).map((item) => {
    const gap = item as Record<string, unknown>
    return {
      area: humanizeCapability(sanitizePath(toText(gap.target ?? gap.path, "Detected target")) || toText(gap.target ?? gap.path, "Detected target")),
      gap: sanitizeEvidenceDetail(gap.reason) || "A test gap was identified for this area.",
      impact: sanitizeEvidenceDetail(gap.suggested_test) || "Add focused tests to improve coverage.",
    }
  })
  return {
    summary: sanitizeEvidenceDetail(raw.summary) || safeText(raw.summary, "No test gap summary was returned for this session."),
    items,
    warnings: toArray(raw.warnings).filter((item): item is string => typeof item === "string").map((item) => sanitizeEvidenceDetail(item) || safeText(item, "")).filter(Boolean),
  }
}

function normalizeOnboardingReport(raw: OnboardingResponse): OnboardingReport {
  const steps = toArray(raw.reading_order).map((item, index) => {
    const step = item as Record<string, unknown>
    return {
      title: humanizeCapability(sanitizePath(toText(step.title, `Onboarding step ${index + 1}`)) || toText(step.title, `Onboarding step ${index + 1}`)),
      detail: sanitizeEvidenceDetail(step.description ?? step.reason) || "Read the detected entry points and important modules first.",
    }
  })
  return {
    summary: sanitizeEvidenceDetail(raw.summary) || safeText(raw.summary, "No onboarding summary was returned for this session."),
    steps,
    warnings: toArray(raw.warnings).filter((item): item is string => typeof item === "string").map((item) => sanitizeEvidenceDetail(item) || safeText(item, "")).filter(Boolean),
  }
}

function normalizeDiffReport(raw: PrdDiffResponse): PrdDiffResult {
  const changes = toArray(raw.changes).map((item, index) => {
    const change = item as Record<string, unknown>
    return {
      title: humanizeCapability(sanitizePath(toText(change.title, `Change ${index + 1}`)) || toText(change.title, `Change ${index + 1}`)),
      detail: sanitizeEvidenceDetail(change.detail ?? change.summary ?? change.description) || "A project difference was detected.",
    }
  })
  return {
    summary: sanitizeEvidenceDetail(raw.summary) || safeText(raw.summary, "No diff summary is available yet."),
    changes,
  }
}

function normalizeAnalyzeResponse(raw: SessionResponse): AnalyzeResponse {
  return {
    sessionId: raw.session_id,
    accessToken: raw.access_token,
    message: raw.message,
  }
}

export async function analyzeCode(payload: AnalyzeCodePayload) {
  const demo: SessionResponse = {
    session_id: buildDemoSession().data.sessionId,
    access_token: buildDemoSession().data.accessToken,
    status: "accepted",
    message: "Demo code session created.",
  }
  const result = await requestJson<SessionResponse>(
    "/analyze/code",
    {
      method: "POST",
      headers: buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        code: payload.code,
        filename: payload.filename,
        language: payload.language,
        include_llm: false,
      }),
    },
    demo,
  )

  return { ...result, data: normalizeAnalyzeResponse(result.data) }
}

export async function analyzeFolder(file: File) {
  if (!isBackendConfigured()) {
    const demo: SessionResponse = {
      session_id: buildDemoSession().data.sessionId,
      access_token: buildDemoSession().data.accessToken,
      status: "accepted",
      message: "Demo folder session created.",
    }
    return { data: normalizeAnalyzeResponse(demo), demoMode: true }
  }

  const formData = new FormData()
  formData.append("file", file)
  const result = await requestJson<SessionResponse>(
    "/analyze/upload",
    {
      method: "POST",
      headers: buildHeaders(),
      body: formData,
    },
    {
      session_id: buildDemoSession().data.sessionId,
      access_token: buildDemoSession().data.accessToken,
      status: "accepted",
      message: "Demo folder session created.",
    },
  )

  return { ...result, data: normalizeAnalyzeResponse(result.data) }
}

export async function analyzeRepo(repoUrl: string) {
  const demo: SessionResponse = {
    session_id: buildDemoSession().data.sessionId,
    access_token: buildDemoSession().data.accessToken,
    status: "accepted",
    message: "Demo repository session created.",
  }
  const result = await requestJson<SessionResponse>(
    "/analyze/github",
    {
      method: "POST",
      headers: buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        repo_url: repoUrl,
        github_url: repoUrl,
      }),
    },
    demo,
  )

  return { ...result, data: normalizeAnalyzeResponse(result.data) }
}

export async function getStatus(sessionId: string) {
  const demo: StatusResponse = {
    session_id: sessionId,
    status: "completed",
    progress: 100,
    message: "Demo session is ready.",
  }
  return requestJson<StatusResponse>(`/analyze/status/${sessionId}`, { headers: buildHeaders() }, demo)
}

export async function getTimeline(sessionId: string) {
  if (!isBackendConfigured()) {
    return { data: demoTimeline, demoMode: true }
  }
  const result = await requestJson<TimelineResponse>(
    `/analyze/timeline/${sessionId}`,
    { headers: buildHeaders() },
    { session_id: sessionId, events: demoTimeline as unknown as TimelineEvent[] },
  )
  return { ...result, data: normalizeTrustedTimeline(result.data) }
}

export async function getIntelligence(sessionId: string) {
  if (!isBackendConfigured()) {
    return { data: { ...demoIntelligence, sessionId }, demoMode: true }
  }
  const result = await requestJson<IntelligenceResponse>(
    `/analyze/intelligence/${sessionId}`,
    { headers: buildHeaders() },
    demoIntelligence as unknown as IntelligenceResponse,
  )
  return { ...result, data: normalizeIntelligence(result.data, sessionId) }
}

export async function sendChat(sessionId: string, question: string) {
  if (!isBackendConfigured()) {
    return { data: demoChatResponse, demoMode: true }
  }
  const result = await requestJson<BackendChatResponse>(
    `/analyze/chat/${sessionId}`,
    {
      method: "POST",
      headers: buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        question,
        include_history: true,
        max_context_items: 20,
      }),
    },
    {
      answer: demoChatResponse.message.content,
      confidence: "high",
      warnings: demoChatResponse.message.warnings,
      evidence: demoChatResponse.message.evidence as unknown as Array<Record<string, unknown>>,
    },
  )
  return { ...result, data: normalizeChatResponse(result.data) }
}

export async function sendChatStream(
  sessionId: string,
  question: string,
  callbacks?: {
    onStart?: () => void
    onComplete?: (response: ChatResponse) => void
    onError?: (error: unknown) => void
  },
) {
  callbacks?.onStart?.()
  try {
    const result = await sendChat(sessionId, question)
    callbacks?.onComplete?.(result.data)
    return result
  } catch (error) {
    callbacks?.onError?.(error)
    throw error
  }
}

export async function downloadPrd(sessionId: string, format: "pdf" | "markdown" | "latex" | "json") {
  return requestBlob(`/analyze/prd/${sessionId}?format=${format}`, format, sessionId)
}

export async function getTestGaps(sessionId: string) {
  if (!isBackendConfigured()) {
    return { data: demoTestGaps, demoMode: true }
  }
  const result = await requestJson<TestGapResponse>(
    `/analyze/testgap/${sessionId}`,
    { headers: buildHeaders() },
    demoTestGaps as unknown as TestGapResponse,
  )
  return { ...result, data: normalizeTestGapReport(result.data) }
}

export async function getOnboarding(sessionId: string) {
  if (!isBackendConfigured()) {
    return { data: demoOnboarding, demoMode: true }
  }
  const result = await requestJson<OnboardingResponse>(
    `/analyze/onboard/${sessionId}`,
    { headers: buildHeaders() },
    demoOnboarding as unknown as OnboardingResponse,
  )
  return { ...result, data: normalizeOnboardingReport(result.data) }
}

export async function createRepoIndex(sessionId: string) {
  if (!isBackendConfigured()) {
    return {
      data: {
        index_id: "demo-index",
        session_id: sessionId,
        status: "completed",
        source_name: "Demo repository",
        warnings: ["Demo index created because no backend URL is configured."],
      },
      demoMode: true,
    }
  }
  return requestJson<RepoIndexResponse>(
    `/analyze/index/${sessionId}`,
    {
      method: "POST",
      headers: buildHeaders(),
    },
    {
      index_id: "demo-index",
      session_id: sessionId,
      status: "completed",
      source_name: "Demo repository",
      warnings: ["Demo index created because no backend URL is configured."],
    },
  )
}

export async function runDeltaScan(indexId: string, payload: Record<string, unknown> = {}) {
  if (!isBackendConfigured()) {
    return {
      data: {
        index_id: indexId,
        summary: "Demo delta scan completed.",
        new_session_id: "demo-ahal-session",
        warnings: ["Demo mode delta scan used mock output."],
        confidence: "medium",
      },
      demoMode: true,
    }
  }
  return requestJson<DeltaScanResponse>(
    `/analyze/index/${indexId}/delta`,
    {
      method: "POST",
      headers: buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        index_id: indexId,
        ...payload,
      }),
    },
    {
      index_id: indexId,
      summary: "Demo delta scan completed.",
      new_session_id: "demo-ahal-session",
      warnings: ["Demo mode delta scan used mock output."],
      confidence: "medium",
    },
  )
}

export async function getPrdDiff(baseSessionId: string, targetSessionId: string) {
  if (!isBackendConfigured()) {
    return { data: demoDiff, demoMode: true }
  }
  const result = await requestJson<PrdDiffResponse>(
    `/analyze/prd/${baseSessionId}/diff/${targetSessionId}`,
    { headers: buildHeaders() },
    demoDiff as unknown as PrdDiffResponse,
  )
  return { ...result, data: normalizeDiffReport(result.data) }
}

export async function getHealth() {
  if (!isBackendConfigured()) {
    return { data: { ok: true, status: "demo", service: "AHAL AI Demo" }, demoMode: true }
  }
  const demo: HealthResponse = { ok: true, status: "demo", service: "AHAL AI Demo" }
  return requestJson<HealthResponse>("/health", { headers: buildHeaders() }, demo)
}
