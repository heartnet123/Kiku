import { writable, get } from 'svelte/store';
import { apiRequest } from '../api/client';

export interface UserProfile {
	id: string;
	email: string;
	full_name: string;
}

export type WorkspaceRole = 'owner' | 'admin' | 'editor' | 'viewer' | 'member';

export interface WorkspaceItem {
	id: string;
	name: string;
	slug: string;
	role: WorkspaceRole;
}

export interface AuthState {
	token: string | null;
	refreshToken: string | null;
	user: UserProfile | null;
	workspaces: WorkspaceItem[];
	currentWorkspace: WorkspaceItem | null;
	isAuthenticated: boolean;
	isRehydrating: boolean;
}

const initialAuth: AuthState = {
	token: null,
	refreshToken: null,
	user: null,
	workspaces: [],
	currentWorkspace: null,
	isAuthenticated: false,
	isRehydrating: true
};

export const authStore = writable<AuthState>(initialAuth);

export function setAuthSession(
	token: string,
	user: UserProfile,
	workspaces: WorkspaceItem[],
	refreshToken: string | null = null
) {
	const defaultWorkspace = workspaces.length > 0 ? workspaces[0] : null;
	authStore.set({
		token,
		refreshToken,
		user,
		workspaces,
		currentWorkspace: defaultWorkspace,
		isAuthenticated: true,
		isRehydrating: false
	});
	if (typeof window !== 'undefined') {
		sessionStorage.setItem('kiku_auth_token', token);
		if (refreshToken) sessionStorage.setItem('kiku_refresh_token', refreshToken);
		else sessionStorage.removeItem('kiku_refresh_token');
	}
}

export function addWorkspace(workspace: WorkspaceItem) {
	authStore.update((state) => ({
		...state,
		workspaces: [...state.workspaces.filter((item) => item.id !== workspace.id), workspace],
		currentWorkspace: workspace
	}));
}

export function logout() {
	authStore.set({ ...initialAuth, isRehydrating: false });
	if (typeof window !== 'undefined') {
		sessionStorage.removeItem('kiku_auth_token');
		sessionStorage.removeItem('kiku_refresh_token');
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

export function switchWorkspace(workspaceId: string) {
	authStore.update((state) => ({
		...state,
		currentWorkspace:
			state.workspaces.find((workspace) => workspace.id === workspaceId) ?? state.currentWorkspace
	}));
}

export function getAuthToken(): string | null {
	return get(authStore).token;
}

export function getCurrentWorkspaceId(): string | null {
	return get(authStore).currentWorkspace?.id ?? null;
}
