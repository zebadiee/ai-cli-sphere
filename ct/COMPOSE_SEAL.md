# COMPOSE PRODUCTION LOCK

**Status:** PRODUCTION COMPOSE FROZEN & LOCKED
**Date:** 2026-01-12
**Tag:** ct-compose-prod-locked

## Actions Performed
- Added `.env.example` and `.env.prod` as template (no secrets committed).
- Added `docker-compose.override.yml` with production-safe defaults:
  - `env_file: .env.prod` (template only)
  - Logging rotation (json-file)
  - Resource limits (CPU/memory)
  - Restart policy: `unless-stopped`
- Added lightweight Docker `healthcheck` blocks for `gateway`, `orchestrator`, `observer`, `mock-tool` (read-only probes against `/health`).
- Removed deprecated `version` key from `docker-compose.yml`.
- Added `.env.prod` to `.gitignore` and untracked any committed `.env.prod`.

## Guarantees
- No secrets are committed in repo. Production secrets must be supplied at deploy time.
- Compose config validated (with override applied) and includes healthchecks + resource limits.
- Any future change to compose requires explicit commit and tag; this state is the authoritative baseline for production deployment.

## Validation
- `docker compose -f docker-compose.yml -f docker-compose.override.yml config` passed and shows healthchecks and `deploy.resources` limits.

## Next steps (manual)
- Deploy to production host with `.env.prod` provided by ops.
- Add CI enforcement (optional): verify compose config and no committed secrets.
- Add artifact provenance & signing as part of release pipeline.

---

This file is the canonical seal for the compose configuration at tag `ct-compose-prod-locked`.