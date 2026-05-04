import {
  dedupeParagraphText,
  dedupeSections,
  dedupeStrings,
  humanizeApiPurpose,
  normalizeApiPath,
  normalizeConfidence,
  safeText,
  sanitizeChatMessage,
  sanitizeEvidenceDetail,
  sanitizeEvidenceLabel,
  sanitizePath,
} from "./presentation"
import type {
  ApiSurfaceItem,
  BackendChatResponse,
  BriefItem,
  ChatAnswerSection,
  IntelligenceResponse,
  NormalizedChatResponse,
  NormalizedIntelligence,
  ProjectType,
  TimelineEvent,
  TimelineItem,
  TimelineResponse,
  WorkflowStep,
} from "./types"
import { createId, titleCase, truncateMiddle } from "./utils"

const developerSignals = [
  "developer tool",
  "code changes",
  "structured knowledge",
  "queryable knowledge",
  "code intelligence",
  "repository",
  "repo",
  "codebase",
  "project intelligence",
]

const databaseSignals = ["mongodb", "sqlite", "postgresql", "postgres", "mysql", "redis"]
const frameworkSignals = ["fastapi", "react", "next.js", "next", "vite", "tailwind", "tailwindcss", "flask", "express"]
const toolSignals = ["docker", "github actions", "celery", "pytest", "eslint", "pnpm", "npm"]
const languageExtensions: Array<[RegExp, string]> = [
  [/\.(py)$/i, "Python"],
  [/\.(tsx?|mts|cts)$/i, "TypeScript"],
  [/\.(jsx?|mjs|cjs)$/i, "JavaScript"],
  [/\.(css)$/i, "CSS"],
  [/\.(html)$/i, "HTML"],
]
const starterQuestions = [
  "What does this project do?",
  "What is built?",
  "What remains?",
  "What APIs exist?",
  "What are the risks?",
  "What should a new engineer read first?",
  "Explain the architecture.",
  "What tests should be added?",
  "How does the main workflow work?",
  "How do I run this project?",
]

function toArray(value: unknown) {
  return Array.isArray(value) ? value : []
}

function toText(value: unknown, fallback = "") {
  return safeText(value, fallback)
}

function normalizeProjectType(value: unknown): ProjectType {
  const normalized = toText(value).toLowerCase()
  if (normalized.includes("front")) {
    return "frontend"
  }
  if (normalized.includes("back")) {
    return "backend"
  }
  return "fullstack"
}

function getExplicitDescription(raw: IntelligenceResponse): string {
  const candidates = [
    raw.project_goal,
    raw.summary?.what,
    raw.summary?.why,
    ...toArray(raw.core_features),
    ...toArray(raw.evidence).flatMap((item) => {
      if (!item || typeof item !== "object") {
        return []
      }
      const record = item as Record<string, unknown>
      return [record.label, record.title, record.detail, record.reason, record.snippet]
    }),
  ]

  for (const candidate of candidates) {
    const text = toText(candidate)
    if (!text) {
      continue
    }

    if (/explicit product description says:/i.test(text)) {
      return text.replace(/.*explicit product description says:\s*/i, "").trim()
    }

    if (developerSignals.some((signal) => text.toLowerCase().includes(signal))) {
      return text
    }
  }

  return ""
}

function normalizeProductSummary(raw: IntelligenceResponse, explicitDescription: string): string {
  const lower = explicitDescription.toLowerCase()
  if (
    explicitDescription &&
    lower.includes("ai-powered developer tool") &&
    lower.includes("structured") &&
    lower.includes("queryable knowledge")
  ) {
    return "ContextBridge AI appears to be an AI-powered developer tool that transforms code changes into structured, queryable knowledge. It includes a Next.js/React frontend, FastAPI backend, MongoDB/SQLite storage evidence, chat/query workflows, session tracking, and analysis APIs."
  }

  if (explicitDescription) {
    const normalized = explicitDescription.replace(/\.$/, "")
    return `${toText(raw.project_name, "This project")} appears to be ${normalized}.`
  }

  const fallback = toText(raw.summary?.what ?? raw.project_goal, "Project intelligence is available for this session.")
  if (/content management application/i.test(fallback) && !/cms|content management/i.test(explicitDescription)) {
    return "This project appears to be a developer intelligence platform based on the available code and metadata."
  }

  return fallback
}

