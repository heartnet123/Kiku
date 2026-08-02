import type { ChatSession, ChatMessage, ChatCitation } from './types';

const API_BASE = '/api/v1/workspaces/ws_acme/chat';

export async function createSession(title: string = 'New Chat'): Promise<ChatSession> {
	const res = await fetch(`${API_BASE}/sessions`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ title })
	});
	return res.json();
}

export async function listSessions(): Promise<ChatSession[]> {
	const res = await fetch(`${API_BASE}/sessions`);
	if (!res.ok) return [];
	return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
	await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function getMessages(sessionId: string): Promise<ChatMessage[]> {
	const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
	if (!res.ok) return [];
	return res.json();
}

export async function streamChatMessage(
	sessionId: string,
	query: string,
	category: string,
	onMetadata: (citations: ChatCitation[]) => void,
	onDelta: (content: string) => void,
	onDone: () => void,
	signal?: AbortSignal
): Promise<void> {
	const response = await fetch(`${API_BASE}/sessions/${sessionId}/stream`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ query, category }),
		signal
	});

	if (!response.body) return;
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
				} catch {}
			} else if (eventType === 'delta') {
				try {
					const delta = JSON.parse(dataStr);
					onDelta(delta.content || '');
				} catch {}
			} else if (eventType === 'done') {
				onDone();
			}
		}
	}
}
