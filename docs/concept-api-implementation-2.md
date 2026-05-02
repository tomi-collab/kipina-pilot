# Kipina Concept API — Implementation Instructions

**For:** Claude Code / Codex
**Target repository:** Kipina pilot (`pilot.kipina.digiter.fi`)
**Date:** 2026-05-01
**Goal:** Add a new containerized service that turns a Reveal report into a free-text concept description using Gemini 3 on Vertex AI, and expose a button on the pilot frontend that triggers it.

---

## 1. Scope and non-goals

### In scope
- New container `kipina-concept-api` running on `127.0.0.1:8082`.
- One endpoint that accepts a report and returns a Gemini-generated concept as plain text.
- Caddy route so the public site can reach it.
- A "Luo konsepti" / "Generate concept" button on the report view that calls the endpoint and shows the result.
- GCP Service Account authentication via a JSON key file mounted into the container.

### Explicitly out of scope (do not build these)
- PostgreSQL persistence of concepts. Concepts are returned to the browser only; not stored server-side.
- Vibe-coding platform integration. The concept is plain text for human reading only.
- Reveal Engine changes. The Reveal side is already done and frozen.
- Tenant-aware logic. The concept-api does not know or care which tenant produced the report.
- Workload Identity Federation. Use a JSON key file for now.
- Any modification to `reveal-data-api`, the placeholder nginx, or the existing Caddy routes for `/api/health`.

---

## 2. Files to create

```
apps/concept-api/
├── app.py
├── Dockerfile
└── requirements.txt
```

Plus modifications to:
- `docker-compose.yml` (add the new service)
- `infra/caddy/Caddyfile` (add the route)
- `html/index.html` or whichever frontend file currently renders the report view (add the button + fetch call)
- `.env.example` (document the new variables)
- `.gitignore` (ensure `secrets/gcp-sa.json` is ignored — it likely already is via `secrets/`, but verify)

---

## 3. `apps/concept-api/requirements.txt`

```
google-genai==1.0.0
```

> Use the `google-genai` SDK (the unified SDK that supports Vertex AI). Do not use the legacy `google-cloud-aiplatform` SDK. If 1.0.0 is unavailable when you build, pin to the latest stable 1.x and report the version used.

---

## 4. `apps/concept-api/Dockerfile`

```dockerfile
FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080

CMD ["python", "-u", "app.py"]
```

---

## 5. `apps/concept-api/app.py`

Requirements:

- Pure stdlib HTTP using `http.server.BaseHTTPRequestHandler` + `ThreadingHTTPServer`. No Flask, no FastAPI. This matches `reveal-data-api`.
- Reads from environment:
  - `GCP_PROJECT_ID` (e.g. `apply-project-35406`)
  - `GCP_LOCATION` (default `europe-west4`)
  - `GEMINI_MODEL` (default `gemini-3-pro` — adjust if the actual GA model name differs; document which value you used)
  - `GOOGLE_APPLICATION_CREDENTIALS` (path inside container, e.g. `/secrets/gcp-sa.json`)
- Listens on `0.0.0.0:8080` inside the container (mapped to `127.0.0.1:8082` on the host via compose).
- CORS: respond to `OPTIONS` preflights with `Access-Control-Allow-Origin: https://pilot.kipina.digiter.fi`, allowed methods `POST, OPTIONS`, allowed headers `Content-Type`. Frontend and API share an origin in production (both behind Caddy), so CORS may not be strictly needed — but include it defensively in case the frontend ever runs from a different origin during testing.

### Endpoints

#### `GET /api/concepts/health`
Returns `200` with JSON `{"ok": true, "service": "kipina-concept-api"}`. Used for liveness checks.

#### `POST /api/concepts/generate`

Request body (JSON):
```json
{
  "report": "string — the full Reveal report text",
  "language": "fi" | "en"
}
```

`language` is optional. If absent, default to `"fi"`.