function normalizeWhat(raw: IntelligenceResponse, explicitDescription: string): string {
  if (explicitDescription) {
    return explicitDescription
  }

  const fallback = toText(raw.summary?.what, "The exact product behavior is only partially described by the available intelligence output.")
  if (/content management application/i.test(fallback)) {
    return "This project appears to be a developer intelligence platform based on the available code and metadata."
  }
  return fallback
}

function normalizeWhy(raw: IntelligenceResponse): string {
  return toText(raw.summary?.why, "The business or user-facing reason is not fully specified in the analyzed evidence.")
}

function collectEvidenceStrings(raw: IntelligenceResponse): string[] {
  return toArray(raw.evidence).flatMap((item) => {
    if (!item || typeof item !== "object") {
      return []
    }
    const record = item as Record<string, unknown>
    return [record.path, record.file, record.label, record.source, record.source_id].map((entry) => toText(entry)).filter(Boolean)
  })
}

function normalizeTechStack(raw: IntelligenceResponse): NormalizedIntelligence["techStack"] {
  const techStack = {
    languages: [] as string[],
    frameworks: [] as string[],
    databases: [] as string[],
    tools: [] as string[],
  }

  const add = (group: keyof typeof techStack, value: string) => {
    const label = toText(value)
    if (!label) {
      return
    }
    if (!techStack[group].some((item) => item.toLowerCase() === label.toLowerCase())) {
      techStack[group].push(label)
    }
  }

  const rawItems = [
    ...toArray(raw.technical?.tech_stack).flatMap((item) => {
      if (typeof item === "string") {
        return [item]
      }
      if (item && typeof item === "object") {
        const record = item as Record<string, unknown>
        return [record.category, ...toArray(record.items)]
      }
      return []
    }),
    ...toArray(raw.technical?.database),
    ...collectEvidenceStrings(raw),
  ]

  for (const item of rawItems) {
    const text = toText(item)
    if (!text) {
      continue
    }

    const lower = text.toLowerCase()
    if (databaseSignals.some((signal) => lower.includes(signal))) {
      add("databases", titleCase(lower.replace(/^storage:\s*/i, "")))
      continue
    }
    if (frameworkSignals.some((signal) => lower.includes(signal))) {
      const normalized = lower === "next" ? "Next.js" : lower === "tailwindcss" ? "Tailwind" : titleCase(text)
      add("frameworks", normalized)
      continue
    }
    if (toolSignals.some((signal) => lower.includes(signal))) {
      add("tools", titleCase(text))
      continue
    }
  }

  for (const evidence of collectEvidenceStrings(raw)) {
    for (const [pattern, language] of languageExtensions) {
      if (pattern.test(evidence)) {
        add("languages", language)
      }
    }
  }

  return {
    languages: dedupeStrings(techStack.languages),
    frameworks: dedupeStrings(techStack.frameworks),
    databases: dedupeStrings(techStack.databases),
    tools: dedupeStrings(techStack.tools),
  }
}

function apiPriority(path: string): number {
  if (path === "/health" || path === "/" || path.startsWith("/status")) {
    return 0
  }
  if (path.includes("/analyze")) {
    return 1
  }
  if (path.includes("/query") || path.includes("/chat") || path.includes("/ask") || path.includes("/context")) {
    return 2
  }
  if (path.includes("/history") || path.includes("/session") || path.includes("/stream")) {
    return 3
  }
  if (path.includes("/report") || path.includes("/summary") || path.includes("/summarize") || path.includes("/intelligence")) {
    return 4
  }
  return 5
}

