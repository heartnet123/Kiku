import { env } from '$env/dynamic/public';
import { getAuthToken } from '../stores/workspace';

const apiBaseUrl = (env.PUBLIC_API_BASE_URL ?? '').replace(/\/$/, '');

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
	const token = getAuthToken();
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(token ? { Authorization: `Bearer ${token}` } : {}),
		...((init?.headers as Record<string, string>) ?? {})
	};

	const response = await fetch(apiBaseUrl + path, {
		...init,
		headers
	});

	if (response.status === 401) {
		throw new Error('UNAUTHORIZED: Authentication required or token expired');
	}

	if (response.status === 403) {
		throw new Error('FORBIDDEN: Insufficient workspace permissions');
	}

	if (!response.ok) {
		throw new Error('API request failed with status ' + response.status);
	}

	return response.json() as Promise<T>;
}
