import { afterEach, describe, expect, it, vi } from 'vitest';
import { logout, setAuthSession } from '$lib/stores/auth';
import { getMessages } from './chatApi';
import { streamChatMessage } from './chatApi';

describe('durable chat stream parser', () => {
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

	it('parses CRLF, split chunks, token/content fragments, status/error/done, and a final unterminated event', async () => {
		setAuthSession('token-test', user, [workspace]);
		const body = new ReadableStream<Uint8Array>({
			start(controller) {
				const encoder = new TextEncoder();
				controller.enqueue(
					encoder.encode(
						'event: status\r\ndata: {"status":"retrieving_sources"}\r\n\r\n' +
							'event: metadata\r\ndata: {"query":"Hello","citations_json":[{"source_id":"src-1"}]}'
					)
				);
				controller.enqueue(
					encoder.encode(
						'\r\n\r\nevent: delta\r\ndata: {"token":"Hi"}\r\n\r\n' +
							'event: error\r\ndata: {"message":"Fallback used","recoverable":true}\r\n\r\n' +
							'event: done\r\ndata: {"status":"completed","message_id":"message-1"}'
					)
				);
				controller.close();
			}
		});
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue(
				new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
			)
		);

		const statuses: string[] = [];
		const metadata: unknown[] = [];
		const deltas: string[] = [];
		const errors: unknown[] = [];
		const done: unknown[] = [];

		await streamChatMessage('session/one', 'Hello', 'All', {
			onStatus: (status) => statuses.push(status),
			onMetadata: (value) => metadata.push(value),
			onDelta: (value) => deltas.push(value),
			onError: (message, recoverable) => errors.push({ message, recoverable }),
			onDone: (value) => done.push(value)
		});

		expect(statuses).toEqual(['retrieving_sources']);
		expect(metadata).toEqual([{ query: 'Hello', citations: [{ source_id: 'src-1' }] }]);
		expect(deltas).toEqual(['Hi']);
		expect(errors).toEqual([{ message: 'Fallback used', recoverable: true }]);
		expect(done).toEqual([{ status: 'completed', message_id: 'message-1' }]);
		expect(fetch).toHaveBeenCalledWith(
			'http://localhost:8000/api/v1/workspaces/ws_acme/chat/sessions/session%2Fone/stream',
			expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer token-test' }) })
		);
	});

	it('maps backend citations_json to frontend citations when loading messages', async () => {
		setAuthSession('token-test', user, [workspace]);
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue(
				new Response(
					JSON.stringify([
						{
							id: 'message-1',
							session_id: 'session-1',
							workspace_id: 'ws_acme',
							role: 'assistant',
							content: 'Answer',
							citations_json: [{ source_id: 'src-1', title: 'Policy' }],
							created_at: '2026-08-02T00:00:00Z'
						}
					])
				)
			)
		);

		const messages = await getMessages('session-1');

		expect(messages[0].citations).toEqual([{ source_id: 'src-1', title: 'Policy' }]);
	});
});