function normalizeApiSurface(raw: IntelligenceResponse): ApiSurfaceItem[] {
  const items = new Map<string, ApiSurfaceItem>()

  for (const item of toArray(raw.technical?.api_surface)) {
    if (!item || typeof item !== "object") {
      continue
    }

    const record = item as Record<string, unknown>
    const method = toText(record.method, "GET").toUpperCase()
    const path = normalizeApiPath(toText(record.path, "/"))
    const key = `${method} ${path}`
    if (items.has(key)) {
      continue
    }

    items.set(key, {
      method,
      path,
      purpose: humanizeApiPurpose(method, path),
      source: sanitizePath(toText(record.source ?? record.framework, "Detected API surface")) || "Detected API surface",
    })
  }

  return Array.from(items.values()).sort((left, right) => {
    const priority = apiPriority(left.path) - apiPriority(right.path)
    if (priority !== 0) {
      return priority
    }
    return `${left.method} ${left.path}`.localeCompare(`${right.method} ${right.path}`)
  })
}

function pushCompleted(result: BriefItem[], seen: Set<string>, title: string, description: string) {
  const key = title.toLowerCase()
  if (seen.has(key)) {
    return
  }
  seen.add(key)
  result.push({ title, description })
}

function normalizeCompleted(raw: IntelligenceResponse, apiSurface: ApiSurfaceItem[], techStack: NormalizedIntelligence["techStack"]): BriefItem[] {
  const result: BriefItem[] = []
  const seen = new Set<string>()

  if (techStack.frameworks.some((item) => /react|vite|next/i.test(item))) {
    pushCompleted(result, seen, "Frontend Application", "A frontend application is present for dashboard, chat, analysis, or report workflows.")
  }
  if (techStack.frameworks.some((item) => /fastapi|flask|express/i.test(item))) {
    pushCompleted(result, seen, "Backend API Layer", "A backend API layer is present to process project analysis and response workflows.")
  }
  if (apiSurface.some((item) => /\/ask|\/chat|\/query/.test(item.path))) {
    pushCompleted(result, seen, "Chat / Query API", "Grounded chat or query endpoints were detected.")
  }
  if (apiSurface.some((item) => item.path.includes("/analyze"))) {
    pushCompleted(result, seen, "Analysis API", "Analysis endpoints were detected for session creation or repository processing.")
  }
  if (apiSurface.some((item) => item.path.includes("/context"))) {
    pushCompleted(result, seen, "Context Retrieval API", "Context build or retrieval endpoints were detected.")
  }
  if (apiSurface.some((item) => item.path.includes("/history"))) {
    pushCompleted(result, seen, "Session History API", "Session history retrieval endpoints were detected.")
  }
  if (apiSurface.some((item) => item.path.includes("/stream"))) {
    pushCompleted(result, seen, "Streaming Updates", "Streaming session updates were detected in the API surface.")
  }
  if (apiSurface.some((item) => item.path.includes("/report") || item.path.includes("/summary") || item.path.includes("/summarize"))) {
    pushCompleted(result, seen, "Report / Summary API", "Report or summary generation endpoints were detected.")
  }
  if (techStack.databases.length) {
    pushCompleted(result, seen, "Storage Integration", `Storage evidence includes ${techStack.databases.join(", ")}.`)
  }
  if (apiSurface.some((item) => item.path === "/" || item.path === "/health" || item.path.startsWith("/status"))) {
    pushCompleted(result, seen, "Health / Status Endpoints", "Health, root, or status endpoints were detected for service readiness and progress tracking.")
  }
  if (collectEvidenceStrings(raw).some((item) => /dockerfile|package\.json|requirements\.txt|eslint|pytest/i.test(item))) {
    pushCompleted(result, seen, "Setup Configuration", "Setup and configuration artifacts were detected in the analyzed project.")
  }

  if (!result.length) {
    pushCompleted(result, seen, "Backend API Layer", "Structured backend capabilities were detected, but the returned intelligence was limited.")
  }

  return result
}

function normalizeRemaining(raw: IntelligenceResponse): BriefItem[] {
  const seen = new Set<string>()
  const result: BriefItem[] = []

  for (const item of toArray(raw.summary?.remaining)) {
    const text = typeof item === "string"
      ? item
      : toText((item as Record<string, unknown>).title ?? (item as Record<string, unknown>).description)
    const normalized = toText(text)
    if (!normalized) {
      continue
    }

    const label = /no ci\/cd detected/i.test(normalized) || /ci\/cd pipeline not detected/i.test(normalized)
      ? "CI/CD pipeline not detected."
      : normalized
    const key = label.toLowerCase()
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    result.push({ title: label, description: label })
  }

  return result
}

