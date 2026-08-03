import { describe, expect, it, beforeEach } from 'vitest';
import {
	workspaceStore,
	setWorkspaces,
	addWorkspace,
	switchWorkspace,
	clearWorkspaces,
	getCurrentWorkspaceId,
	type WorkspaceItem
} from './workspace';

describe('workspaceStore', () => {
	beforeEach(() => {
		clearWorkspaces();
	});

	it('returns empty string when no workspaces exist (no ws_acme fallback)', () => {
		expect(getCurrentWorkspaceId()).toBe('');
	});

	it('sets workspaces and selects the first workspace by default', () => {
		const items: WorkspaceItem[] = [
			{ id: 'ws-1', name: 'WS 1', slug: 'ws-1', role: 'owner' },
			{ id: 'ws-2', name: 'WS 2', slug: 'ws-2', role: 'member' }
		];
		setWorkspaces(items);

		expect(getCurrentWorkspaceId()).toBe('ws-1');
	});

	it('adds a new workspace and sets it as active', () => {
		const newWs: WorkspaceItem = { id: 'ws-new', name: 'New WS', slug: 'new-ws', role: 'owner' };
		addWorkspace(newWs);

		expect(getCurrentWorkspaceId()).toBe('ws-new');
	});

	it('switches between workspaces', () => {
		const items: WorkspaceItem[] = [
			{ id: 'ws-1', name: 'WS 1', slug: 'ws-1', role: 'owner' },
			{ id: 'ws-2', name: 'WS 2', slug: 'ws-2', role: 'member' }
		];
		setWorkspaces(items);
		switchWorkspace('ws-2');

		expect(getCurrentWorkspaceId()).toBe('ws-2');
	});
});
