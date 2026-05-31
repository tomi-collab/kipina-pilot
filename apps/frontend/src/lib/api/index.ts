/**
 * Kutsut menevät saman originin /api-prefiksin alle.
 * Devissä Vite proxy ohjaa reveal-polut porttiin 8081 ja konseptipolut porttiin 8082.
 * Tuotannossa Caddy ohjaa polut vastaaville localhost-palveluille.
 */

export interface AuthCheckResponse {
  ok: boolean
}

export interface Tenant {
  id: string
  name: string
  description: string
}

export interface TenantsResponse {
  ok: boolean
  tenants: Tenant[]
}

export interface ChatRequest {
  message: string
  tenant_id: string
  session_id?: string | null
}

export interface ChatResponse {
  reply: string
  session_id: string
  finished: boolean
  turn: number
  milestone: string | null
  report: unknown
}

export interface GenerateConceptRequest {
  report: string
  language: 'fi' | 'en'
}

export interface GenerateConceptResponse {
  concept: string
  suggested_templates?: string[]
}

class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    let message = `Request failed: ${res.status}`
    try {
      const data = await res.json()
      if (data && typeof data.error === 'string') message = data.error
    } catch {
      // ignore
    }
    throw new ApiError(message, res.status)
  }

  return (await res.json()) as T
}

export async function getTenants(): Promise<Tenant[]> {
  const res = await fetch('/api/tenants')
  if (!res.ok) throw new ApiError('Failed to load tenants', res.status)
  const data = (await res.json()) as TenantsResponse
  return data.tenants
}

export async function checkAccessCode(code: string): Promise<AuthCheckResponse> {
  return postJson<AuthCheckResponse>('/api/auth/check', { code })
}

export async function sendChatMessage(req: ChatRequest): Promise<ChatResponse> {
  return postJson<ChatResponse>('/api/idea', req)
}

export async function generateConcept(
  req: GenerateConceptRequest
): Promise<GenerateConceptResponse> {
  return postJson<GenerateConceptResponse>('/api/concepts/generate', req)
}

export { ApiError }
