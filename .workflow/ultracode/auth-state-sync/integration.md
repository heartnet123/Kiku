# Ultracode Integration Notes

## Changed Files
1. `frontend/src/app.d.ts` - Added `workspaces: WorkspaceItem[] | null` to `App.Locals`.
2. `frontend/src/hooks.server.ts` - Preserved `data.workspaces` on successful token check.
3. `frontend/src/routes/+layout.server.ts` - Returned `workspaces: locals.workspaces ?? []`.
4. `frontend/src/routes/+layout.svelte` - Passed `data.workspaces` to `initFromServer`.
5. `frontend/src/lib/components/Sidebar.svelte` - Updated `team-switcher` title and subtitle logic for authenticated, rehydrating, and guest states.
6. `frontend/src/lib/components/AppShell.svelte` - Deferred `<LoginModal />` render until `!$authStore.isRehydrating`.
7. `frontend/src/routes/sources/+page.svelte` - Bound `workspaceId` to `$workspaceStore.currentWorkspace?.id`.
8. `frontend/src/lib/stores/auth.ts` - Fixed `_scheduleTokenRefresh` 32-bit integer overflow.
9. `frontend/src/lib/stores/authFlow.test.ts` - Added unit & flow integration tests for 6 core auth scenarios.
