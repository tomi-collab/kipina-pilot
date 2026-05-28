# Kipina Template Proxy

B2a service for server-side template calls used by Mestari-generated prototypes.

## Endpoints

- `GET /api/templates/health`
- `POST /api/templates/analyze`

`POST /api/templates/analyze` requires the `X-Kipina-Sandbox-Id` header for
pilot rate limiting. The request body contains `question`, `options`,
`analysis_type`, and optional `language`.

Supported `analysis_type` values:

- `pros_cons`
- `ranking`
- `advice`
- `summary`

The service calls Gemini Flash through `google-genai` with Vertex AI credentials.
It does not log request bodies or Gemini responses.
