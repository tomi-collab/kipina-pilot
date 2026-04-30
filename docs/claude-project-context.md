# Kipina Pilot — Project Context for Claude

This document is the authoritative context for Kipina pilot development work. It covers infrastructure, current stack, architecture decisions, and the relationship to Reveal Platform.

---

## What Is Kipina Pilot?

Kipina is Digiterin pilottipalvelu: a service that helps young people articulate their ideas and take them toward a working digital solution ("Ideasta ensimmäiseksi askeleeksi"). The pilot runs at `https://pilot.kipina.digiter.fi`.

The pilot is intentionally kept separate from Reveal Platform (`/opt/reveal-platform`). Kipina can later become one tenant inside Reveal Platform, but the repositories must remain independent.

---

## Server

UpCloud VPS, running Ubuntu/Debian with Docker and Caddy.

| Resource | Value |
|----------|-------|
| CPU | 2 vCPU |
| RAM | ~8 GB |
| Disk | 40 GB total, ~34 GB free (13% used) |
| Public domain | `pilot.kipina.digiter.fi` |

The server also hosts Reveal Platform at `/opt/reveal-platform` — a separate codebase on the same machine.

---

## Infrastructure

### Caddy (host-level reverse proxy)

Config at `infra/caddy/Caddyfile`. Caddy runs as a systemd service (`caddy.service`, enabled, active). It handles TLS automatically via ACME.

Routing for `pilot.kipina.digiter.fi`:

| Path | Target |
|------|--------|
| `/api/*` | `localhost:8081` (reveal-data-api) |
| `/` (everything else) | `localhost:8080` (nginx placeholder) |

### Docker Compose

All services defined in `docker-compose.yml`. Start with `docker compose up -d`.

**Active services:**

| Container | Image | Bind | Purpose |
|-----------|-------|------|---------|
| `kipina-hello` | `nginx:alpine` | `127.0.0.1:8080` | Serves `html/index.html` placeholder |
| `kipina-reveal-data-api` | `kipina-pilot-reveal-data-api` (local build) | `127.0.0.1:8081` | Health API |

Both containers have been running for 5+ days and are healthy.

---

## Repository Structure

```
.
├── apps/
│   ├── frontend/          (empty, .gitkeep — future frontend)
│   └── reveal-data-api/   (Python HTTP health API)
│       ├── app.py
│       └── Dockerfile
├── docs/
│   └── architecture.md
├── html/
│   └── index.html         (Finnish-language placeholder page, dark theme)
├── infra/
│   ├── caddy/
│   │   └── Caddyfile
│   └── docker/            (empty, .gitkeep)
├── scripts/               (empty, .gitkeep)
├── secrets/               (gitignored runtime secrets)
├── services/
│   ├── postgres/          (empty, .gitkeep — future)
│   └── valkey/            (empty, .gitkeep — future)
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## Current Tech Stack

### reveal-data-api (`apps/reveal-data-api/`)

- Python 3.12, Alpine base image
- Pure stdlib: `http.server.BaseHTTPRequestHandler`, `ThreadingHTTPServer`
- No web framework — same pattern as Reveal Platform backends
- Single endpoint: `GET /api/health` → `{"ok": true, "service": "reveal-data-api", "environment": "kipina-pilot"}`
- Port 8080 inside container, mapped to `127.0.0.1:8081` on host

### Placeholder frontend (`html/index.html`)

- Static HTML, dark theme (`#101418` background)
- Finnish language (`lang="fi"`)
- Text: "Ideasta ensimmäiseksi askeleeksi."
- Served by `nginx:alpine` via Docker

### .env.example — prepared environment variables

```
PROJECT_NAME=kipina-pilot
APP_ENV=production
PUBLIC_BASE_URL=https://pilot.kipina.digiter.fi
REVEAL_ENGINE_BASE_URL=https://reveal-engine.example.run.app
VALKEY_HOST=valkey
VALKEY_PORT=6379
VALKEY_TTL_SECONDS=86400
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=kipina_pilot
POSTGRES_USER=kipina_app
```

`.env` itself is gitignored. `secrets/` is gitignored (only `.gitkeep` tracked).

---

## Architecture Direction

Split architecture: compute on hyperscalers, data control on UpCloud.

