# CT System Bootstrap (Authoritative Control Document)

Status: **Authoritative control artifact** — not a marketing README, not developer fluff. This document defines the system's purpose, non-goals, topology, authority model, exact bootstrap sequence, operating modes, and extension rules. It is intended for auditors, security reviewers, and operators.

---
## 1. Purpose & Non-Goals ✅

Purpose
- CT is an intent-as-data system: external actors submit *intents* that are schema-validated, auditable, and require human approval before any execution occurs.
- Human-in-the-loop by design: every approval action requires an explicit human operation.

Non-goals (explicit, immutable)
- CT will never autonomously approve or execute intents.
- CT will never allow third-party UI tools to hold approval/execution authority.
- CT will never persist production secrets in user-editable documents (notes, Markdown vaults, plugin settings without SecretStorage).

Rationale
- These non-goals preserve a minimal attack surface and provide forensic auditability.

---
## 2. System Topology (Mental Model first) 🧭

Components
- **Gateway** (edge): Authn/Authz, rate-limits, request validation, proxy to orchestrator. Public facing to registered clients only.
- **Orchestrator** (authority): Intent validation, intent queue, approval bridge, plan composition, audit log (append-only).
- **Observer(s)** (instrumentation): Optional emitters of artifacts and telemetry. Observers do NOT have control authority.
- **Clients**: CLI (human), SDK (thin), Obsidian (read-only intent origin only). Clients talk to Gateway only.

Deployment mapping
- **MacBook (beta client)**: local development & human operators (explicitly a non-authority device).
- **Pixel / Observer devices**: observer-only, recovery or monitoring surfaces.
- **Hades (authority host)**: orchestrator, execution, production-only responsibilities.

Communication rules
- Clients → Gateway → Orchestrator. No client talks directly to Hades components except authorized admin channels.
- Gateway enforces deny-by-default policy; only allowed endpoints are whitelisted.

---
## 3. Authority Model (Auditor-focused) 🔐

Who may submit intents
- Any authenticated client with `intent.submit` permission (API keys restricted to test/prod naming and stored appropriately).

Who may approve
- Authorized human operators using the CLI (or an approved admin console). Approval must be explicit and authenticated.

What approval means
- Approval transitions intent status: `pending` → `approved`. Approval may trigger plan composition (best-effort) but does NOT implicitly cause execution.

HALT semantics
- Approvals set HALT = true by default when necessary. Nothing will resume without an explicit resume API call and human confirmation.

Why nothing resumes itself
- Execution has additional control gates (approve-composed-plan, resume signal) that require human interaction and are recorded in audit chain.

Audit attribution
- Every intent and approval emits append-only audit events with actor and timestamp.
- Audit chains must be followed backward to `intent_received` for forensic analysis.

---
## 4. Bootstrap Sequence — Exact Checklist (Reproducible) ✅

Preconditions
- Local machine (MacBook) has Docker Engine & Compose, Python 3.11+, and `openssl` available.
- Repository cloned and checked out.

Exact steps (literal commands)
1. Clone repo
   - git clone <repo> && cd ct
2. Create a local env variables file (or export) with test key (do not commit)
   - export CT_API_KEY=sk_test_obsidian_beta_$(openssl rand -hex 8)
3. Build and start the stack
   - docker compose -f docker-compose.yml up -d --build
4. Wait for gateway health
   - curl -sSf http://localhost:9001/health
5. Submit a test intent via SDK
   - python - <<'PY'
     from ct_client import CTClient
     import os
     client = CTClient(gateway_url='http://localhost:9001', api_key=os.environ.get('CT_API_KEY'))
     resp = client.submit_intent(intent='inspect_repo', target='Graph.tsx', mode='reason-only', confidence=0.8, context={'source':'obsidian_beta'})
     print('INTENT_ID:', resp.intent_id, 'STATUS:', resp.status)
     PY
   - Expect: INTENT_ID (UUID) and STATUS = pending
6. Verify intent present
   - curl -H "Authorization: Bearer $CT_API_KEY" http://localhost:9001/governance/intents
   - Expect: entry with `intent_id`, `source: obsidian_beta`, `status: pending`
7. Verify audit recorded
   - curl -H "Authorization: Bearer $CT_API_KEY" "http://localhost:9001/governance/audit?limit=50"
   - Expect: `intent_received` event referencing the intent_id
8. Approve via CLI (human) — **manual**
   - curl -X POST -H "Authorization: Bearer $CT_API_KEY" http://localhost:9002/governance/approve/<INTENT_ID>
   - Expect: 200 OK, status approved
9. Verify approval in audit and intents endpoint
   - GET intents/audit and confirm `intent_approved` event and `approved` status
10. Tear down
    - docker compose -f docker-compose.yml down --volumes --remove-orphans

Acceptance criteria
- All bootstrap steps succeed reproducibly. The live validation harness and abuse tests must pass (these are CI gates).

---
## 5. Operating Modes (Clear separation) ⚙️

- Local Dev: All components in Docker Compose on a developer machine. No production keys. Use test keys ONLY.
- Beta Client (MacBook): Human operators and non-authoritative clients. Allowed to submit intents but not to approve unless explicitly authorized.
- Authority Host (Hades / Server): Runs orchestrator and execution engines; production secrets live on host-only secret storage.
- Observer-only devices (Pixel, Obsidian clients): Emit telemetry or submit read-only intents only (Obsidian is read-only origin unless explicitly allowed via documented process).

---
## 6. Extension Rules (Change governance) 📜

What requires a new phase (major governance change)
- Any change that modifies the approval model, approval semantics, or removes the human-in-the-loop guarantee.
- Any endpoint that enables data mutation of audit or approval artifacts.

Forbidden forever (without explicit board sign-off)
- UI tools or plugins being given approval/execution authority.
- Implicit or automatic resume/approval paths.

How changes are audited
- New features that affect authority must include:
  - A formal design note in docs/ (proposal, threat model, justification)
  - A security review and acceptance by the architecture/security owners
  - A CI gating addition ensuring no regression

Freeze rules
- A freeze for major governance changes requires: design sign-off, tests, CI gates, and a documented rollback plan.

---
## Appendices

A. Security Notes (short)
- No secrets in vaults. Use SecretStorage for plugin-only, short-lived viewer tokens.
- CI secrets: `CT_TEST_KEY` stored in repository secrets — production secrets never stored in repo.

B. Checklist for enforcement
- Add `Integration Tests (Governance Enforced)` workflow as required in branch protection (see `docs/CI_ENFORCEMENT.md`).
- Ensure `CT_TEST_KEY` exists in GitHub Secrets.

C. Change log reference
- See `docs/CHANGELOG_CI_ENFORCEMENT.md` for the CI gating addition and `docs/CHANGELOG_BOOTSTRAP_README.md` for this README's addition.

---
*This file was generated as the authoritative bootstrap README. Any changes that alter the authority model must follow the Extension Rules and be reviewed and approved by architecture and security owners.*
