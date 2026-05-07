import { useRef, useState } from "react"
import { ArrowUpRight, ChevronDown, Copy, SendHorizontal, Sparkles } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { isBackendConfigured, sendChatStream } from "../../lib/ahal-api"
import { toFriendlyError } from "../../lib/errors"
import { demoChatResponse, demoSessionId } from "../../lib/mock-data"
import { safeText, sanitizeChatMessage, uniqueEvidence } from "../../lib/presentation"
import type { ChatAnswerSection, ChatMessage, IntelligenceData } from "../../lib/types"
import { formatDateTime } from "../../lib/utils"
import { Button } from "../ui/Button"
import { ConfidenceBadge } from "../ui/ConfidenceBadge"
import { GlassCard } from "../ui/GlassCard"
import { Textarea } from "../ui/Textarea"

const starterQuestions = [
  "What does this project do?",
  "Why does this project exist?",
  "What is built?",
  "What remains?",
  "What APIs exist?",
  "Explain the architecture.",
  "How does the main workflow work?",
  "What risks should I review?",
  "What tests should be added?",
  "What should a new engineer read first?",
]

function SectionBlock({ section, evidence }: { section: ChatAnswerSection; evidence: string[] }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-slate-950/45 p-4">
      <h4 className="text-sm font-semibold text-white">{section.title}</h4>
      {section.content ? <p className="mt-2 wrap-break-word text-sm leading-7 text-slate-300">{section.content}</p> : null}
      {section.bullets.length ? (
        <div className="mt-3 space-y-2">
          {section.bullets.map((bullet) => (
            <p key={bullet} className="wrap-break-word text-sm text-slate-300">
              {bullet}
            </p>
          ))}
        </div>
      ) : null}
      {evidence.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {evidence.map((label) => (
            <span key={`${section.title}-${label}`} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] text-slate-300">
              {label}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function alignAssistantMessageWithCanonical(message: ChatMessage, intelligence?: IntelligenceData | null): ChatMessage {
  if (!intelligence || message.role !== "assistant") {
    return message
  }

  const summary = safeText(intelligence.projectSummary, "")
  const what = safeText(intelligence.what, "")
  const lowerSummary = summary.toLowerCase()
  const lowerWhat = what.toLowerCase()
  const isDeveloperIdentity = lowerSummary.includes("developer tool") || lowerSummary.includes("code intelligence") || lowerWhat.includes("developer tool") || lowerWhat.includes("code intelligence")
  if (!isDeveloperIdentity) {
    return message
  }

  const unsupportedTerms = [
    /content management application/i,
    /\bCMS\b/i,
    /\becommerce\b/i,
    /financial research/i,
    /finance workflows/i,
    /Backend API Layer/i,
    /unfamiliar codebases/i,
    /repository-aware questions/i,
    /\.env\.example/i,
    /mongodb:\/\/[^\s)]+/i,
  ]

  const replaceLeak = (value?: string) => {
    const text = safeText(value, "")
    if (!unsupportedTerms.some((pattern) => pattern.test(text))) {
      return value ?? ""
    }
    return what || summary || text.replace(/content management application/gi, "developer intelligence platform")
  }

  return {
    ...message,
    content: replaceLeak(message.content),
    shortAnswer: replaceLeak(message.shortAnswer),
    sections: (message.sections ?? []).map((section) => ({
      ...section,
      content: replaceLeak(section.content),
      bullets: section.bullets.map((bullet) => replaceLeak(bullet)),
    })),
  }
}

export function ChatPanel({ sessionId, intelligence }: { sessionId: string; intelligence?: IntelligenceData | null }) {
  const navigate = useNavigate()
  const messageCounter = useRef(0)
  const [messages, setMessages] = useState<ChatMessage[]>(
    !isBackendConfigured() || sessionId === demoSessionId ? [demoChatResponse.message] : [],
  )
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>(starterQuestions)
  const [showWarnings, setShowWarnings] = useState(false)
  const [showEvidence, setShowEvidence] = useState(true)
  const [copiedId, setCopiedId] = useState("")

  async function ask(prompt: string) {
    if (!prompt.trim()) {
      return
    }

    messageCounter.current += 1
    const messageId = `user-${messageCounter.current}`
    const userMessage: ChatMessage = {
      id: messageId,
      role: "user",
      content: prompt,
      timestamp: new Date().toISOString(),
    }

    setMessages((current) => [...current, userMessage])
    setQuestion("")
    setLoading(true)
    try {
      const result = await sendChatStream(sessionId, prompt)
      setMessages((current) => [...current, result.data.message])
      setSuggestions(result.data.message.suggestedFollowups?.length ? result.data.message.suggestedFollowups : result.data.suggestedQuestions)
    } catch (error) {
      messageCounter.current += 1
      const assistantError: ChatMessage = {
        id: `assistant-error-${messageCounter.current}`,
        role: "assistant",
        content: toFriendlyError(error),
        timestamp: new Date().toISOString(),
      }
      setMessages((current) => [...current, assistantError])
    } finally {
      setLoading(false)
    }
  }

  async function copyAnswer(message: ChatMessage) {
    const text = [message.shortAnswer || message.content]
      .concat((message.sections ?? []).flatMap((section) => [section.title, section.content, ...section.bullets]))
      .filter(Boolean)
      .join("\n\n")
    await navigator.clipboard.writeText(text)
    setCopiedId(message.id)
    window.setTimeout(() => setCopiedId(""), 1500)
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
      <GlassCard className="space-y-6 overflow-hidden">
        <div className="space-y-4">
          {!messages.length ? (
            <div className="rounded-3xl border border-white/10 bg-white/4 p-6 text-sm text-slate-400">
              <p className="font-medium text-white">Ask another question...</p>
              <p className="mt-2 leading-7">
                Repo chat uses deterministic project intelligence, selected evidence, and conversation memory to answer repository questions more reliably than a generic assistant.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {starterQuestions.slice(0, 6).map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => ask(item)}
                    className="rounded-full border border-white/10 bg-white/3 px-3 py-2 text-xs text-slate-300 transition hover:border-cyan-300/20 hover:bg-cyan-300/10 hover:text-white"
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {messages.map((message) => {
            const normalizedMessage = message.role === "assistant" ? sanitizeChatMessage(alignAssistantMessageWithCanonical(message, intelligence)) : message
            const evidenceLabels = uniqueEvidence(normalizedMessage.evidence ?? [], 6)
            const totalEvidenceCount = uniqueEvidence(normalizedMessage.evidence ?? [], 99).length
            const hiddenCount = Math.max(totalEvidenceCount - evidenceLabels.length, 0)
            const sections = normalizedMessage.sections ?? []
            const isOnboarding = normalizedMessage.intent === "onboarding_question"

            return (
              <div
                key={normalizedMessage.id}
                className={normalizedMessage.role === "assistant"
                  ? "rounded-[28px] border border-white/10 bg-white/4 p-5"
                  : "ml-auto max-w-2xl rounded-[28px] bg-cyan-400/12 p-5"}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <p className="font-medium text-white">{normalizedMessage.role === "assistant" ? "AHAL AI" : "You"}</p>
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{formatDateTime(normalizedMessage.timestamp)}</p>
                    {normalizedMessage.confidence && (normalizedMessage.evidence?.length || normalizedMessage.sections?.length) ? <ConfidenceBadge value={normalizedMessage.confidence} /> : null}
                  </div>
                  {normalizedMessage.role === "assistant" ? (
                    <div className="flex flex-wrap gap-2">
                      <Button variant="ghost" size="sm" onClick={() => void copyAnswer(normalizedMessage)} aria-label="Copy answer">
                        <Copy className="h-4 w-4" />
                        {copiedId === normalizedMessage.id ? "Copied" : "Copy"}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => navigate(`/dashboard/${sessionId}`)} aria-label="Open in dashboard">
                        <ArrowUpRight className="h-4 w-4" />
                        Open in dashboard
                      </Button>
                    </div>
                  ) : null}
                </div>

                <p className="mt-4 wrap-break-word text-sm leading-7 text-slate-300">
                  {safeText(normalizedMessage.shortAnswer || normalizedMessage.content, "No answer was returned.")}
                </p>

                {normalizedMessage.role === "assistant" && sections.length ? (
                  <div className="mt-4 space-y-3">
                    {sections.map((section) => (
                      <SectionBlock
                        key={`${normalizedMessage.id}-${section.title}`}
                        section={section}
                        evidence={showEvidence && (!isOnboarding || section.title.toLowerCase().includes("key files")) ? evidenceLabels.slice(0, isOnboarding ? 5 : 6) : []}
                      />
                    ))}
                  </div>
                ) : null}

                {normalizedMessage.role === "assistant" && !sections.length && normalizedMessage.content && normalizedMessage.content !== normalizedMessage.shortAnswer ? (
                  <p className="mt-4 wrap-break-word text-sm leading-7 text-slate-300">{safeText(normalizedMessage.content, "No answer was returned.")}</p>
                ) : null}

                {normalizedMessage.role === "assistant" && evidenceLabels.length && !isOnboarding ? (
                  <div className="mt-4">
                    <button
                      type="button"
                      onClick={() => setShowEvidence((value) => !value)}
                      className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-500 transition hover:text-slate-300"
                    >
                      <ChevronDown className={`h-4 w-4 transition ${showEvidence ? "rotate-180" : ""}`} />
                      {showEvidence ? "Hide evidence" : "View evidence"}
                    </button>
                    {showEvidence ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {evidenceLabels.map((label) => (
                          <span key={`${normalizedMessage.id}-${label}`} className="max-w-full rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                            {label}
                          </span>
                        ))}
                        {hiddenCount > 0 ? <span className="rounded-full border border-white/10 bg-white/3 px-3 py-1 text-xs text-slate-400">+{hiddenCount} more</span> : null}
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {normalizedMessage.role === "assistant" && normalizedMessage.warnings?.length ? (
                  <div className="mt-4">
                    <button
                      type="button"
                      onClick={() => setShowWarnings((value) => !value)}
                      className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-amber-200/75 transition hover:text-amber-100"
                    >
                      <ChevronDown className={`h-4 w-4 transition ${showWarnings ? "rotate-180" : ""}`} />
                      {showWarnings ? "Hide warnings" : "Show warnings"}
                    </button>
                    {showWarnings ? (
                      <div className="mt-3 space-y-2">
                        {normalizedMessage.warnings.map((warning) => (
                          <div key={`${normalizedMessage.id}-${warning}`} className="rounded-2xl border border-amber-400/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/85">
                            {safeText(warning, "Warning returned by backend.")}
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {normalizedMessage.role === "assistant" && normalizedMessage.suggestedFollowups?.length ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {normalizedMessage.suggestedFollowups.map((item) => (
                      <button
                        key={`${normalizedMessage.id}-${item}`}
                        type="button"
                        onClick={() => ask(item)}
                        className="rounded-full border border-cyan-300/15 bg-cyan-300/10 px-3 py-2 text-xs text-cyan-100 transition hover:border-cyan-300/30 hover:bg-cyan-300/15"
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            )
          })}

          {loading ? (
            <div className="rounded-[28px] border border-white/10 bg-white/4 p-5">
              <div className="flex items-center gap-3 text-slate-300">
                <Sparkles className="h-4 w-4 animate-pulse text-cyan-200" />
                <span className="inline-flex items-center gap-1">
                  <span>Thinking</span>
                  <span className="animate-pulse">...</span>
                </span>
              </div>
            </div>
          ) : null}
        </div>

        <div className="rounded-[28px] border border-white/10 bg-slate-950/55 p-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-end">
            <Textarea
              aria-label="Ask another question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault()
                  void ask(question)
                }
              }}
              placeholder="Ask another question..."
              className="min-h-[96px]"
            />
            <Button icon={<SendHorizontal className="h-4 w-4" />} onClick={() => void ask(question)} disabled={loading}>
              Send
            </Button>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="space-y-5">
        <div>
          <h3 className="text-lg font-semibold text-white">Suggested Prompts</h3>
          <p className="mt-2 text-sm leading-7 text-slate-400">
            Good repo chat stays grounded in APIs, workflows, modules, onboarding cues, and test coverage evidence.
          </p>
        </div>
        <div className="space-y-3">
          {suggestions.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => ask(item)}
              className="w-full rounded-2xl border border-white/10 bg-white/3 px-4 py-4 text-left text-sm text-slate-300 transition hover:border-cyan-300/20 hover:bg-cyan-300/10 hover:text-white"
            >
              {item}
            </button>
          ))}
        </div>
      </GlassCard>
    </div>
  )
}
