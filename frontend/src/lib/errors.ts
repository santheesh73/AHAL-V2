export function toFriendlyError(error: unknown): string {
  const details = error && typeof error === "object" ? (error as { status?: unknown; message?: unknown; network?: unknown }) : {}
  const status = typeof details.status === "number" ? details.status : undefined
  const message = typeof details.message === "string" ? details.message : ""

  if (details.network || /cannot reach ahal backend/i.test(message) || /failed to fetch/i.test(message)) {
    return "Cannot reach AHAL backend. Make sure FastAPI is running at http://localhost:8000 and CORS allows http://localhost:5173."
  }
  if (status === 401) {
    return "Session authorization failed. Start a new analysis."
  }
  if (status === 404) {
    return "Session not found. The analysis may have expired."
  }
  if (status === 202) {
    return "Analysis is still running. Please wait."
  }
  if (status === 500) {
    return "AHAL backend returned an internal error. Try again or check the backend logs."
  }
  if (message) {
    return message
  }

  return "Something went wrong while processing this request."
}
