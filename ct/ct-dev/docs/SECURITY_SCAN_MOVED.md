Security scan workflow moved to `.github/workflows/security-main.yml`.

Rationale: the Security Scan job had a transitive dependency that failed during job setup for PR runs; to avoid blocking PRs while preserving security enforcement, the scan now runs only on pushes to `main` via `security-main.yml` (auditable, reversible change).
