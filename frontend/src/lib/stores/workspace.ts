import { writable, get } from 'svelte/store';
import { apiRequest } from '../api/client';

export interface UserProfile {
	id: string;
	email: string;
	full_name: string;
}

export interface WorkspaceItem {
	id: string;
	name: string;
	slug: string;
	role: 'admin' | 'member';
}

export interface AuthState {
	token: string | null;
	user: UserProfile | null;
	workspaces: WorkspaceItem[];
	currentWorkspace: WorkspaceItem | null;
	isAuthenticated: boolean;
	isRehydrating: boolean;
}

const initialAuth: AuthState = {
	token: null,
	user: null,
	workspaces: [],
	currentWorkspace: null,
	isAuthenticated: false,
	isRehydrating: true
};

export const authStore = writable<AuthState>(initialAuth);

export function setAuthSession(token: string, user: UserProfile, workspaces: WorkspaceItem[]) {
	const defaultWorkspace = workspaces.length > 0 ? workspaces[0] : null;
	authStore.set({
		token,
		user,
		workspaces,
		currentWorkspace: defaultWorkspace,
		isAuthenticated: true,
		isRehydrating: false
	});
	if (typeof window !== 'undefined') {
		sessionStorage.setItem('kiku_auth_token', token);
	}
}

export function logout() {
	authStore.set({ ...initialAuth, isRehydrating: false });
	if (typeof window !== 'undefined') {
		sessionStorage.removeItem('kiku_auth_token');
	}
}

export async function rehydrateAuth(): Promise<void> {
	if (typeof window === 'undefined') {
		authStore.update((s) => ({ ...s, isRehydrating: false }));
		return;
	}

	const storedToken = sessionStorage.getItem('kiku_auth_token');
	if (!storedToken) {
		authStore.update((s) => ({ ...s, isRehydrating: false }));
		return;
	}

	try {
		authStore.update((s) => ({ ...s, token: storedToken }));
		const res = await apiRequest<{ token: string; user: UserProfile; workspaces: WorkspaceItem[] }>('/api/v1/auth/me');
		setAuthSession(res.token || storedToken, res.user, res.workspaces);
	} catch (e) {
		logout();
	}
}

export function switchWorkspace(workspaceId: string) {
	authStore.update((state) => {
		const target = state.workspaces.find((w) => w.id === workspaceId);
		return {
			...state,
			currentWorkspace: target || state.currentWorkspace
		};
	});
}

export function getAuthToken(): string | null {
	return get(authStore).token;
}

export function getCurrentWorkspaceId(): string | null {
	return get(authStore).currentWorkspace?.id ?? null;
}
