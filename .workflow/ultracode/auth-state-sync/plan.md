# Ultracode Plan: Frontend Auth State Sync Fix

- Goal: Fix frontend auth state mismatch where Sidebar displays "Sign in Required" after login and during hydration.
- Mode: Workflow mode
- Risk: Medium
- Target Scope: `frontend/src/`

## Strategy
1. Fix SSR hydration pipeline to preserve workspaces from `hooks.server.ts` through `+layout.server.ts` to `+layout.svelte`.
2. Fix `Sidebar.svelte` title/subtitle fallbacks for authenticated and loading states.
3. Fix `AppShell.svelte` modal render timing to wait for `isRehydrating == false`.
4. Fix `sources/+page.svelte` workspace ID state binding.
5. Add comprehensive unit & integration tests covering guest, auth, hydration, login/logout without refresh, refresh session persistence, and protected UI state.