Behavior:
1. Validate that `report` is a non-empty string. If missing or empty → `400` with `{"error": "report is required"}`.
2. Validate `report` length: max 50,000 characters. If exceeded → `400` with `{"error": "report too long"}`.
3. Build the prompt (see section 6) using the supplied language.
4. Call Gemini 3 on Vertex AI via the `google-genai` SDK.
5. On success → `200` with `{"concept": "<plain text from Gemini>"}`.
6. On Gemini error or timeout → `502` with `{"error": "concept generation failed", "detail": "<short message>"}`. Do not leak the full stack trace to the client; log it to stdout instead.

### SDK usage sketch

```python
from google import genai

client = genai.Client(
    vertexai=True,
    project=GCP_PROJECT_ID,
    location=GCP_LOCATION,
)

response = client.models.generate_content(
    model=GEMINI_MODEL,
    contents=prompt,
)

concept_text = response.text
```

> **Thought signatures:** The Reveal report → concept generation is a single-turn call. We do NOT carry conversation across turns. Therefore thought signature circulation is not required for this endpoint. Do not implement it.

### Logging
Print to stdout: timestamp, request method, path, response status, and elapsed milliseconds. One line per request. No request bodies or report contents in logs (privacy).

---

## 6. The Gemini prompt

The prompt must produce a **plain-text concept in the same language as the report**. Build the prompt in Python as a single string. Use the language parameter to select between two prompt variants below.

### Finnish prompt (when `language == "fi"`)

```
Olet konseptisuunnittelija Kipinä-pilotissa. Saat raportin nuoren ideasta. Tehtäväsi on muotoilla siitä konseptikuvaus, jonka pohjalta nuori voi rakentaa toimivan sovelluksen vibekoodausalustalla (kuten Replit, Lovable tai Bolt) yhdessä tai muutamassa istunnossa.

TÄRKEÄ TOTEUTUSKONTEKSTI:
- Sovellus rakennetaan vibekoodausalustalla, joka tuottaa selainpohjaista web-koodia (HTML, JavaScript, React).
- Lopputulos on selaimessa toimiva web-sovellus. Ei natiivimobiilia, ei työpöytäsovellusta.
- Sovellus tulee voida saada toimivaan kuntoon nopeasti — painota toteutettavuutta yli kunnianhimoa.
- ÄLÄ ehdota: omia pelimoottoreita, 3D-grafiikkaa, kompleksisia editoreita, drag-and-drop -rakentajia, reaaliaikaista multiplayeria, natiivien sensorien syviä integraatioita.
- ÄLÄ ehdota maksuliikennettä tai arkaluontoisen henkilödatan käsittelyä missään muodossa.
- Vibekoodausalustat osaavat tehdä: lomakkeita, listoja, kortteja, karttoja, chat-näkymiä, kalentereita, suodattimia, hakuja, yksinkertaisia visualisointeja, API-kutsuja, tekstipohjaista tekoälyvuorovaikutusta.

Mieluummin "yksi näyttö joka tekee yhden asian hyvin" kuin "alusta joka mahdollistaa kaiken". Onnistumisen ydin on että nuori näkee oman ideansa toimivan oikeasti pian — ei lupausta valtavasta järjestelmästä.

Kirjoita konsepti vapaamuotoisena tekstinä, ei JSONina, ei taulukoina. Käytä selkeitä alaotsikoita. Pidä koko konsepti alle 500 sanan mittaisena.

Sisällytä seuraavat osiot, tässä järjestyksessä, tarkalleen näillä otsikoilla:

## Idean nimi
Yksi lyhyt, iskevä työnimi.

## Pähkinänkuoressa
Yksi lause: mitä sovellus tekee ja kenelle.

## Käyttäjäpolku
Noin viisi numeroitua askelta siitä, miten käyttäjä etenee sovelluksessa alusta hyödyn saamiseen.

## Ydintoiminnot
3–5 ranskalaisella viivalla listattua toiminnallisuutta. Jokaisen tulee olla sellainen, jonka voi rakentaa selainpohjaisena web-toiminnallisuutena.

## Tarvittavat tietovirrat
Listaa ranskalaisilla viivoilla, MILLAISTA tietoa sovellus tarvitsisi ulkoisista lähteistä toimiakseen järkevästi. ÄLÄ nimeä mitään konkreettista palvelua, tuotetta tai brändiä (älä mainitse Googlea, OpenAI:ta, Mapsia, Spotifyta tms.). Kuvaa vain tiedon LUONNE — esimerkiksi: "reaaliaikaista joukkoliikenteen aikataulutietoa", "julkista säätietoa", "tekstin kääntämistä kielestä toiseen", "tekstipohjaista keskustelua tekoälyn kanssa", "kuvantunnistusta valokuvasta". Tämä lista auttaa kehittäjiä ymmärtämään, mitä API-rajapintoja vibekoodausalustan templaten tulisi tarjota.

## Toteutus vibekoodausalustalla
2–4 lauseessa: miten tämä rakennetaan käytännössä selainpohjaisena web-sovelluksena? Mistä aloittaa, mikä on yksinkertaisin toimiva versio jonka voi saada näytölle ensimmäisenä, ja mitä päälle voi laajentaa? Tämä osio pitää konseptin maan pinnalla.

Suunnittele konsepti niin, että se toimii hyvin mobiililla. Mobiilikäyttö on vahva lähtökohta: käyttöliittymä, käyttäjäpolku ja toiminnot tulee voida toteuttaa luontevasti puhelimen selaimessa. Tämä ei ole ehdoton vaatimus, eikä konseptin tarvitse olla vain mobiililla toimiva, mutta puhelimen ruutu, kosketuskäyttö ja lyhyet käyttöhetket ohjaavat suunnittelua.

Tässä on raportti:

---
{report}
---
```

