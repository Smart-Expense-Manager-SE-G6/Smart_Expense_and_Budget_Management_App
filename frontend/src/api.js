// Thin wrapper around fetch for the /api/v1 JSON API.
// - Sends the session cookie (same origin via the Vite proxy).
// - Adds the X-CSRFToken header on unsafe methods (ADR 0001).
// - Turns the SASD 4.4 error envelope into an ApiError.

const BASE = '/api/v1'
const UNSAFE = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

// Fired on any 401 so the app can drop a session that expired on the server (ADR 0001: 30 min idle).
export const SESSION_EXPIRED_EVENT = 'auth:session-expired'

export class ApiError extends Error {
  constructor({ code, message, field, request_id }, status) {
    super(message)
    this.code = code
    this.field = field
    this.requestId = request_id
    this.status = status
  }
}

function csrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : ''
}

// Builds "?a=1&b=2", skipping empty values.
export function query(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value)
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

export async function api(path, { method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' }
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData
  // FormData sets its own multipart boundary header.
  if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json'
  if (UNSAFE.has(method)) headers['X-CSRFToken'] = csrfToken()

  const response = await fetch(`${BASE}${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  })

  if (response.status === 401) window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const error = data?.error ?? { code: 'network_error', message: 'Could not reach the server.' }
    throw new ApiError(error, response.status)
  }
  return data
}

// Downloads a binary response (PDF/Excel exports) and returns { blob, filename }.
export async function apiDownload(path) {
  const response = await fetch(`${BASE}${path}`, { credentials: 'same-origin' })
  if (response.status === 401) window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    const error = data?.error ?? { code: 'network_error', message: 'Could not download the file.' }
    throw new ApiError(error, response.status)
  }
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const filename = /filename="?([^";]+)"?/.exec(disposition)?.[1] ?? 'download'
  return { blob: await response.blob(), filename }
}
