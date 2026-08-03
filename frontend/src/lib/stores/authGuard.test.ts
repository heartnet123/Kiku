import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import {
	authStore,
	authModalStore,
	requireAuth,
	openLoginModal,
	openRegisterModal,
	closeLoginModal,
	setAuthSession,
	logout
} from './auth';

describe('YAGNI Auth Guard & Modal Intercept Flow', () => {
	const mockUser = { id: 'usr-guest-1', email: 'guest@example.com', full_name: 'Guest User' };
	const mockWorkspace = { id: 'ws-1', name: 'Default WS', slug: 'default-ws', role: 'member' as const };
	const mockJwt = 'header.payload.signature';

	afterEach(() => {
		vi.restoreAllMocks();
		logout();
		closeLoginModal();
	});

	it('1. Guest initialization keeps LoginModal closed (Acceptance Criteria 1 & 2)', () => {
		const auth = get(authStore);
		const modal = get(authModalStore);

		expect(auth.isAuthenticated).toBe(false);
		expect(modal.isOpen).toBe(false);
		expect(modal.pendingAction).toBeNull();
	});

	it('2. Guest calling read-only action does not open modal', () => {
		const readOnlyFn = vi.fn();
		readOnlyFn();

		expect(readOnlyFn).toHaveBeenCalledOnce();
		expect(get(authModalStore).isOpen).toBe(false);
	});

	it('3. Guest calling database mutation triggers LoginModal & sets pendingAction (Acceptance Criteria 3)', () => {
		const mutationFn = vi.fn();
		const result = requireAuth(mutationFn);

		expect(result).toBe(false);
		expect(mutationFn).not.toHaveBeenCalled();

		const modal = get(authModalStore);
		expect(modal.isOpen).toBe(true);
		expect(modal.pendingAction).toBe(mutationFn);
	});

	it('4. Authenticated user calling mutation executes action immediately without modal (Acceptance Criteria 4)', () => {
		setAuthSession(mockJwt, mockUser, [mockWorkspace]);
		expect(get(authStore).isAuthenticated).toBe(true);

		const mutationFn = vi.fn();
		const result = requireAuth(mutationFn);

		expect(result).toBe(true);
		expect(mutationFn).toHaveBeenCalledOnce();
		expect(get(authModalStore).isOpen).toBe(false);
	});

	it('5. Post-login auto-resumes pending action and closes modal (Acceptance Criteria 4 & 5)', () => {
		const pendingMutation = vi.fn();
		requireAuth(pendingMutation);

		expect(get(authModalStore).isOpen).toBe(true);

		// Perform login
		setAuthSession(mockJwt, mockUser, [mockWorkspace]);

		expect(pendingMutation).toHaveBeenCalledOnce();
		expect(get(authModalStore).isOpen).toBe(false);
		expect(get(authModalStore).pendingAction).toBeNull();
	});

	it('6. Guest can dismiss LoginModal cleanly via closeLoginModal', () => {
		const pendingFn = vi.fn();
		openLoginModal(pendingFn);

		expect(get(authModalStore).isOpen).toBe(true);
		expect(get(authModalStore).mode).toBe('login');

		closeLoginModal();

		expect(get(authModalStore).isOpen).toBe(false);
		expect(get(authModalStore).pendingAction).toBeNull();
		expect(pendingFn).not.toHaveBeenCalled();
	});

	it('7. openRegisterModal opens AuthModal in register mode', () => {
		openRegisterModal();

		const modal = get(authModalStore);
		expect(modal.isOpen).toBe(true);
		expect(modal.mode).toBe('register');
	});
});