### English prompt (when `language == "en"`)

```
You are a concept designer in the Kipina pilot. You receive a report describing a young person's idea. Your job is to turn it into a concept description that the young person can use to build a working application on a vibe-coding platform (such as Replit, Lovable, or Bolt) in one or a few sessions.

IMPORTANT BUILD CONTEXT:
- The application will be built on a vibe-coding platform that produces browser-based web code (HTML, JavaScript, React).
- The end result is a web app that runs in a browser. No native mobile, no desktop apps.
- The app should be reachable to a working state quickly — favour feasibility over ambition.
- DO NOT propose: custom game engines, 3D graphics, complex editors, drag-and-drop builders, real-time multiplayer, deep native sensor integrations.
- DO NOT propose payment processing or handling of sensitive personal data in any form.
- Vibe-coding platforms are good at: forms, lists, cards, maps, chat views, calendars, filters, search, simple visualisations, API calls, text-based AI interaction.

Prefer "one screen that does one thing well" over "a platform that enables everything". The point is for the young person to see their idea actually working soon — not a promise of a vast system.

Write the concept as free-form prose, not JSON, not tables. Use clear subheadings. Keep the whole concept under 500 words.

Include the following sections, in this order, with exactly these headings:

## Idea name
One short, catchy working title.

## In a nutshell
One sentence: what the app does and for whom.

## User journey
About five numbered steps showing how the user moves through the app from start to value.

## Core features
3–5 bullet-listed features. Each must be something buildable as browser-based web functionality.

## Data flows needed
Bullet-list WHAT KIND of information the app would need from external sources to work meaningfully. DO NOT name any specific service, product, or brand (no Google, OpenAI, Maps, Spotify, etc.). Describe only the NATURE of the data — e.g. "real-time public transport timetables", "public weather data", "text translation between languages", "text-based conversation with an AI", "image recognition from a photo". This list helps developers understand which API integrations the vibe-coding template should expose.

## Building it on a vibe-coding platform
In 2–4 sentences: how would this be built in practice as a browser-based web app? Where to start, what is the simplest working version that can be put on screen first, and what can be layered on top? This section keeps the concept grounded.

Design the concept so that it works well on mobile. Mobile use is a strong starting point: the UI, user journey, and features should be naturally usable in a phone browser. This is not an absolute requirement and the concept does not have to be mobile-only, but the phone screen, touch input, and short bursts of use should guide the design.

Here is the report:

---
{report}
---
```

