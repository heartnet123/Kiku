import { apiRequest } from '$lib/api/client';
import type { WorkspaceItem } from '$lib/stores/workspace';

export function createWorkspace(name: string, slug?: string): Promise<WorkspaceItem> {
	return apiRequest<WorkspaceItem>('/api/v1/workspaces', {
		method: 'POST',
		body: JSON.stringify({ name, slug: slug || undefined })
	});
}

export function joinWorkspace(identifier: string): Promise<WorkspaceItem> {
	const value = identifier.trim();
	const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
		value
	);
	return apiRequest<WorkspaceItem>('/api/v1/workspaces/join', {
		method: 'POST',
		body: JSON.stringify(isUuid ? { workspace_id: value } : { slug: value })
	});
}
