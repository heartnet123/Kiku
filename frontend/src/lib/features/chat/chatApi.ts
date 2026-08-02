import type { ChatSession, ChatMessage, ChatCitation } from './types';
import { apiRequest, apiUrl, authHeaders } from '$lib/api/client';
import { getCurrentWorkspaceId, logout } from '$lib/stores/workspace';

function chatBasePath(): string {
	const workspaceId = getCurrentWorkspaceId();
	if (!workspaceId) {
		throw new Error('Authentication required before using chat');
	}
	return '/api/v1/workspaces/' + encodeURIComponent(workspaceId) + '/chat';
}

export async function createSession(title: string = 'New Chat'): Promise<ChatSession> {
	return apiRequest<ChatSession>(chatBasePath() + '/sessions', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ title })
	});
}

export async function listSessions(): Promise<ChatSession[]> {
	return apiRequest<ChatSession[]>(chatBasePath() + '/sessions');
}

export async function deleteSession(sessionId: string): Promise<void> {
	await apiRequest(chatBasePath() + '/sessions/' + sessionId, { method: 'DELETE' });
}

export async function getMessages(sessionId: string): Promise<ChatMessage[]> {
	return apiRequest<ChatMessage[]>(chatBasePath() + '/sessions/' + sessionId + '/messages');
}

export async function streamChatMessage(
	sessionId: string,
	query: string,
	category: string,
	onMetadata: (citations: ChatCitation[]) => void,
	onDelta: (content: string) => void,
	onDone: () => void,
	signal?: AbortSignal,
	onError?: (message: string) => void
): Promise<void> {
	const response = await fetch(apiUrl(chatBasePath() + '/sessions/' + sessionId + '/stream'), {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify({ query, category }),
		signal
	});

	if (response.status === 401) {
		logout();
		throw new Error('UNAUTHORIZED: Authentication required or token expired');
	}
	if (response.status === 403) {
		throw new Error('FORBIDDEN: Insufficient workspace permissions');
	}
	if (!response.ok) {
		throw new Error('Chat stream failed with status ' + response.status);
	}
	if (!response.body) {
		throw new Error('Chat stream returned an empty response body');
	}
	const reader = response.body.getReader();
	const decoder = new TextDecoder('utf-8');
	let buffer = '';

	while (true) {
		const { done, value } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true });
		const parts = buffer.split('\n\n');
		buffer = parts.pop() || '';

		for (const part of parts) {
			const lines = part.split('\n');
			let eventType = '';
			let dataStr = '';
			for (const line of lines) {
				if (line.startsWith('event: ')) {
					eventType = line.substring(7).trim();
				} else if (line.startsWith('data: ')) {
					dataStr = line.substring(6).trim();
				}
			}
			if (eventType === 'metadata') {
				try {
					const meta = JSON.parse(dataStr);
					onMetadata(meta.citations || []);
				} catch {
					// Ignore malformed event payloads and continue streaming.
				}
			} else if (eventType === 'delta') {
				try {
					const delta = JSON.parse(dataStr);
					onDelta(delta.content || '');
				} catch {
					// Ignore malformed event payloads and continue streaming.
				}
			} else if (eventType === 'done') {
				onDone();
			} else if (eventType === 'error') {
				try {
					const err = JSON.parse(dataStr);
					onError?.(err.message || 'Stream error');
				} catch {
					onError?.('Stream error');
				}
			}
		}
	}
}
