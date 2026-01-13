# Architectural Invariants — Obsidian & CT

This document records the explicit decisions and invariants for any Obsidian integration with CT.

1. Obsidian is a **viewer-only** surface. It may not:
   - Hold approval or execution authority
   - Mutate plan or orchestrator state
   - Be part of CI or runtime automation

2. All governance decisions, audits, and runtime state remain authoritative in CT's orchestrator and CI pipelines.

3. Any Obsidian plugin must only display information retrievable via the gateway's read-only endpoints and must not expose write operations.

4. Operational: installation is opt-in; no secrets are stored in vault files or synced via Obsidian Sync. If SecretStorage is used, it is for transient, read-only tokens only.

These invariants are intentionally strict to preserve the sealed governance posture of the CT system.