1. **Cloud Run** — runs the stable Reveal Engine (`reveal-api-kanavana`)
2. **UpCloud** — hosts the sovereign data layer for the pilot

Intended data flow:
1. User interactions processed by Reveal Engine (Cloud Run)
2. Temporary handoff context written to Valkey on UpCloud (max 24h TTL)
3. DLP-cleaned final reports stored in PostgreSQL on UpCloud
4. Raw user answers **must never be stored permanently**

### Future services (defined in docker-compose.yml as commented-out stubs)

| Service | Image | Purpose | Network |
|---------|-------|---------|---------|
| `valkey` | `valkey/valkey:8-alpine` | Temporary handoff context, 24h TTL | Internal only |
| `postgres` | `postgres:16-alpine` | DLP-cleaned final reports | Internal only |
| `frontend` | (local build from `apps/frontend/`) | User-facing Kipina UI | Public via Caddy |

Future Docker networks: `public` (external) and `private` (internal only). Neither Valkey nor PostgreSQL should ever publish ports.

---

## Security Principles

- No secrets committed to git. Runtime secrets go in `secrets/` or host environment.
- Internal services (Valkey, PostgreSQL) reachable only from trusted app containers or host.
- Public ingress terminates at Caddy only.
- All containers bind to `127.0.0.1` (localhost), never `0.0.0.0`.

---

## Git History

| Commit | Message |
|--------|---------|
| `a9bc15d` | Document expanded server capacity |
| `36cf2ce` | Add reveal data API health endpoint |
| `9b9488d` | Bind placeholder container to localhost |
| `ce20564` | Initial Kipina pilot skeleton |

No remote configured. Local git repository only (at this time).

---

## Relationship to Reveal Platform

Reveal Platform (`/opt/reveal-platform`, domain `reveal.kanavana.fi`) is the multi-tenant commercial control layer. It runs on the same UpCloud host but is an entirely separate codebase and Docker Compose stack.

Reveal Platform services currently running on the same host:

| Container | Bind | Purpose |
|-----------|------|---------|
| `reveal-platform-reveal-admin-ui-1` | `127.0.0.1:8090` | Admin SPA (React/TypeScript) |
| `reveal-platform-reveal-admin-api-1` | `127.0.0.1:8091` | Admin HTTP API (Python) |
| `reveal-platform-reveal-data-api-1` | `127.0.0.1:8092` | Engine-facing data API (Python) |
| `reveal-platform-postgres-1` | internal only | PostgreSQL (5 days healthy) |

Kipina pilot will eventually connect to Reveal Platform as one tenant via the runtime config resolve API (`POST /data/api/runtime-config/resolve`), but this is not yet implemented.

---

## What Is Built vs. Not Yet Built

### Built and working
- Caddy reverse proxy with TLS for `pilot.kipina.digiter.fi`
- nginx placeholder serving Finnish-language holding page
- `reveal-data-api` with `GET /api/health` endpoint
- Docker Compose stack for placeholder workload
- Repository structure prepared for next phase

### Not yet built (stubs/comments in place)
- Valkey temporary session state service
- PostgreSQL report storage service
- Frontend application (`apps/frontend/`)
- Docker networks (`public`/`private`)
- Any Reveal Engine integration for Kipina
- Scripts in `scripts/`

---

## Development Workflow

```bash
# Start current placeholder stack
docker compose up -d

# Verify health
curl http://localhost:8081/api/health
# → {"ok": true, "service": "reveal-data-api", "environment": "kipina-pilot"}

# View placeholder page
curl http://localhost:8080/
```

---

## Key Design Decisions

1. **Same server, separate stacks.** Reveal Platform and Kipina pilot run on the same UpCloud host but in separate Docker Compose projects. This keeps them operationally and conceptually independent.

2. **No web framework in backends.** Python stdlib HTTP handlers only — consistent with Reveal Platform approach.

3. **Raw user answers never stored permanently.** Only DLP-cleaned final reports reach PostgreSQL. Valkey handles transient state with 24h TTL max.

4. **All containers bind to localhost.** Public traffic must go through Caddy. No service publishes to `0.0.0.0`.

5. **Frontend-agnostic by design.** The data layer will accept any client that integrates correctly, not just the Kipina frontend.
