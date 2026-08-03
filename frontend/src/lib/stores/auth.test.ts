import { afterEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
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

	it('sets auth session, persists to sessionStorage, and populates workspace store', () => {
		setAuthSession(dummyJwt, user, [workspace], 'refresh-123');

		const state = get(authStore);
		expect(state.isAuthenticated).toBe(true);
		expect(state.token).toBe(dummyJwt);
		expect(state.refreshToken).toBe('refresh-123');
		expect(state.user).toEqual(user);
		expect(state.tokenExpiresAt).toBe(1800000000 * 1000);

		expect(getAuthToken()).toBe(dummyJwt);
		expect(getCurrentUser()).toEqual(user);

		const wsState = get(workspaceStore);
		expect(wsState.workspaces).toEqual([workspace]);
		expect(wsState.currentWorkspace).toEqual(workspace);
	});

	it('clears session and workspace state on logout', () => {
		setAuthSession(dummyJwt, user, [workspace], 'refresh-123');
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

	it('triggers refresh immediately if delay is less than or equal to 0', async () => {
		// JWT with exp in past: exp = 1000 (Jan 1 1970)
		// Payload base64 for '{"exp":1000}' is 'eyJleHAiOjEwMDB9'
		const expiredJwt = 'header.eyJleHAiOjEwMDB9.signature';

		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					token: 'new-token',
					refresh_token: 'new-refresh',
					user,
					workspaces: [workspace]
				}),
				{ status: 200 }
			)
		);
		vi.stubGlobal('fetch', fetchMock);

		authStore.set({
			token: expiredJwt,
			refreshToken: 'refresh-old',
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
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ refresh_token: 'refresh-old' })
			})
		);

		const state = get(authStore);
		expect(state.token).toBe('new-token');
		expect(state.refreshToken).toBe('new-refresh');
	});
});
