import type { AuthState } from '$lib/stores/auth';
import type { WorkspaceItem } from '$lib/stores/workspace';

declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			authState: AuthState | null;
			workspaces: WorkspaceItem[] | null;
		}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