> **Important constraint to enforce in the prompt:** No named third-party services. This is deliberate — at this experimental stage we want to learn from Gemini what *kinds* of data integrations matter, not get a list of specific vendors.

---

## 7. `docker-compose.yml` changes

Add a new service entry alongside the existing two. Keep the existing `kipina-hello` and `kipina-reveal-data-api` blocks unchanged.

```yaml
  concept-api:
    build:
      context: ./apps/concept-api
    container_name: kipina-concept-api
    restart: unless-stopped
    ports:
      - "127.0.0.1:8082:8080"
    environment:
      GCP_PROJECT_ID: "apply-project-35406"
      GCP_LOCATION: "europe-west4"
      GEMINI_MODEL: "gemini-3-pro"
      GOOGLE_APPLICATION_CREDENTIALS: "/secrets/gcp-sa.json"
    volumes:
      - ./secrets/gcp-sa.json:/secrets/gcp-sa.json:ro
```

> Do NOT publish on `0.0.0.0`. Bind to `127.0.0.1` only. Public access goes through Caddy.

---

## 8. `infra/caddy/Caddyfile` changes

Inside the existing `pilot.kipina.digiter.fi` block, add a route for `/api/concepts/*` BEFORE the existing `/api/*` route. Caddy matches in order, so the more specific path must come first.

Conceptually:

```
pilot.kipina.digiter.fi {
    handle /api/concepts/* {
        reverse_proxy localhost:8082
    }
    handle /api/* {
        reverse_proxy localhost:8081
    }
    handle {
        reverse_proxy localhost:8080
    }
}
```

After editing, reload Caddy without dropping connections:
```
sudo systemctl reload caddy
```

Verify with:
```
sudo systemctl status caddy
sudo journalctl -u caddy -n 30
```

---

## 9. GCP Service Account setup

Vertex AI is already enabled in `apply-project-35406` (Reveal Platform uses it). You need to create or reuse a service account that has permission to call Gemini.

Required IAM role on the project: `roles/aiplatform.user`.

Steps:

