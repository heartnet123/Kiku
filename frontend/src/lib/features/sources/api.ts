import { apiRequest, apiUrl } from '$lib/api/client';
import { getAuthToken, logout } from '$lib/stores/auth';
import { getCurrentWorkspaceId } from '$lib/stores/workspace';
import type { IngestionMetrics, SourceItem, SourceVersion } from './types';

function _requireWorkspaceId(id?: string): string {
	const activeId = id || getCurrentWorkspaceId();
	if (!activeId) {
		throw new Error('Workspace ID is required.');
	}
	return activeId;
}

export async function fetchWorkspaceSources(workspaceId?: string): Promise<SourceItem[]> {
	const activeId = _requireWorkspaceId(workspaceId);
	return apiRequest<SourceItem[]>(`/api/v1/workspaces/${encodeURIComponent(activeId)}/sources`);
}

export async function uploadWorkspaceSource(file: File, workspaceId?: string): Promise<SourceItem> {
	const activeId = _requireWorkspaceId(workspaceId);
	const token = getAuthToken();
	const formData = new FormData();
	formData.append('file', file);

	const headers: Record<string, string> = {};
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const response = await fetch(
		apiUrl(`/api/v1/workspaces/${encodeURIComponent(activeId)}/sources`),
		{
			method: 'POST',
			headers,
			body: formData,
			credentials: 'include'
		}
	);

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
	const activeId = _requireWorkspaceId(workspaceId);
	return apiRequest<{ status: string; message: string }>(
		`/api/v1/workspaces/${encodeURIComponent(activeId)}/sources/${encodeURIComponent(sourceId)}/retry`,
		{ method: 'POST' }
	);
}

export async function fetchSourceVersions(
	workspaceId: string,
	sourceId: string
): Promise<SourceVersion[]> {
	const activeId = _requireWorkspaceId(workspaceId);
	return apiRequest<SourceVersion[]>(
		`/api/v1/workspaces/${encodeURIComponent(activeId)}/sources/${encodeURIComponent(sourceId)}/versions`
	);
}

export async function fetchSourceMetrics(workspaceId?: string): Promise<IngestionMetrics | null> {
	const activeId = _requireWorkspaceId(workspaceId);
	return apiRequest<IngestionMetrics>(
		`/api/v1/workspaces/${encodeURIComponent(activeId)}/sources/metrics`
	);
}
