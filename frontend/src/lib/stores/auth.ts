import { writable, get } from 'svelte/store';
import { apiRequest } from '../api/client';
import { setWorkspaces, clearWorkspaces, type WorkspaceItem, type UserProfile } from './workspace';

export type { UserProfile };

export interface AuthState {
	token: string | null;
	refreshToken: string | null;
	user: UserProfile | null;
	isAuthenticated: boolean;
	isRehydrating: boolean;
	tokenExpiresAt: number | null;
}

const initialAuth: AuthState = {
	token: null,
	refreshToken: null,
	user: null,
	isAuthenticated: false,
	isRehydrating: true,
	tokenExpiresAt: null
};

export const authStore = writable<AuthState>(initialAuth);

let refreshTimeout: ReturnType<typeof setTimeout> | null = null;

export function _decodeJwtExp(token: string): number | null {
	try {
		const parts = token.split('.');
		if (parts.length < 2) return null;
		const payloadBase64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
		const jsonPayload = decodeURIComponent(
			atob(payloadBase64)
				.split('')
				.map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
				.join('')
		);
		const payload = JSON.parse(jsonPayload);
		return typeof payload.exp === 'number' ? payload.exp * 1000 : null;
	} catch {
		return null;
	}
}

export function setAuthSession(
	token: string,
	user: UserProfile,
	workspaces: WorkspaceItem[],
	refreshToken: string | null = null
) {
	const expiresAt = _decodeJwtExp(token);
	authStore.set({
		token,
		refreshToken,
		user,
		isAuthenticated: true,
		isRehydrating: false,
		tokenExpiresAt: expiresAt
	});

	if (typeof window !== 'undefined') {
		sessionStorage.setItem('kiku_auth_token', token);
		if (refreshToken) sessionStorage.setItem('kiku_refresh_token', refreshToken);
		else sessionStorage.removeItem('kiku_refresh_token');
	}

	setWorkspaces(workspaces);
	_scheduleTokenRefresh();
}

export function logout() {
	if (refreshTimeout) {
		clearTimeout(refreshTimeout);
		refreshTimeout = null;
	}

	authStore.set({ ...initialAuth, isRehydrating: false });
	if (typeof window !== 'undefined') {
		sessionStorage.removeItem('kiku_auth_token');
		sessionStorage.removeItem('kiku_refresh_token');
	}

	clearWorkspaces();
}

async function _doRefresh() {
	const state = get(authStore);
	if (!state.refreshToken) {
		logout();
		return;
	}

	try {
		const response = await apiRequest<{
			token: string;
			refresh_token?: string | null;
			user: UserProfile;
			workspaces: WorkspaceItem[];
		}>('/api/v1/auth/refresh', {
			method: 'POST',
			body: JSON.stringify({ refresh_token: state.refreshToken })
		});

		setAuthSession(
			response.token,
			response.user,
			response.workspaces,
			response.refresh_token ?? state.refreshToken
		);
	} catch {
		logout();
	}
}

export function _scheduleTokenRefresh() {
	if (refreshTimeout) {
		clearTimeout(refreshTimeout);
		refreshTimeout = null;
	}

	const state = get(authStore);
	if (!state.refreshToken || !state.isAuthenticated || !state.token) return;

	const exp = state.tokenExpiresAt ?? _decodeJwtExp(state.token);
	if (!exp) return;

	const delay = exp - Date.now() - 120_000;
	if (delay <= 0) {
		void _doRefresh();
	} else {
		refreshTimeout = setTimeout(() => {
			void _doRefresh();
		}, delay);
	}
}

export async function rehydrateAuth(): Promise<void> {
	if (typeof window === 'undefined') {
		authStore.update((state) => ({ ...state, isRehydrating: false }));
		return;
	}

	const storedToken = sessionStorage.getItem('kiku_auth_token');
	const storedRefreshToken = sessionStorage.getItem('kiku_refresh_token');
	if (!storedToken) {
		authStore.update((state) => ({ ...state, isRehydrating: false }));
		return;
	}

	try {
		authStore.update((state) => ({
			...state,
			token: storedToken,
			refreshToken: storedRefreshToken
		}));
		const response = await apiRequest<{
			token: string;
			user: UserProfile;
			workspaces: WorkspaceItem[];
		}>('/api/v1/auth/me');

		setAuthSession(
			response.token || storedToken,
			response.user,
			response.workspaces,
			storedRefreshToken
		);
	} catch {
		logout();
	}
}

export function getAuthToken(): string | null {
	return get(authStore).token;
}

export function getCurrentUser(): UserProfile | null {
	return get(authStore).user;
}
