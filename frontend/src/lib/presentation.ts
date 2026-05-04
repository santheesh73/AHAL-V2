import { titleCase } from "./utils"
import type { ChatAnswerSection, ChatMessage } from "./types"

const secretTokens = [".env", ".env.example", ".env.local", "credentials", "secret", "token", "private_key", "id_rsa", "mongodb://"]
const filteredEvidenceTokens = [
  "ai_hallucination_detection",
  "ecommerce",
  "detected domain signals for",
  "normalized unsupported evidence",
  "crm",
  "cms",
  "analytics",
  "devops",
  "chatbot",
  "unknown:",
  "magicmock",
  "object at 0x",
  ".env",
  ".env.example",
  "mongodb://",
  "private_key",
  "token",
  "credentials",
  "configuration evidence",
]

function normalizeCompareText(value: string): string {
  return safeText(value, "").toLowerCase().replace(/\s+/g, " ").trim()
}

function paragraphSimilarity(left: string, right: string): number {
  if (!left || !right) {
    return 0
  }
  const a = normalizeCompareText(left)
  const b = normalizeCompareText(right)
  if (!a || !b) {
    return 0
  }
  if (a === b) {
    return 1
  }
  const shorter = a.length < b.length ? a : b
  const longer = a.length < b.length ? b : a
  if (longer.includes(shorter)) {
    return shorter.length / longer.length
  }
  const leftWords = new Set(a.split(" "))
  const rightWords = new Set(b.split(" "))
  const overlap = Array.from(leftWords).filter((word) => rightWords.has(word)).length
  return overlap / Math.max(leftWords.size, rightWords.size, 1)
}

export function sanitizePath(path: string): string {
  const value = safeText(path, "")
  if (!value) {
    return ""
  }

  const lower = value.toLowerCase()
  if (secretTokens.some((token) => lower.includes(token))) {
    return "configuration evidence"
  }

  const normalized = value.replace(/\\/g, "/")
  const parts = normalized.split("/").map((segment) => segment.trim()).filter(Boolean)
  if (!parts.length) {
    return value
  }

  const usefulParts = parts.filter((segment) => {
    const lowerSegment = segment.toLowerCase()
    return ![
      "users",
      "desktop",
      "onedrive",
      "downloads",
      "documents",
      "src",
      "app",
      "ahal v2",
      "ahal ai(final)",
      "ahal ai(fe)",
      "ahal ai after animation",
    ].includes(lowerSegment)
  })

  const tail = (usefulParts.length ? usefulParts : parts).slice(-3)
  if (tail.length >= 2 && tail[tail.length - 1].includes(".")) {
    return tail.slice(-2).join("/")
  }
  return tail.join("/")
}

export function toPathSegments(path: string): string[] {
  const normalized = safeText(path, "").replace(/\\/g, "/")
  return normalized.split("/").map((segment) => segment.trim()).filter(Boolean)
}

export function sanitizeEvidenceDetail(value: unknown): string {
  const text = safeText(value, "")
  if (!text) {
    return ""
  }

  const lower = text.toLowerCase()
  if (secretTokens.some((token) => lower.includes(token))) {
    return "Sensitive configuration evidence was omitted."
  }

  if (filteredEvidenceTokens.some((token) => lower.includes(token))) {
    return ""
  }

  return text.replace(/[A-Za-z]:\\Users\\[^\\\s]+\\[^,;]*/gi, (match) => sanitizePath(match)).replace(/\/[A-Za-z0-9_.-]+(?:\/[A-Za-z0-9_.-]+){3,}/g, (match) => sanitizePath(match))
}

export function sanitizeEvidenceLabel(item: unknown): string {
  if (!item || typeof item !== "object") {
    return ""
  }

  const record = item as Record<string, unknown>
  const raw =
    record.label ??
    record.title ??
    record.path ??
    record.file ??
    record.source ??
    record.source_id ??
    record.reason

  const text = safeText(raw, "")
  if (!text) {
    return ""
  }

  const lower = text.toLowerCase()
  if (filteredEvidenceTokens.some((token) => lower.includes(token))) {
    return ""
  }

  const sanitized = sanitizePath(text)
  const sanitizedLower = sanitized.toLowerCase()
  if (!sanitized || filteredEvidenceTokens.some((token) => sanitizedLower.includes(token))) {
    return ""
  }

  return sanitized
}

export function uniqueEvidence(items: unknown[], limit = 8): string[] {
  const seen = new Set<string>()
  const result: string[] = []

  for (const item of items) {
    const label = sanitizeEvidenceLabel(item)
    if (!label) {
      continue
    }
    const key = label.toLowerCase()
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    result.push(label)
    if (result.length >= limit) {
      break
    }
  }

  return result
}

