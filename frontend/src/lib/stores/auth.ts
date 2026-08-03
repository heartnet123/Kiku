import { writable, get } from 'svelte/store';
import { apiRequest, apiUrl } from '../api/client';
import { decodeJwtExp } from '../utils/jwt';
import { setWorkspaces, clearWorkspaces, type WorkspaceItem, type UserProfile } from './workspace';

export type { UserProfile };

/**
 * Client-visible session. The refresh token deliberately lives only in the
 * HttpOnly `kiku_refresh_token` cookie, so it never reaches this store.
 */
export interface AuthState {
	token: string | null;
	user: UserProfile | null;
	isAuthenticated: boolean;
	isRehydrating: boolean;
	tokenExpiresAt: number | null;
}

const initialAuth: AuthState = {
	token: null,
	user: null,
	isAuthenticated: false,
	isRehydrating: true,
	tokenExpiresAt: null
};

export const authStore = writable<AuthState>(initialAuth);

let refreshTimeout: ReturnType<typeof setTimeout> | null = null;

export const _decodeJwtExp = decodeJwtExp;

export interface AuthModalState {
	isOpen: boolean;
	mode?: 'login' | 'register';
	pendingAction: (() => void | Promise<void>) | null;
}

const initialModalState: AuthModalState = {
	isOpen: false,
	mode: 'login',
	pendingAction: null
};

export const authModalStore = writable<AuthModalState>(initialModalState);

// Single function handles opening the modal with a mode preference.
export function openLoginModal(
	onSuccess?: () => void | Promise<void>,
	mode: 'login' | 'register' = 'login'
): void {
	authModalStore.set({
		isOpen: true,
		mode,
		pendingAction: onSuccess ?? null
	});
}

export function openRegisterModal(onSuccess?: () => void | Promise<void>): void {
	openLoginModal(onSuccess, 'register');
}

export function closeLoginModal(): void {
	authModalStore.set({
		isOpen: false,
		mode: 'login',
		pendingAction: null
	});
}

/**
 * Fire-and-forget a caller action without leaking an unhandled rejection.
 * `action()` runs synchronously; only its async tail gets the catch.
 */
function _runDetached(action: () => void | Promise<void>): void {
	void Promise.resolve(action()).catch(() => {});
}

export function requireAuth(action: () => void | Promise<void>): boolean {
	const state = get(authStore);
	if (state.isAuthenticated) {
		_runDetached(action);
		return true;
	}
	openLoginModal(action);
	return false;
}

export function setAuthSession(token: string, user: UserProfile, workspaces: WorkspaceItem[]) {
	authStore.set({
		token,
		user,
		isAuthenticated: true,
		isRehydrating: false,
		tokenExpiresAt: decodeJwtExp(token)
	});

	setWorkspaces(workspaces);
	_scheduleTokenRefresh();

	const pending = get(authModalStore).pendingAction;
	closeLoginModal();
	if (pending) {
		_runDetached(pending);
	}
}

export function logout(): void {
	if (refreshTimeout) {
		clearTimeout(refreshTimeout);
		refreshTimeout = null;
	}

	authStore.set({ ...initialAuth, isRehydrating: false });
	clearWorkspaces();
	if (typeof window !== 'undefined') {
		// Must hit the API origin so the backend can revoke and expire its cookies.
		void fetch(apiUrl('/api/v1/auth/logout'), {
			method: 'POST',
			credentials: 'include'
		}).catch(() => {});
	}
}

async function _doRefresh() {
	try {
		// The refresh token travels as an HttpOnly cookie; apiRequest sends credentials.
		const response = await apiRequest<{
			token: string;
			user: UserProfile;
			workspaces: WorkspaceItem[];
		}>('/api/v1/auth/refresh', {
			method: 'POST',
			body: JSON.stringify({})
		});

		setAuthSession(response.token, response.user, response.workspaces);
	} catch {
		logout();
	}
}

export function _scheduleTokenRefresh() {
	if (refreshTimeout) {
		clearTimeout(refreshTimeout);
		refreshTimeout = null;
	}

	// Cookie-restored sessions have no client-side refresh token, so gate on the
	// session itself and let the HttpOnly cookie authorize the refresh call.
	const state = get(authStore);
	if (!state.isAuthenticated || !state.token) return;

	const exp = state.tokenExpiresAt ?? decodeJwtExp(state.token);
	if (!exp) return;

	const maxTimerMs = 2_147_483_647;
	const delay = exp - Date.now() - 120_000;
	if (delay <= 0) {
		void _doRefresh();
	} else {
		const safeDelay = Math.min(delay, maxTimerMs);
		refreshTimeout = setTimeout(() => {
			void _doRefresh();
		}, safeDelay);
	}
}

export async function rehydrateAuth(): Promise<void> {
	if (typeof window === 'undefined') {
		authStore.update((state) => ({ ...state, isRehydrating: false }));
		return;
	}

	try {
		const response = await apiRequest<{
			token: string;
			user: UserProfile;
			workspaces: WorkspaceItem[];
		}>('/api/v1/auth/me');

		setAuthSession(response.token, response.user, response.workspaces);
	} catch {
		authStore.update((state) => ({ ...state, isRehydrating: false }));
		clearWorkspaces();
	}
}

export function getAuthToken(): string | null {
	return get(authStore).token;
}

export function getCurrentUser(): UserProfile | null {
	return get(authStore).user;
}

export function initFromServer(serverState: AuthState, workspaces: WorkspaceItem[]): void {
	if (!serverState.isAuthenticated) return;
	authStore.set(serverState);
	setWorkspaces(workspaces);
	_scheduleTokenRefresh();
}
