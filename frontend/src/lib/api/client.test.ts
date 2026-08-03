import { describe, expect, it } from 'vitest';
import { apiUrl } from './client';

describe('apiUrl', () => {
	it('normalizes paths with double slashes into a single slash', () => {
		expect(apiUrl('/api/v1/workspaces//sources')).toContain('/api/v1/workspaces/sources');
		expect(apiUrl('/api/v1/workspaces/ws_acme//sources')).toContain('/api/v1/workspaces/ws_acme/sources');
		expect(apiUrl('///api/v1/workspaces//sources')).toContain('/api/v1/workspaces/sources');
	});

	it('preserves http:// or https:// protocol double slashes', () => {
		const url = apiUrl('/api/v1/workspaces/ws_123/sources');
		expect(url).not.toMatch(/workspaces\/\//);
	});
});
