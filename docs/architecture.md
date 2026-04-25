# Kipina Pilot Architecture

## Overview

The Kipina pilot uses a split architecture:

- `Cloud Run` hosts the stable Reveal Engine.
- `UpCloud` hosts the sovereign data layer and pilot-specific runtime services.

This keeps the mature engine path stable while ensuring sensitive pilot data handling stays under controlled infrastructure on UpCloud.

## Intended Data Flow

1. User interactions are processed through the Reveal Engine running on Cloud Run.
2. Temporary handoff context may be written to `Valkey` on UpCloud.
3. That handoff context must expire automatically with a maximum TTL of `24 hours`.
4. Final outputs that pass DLP cleaning may be stored in `PostgreSQL` on UpCloud.
5. Raw user answers must not be stored permanently.

## Storage Rules

### Valkey

- Purpose: short-lived handoff context between processing stages
- Retention: maximum `24h` TTL
- Persistence goal: temporary operational cache, not a system of record
- Exposure: internal-only, never exposed directly to the public internet

### PostgreSQL

- Purpose: storage of DLP-cleaned final reports
- Retention: according to pilot reporting and governance needs
- Prohibited content: raw user answers and other uncleaned sensitive payloads
- Exposure: internal-only, never exposed directly to the public internet

## Security Principles

- No real secrets are committed to the repository.
- Runtime secrets belong in `secrets/` or the host environment, not in source control.
- Internal data services such as `Valkey` and `PostgreSQL` should be reachable only from trusted application containers or the host as explicitly required.
- Public ingress should terminate at `Caddy`, which proxies only the intended application endpoints.

## Repository Mapping

- `apps/frontend`: future user-facing frontend
- `apps/reveal-data-api`: future API layer on UpCloud
- `services/valkey`: Valkey data/config area
- `services/postgres`: PostgreSQL data/config area
- `infra/caddy`: Caddy-related configuration and notes
- `infra/docker`: Docker-related configuration and compose extensions
- `scripts`: operational helper scripts
- `docs`: architecture and deployment documentation
- `secrets`: untracked runtime secrets
