# Ultracode Plan: Auth Refactor Phase 1

Goal: Refactor auth into single source of truth store + auto-refresh in SvelteKit frontend.
Risk level: Medium
Blast radius: `frontend/src/lib/stores/`, `frontend/src/lib/components/`, `frontend/src/lib/api/`, `frontend/src/routes/`

## Eval contract
- Outcome: Single `authStore` in `auth.ts`, decoupled `workspaceStore` in `workspace.ts`, auto token refresh 2 min prior to JWT exp, clean `LoginModal.svelte` without preset buttons.
- Shared surfaces: `getAuthToken()`, `logout()`, `authStore`, `workspaceStore`, `setAuthSession()`.
- Required checks: `bun run check` (0 errors), `bun run test` (10/10 passed).
- Blocking conditions: Token refresh failures trigger clean `logout()`.

## Work Packets
1. Packet 1: Create `src/lib/stores/auth.ts` with JWT exp decoding and `setTimeout` auto-refresh.
2. Packet 2: Refactor `src/lib/stores/workspace.ts` to own workspace state only.
3. Packet 3: Create `LoginModal.svelte` (renamed from `DemoLoginModal.svelte`) without demo presets.
4. Packet 4: Migrate imports across components (`AppShell`, `Sidebar`, `sources/+page.svelte`, `+layout.svelte`, `client.ts`, `chatApi.ts`, `sources/api.ts`) and unit tests.
