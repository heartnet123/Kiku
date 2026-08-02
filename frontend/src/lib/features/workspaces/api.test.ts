import { afterEach, describe, expect, it, vi } from 'vitest';

const { apiRequestMock } = vi.hoisted(() => ({ apiRequestMock: vi.fn() }));

vi.mock('$lib/api/client', () => ({ apiRequest: apiRequestMock }));

import { joinWorkspace } from './api';

describe('workspace API', () => {
	afterEach(() => apiRequestMock.mockReset());

	it('joins by slug', async () => {
		apiRequestMock.mockResolvedValue({ id: 'workspace-1' });

		await joinWorkspace(' acme ');

		expect(apiRequestMock).toHaveBeenCalledWith('/api/v1/workspaces/join', {
			method: 'POST',
			body: JSON.stringify({ slug: 'acme' })
		});
	});

	it('joins by UUID', async () => {
		apiRequestMock.mockResolvedValue({ id: 'workspace-1' });

		await joinWorkspace('550e8400-e29b-41d4-a716-446655440000');

		expect(apiRequestMock).toHaveBeenCalledWith('/api/v1/workspaces/join', {
			method: 'POST',
			body: JSON.stringify({ workspace_id: '550e8400-e29b-41d4-a716-446655440000' })
		});
	});
});
