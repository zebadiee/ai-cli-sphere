# Changelog: Obsidian Companion docs (design-only)

This change set introduces design-level artifacts to record a safe, read-only Obsidian companion for CT.

Files added:
- docs/obsidian/CT_OBSIDIAN_PLUGIN.md
- docs/obsidian/plugin_skeleton.ts (commented, non-functional)
- docs/obsidian/ARCHITECTURAL_INVARIANTS.md
- SECURITY_NOTES.md

Summary:
- Adds design guidance and strict security posture for any future Obsidian integration.
- Records that Obsidian is read-only and not part of runtime, approval, or CI workflows.

No runtime code changed. No CI workflows altered.
