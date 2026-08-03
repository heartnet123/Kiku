import { writable, get } from 'svelte/store';

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

export interface WorkspaceState {
	workspaces: WorkspaceItem[];
	currentWorkspace: WorkspaceItem | null;
}

const initialWorkspaceState: WorkspaceState = {
	workspaces: [],
	currentWorkspace: null
};

export const workspaceStore = writable<WorkspaceState>(initialWorkspaceState);

export function setWorkspaces(workspaces: WorkspaceItem[]) {
	workspaceStore.update((state) => {
		const current = state.currentWorkspace;
		const currentStillValid = current ? workspaces.find((w) => w.id === current.id) : null;
		const nextCurrent = currentStillValid || (workspaces.length > 0 ? workspaces[0] : null);
		return {
			workspaces,
			currentWorkspace: nextCurrent
		};
	});
}

export function addWorkspace(workspace: WorkspaceItem) {
	workspaceStore.update((state) => ({
		...state,
		workspaces: [...state.workspaces.filter((item) => item.id !== workspace.id), workspace],
		currentWorkspace: workspace
	}));
}

export function switchWorkspace(workspaceId: string) {
	workspaceStore.update((state) => ({
		...state,
		currentWorkspace:
			state.workspaces.find((workspace) => workspace.id === workspaceId) ?? state.currentWorkspace
	}));
}

export function clearWorkspaces() {
	workspaceStore.set(initialWorkspaceState);
}

export function getCurrentWorkspaceId(): string {
	const state = get(workspaceStore);
	return state.currentWorkspace?.id || (state.workspaces.length > 0 ? state.workspaces[0].id : '');
}
