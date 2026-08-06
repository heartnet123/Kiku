import type { Handle } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';
import { decodeJwtExp } from '$lib/utils/jwt';
import type { AuthState } from '$lib/stores/auth';
import type { WorkspaceItem, UserProfile } from '$lib/stores/workspace';

const API_BASE = (env.PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');
const ME_TIMEOUT_MS = 5000;

export const handle: Handle = async ({ event, resolve }) => {
	const token = event.cookies.get('kiku_access_token');

	if (!token) {
		event.locals.authState = null;
		event.locals.workspaces = null;
		const response = await resolve(event);
		if (!response.headers.get('X-Content-Type-Options')) {
			response.headers.set('X-Content-Type-Options', 'nosniff');
		}
		if (!response.headers.get('Referrer-Policy')) {
			response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
		}
		if (!response.headers.get('Permissions-Policy')) {
			response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
		}
		if (!response.headers.get('X-Frame-Options')) {
			response.headers.set('X-Frame-Options', 'DENY');
		}
		return response;
	}

	try {
		const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
			headers: { Authorization: `Bearer ${token}` },
			signal: AbortSignal.timeout(ME_TIMEOUT_MS)
		});

		if (!response.ok) {
			event.locals.authState = null;
			event.locals.workspaces = null;
			const resolved = await resolve(event);
			if (!resolved.headers.get('X-Content-Type-Options')) {
				resolved.headers.set('X-Content-Type-Options', 'nosniff');
			}
			if (!resolved.headers.get('Referrer-Policy')) {
				resolved.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
			}
			if (!resolved.headers.get('Permissions-Policy')) {
				resolved.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
			}
			if (!resolved.headers.get('X-Frame-Options')) {
				resolved.headers.set('X-Frame-Options', 'DENY');
			}
			return resolved;
		}

		const data = (await response.json()) as {
			token: string;
			user: UserProfile;
			workspaces: WorkspaceItem[];
		};

		const resolvedToken = data.token || token;
		const authState: AuthState = {
			token: resolvedToken,
			user: data.user,
			isAuthenticated: true,
			isRehydrating: false,
			tokenExpiresAt: decodeJwtExp(resolvedToken)
		};

		event.locals.authState = authState;
		event.locals.workspaces = data.workspaces ?? [];
	} catch {
		event.locals.authState = null;
		event.locals.workspaces = null;
	}

	const response = await resolve(event);
	if (!response.headers.get('X-Content-Type-Options')) {
		response.headers.set('X-Content-Type-Options', 'nosniff');
	}
	if (!response.headers.get('Referrer-Policy')) {
		response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
	}
	if (!response.headers.get('Permissions-Policy')) {
		response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
	}
	if (!response.headers.get('X-Frame-Options')) {
		response.headers.set('X-Frame-Options', 'DENY');
	}
	return response;
};
