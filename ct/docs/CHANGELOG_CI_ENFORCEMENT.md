# Changelog: CI Enforcement Added

Date: 2026-01-13

- Added GitHub Actions workflow `.github/workflows/integration.yml` which runs full integration checks (Compose up, in-container abuse tests, live validation harness).
- Added `scripts/ci/run_integration_tests.sh` to run the same checks locally or in CI.
- Added `docs/CI_ENFORCEMENT.md` describing the CI workflow, required secrets, and branch protection guidance.

Reason: Convert validated behavior into mandatory CI checks to prevent regressions that could weaken governance constraints.
