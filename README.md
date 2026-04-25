# Kipina Pilot

This repository contains the UpCloud-hosted deployment skeleton for the Kipina pilot.

Today, the stack is intentionally minimal:

- `Caddy` on the host reverse proxies the placeholder site to `localhost:8080` and `/api/*` to `localhost:8081`
- `docker-compose.yml` runs a placeholder `nginx` container
- `docker-compose.yml` also runs a small `reveal-data-api` container for health checks
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

## Server Capacity

The UpCloud host has been expanded and the root filesystem now provides enough working space for both this repository and the separate Reveal Platform structure:

- CPU: `2 vCPU`
- RAM: approximately `8 GB`
- Disk: `40 GB`
- Free disk: approximately `34 GB`
- Disk usage: `13%`

Current root filesystem state:

```text
/dev/vda2  40G  4.6G  34G  13%  /
```

Docker sees the same expanded filesystem through its overlay mounts:

```text
overlay  40G  4.6G  34G  13%
```

This capacity is the intended baseline for:

- `/opt/kipina-pilot`
- `/opt/reveal-platform`

## Current Operation

The current placeholder and health API are the active workload:

```bash
docker compose up -d
```

That command should continue to start:

- `kipina-hello`, serving `./html/index.html` on `127.0.0.1:8080`
- `kipina-reveal-data-api`, serving `GET /api/health` on `127.0.0.1:8081`

Public traffic should go through Caddy:

- `https://pilot.kipina.digiter.fi/`
- `https://pilot.kipina.digiter.fi/api/health`
