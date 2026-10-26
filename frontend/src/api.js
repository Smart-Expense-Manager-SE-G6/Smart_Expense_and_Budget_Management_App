// Thin wrapper around fetch for the /api/v1 JSON API.
// - Sends the session cookie (same origin via the Vite proxy).
// - Adds the X-CSRFToken header on unsafe methods (ADR 0001).
// - Turns the SASD 4.4 error envelope into an ApiError.

const BASE = '/api/v1'
const UNSAFE = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

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

export async function api(path, { method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (UNSAFE.has(method)) headers['X-CSRFToken'] = csrfToken()

  const response = await fetch(`${BASE}${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const error = data?.error ?? { code: 'network_error', message: 'Could not reach the server.' }
    throw new ApiError(error, response.status)
  }
  return data
}
