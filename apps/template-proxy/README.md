# Kipina Template Proxy

B2a service for server-side template calls used by Mestari-generated prototypes.

## Endpoints

- `GET /api/templates/health`
- `POST /api/templates/analyze`
- `GET /api/templates/weather-current?place=Helsinki`
- `GET /api/templates/transit-helsinki?stop_name=Rautatientori`
- `GET /api/templates/image-random?seed=testi`
- `GET /api/templates/calendar-mock`
- `GET /api/templates/messages-mock`
- `POST /api/templates/text-helper`

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

`GET /api/templates/weather-current` returns current Finnish weather observations
from Ilmatieteen laitos open data. It requires `X-Kipina-Sandbox-Id`.

`GET /api/templates/transit-helsinki` returns upcoming HSL/Digitransit departures.
It requires `X-Kipina-Sandbox-Id` and `DIGITRANSIT_SUBSCRIPTION_KEY`; when the key
is missing, the endpoint returns `503 transit_unavailable` without stopping the
service.

`GET /api/templates/image-random` returns a stable Lorem Picsum image URL for a
seed. The image is random and does not match the seed topic.

`GET /api/templates/calendar-mock` and `GET /api/templates/messages-mock` return
deterministic demo data for schedule and chat prototypes.

`POST /api/templates/text-helper` processes text with Gemini Flash using one of
the fixed tasks: `translate`, `summarize`, `simplify`, or `rephrase`.