1. In GCP Console → IAM & Admin → Service Accounts, create `kipina-concept-api@apply-project-35406.iam.gserviceaccount.com` (or reuse an existing dedicated SA — do not reuse Reveal's SA, keep them separated).
2. Grant `Vertex AI User` (`roles/aiplatform.user`) on the project.
3. Create a JSON key for this service account, download it.
4. Copy the JSON to the server at `/opt/kipina-pilot/secrets/gcp-sa.json` (adjust path to wherever the repo lives on the host).
5. Set permissions: `chmod 600 secrets/gcp-sa.json`.
6. Verify it is gitignored: `git check-ignore -v secrets/gcp-sa.json` should report it as ignored.

---

## 10. Frontend changes

The pilot frontend uses i18n with `fi.ts` and `en.ts` translation files. Add new translation keys, then wire up the button.

### Translation keys to add

In `fi.ts`:
```ts
concept: {
  generateButton: "Luo konsepti",
  loading: "Luodaan konseptia…",
  errorTitle: "Konseptin luonti epäonnistui",
  errorRetry: "Yritä uudelleen",
  heading: "Konsepti"
}
```

In `en.ts`:
```ts
concept: {
  generateButton: "Generate concept",
  loading: "Generating concept…",
  errorTitle: "Concept generation failed",
  errorRetry: "Try again",
  heading: "Concept"
}
```

### Button behavior on the report view

1. Render a "Luo konsepti" / "Generate concept" button below the report.
2. On click:
   - Disable the button.
   - Show a spinner with the `loading` text.
   - `POST /api/concepts/generate` with body `{ report: <report text>, language: <current i18n language> }`.
   - On success: render the returned `concept` string below the button. Concept is plain text with `##` markdown headings — render those as `<h2>` (or use a small markdown renderer if one is already in the project; otherwise simple regex-based replacement is fine for this minimal subset).
   - On error: show `errorTitle` and an `errorRetry` button. Clicking retry repeats the request.
3. If a concept has already been generated in this session for this report, do not call the API again — just keep showing it. (No persistence beyond browser memory in this version.)

### Styling

Match the existing dark theme. Concept block uses the same card/panel style as the existing tenant cards (rounded corners, subtle border, slightly lighter background than the page).

---

## 11. `.env.example` additions

Append:

```
# Concept API (Vertex AI / Gemini 3)
GCP_PROJECT_ID=apply-project-35406
GCP_LOCATION=europe-west4
GEMINI_MODEL=gemini-3-pro
```

The `GOOGLE_APPLICATION_CREDENTIALS` path is hardcoded in compose since it points to the in-container mount path; it does not need to be in `.env`.

---

## 12. Acceptance criteria

The task is complete when ALL of the following are true:

1. `docker compose build concept-api` completes successfully.
2. `docker compose up -d` brings the new container up alongside the existing two.
3. `docker ps` shows `kipina-concept-api` healthy.
4. `curl http://localhost:8082/api/concepts/health` returns `{"ok": true, "service": "kipina-concept-api"}`.
5. `curl https://pilot.kipina.digiter.fi/api/concepts/health` returns the same (i.e. Caddy routes correctly).
6. `curl https://pilot.kipina.digiter.fi/api/health` STILL returns the reveal-data-api health (i.e. existing route untouched).
7. A POST to `/api/concepts/generate` with a small dummy report returns a plain-text concept in the requested language. Verify both `fi` and `en`.
8. Concept text contains the six expected section headings (`## Idean nimi` / `## Idea name`, `## Pähkinänkuoressa` / `## In a nutshell`, `## Käyttäjäpolku` / `## User journey`, `## Ydintoiminnot` / `## Core features`, `## Tarvittavat tietovirrat` / `## Data flows needed`, `## Toteutus vibekoodausalustalla` / `## Building it on a vibe-coding platform`) and contains NO named third-party services in the data-flows section. If Gemini names a service anyway, that's a prompt-tuning issue to flag — but acceptance still passes.
9. The frontend "Luo konsepti" button appears on the report view, calls the API, shows a spinner, and renders the returned concept.
10. `secrets/gcp-sa.json` is present on the host, mounted read-only into the container, and not tracked by git.
11. No container in `docker ps` exposes a public `0.0.0.0` port. All app containers stay on `127.0.0.1`.

---

## 13. What to verify on the running server before declaring done

Run these in order on the UpCloud host. Report the output of each:

```bash
docker compose ps
docker logs kipina-concept-api --tail 20
curl -s http://localhost:8082/api/concepts/health
curl -s https://pilot.kipina.digiter.fi/api/concepts/health
curl -s https://pilot.kipina.digiter.fi/api/health
curl -s -X POST https://pilot.kipina.digiter.fi/api/concepts/generate \
  -H 'Content-Type: application/json' \
  -d '{"report":"Idea: sovellus joka muistuttaa nuorta juomaan vettä päivän aikana. Käyttäjä saa hellät push-viestit ja näkee oman edistymisensä viikkotasolla.","language":"fi"}'
```

The last call should return a JSON object with a `concept` field containing a Finnish concept description with the five required headings.

---

## 14. Things to flag back rather than guess

If any of these are unclear when you reach them, stop and ask before proceeding — do not invent answers:

- The exact GA model identifier for Gemini 3 on Vertex AI (`gemini-3-pro` is the assumed default but verify against current Vertex AI docs at build time).
- The exact location of the existing report-view component in the frontend code (the project has both placeholder `html/index.html` and an i18n-enabled app — clarify which one is the live one before wiring the button).
- Whether `secrets/gcp-sa.json` already exists on the server, or you need to coordinate its creation with the project owner.
