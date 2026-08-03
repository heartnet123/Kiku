import { env } from '$env/dynamic/public';
import { getAuthToken, logout } from '../stores/auth';

const apiBaseUrl = (env.PUBLIC_API_BASE_URL ?? '').replace(/\/$/, '');

export function apiUrl(path: string): string {
	return apiBaseUrl + path;
}

export function authHeaders(): Record<string, string> {
	const token = getAuthToken();
	return token ? { Authorization: 'Bearer ' + token } : {};
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...authHeaders(),
		...((init?.headers as Record<string, string>) ?? {})
	};
	const response = await fetch(apiUrl(path), { ...init, headers });

	if (response.status === 401) {
		logout();
		throw new Error('UNAUTHORIZED: Authentication required or token expired');
	}
	if (response.status === 403) {
		throw new Error('FORBIDDEN: Insufficient workspace permissions');
	}
	if (!response.ok) {
		const payload = await response.json().catch(() => null);
		const detail = payload?.detail;
		throw new Error(
			typeof detail === 'string' ? detail : 'API request failed with status ' + response.status
		);
	}
	return response.json() as Promise<T>;
}
