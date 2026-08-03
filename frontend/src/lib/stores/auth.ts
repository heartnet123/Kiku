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

export interface AuthModalState {
	isOpen: boolean;
	pendingAction: (() => void | Promise<void>) | null;
}

const initialModalState: AuthModalState = {
	isOpen: false,
	pendingAction: null
};

export const authModalStore = writable<AuthModalState>(initialModalState);

export function openLoginModal(onSuccess?: () => void | Promise<void>): void {
	authModalStore.set({
		isOpen: true,
		pendingAction: onSuccess ?? null
	});
}

export function closeLoginModal(): void {
	authModalStore.set({
		isOpen: false,
		pendingAction: null
	});
}

export function requireAuth(action: () => void | Promise<void>): boolean {
	const state = get(authStore);
	if (state.isAuthenticated) {
		void action();
		return true;
	}
	openLoginModal(action);
	return false;
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

	setWorkspaces(workspaces);
	_scheduleTokenRefresh();

	const modalState = get(authModalStore);
	const pending = modalState.pendingAction;
	closeLoginModal();
	if (pending) {
		void pending();
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
		void fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' });
	}
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

		setAuthSession(response.token, response.user, response.workspaces, null);
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
