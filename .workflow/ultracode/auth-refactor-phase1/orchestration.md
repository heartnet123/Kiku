# Ultracode Orchestration: Auth Refactor Phase 1

- Parent critical path: Plan generation, user approval gate, integration, verification.
- Mode: Workflow mode / Planning mode gate.
- Packets:
  - Packet 1: `auth.ts` (Auth Store + Auto Refresh)
  - Packet 2: `workspace.ts` (Workspace Store)
  - Packet 3: `LoginModal.svelte` (Clean Modal)
  - Packet 4: Import Migration & Test Updates
- Fallback reason for native subagents: Awaiting plan approval from user before code edits.
- Verification order: `bun run check` -> `bun run test`.