export function dedupeParagraphText(text: unknown, similarityThreshold = 0.9): string {
  const paragraphs = String(text ?? "")
    .split(/\n\s*\n/)
    .map((item) => safeText(item, ""))
    .filter(Boolean)

  const result: string[] = []
  for (const paragraph of paragraphs) {
    if (result.some((existing) => paragraphSimilarity(existing, paragraph) >= similarityThreshold)) {
      continue
    }
    result.push(paragraph)
  }

  return result.join("\n\n").trim()
}

export function dedupeSections(sections: ChatAnswerSection[]): ChatAnswerSection[] {
  const result: ChatAnswerSection[] = []

  for (const section of sections) {
    const cleaned: ChatAnswerSection = {
      title: safeText(section.title, "Answer"),
      content: dedupeParagraphText(section.content),
      bullets: dedupeStrings(section.bullets.map((item) => safeText(item, "")).filter(Boolean)),
      evidenceIds: dedupeStrings(section.evidenceIds.map((item) => safeText(item, "").replace(/^\[|\]$/g, "")).filter(Boolean)),
    }
    const signature = normalizeCompareText([cleaned.title, cleaned.content, ...cleaned.bullets].join(" | "))
    if (!signature) {
      continue
    }
    if (result.some((existing) => paragraphSimilarity([existing.title, existing.content, ...existing.bullets].join(" | "), signature) >= 0.9)) {
      continue
    }
    result.push(cleaned)
  }

  return result
}

export function sanitizeChatMessage(message: ChatMessage): ChatMessage {
  return {
    ...message,
    content: dedupeParagraphText(message.content),
    shortAnswer: dedupeParagraphText(message.shortAnswer ?? ""),
    sections: dedupeSections(message.sections ?? []),
    warnings: dedupeStrings((message.warnings ?? []).map((item) => safeText(item, "")).filter(Boolean)),
    suggestedFollowups: dedupeStrings((message.suggestedFollowups ?? []).map((item) => safeText(item, "")).filter(Boolean)),
    evidence: uniqueEvidence(message.evidence ?? [], 99).map((label) => ({ label })),
  }
}

export function dedupeStrings(items: string[]): string[] {
  const seen = new Set<string>()
  const result: string[] = []

  for (const item of items) {
    const normalized = safeText(item, "")
    if (!normalized) {
      continue
    }

    const key = normalized.toLowerCase()
    if (seen.has(key)) {
      continue
    }

    seen.add(key)
    result.push(normalized)
  }

  return result
}

export function normalizeApiPath(path: string): string {
  const value = safeText(path, "/").replace(/\s+/g, "")
  if (!value) {
    return "/"
  }

  const normalized = value
    .replace(/\\/g, "/")
    .replace(/\/+/g, "/")
    .replace(/\{[^}]*task[^}]*id[^}]*\}/gi, "{task_id}")
    .replace(/\{[^}]*job[^}]*id[^}]*\}/gi, "{task_id}")
    .replace(/\{[^}]*session[^}]*id[^}]*\}/gi, "{session_id}")
    .replace(/\{[^}]*taskid[^}]*\}/gi, "{task_id}")
    .replace(/\{[^}]*jobid[^}]*\}/gi, "{task_id}")
    .replace(/\{[^}]*taskid[^}]*\}/gi, "{task_id}")
    .replace(/\{[^}]*id[^}]*\}/gi, (match) => {
      const lower = match.toLowerCase()
      if (lower.includes("session")) {
        return "{session_id}"
      }
      if (lower.includes("task") || lower.includes("job") || lower.includes("status")) {
        return "{task_id}"
      }
      return match.toLowerCase().replace(/\s+/g, "_")
    })

  const cleaned = normalized.startsWith("/") ? normalized : `/${normalized}`
  return cleaned.replace(/\/status\/\{job_id\}/gi, "/status/{task_id}").replace(/\/status\/\{taskid\}/gi, "/status/{task_id}").toLowerCase()
}

export function isStatusLikePath(path: string): boolean {
  return /^\/(health|status|)$/.test(path) || path.startsWith("/status")
}

const capabilityMap: Array<[RegExp, string]> = [
  [/^\/ask$/i, "Chat / Question Answering API"],
  [/^\/context$/i, "Context Retrieval API"],
  [/^\/analyze$/i, "Analysis API"],
  [/\/history\/\{?session_id\}?/i, "Session History API"],
  [/\/\{?session_id\}?\/stream/i, "Streaming Response API"],
  [/frameworks?/i, "Framework Integrations"],
  [/api layer/i, "API Layer"],
  [/database integration/i, "Database / Storage Integration"],
  [/setup configuration/i, "Setup Configuration"],
]

export function humanizeCapability(text: string): string {
  const value = safeText(text, "")
  if (!value) {
    return "Detected Capability"
  }

  for (const [pattern, replacement] of capabilityMap) {
    if (pattern.test(value)) {
      return replacement
    }
  }

  if (/^built capability \d+$/i.test(value)) {
    return "Detected Capability"
  }

  if (value.length <= 48) {
    return titleCase(value)
  }

  return safeText(value, "Detected Capability")
}

