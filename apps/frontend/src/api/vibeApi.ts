const BASE = '/api/prototype'

export interface StartRequest {
  sessionId: string
  concept?: string
  report?: string
  tenantId?: string
  vibe?: string
}

export interface StartResponse {
  sandbox_id: string
  prototype_html: string
  mestari_message: string
  ttl_seconds: number
}

export interface IterateRequest {
  sandboxId: string
  mode: 'koodaus' | 'pohdinta'
  userInput: string
  language: 'fi' | 'en'
}

export interface IterateResponse {
  prototype_html?: string
  mestari_message: string
  iteration_count: number
  concept_drift_warning?: string | null
}

export class VibeApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function readErrorMessage(response: Response, fallback: string) {
  try {
    const data = await response.json()
    if (data && typeof data.error === 'string') return data.error
  } catch {
    // keep fallback
  }
  return fallback
}

export async function startPrototype(
  payload: StartRequest
): Promise<StartResponse> {
  const body: Record<string, string | undefined> = {
    session_id: payload.sessionId,
  }

  if (payload.vibe) {
    body.vibe = payload.vibe
  } else {
    body.concept = payload.concept
    body.report = payload.report
    body.tenant_id = payload.tenantId
  }

  const response = await fetch(`${BASE}/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const message = await readErrorMessage(response, `start_failed_${response.status}`)
    throw new VibeApiError(message, response.status)
  }

  return (await response.json()) as StartResponse
}

export async function iteratePrototype(
  payload: IterateRequest
): Promise<IterateResponse> {
  const response = await fetch(`${BASE}/iterate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sandbox_id: payload.sandboxId,
      mode: payload.mode,
      user_input: payload.userInput,
      language: payload.language,
    }),
  })

  if (!response.ok) {
    const message =
      response.status === 404
        ? 'sandbox_not_found'
        : await readErrorMessage(response, `iterate_failed_${response.status}`)
    throw new VibeApiError(message, response.status)
  }

  return (await response.json()) as IterateResponse
}
