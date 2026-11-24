/**
 * Small wrapper around fetch() for the BiletFlow API.
 *
 *   const events = await api.get<EventPage>('/events', { q: 'jazz' })
 *   const order  = await api.post<Order>('/orders', body)
 *
 * Every failed call throws an ApiError that carries the HTTP status, the machine
 * `code` sent by the backend (for translated messages) and the English `detail`.
 */
const BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')
export const API_URL = `${BASE}/api/v1`
const TOKEN_KEY = 'biletflow_token'

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public detail: string,
  ) {
    super(detail)
  }
}

let token: string | null = null
try {
  token = localStorage.getItem(TOKEN_KEY)
} catch {
  /* storage can be blocked (private mode); the session then lasts until the tab closes */
}
let onUnauthorized: () => void = () => {}

export function setToken(value: string | null): void {
  token = value
  try {
    if (value) localStorage.setItem(TOKEN_KEY, value)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* ignore */
  }
}
export const hasToken = (): boolean => token !== null
/** Called when the server says the saved sign-in is no longer valid. */
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler
}

type Query = Record<string, string | number | boolean | null | undefined>

function buildUrl(path: string, query?: Query): string {
  const url = new URL(API_URL + path)
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== null && value !== undefined && value !== '') url.searchParams.set(key, String(value))
  }
  return url.toString()
}

async function send(method: string, path: string, options: { query?: Query; body?: unknown; form?: FormData } = {}): Promise<Response> {
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  let body: BodyInit | undefined
  if (options.form) body = options.form
  else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }
  let response: Response
  try {
    response = await fetch(buildUrl(path, options.query), { method, headers, body })
  } catch {
    throw new ApiError(0, 'network_error', 'The server cannot be reached. Check your connection and try again.')
  }
  if (!response.ok) {
    let payload: { detail?: string; code?: string } = {}
    try {
      payload = await response.json()
    } catch {
      /* not JSON */
    }
    if (response.status === 401 && token) onUnauthorized()
    throw new ApiError(response.status, payload.code ?? 'error', typeof payload.detail === 'string' ? payload.detail : 'Request failed')
  }
  return response
}

async function json<T>(method: string, path: string, options?: { query?: Query; body?: unknown; form?: FormData }): Promise<T> {
  const response = await send(method, path, options)
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

export const api = {
  get: <T>(path: string, query?: Query) => json<T>('GET', path, { query }),
  post: <T>(path: string, body: unknown = {}) => json<T>('POST', path, { body }),
  put: <T>(path: string, body: unknown = {}) => json<T>('PUT', path, { body }),
  patch: <T>(path: string, body: unknown = {}) => json<T>('PATCH', path, { body }),
  delete: (path: string) => json<void>('DELETE', path),

  /** Protected files (PDF tickets, QR images, CSV) need the Authorization header, so they are fetched as blobs. */
  async blobUrl(path: string): Promise<string> {
    const response = await send('GET', path)
    return URL.createObjectURL(await response.blob())
  },
  async download(path: string, filename: string): Promise<void> {
    const url = await this.blobUrl(path)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 10_000)
  },
  async uploadImage(file: File): Promise<string> {
    const form = new FormData()
    form.append('file', file)
    return (await json<{ url: string }>('POST', '/uploads/images', { form })).url
  },
}
