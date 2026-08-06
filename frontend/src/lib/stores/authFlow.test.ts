import { afterEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import {
	authStore,
	setAuthSession,
	logout,
	rehydrateAuth,
	getAuthToken,
	getCurrentUser,
	initFromServer
} from './auth';
import { workspaceStore, setWorkspaces, switchWorkspace } from './workspace';

describe('Frontend Auth State Sync & Session Lifecycle Flow', () => {
	const user = { id: 'usr-100', email: 'alice@example.com', full_name: 'Alice Cooper' };
	const workspace = {
		id: 'ws-100',
		name: 'Acme Corp',
		slug: 'acme-corp',
		role: 'admin' as const
	};
	const dummyJwt = 'header.eyJleHAiOjE4MDAwMDAwMDB9.signature';

	afterEach(() => {
		vi.restoreAllMocks();
		logout();
		vi.unstubAllGlobals();
	});

	// 1. Guest state
	it('1. correctly represents Guest state on unauthenticated initialization', () => {
		const state = get(authStore);
		const wsState = get(workspaceStore);

		expect(state.isAuthenticated).toBe(false);
		expect(state.user).toBeNull();
		expect(state.token).toBeNull();
		expect(getAuthToken()).toBeNull();
		expect(getCurrentUser()).toBeNull();

		expect(wsState.workspaces).toEqual([]);
		expect(wsState.currentWorkspace).toBeNull();
	});

	// 2. Authenticated state
	it('2. correctly represents Authenticated state with synchronized user and workspace', () => {
		setAuthSession(dummyJwt, user, [workspace]);

		const state = get(authStore);
		const wsState = get(workspaceStore);

		expect(state.isAuthenticated).toBe(true);
		expect(state.isRehydrating).toBe(false);
		expect(state.user).toEqual(user);
		expect(state.token).toBe(dummyJwt);
		// The refresh token stays in the HttpOnly cookie, never in this store.
		expect('refreshToken' in state).toBe(false);

		expect(wsState.workspaces).toEqual([workspace]);
		expect(wsState.currentWorkspace).toEqual(workspace);
	});

	// 3. Loading/hydration state
	it('3. manages Loading/hydration state correctly during SSR & client rehydration', async () => {
		// Initial state has isRehydrating: true
		authStore.set({
			token: null,
			user: null,
			isAuthenticated: false,
			isRehydrating: true,
			tokenExpiresAt: null
		});

		expect(get(authStore).isRehydrating).toBe(true);

		// SSR pre-hydration with workspace
		initFromServer(
			{
				token: dummyJwt,
				user,
				isAuthenticated: true,
				isRehydrating: false,
				tokenExpiresAt: 1800000000 * 1000
			},
			[workspace]
		);

		const hydratedState = get(authStore);
		const wsState = get(workspaceStore);

		expect(hydratedState.isAuthenticated).toBe(true);
		expect(hydratedState.isRehydrating).toBe(false);
		expect(wsState.currentWorkspace).toEqual(workspace);
	});

	// 4. Login and logout without refresh
	it('4. updates store immediately on login and logout without requiring a page refresh', async () => {
		// Start guest
		expect(get(authStore).isAuthenticated).toBe(false);

		// Execute login session update
		setAuthSession(dummyJwt, user, [workspace]);

		// Instant state assertion
		expect(get(authStore).isAuthenticated).toBe(true);
		expect(get(authStore).user?.full_name).toBe('Alice Cooper');
		expect(get(workspaceStore).currentWorkspace?.name).toBe('Acme Corp');

		// Execute logout
		const fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
		vi.stubGlobal('window', {});
		vi.stubGlobal('fetch', fetchSpy);

		logout();

		// Instant reset assertion
		expect(get(authStore).isAuthenticated).toBe(false);
		expect(get(authStore).user).toBeNull();
		expect(get(workspaceStore).currentWorkspace).toBeNull();
	});

	// 5. Refresh and maintain session
	it('5. maintains session on rehydrateAuth when session is active', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					token: 'token-refreshed',
					user,
					workspaces: [workspace]
				}),
				{ status: 200 }
			)
		);
		vi.stubGlobal('window', {});
		vi.stubGlobal('fetch', fetchMock);

		await rehydrateAuth();

		const state = get(authStore);
		const wsState = get(workspaceStore);

		expect(state.isAuthenticated).toBe(true);
		expect(state.token).toBe('token-refreshed');
		expect(state.user).toEqual(user);
		expect(wsState.currentWorkspace).toEqual(workspace);

		vi.unstubAllGlobals();
	});

	// 6. Protected UI & workspace state consistency
	it('6. keeps protected UI state and workspace selection consistent even with empty or updated workspaces', () => {
		// User with multiple workspaces
		const ws1 = { id: 'ws-1', name: 'WS One', slug: 'ws-1', role: 'owner' as const };
		const ws2 = { id: 'ws-2', name: 'WS Two', slug: 'ws-2', role: 'member' as const };

		setAuthSession(dummyJwt, user, [ws1, ws2]);

		expect(get(workspaceStore).currentWorkspace).toEqual(ws1);

		// Switching workspace updates currentWorkspace synchronously
		switchWorkspace('ws-2');
		expect(get(workspaceStore).currentWorkspace?.id).toBe('ws-2');

		// A refreshed list keeps the active selection rather than resetting to the first
		setWorkspaces([ws2, ws1]);
		expect(get(workspaceStore).currentWorkspace?.id).toBe('ws-2');

		// If setWorkspaces is called with empty array for authenticated user
		setWorkspaces([]);
		expect(get(workspaceStore).currentWorkspace).toBeNull();
		// Auth state remains authenticated
		expect(get(authStore).isAuthenticated).toBe(true);
	});
});
