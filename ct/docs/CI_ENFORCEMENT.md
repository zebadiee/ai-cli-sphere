# CI Enforcement: Integration & Governance Gates

Purpose
- Convert validated behavior into mandatory CI gates to prevent regressions that would weaken governance guarantees.

What this adds
- A GitHub Actions workflow: `.github/workflows/integration.yml`
  - Runs on PRs and pushes to `main`/`master`
  - Builds the Compose stack, waits for health, runs the automated abuse suite inside the orchestrator container, runs the live validation harness, then tears down.
- A runnable script: `scripts/ci/run_integration_tests.sh` for local and CI usage.

Required secrets
- `CT_TEST_KEY` (set in the repository Secrets)
  - Purpose: Test-only API key with `intent.submit` and read permissions only.
  - Do NOT commit keys to the repo. Use GitHub Secrets to inject this during CI runs.

Branch protection
- Configure branch protection for `main` to require the `Integration Tests (Governance Enforced)` workflow to pass before merging.

Operational notes
- The CI job is intentionally strict: failure blocks merges.
- Jobs run in GitHub runners and depend on Docker Compose availability.
- The orchestrator container is used to run in-container unit-style abuse tests to avoid installing server-side dependencies in the runner.

Local reproduction
- To run locally (fast feedback):
  - export CT_TEST_KEY=sk_test_xxx
  - ./scripts/ci/run_integration_tests.sh

Rationale
- Lock the proven behavior: schema validation, audit trail, approval semantics, and denial-of-service guard awareness.
- Prevent accidental regressions from being merged without explicit human review and re-validation.

Change log
- This enforcement was added as part of the Phase A/B/C stabilization and is the authoritative check for future PRs.
