# CT — Obsidian Companion (Design Spec)

Status: design-only, read-only, NOT shipped or enabled.

## Purpose
- Provide a minimal, read-only Obsidian companion that surfaces CT status information (intents, orchestrator state, audit trail) for human review and note-taking.
- No control plane privileges; strictly viewer-only for compliance and human context.

## Scope & Guarantees
- Read-only: supports GET-only views of status, intents, plans, and audit trail.
- Secrets: uses Obsidian SecretStorage for *read-only* tokens (if the user wants to display contextual information from an external monitoring token). Secrets are never persisted as plaintext in notes or files.
- Non-blocking: plugin is a passive viewer. It does NOT perform approvals, plan executions, or any state mutations.
- Non-authoritative: the CT runtime, CI, and orchestrator remain the single source of truth.

## SecretStorage — Conceptual usage (security-first)
- The plugin stores any short-lived viewer token in Obsidian's SecretStorage API (plugin-managed secrets). DO NOT store API keys in notes, config, or synced plugin settings.
- The plugin will only request secrets from SecretStorage at runtime and use them transiently for read-only API calls that fetch status. No secrets are written to disk or shared via sync.

Conceptual (non-functional) pattern:

// Pseudocode - conceptual only
// const secret = await this.app.secretStorage.get("ct.viewer.token")
// const resp = await fetch("https://ct-gateway.example/governance/orchestrator-state", { headers: { Authorization: `Bearer ${secret}` }})

> Note: This doc intentionally avoids copying exact API surface; see `plugin_skeleton.ts` for a commented, minimal example.

## Non-goals (explicit)
- No approval, no POST/PUT/PATCH/DELETE to CT APIs.
- No CI integration, no pipeline hooks, no automation of approvals.
- No storage of production secrets in vaults or files.
- Not intended as a replacement for CT dashboards, only a lightweight human context surface.

## Operational notes
- Users must opt-in to install or enable the plugin. Default behavior is disabled.
- Recommend a short README and a permissions page explaining SecretStorage and why vaults must remain secret-free.

## Files
- `docs/obsidian/plugin_skeleton.ts` — commented, non-functional skeleton for future implementation.
- `docs/obsidian/ARCHITECTURAL_INVARIANTS.md` — records the deferral of Obsidian from control plane tasks.

---
*Created as design-level artifact only.*
