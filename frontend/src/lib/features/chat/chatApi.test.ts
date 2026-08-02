import { afterEach, describe, expect, it, vi } from 'vitest';
import { logout, setAuthSession } from '$lib/stores/workspace';
import { createSession, streamChatMessage } from './chatApi';

describe('chat API', () => {
	const user = { id: 'user_acme_admin', email: 'admin@acme.com', full_name: 'Acme Admin User' };
	const workspace = {
		id: 'ws_acme',
		name: 'Acme Team Workspace',
		slug: 'acme',
		role: 'admin' as const
	};

	afterEach(() => {
		vi.restoreAllMocks();
		logout();
	});

	it('sends the current workspace and bearer token when creating a session', async () => {
		setAuthSession('token-test', user, [workspace]);
		const fetchMock = vi
			.fn()
			.mockResolvedValue(new Response(JSON.stringify({ id: 'session-1' }), { status: 200 }));
		vi.stubGlobal('fetch', fetchMock);

		await createSession('Test chat');

		expect(fetchMock).toHaveBeenCalledWith(
			'http://localhost:8000/api/v1/workspaces/ws_acme/chat/sessions',
			expect.objectContaining({
				headers: expect.objectContaining({ Authorization: 'Bearer token-test' })
			})
		);
	});

	it('rejects an unsuccessful session response', async () => {
		setAuthSession('token-test', user, [workspace]);
		vi.stubGlobal(
			'fetch',
			vi
				.fn()
				.mockResolvedValue(
					new Response(JSON.stringify({ detail: 'Unauthorized' }), { status: 401 })
				)
		);

		await expect(createSession()).rejects.toThrow('UNAUTHORIZED');
	});

	it('passes authenticated SSE events to the chat callbacks', async () => {
		setAuthSession('token-test', user, [workspace]);
		const fetchMock = vi
			.fn()
			.mockResolvedValue(
				new Response(
					'event: metadata\ndata: {"citations":[]}\n\n' +
						'event: delta\ndata: {"content":"Hello"}\n\n' +
						'event: done\ndata: {"status":"completed"}\n\n',
					{ status: 200, headers: { 'Content-Type': 'text/event-stream' } }
				)
			);
		vi.stubGlobal('fetch', fetchMock);

		const citations: unknown[] = [];
		const deltas: string[] = [];
		let done = false;
		await streamChatMessage(
			'session-1',
			'Hello?',
			'All',
			(value) => citations.push(value),
			(value) => deltas.push(value),
			() => {
				done = true;
			}
		);

		expect(fetchMock).toHaveBeenCalledWith(
			'http://localhost:8000/api/v1/workspaces/ws_acme/chat/sessions/session-1/stream',
			expect.objectContaining({
				headers: expect.objectContaining({ Authorization: 'Bearer token-test' })
			})
		);
		expect(citations).toEqual([[]]);
		expect(deltas).toEqual(['Hello']);
		expect(done).toBe(true);
	});
});