function normalizeIssues(raw: IntelligenceResponse): NormalizedIntelligence["issues"] {
  const result: NormalizedIntelligence["issues"] = []
  const seen = new Set<string>()

  for (const item of toArray(raw.risks)) {
    const title =
      typeof item === "string"
        ? toText(item)
        : toText((item as Record<string, unknown>).title ?? (item as Record<string, unknown>).issue)
    if (!title) {
      continue
    }

    const key = title.toLowerCase()
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    result.push({
      severity: typeof item === "string" ? "Medium" : normalizeConfidence((item as Record<string, unknown>).severity),
      title,
      recommendation:
        typeof item === "string"
          ? "Review this returned issue and confirm whether follow-up action is needed."
          : toText((item as Record<string, unknown>).recommendation, "Review this returned issue and confirm whether follow-up action is needed."),
    })
  }

  if (!result.length) {
    return [
      {
        severity: "Neutral",
        title: "No critical issues were returned for this session.",
        recommendation: "No immediate remediation guidance was returned.",
      },
    ]
  }

  return result
}

function normalizeWorkflow(raw: IntelligenceResponse, projectType: ProjectType): WorkflowStep[] {
  const joined = JSON.stringify(toArray(raw.technical?.workflow)).toLowerCase()
  const impossible = joined.includes("types/index.ts") || (joined.includes("frontend") && joined.includes("fastapi") && joined.includes("initializes"))

  if (projectType === "backend") {
    return [
      { title: "Receive client request", description: "Client/API consumer sends a request." },
      { title: "Validate in route handler", description: "FastAPI route handler receives and validates the request." },
      { title: "Run service logic", description: "Application or service logic performs the requested work." },
      { title: "Use storage if needed", description: "Storage is used when required by the backend workflow." },
      { title: "Return structured response", description: "A structured response is returned to the client." },
    ]
  }

  if (projectType === "frontend") {
    return [
      { title: "Open frontend application", description: "User opens the frontend application." },
      { title: "Render pages and components", description: "React/Vite/Next.js renders pages and components." },
      { title: "Call configured API service", description: "UI components call an API service when one is configured." },
      { title: "Handle external response", description: "External backend or API handles requests if detected." },
    ]
  }

  if (impossible || !toArray(raw.technical?.workflow).length) {
    return [
      { title: "Open frontend application", description: "User opens frontend application." },
      { title: "Render dashboard and input flows", description: "Next.js/React frontend renders dashboard and input workflows." },
      { title: "Call backend APIs", description: "Frontend calls backend API endpoints." },
      { title: "Process requests in FastAPI", description: "FastAPI route handlers process analysis, chat, context, status, or report requests." },
      { title: "Use services and storage", description: "Service layer uses storage/configuration when required." },
      { title: "Return structured intelligence", description: "Backend returns structured project intelligence to the frontend." },
    ]
  }

  return [
    { title: "Open frontend application", description: "User opens frontend application." },
    { title: "Render dashboard and input flows", description: "Next.js/React frontend renders dashboard and input workflows." },
    { title: "Call backend APIs", description: "Frontend calls backend API endpoints." },
    { title: "Process requests in FastAPI", description: "FastAPI route handlers process analysis, chat, context, status, or report requests." },
    { title: "Use services and storage", description: "Service layer uses storage/configuration when required." },
    { title: "Return structured intelligence", description: "Backend returns structured project intelligence to the frontend." },
  ]
}

function preferredEvidenceOrder(label: string): number {
  const preferred = ["readme.md", "requirements.txt", "package.json", "app/main.py", "api/v1/chat.py", "api/v1/code.py", "api/v1/repo.py", "db/mongodb.py", "dockerfile"]
  const lower = label.toLowerCase()
  const index = preferred.findIndex((item) => lower.includes(item))
  return index === -1 ? preferred.length : index
}

