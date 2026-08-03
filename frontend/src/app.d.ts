import type { AuthState } from '$lib/stores/auth';

declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			authState: AuthState | null;
		}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