export function humanizeWorkflowStep(step: unknown): { title: string; description: string } {
  if (!step || typeof step !== "object") {
    return {
      title: "Workflow step detected",
      description: "Detected application flow evidence was normalized for presentation.",
    }
  }

  const record = step as Record<string, unknown>
  const rawTitle = safeText(record.title ?? record.action, "Workflow step detected")
  const rawDescription = safeText(record.detail ?? record.description, "Detected application flow evidence.")
  const combined = `${rawTitle} ${rawDescription}`.toLowerCase()

  if (combined.includes("fastapi") && combined.includes("frontend")) {
    return {
      title: "Application routes initialize",
      description: "Detected frontend routing or API contract definitions connect the UI to backend routes.",
    }
  }

  if (combined.includes("mongodb")) {
    return {
      title: "Storage configuration detected",
      description: "The backend includes MongoDB-related configuration evidence.",
    }
  }

  const sanitizedTitle = sanitizePath(rawTitle)
  const sanitizedDescription = safeText(rawDescription.replace(rawTitle, ""), rawDescription)

  return {
    title: humanizeCapability(sanitizedTitle || rawTitle),
    description: safeText(sanitizePath(sanitizedDescription) || sanitizedDescription, "Detected application flow evidence."),
  }
}

export function normalizeConfidence(value: unknown): "High" | "Medium" | "Low" | "Unknown" {
  const normalized = safeText(value, "").toLowerCase()
  if (normalized === "high") {
    return "High"
  }
  if (normalized === "medium") {
    return "Medium"
  }
  if (normalized === "low") {
    return "Low"
  }
  return "Unknown"
}

export function safeText(text: unknown, fallback: string): string {
  if (text === null || text === undefined) {
    return fallback
  }

  const value = String(text)
    .replace(/MagicMock[^\s]*/gi, "")
    .replace(/<[^>]*object at 0x[0-9a-f]+>/gi, "")
    .replace(/\s+/g, " ")
    .trim()

  if (!value) {
    return fallback
  }

  const lower = value.toLowerCase()
  if (lower.includes("object at 0x") || lower.includes("magicmock")) {
    return fallback
  }

  if (value.length > 240) {
    return `${value.slice(0, 237).trimEnd()}...`
  }

  return value
}

export function humanizeApiPurpose(method: string, path: string): string {
  const normalizedPath = normalizeApiPath(path)
  const normalizedMethod = method.toUpperCase()

  if (normalizedMethod === "GET" && normalizedPath === "/") {
    return "Root or landing endpoint."
  }
  if (normalizedMethod === "GET" && normalizedPath === "/health") {
    return "Health check endpoint."
  }
  if (normalizedMethod === "POST" && normalizedPath.includes("/ask")) {
    return "Accepts a user question and returns a grounded answer."
  }
  if (normalizedMethod === "POST" && normalizedPath.includes("/context")) {
    return "Builds or retrieves context for analysis/chat."
  }
  if (normalizedMethod === "POST" && normalizedPath.includes("/query")) {
    return "Runs a query workflow."
  }
  if (normalizedMethod === "POST" && normalizedPath.includes("/analyze")) {
    return "Starts an analysis workflow."
  }
  if (normalizedMethod === "GET" && normalizedPath.includes("/history")) {
    return "Retrieves session chat/history."
  }
  if (normalizedMethod === "GET" && normalizedPath.includes("/status")) {
    if (normalizedPath.includes("{job_id}")) {
      return "Retrieves job status."
    }
    return "Retrieves analysis task status."
  }
  if (normalizedMethod === "GET" && normalizedPath.includes("/identity/summary")) {
    return "Returns summarized identity metadata."
  }
  if (normalizedMethod === "GET" && normalizedPath.includes("/identity")) {
    return "Returns project identity information."
  }
  if (normalizedMethod === "POST" && normalizedPath.includes("/summarize/upload")) {
    return "Uploads content for summarization."
  }
  if (normalizedMethod === "POST" && normalizedPath.includes("/summarize")) {
    return "Starts summarization workflow."
  }
  if (normalizedMethod === "GET" && normalizedPath.includes("/intelligence")) {
    return "Retrieves project intelligence for a session."
  }
  if (normalizedMethod === "GET" && normalizedPath.includes("/stream")) {
    return "Streams session updates."
  }
  if (normalizedMethod === "GET" && normalizedPath.includes("/report")) {
    return "Retrieves generated report output."
  }
  if (normalizedMethod === "POST" && normalizedPath.includes("/chat")) {
    return "Accepts a user question and returns a grounded answer."
  }

  return "Detected API endpoint."
}
