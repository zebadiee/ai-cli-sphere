# Security Notes — Secrets Posture

Purpose: record a hard line on where secrets may and may not live, and how Obsidian may safely be used for read-only viewer tokens.

Key rules
- **Do not** store production secrets in Obsidian vault notes or files.
- **Do not** commit secrets to Git or put secrets in repository files scanned by CI.
- **Do not** add Obsidian plugins that store host-level secrets in plaintext plugin settings or sync them to cloud providers unless the plugin uses secure SecretStorage.

Allowed pattern (conservative):
- Obsidian's SecretStorage may be used to store a short-lived, read-only viewer token for a user's convenience, but:
  - Tokens stored in SecretStorage must not be considered authoritative credentials for operations that change state.
  - Tokens should be scoped to read-only endpoints and be short lived.
  - The CI secret scanner and host .env.prod (host-local) remain the canonical place for operational secrets.

CI and scanning
- CI secret scanning remains authoritative; any secrets found in repo files must be removed and rotated.
- The workflow for secrets: prefer host-managed secrets (vault, secret manager), then CI scanning, then short-lived viewer tokens only in SecretStorage for read-only use.

Rationale
- Obsidian vaults are editable and often synced; storing secrets in them risks leakage and undermines auditability.
- Conservatively limiting Obsidian to read-only viewer tokens prevents accidental privilege escalation via third-party UI tools.

If you need a sample policy to include in onboarding docs, copy this file into your security playbook and add org-specific guidance (rotations, TTL, approvers).