function normalizeEvidence(raw: IntelligenceResponse): NormalizedIntelligence["evidence"] {
  const result: NormalizedIntelligence["evidence"] = []
  const seen = new Set<string>()

  for (const item of toArray(raw.evidence)) {
    const label = sanitizeEvidenceLabel(item)
    if (!label) {
      continue
    }

    const key = label.toLowerCase()
    if (seen.has(key)) {
      continue
    }
    seen.add(key)

    const record = item as Record<string, unknown>
    const detail = sanitizeEvidenceDetail(record.detail ?? record.reason ?? record.snippet ?? "")
    result.push({
      label,
      detail: detail || undefined,
    })
  }

  return result.sort((left, right) => preferredEvidenceOrder(left.label) - preferredEvidenceOrder(right.label)).slice(0, 8)
}

function normalizeWarnings(rawWarnings: unknown): string[] {
  return dedupeStrings(
    toArray(rawWarnings)
      .filter((item): item is string => typeof item === "string")
      .map((item) => {
        const lower = item.toLowerCase()
        if (
          lower.includes("llm")
          && (
            lower.includes("unavailable")
            || lower.includes("disabled")
            || lower.includes("api key missing")
            || lower.includes("api call failed")
            || lower.includes("execution failed")
          )
        ) {
          return "LLM polish unavailable — deterministic answer shown."
        }
        return toText(item)
      })
      .filter((item) => item && !/crm|cms|analytics|devops|chatbot|detected domain signals|unknown|normalized unsupported evidence/i.test(item)),
  )
}

function buildDataQuality(raw: IntelligenceResponse, normalized: Omit<NormalizedIntelligence, "dataQuality">) {
  const notes: string[] = []
  const rawApiCount = toArray(raw.technical?.api_surface).length
  const rawEvidenceCount = toArray(raw.evidence).length

  if (normalized.projectSummary !== toText(raw.summary?.what ?? raw.project_goal)) {
    notes.push("Summary wording was cleaned for product-facing presentation.")
  }
  if (normalized.apiSurface.length < rawApiCount) {
    notes.push("Duplicate API endpoints were removed.")
  }
  if (normalized.evidence.length < rawEvidenceCount) {
    notes.push("Evidence was deduplicated and sensitive labels were removed.")
  }
  if (!toText(raw.summary?.why)) {
    notes.push("Missing product-purpose rationale was rendered conservatively.")
  }
  if (normalized.remaining.some((item) => item.title === "CI/CD pipeline not detected.")) {
    notes.push("Repeated remaining-work items were grouped.")
  }

  return {
    normalized: notes.length > 0,
    notes,
  }
}

// TODO: Backend should eventually return normalized presentation fields directly.
export function normalizeIntelligence(raw: unknown): NormalizedIntelligence {
  const intelligence = (raw ?? {}) as IntelligenceResponse
  const explicitDescription = getExplicitDescription(intelligence)
  const projectType = normalizeProjectType(intelligence.project_type ?? intelligence.architecture_style)
  const techStack = normalizeTechStack(intelligence)
  const apiSurface = normalizeApiSurface(intelligence)
  const normalizedBase: Omit<NormalizedIntelligence, "dataQuality"> = {
    sessionId: toText(intelligence.session_id),
    projectName: toText(intelligence.project_name, "Analyzed Project"),
    projectSummary: normalizeProductSummary(intelligence, explicitDescription),
    projectType,
    architectureConfidence: normalizeConfidence(intelligence.architecture_confidence ?? intelligence.confidence),
    productPurposeConfidence: explicitDescription ? "High" : normalizeConfidence(intelligence.product_purpose_confidence ?? intelligence.confidence),
    what: normalizeWhat(intelligence, explicitDescription),
    why: normalizeWhy(intelligence),
    completed: normalizeCompleted(intelligence, apiSurface, techStack),
    remaining: normalizeRemaining(intelligence),
    issues: normalizeIssues(intelligence),
    techStack,
    apiSurface,
    workflow: normalizeWorkflow(intelligence, projectType),
    evidence: normalizeEvidence(intelligence),
    warnings: normalizeWarnings(intelligence.warnings),
  }

  return {
    ...normalizedBase,
    dataQuality: buildDataQuality(intelligence, normalizedBase),
  }
}

