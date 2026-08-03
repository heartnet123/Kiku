import type { Handle } from '@sveltejs/kit';
import type { AuthState } from '$lib/stores/auth';
import type { WorkspaceItem, UserProfile } from '$lib/stores/workspace';

const API_BASE = (process.env.PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');

function decodeJwtExp(token: string): number | null {
	try {
		const payload = JSON.parse(
			decodeURIComponent(
				atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))
					.split('')
					.map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
					.join('')
			)
		);
		return typeof payload.exp === 'number' ? payload.exp * 1000 : null;
	} catch {
		return null;
	}
}

export const handle: Handle = async ({ event, resolve }) => {
	const token = event.cookies.get('kiku_access_token');
	const refreshToken = event.cookies.get('kiku_refresh_token') ?? null;

	if (!token) {
		event.locals.authState = null;
		return resolve(event);
	}

	try {
		const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
			headers: { Authorization: `Bearer ${token}` }
		});

		if (!response.ok) {
			event.locals.authState = null;
			return resolve(event);
		}

		const data = (await response.json()) as {
			token: string;
			user: UserProfile;
			workspaces: WorkspaceItem[];
		};

		const resolvedToken = data.token || token;
		const authState: AuthState = {
			token: resolvedToken,
			refreshToken,
			user: data.user,
			isAuthenticated: true,
			isRehydrating: false,
			tokenExpiresAt: decodeJwtExp(resolvedToken)
		};

		event.locals.authState = authState;
	} catch {
		event.locals.authState = null;
	}

	return resolve(event);
};
