import type { SessionInfo } from "./types"

const SESSION_ID_KEY = "ahal_session_id"
const ACCESS_TOKEN_KEY = "ahal_access_token"
const API_URL_OVERRIDE_KEY = "ahal_api_url_override"

export function saveSession(sessionId: string, accessToken?: string): void {
  localStorage.setItem(SESSION_ID_KEY, sessionId)
  if (accessToken) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  } else {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
  }
}

export function getSession(): SessionInfo {
  return {
    sessionId: localStorage.getItem(SESSION_ID_KEY),
    accessToken: localStorage.getItem(ACCESS_TOKEN_KEY),
  }
}

export function getToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_ID_KEY)
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}

export function getBackendUrlOverride() {
  return localStorage.getItem(API_URL_OVERRIDE_KEY) ?? ""
}

export function setBackendUrlOverride(url: string) {
  const cleaned = url.trim()
  if (!cleaned) {
    localStorage.removeItem(API_URL_OVERRIDE_KEY)
    return
  }

  localStorage.setItem(API_URL_OVERRIDE_KEY, cleaned)
}
