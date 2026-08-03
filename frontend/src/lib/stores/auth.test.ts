import { afterEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

// client.ts reads the base URL once at import, so the env has to be mocked
// (hoisted) rather than stubbed inside a test.
vi.mock('$env/dynamic/public', () => ({ env: { PUBLIC_API_BASE_URL: 'http://api.test:8000' } }));

import {
	authStore,
	setAuthSession,
	logout,
	_decodeJwtExp,
	_scheduleTokenRefresh,
	getAuthToken,
	getCurrentUser
} from './auth';
import { workspaceStore } from './workspace';

describe('authStore and auto-refresh', () => {
	const user = { id: 'usr-1', email: 'test@example.com', full_name: 'Test User' };
	const workspace = { id: 'ws-1', name: 'Test WS', slug: 'test-ws', role: 'admin' as const };

	// Dummy JWT with exp payload: { "exp": 1800000000 }
	// Payload base64 for '{"exp":1800000000}' is 'eyJleHAiOjE4MDAwMDAwMDB9'
	const dummyJwt = 'header.eyJleHAiOjE4MDAwMDAwMDB9.signature';

	afterEach(() => {
		vi.restoreAllMocks();
		logout();
	});

	it('decodes JWT expiration timestamp correctly', () => {
		const expMs = _decodeJwtExp(dummyJwt);
		expect(expMs).toBe(1800000000 * 1000);

		expect(_decodeJwtExp('invalid-token')).toBeNull();
		expect(_decodeJwtExp('header.invalid-base64.signature')).toBeNull();
	});

	it('sets auth session and populates workspace store', () => {
		setAuthSession(dummyJwt, user, [workspace]);

		const state = get(authStore);
		expect(state.isAuthenticated).toBe(true);
		expect(state.token).toBe(dummyJwt);
		expect(state.user).toEqual(user);
		expect(state.tokenExpiresAt).toBe(1800000000 * 1000);

		expect(getAuthToken()).toBe(dummyJwt);
		expect(getCurrentUser()).toEqual(user);

		const wsState = get(workspaceStore);
		expect(wsState.workspaces).toEqual([workspace]);
		expect(wsState.currentWorkspace).toEqual(workspace);
	});

	it('clears session and workspace state on logout', () => {
		setAuthSession(dummyJwt, user, [workspace]);
		logout();

		const state = get(authStore);
		expect(state.isAuthenticated).toBe(false);
		expect(state.token).toBeNull();
		expect(state.user).toBeNull();
		expect(getAuthToken()).toBeNull();

		const wsState = get(workspaceStore);
		expect(wsState.workspaces).toEqual([]);
		expect(wsState.currentWorkspace).toBeNull();
	});

	// A cookie-restored session has no client-readable refresh token; the refresh
	// must still fire and rely on the HttpOnly cookie via credentials: 'include'.
	it('triggers refresh immediately if delay is less than or equal to 0', async () => {
		// JWT with exp in past: exp = 1000 (Jan 1 1970)
		// Payload base64 for '{"exp":1000}' is 'eyJleHAiOjEwMDB9'
		const expiredJwt = 'header.eyJleHAiOjEwMDB9.signature';

		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					token: 'new-token',
					user,
					workspaces: [workspace]
				}),
				{ status: 200 }
			)
		);
		vi.stubGlobal('fetch', fetchMock);

		authStore.set({
			token: expiredJwt,
			user,
			isAuthenticated: true,
			isRehydrating: false,
			tokenExpiresAt: 1000 * 1000
		});

		_scheduleTokenRefresh();

		// Wait for microtask queue to process async _doRefresh
		await new Promise((r) => setTimeout(r, 10));

		expect(fetchMock).toHaveBeenCalledWith(
			expect.stringContaining('/api/v1/auth/refresh'),
			expect.objectContaining({ method: 'POST', credentials: 'include' })
		);
		// The refresh token must never travel in the request body.
		const sentBody = fetchMock.mock.calls[0][1]?.body;
		expect(sentBody).not.toContain('refresh_token');

		expect(get(authStore).token).toBe('new-token');
		vi.unstubAllGlobals();
	});

	it('setAuthSession keeps the token out of web storage', () => {
		// The node test env has no Storage class, so stub the globals auth.ts
		// would reach for and assert nothing is persisted at all.
		const setItem = vi.fn();
		vi.stubGlobal('window', {});
		vi.stubGlobal('sessionStorage', { setItem, getItem: vi.fn(), removeItem: vi.fn() });
		vi.stubGlobal('localStorage', { setItem, getItem: vi.fn(), removeItem: vi.fn() });

		setAuthSession(dummyJwt, user, [workspace]);

		expect(setItem).not.toHaveBeenCalled();
		vi.unstubAllGlobals();
	});

	it('logout posts to the API origin, not the SvelteKit origin', async () => {
		vi.stubEnv('PUBLIC_API_BASE_URL', 'http://api.test:8000');
		const fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
		vi.stubGlobal('window', {});
		vi.stubGlobal('fetch', fetchSpy);
		logout();
		await new Promise((r) => setTimeout(r, 0));
		expect(fetchSpy).toHaveBeenCalledWith(
			'http://api.test:8000/api/v1/auth/logout',
			expect.objectContaining({ method: 'POST', credentials: 'include' })
		);
		vi.unstubAllGlobals();
		vi.unstubAllEnvs();
	});
});
