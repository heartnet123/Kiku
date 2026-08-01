import { env } from '$env/dynamic/public';

const apiBaseUrl = (env.PUBLIC_API_BASE_URL ?? '').replace(/\/$/, '');

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(apiBaseUrl + path, {
		headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
		...init
	});

	if (!response.ok) throw new Error('API request failed with status ' + response.status);
	return response.json() as Promise<T>;
}
