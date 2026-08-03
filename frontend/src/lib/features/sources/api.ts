import { env } from '$env/dynamic/public';
import { apiRequest } from '$lib/api/client';
import { getAuthToken, logout } from '$lib/stores/auth';
import type { IngestionMetrics, SourceItem, SourceVersion } from './types';

const apiBaseUrl = (env.PUBLIC_API_BASE_URL ?? '').replace(/\/$/, '');

export async function fetchWorkspaceSources(workspaceId: string): Promise<SourceItem[]> {
	return apiRequest<SourceItem[]>(`/api/v1/workspaces/${workspaceId}/sources`);
}

export async function uploadWorkspaceSource(workspaceId: string, file: File): Promise<SourceItem> {
	const token = getAuthToken();
	const formData = new FormData();
	formData.append('file', file);

	const headers: Record<string, string> = {};
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const response = await fetch(`${apiBaseUrl}/api/v1/workspaces/${workspaceId}/sources`, {
		method: 'POST',
		headers,
		body: formData
	});

	if (response.status === 401) {
		logout();
		throw new Error('UNAUTHORIZED: Authentication required');
	}

	if (response.status === 403) {
		throw new Error('FORBIDDEN: Only workspace administrators can upload knowledge sources');
	}

	if (!response.ok) {
		const errJson = await response.json().catch(() => ({ detail: null }));
		throw new Error(errJson.detail || `Upload failed with status ${response.status}`);
	}

	return response.json() as Promise<SourceItem>;
}

export async function retryWorkspaceSource(
	workspaceId: string,
	sourceId: string
): Promise<{ status: string; message: string }> {
	return apiRequest<{ status: string; message: string }>(
		`/api/v1/workspaces/${workspaceId}/sources/${sourceId}/retry`,
		{ method: 'POST' }
	);
}

export async function fetchSourceVersions(
	workspaceId: string,
	sourceId: string
): Promise<SourceVersion[]> {
	return apiRequest<SourceVersion[]>(
		`/api/v1/workspaces/${workspaceId}/sources/${sourceId}/versions`
	);
}

export async function fetchSourceMetrics(workspaceId: string): Promise<IngestionMetrics> {
	return apiRequest<IngestionMetrics>(`/api/v1/workspaces/${workspaceId}/sources/metrics`);
}
