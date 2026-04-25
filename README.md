# Kipina Pilot

This repository contains the UpCloud-hosted deployment skeleton for the Kipina pilot.

Today, the stack is intentionally minimal:

- `Caddy` on the host reverse proxies `pilot.kipina.digiter.fi` to `localhost:8080`
- `docker-compose.yml` runs a placeholder `nginx` container
- `html/index.html` is the currently served placeholder page

The folder structure is prepared for the next production-oriented phase without changing the current working placeholder.

## Structure

```text
.
├── apps/
│   ├── frontend/
│   └── reveal-data-api/
├── docs/
│   └── architecture.md
├── html/
│   └── index.html
├── infra/
│   ├── caddy/
│   └── docker/
├── scripts/
├── secrets/
├── services/
│   ├── postgres/
│   └── valkey/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Architecture Direction

- `Cloud Run` will continue running the stable Reveal Engine.
- `UpCloud` will host the sovereign data layer for the pilot.
- `Valkey` will be used for temporary handoff context only, with a maximum `24h` TTL.
- `PostgreSQL` will store only DLP-cleaned final reports.
- Raw user answers must not be stored permanently.

More detail is in [docs/architecture.md](/opt/kipina-pilot/docs/architecture.md).

## Deployment Notes

- The current `docker-compose.yml` keeps the placeholder site running on `localhost:8080`.
- Future `Valkey` and `PostgreSQL` services are documented as internal-only and should not publish ports to the public internet.
- The `secrets/` directory is reserved for deployment-time secrets and is excluded from git.

## Current Operation

The current placeholder remains the active workload:

```bash
docker compose up -d
```

That command should continue to start the `nginx` placeholder container serving `./html/index.html`.