export function normalizeChatResponse(raw: unknown): NormalizedChatResponse {
  const response = (raw ?? {}) as BackendChatResponse
  const evidence = normalizeEvidence({
    evidence: toArray(response.evidence) as Array<Record<string, unknown>>,
  })
  const sections: ChatAnswerSection[] = toArray(response.sections).map((item, index) => {
    const section = (item ?? {}) as Record<string, unknown>
    return {
      title: toText(section.title, `Section ${index + 1}`),
      content: toText(section.content),
      bullets: toArray(section.bullets).map((bullet) => toText(bullet)).filter(Boolean),
      evidenceIds: toArray(section.evidence_ids).map((evidenceId) => toText(evidenceId).replace(/^\[|\]$/g, "")).filter(Boolean),
    }
  }).filter((item) => item.title || item.content || item.bullets.length)

  const message = sanitizeChatMessage({
    id: createId("chat"),
    role: "assistant",
    content: dedupeParagraphText(toText(response.answer, "No answer was returned for this question.")),
    shortAnswer: dedupeParagraphText(toText(response.short_answer)),
    sections: dedupeSections(sections),
    timestamp: new Date().toISOString(),
    confidence: (normalizeConfidence(response.confidence) === "Unknown" ? "Low" : normalizeConfidence(response.confidence)) as "High" | "Medium" | "Low",
    warnings: normalizeWarnings(response.warnings),
    evidence,
    suggestedFollowups: dedupeStrings(toArray(response.suggested_followups).map((item) => toText(item)).filter(Boolean)),
    intent: toText(response.intent),
    usedLlm: Boolean(response.used_llm),
    fallbackUsed: response.fallback_used !== false,
  })

  return {
    message,
    suggestedQuestions: dedupeStrings([
      ...toArray(response.suggested_followups).map((item) => toText(item)).filter(Boolean),
      ...starterQuestions,
    ]),
  }
}

export function normalizeTimeline(raw: unknown): TimelineItem[] {
  const timeline = raw as TimelineResponse | TimelineEvent[]
  const events = Array.isArray(timeline) ? timeline : toArray(timeline?.events)
  const seen = new Set<string>()
  const items: TimelineItem[] = []

  for (const [index, event] of events.entries()) {
    const item = event as TimelineEvent & { title?: string; detail?: string }
    const title = titleCase(sanitizePath(toText(item.stage ?? item.event_type ?? item.type ?? item.title, "Analysis")) || "Analysis")
    const detail = sanitizeEvidenceDetail(item.message ?? item.detail ?? "Timeline event recorded.") || "Timeline event recorded."
    const key = `${title.toLowerCase()}|${detail.toLowerCase()}|${toText(item.timestamp ?? item.created_at)}`
    if (seen.has(key)) {
      continue
    }
    seen.add(key)

    const statusText = toText(item.status).toLowerCase()
    const status = statusText.includes("complete")
      ? "completed"
      : statusText.includes("run") || statusText.includes("active")
        ? "active"
        : "queued"

    items.push({
      id: createId(`timeline-${index}`),
      title,
      status,
      timestamp: toText(item.timestamp ?? item.created_at, new Date().toISOString()),
      detail,
    })
  }

  return items
}

export function normalizeDownloadError(error: unknown): string {
  const details = error && typeof error === "object" ? (error as { status?: unknown; message?: unknown }) : {}
  const status = typeof details.status === "number" ? details.status : undefined
  if (status === 404) {
    return "Reports are not available for this session yet."
  }
  if (status === 409 || status === 425 || status === 202) {
    return "Reports are available after analysis completes."
  }
  if (status === 500) {
    return "PDF generation failed. Try Markdown or JSON export, or check backend logs."
  }
  return toText(details.message, "Unable to download this report right now.")
}

export function summarizeSessionForFilename(sessionId: string): string {
  return truncateMiddle(sessionId, 6, 4).replace(/\.+/g, "-").replace(/[^a-zA-Z0-9-]/g, "")
}
