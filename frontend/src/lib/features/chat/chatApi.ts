import type { ChatCitation, ChatMessage, ChatSession } from './types';
import { apiRequest, apiUrl, authHeaders } from '$lib/api/client';
import { logout } from '$lib/stores/auth';
import { getCurrentWorkspaceId } from '$lib/stores/workspace';

export type ChatStatus =
	| 'retrieving_sources'
	| 'composing_answer'
	| 'streaming_answer'
	| 'completed';

export interface ChatStreamMetadata {
	query?: string;
	citations: ChatCitation[];
}

export interface ChatStreamDone {
	status: string;
	message_id?: string | null;
	fallback?: boolean;
}

export interface ChatStreamHandlers {
	onStatus?: (status: ChatStatus, message?: string) => void;
	onMetadata?: (metadata: ChatStreamMetadata) => void;
	onDelta?: (content: string) => void;
	onError?: (message: string, recoverable: boolean) => void;
	onDone?: (result: ChatStreamDone) => void;
}

interface RawChatMessage extends ChatMessage {
	citations_json?: ChatCitation[] | null;
}

interface SseEvent {
	event: string;
	data: string;
}

export class SseParser {
	private buffer = '';

	push(chunk: string): SseEvent[] {
		this.buffer += chunk.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
		const blocks = this.buffer.split('\n\n');
		this.buffer = blocks.pop() ?? '';
		return blocks.map(parseSseBlock).filter((event): event is SseEvent => event !== null);
	}

	flush(): SseEvent[] {
		const block = this.buffer.trim();
		this.buffer = '';
		if (!block) return [];
		const event = parseSseBlock(block);
		return event ? [event] : [];
	}
}

function parseSseBlock(block: string): SseEvent | null {
	let event = 'message';
	const dataLines: string[] = [];

	for (const line of block.split('\n')) {
		if (line.startsWith('event:')) {
			event = line.slice('event:'.length).trim();
		} else if (line.startsWith('data:')) {
			dataLines.push(line.slice('data:'.length).replace(/^ /, ''));
		}
	}

	return dataLines.length > 0 ? { event, data: dataLines.join('\n') } : null;
}

function chatBasePath(): string {
	const workspaceId = getCurrentWorkspaceId();
	if (!workspaceId) {
		throw new Error('Authentication required before using chat');
	}
	return '/api/v1/workspaces/' + encodeURIComponent(workspaceId) + '/chat';
}

function sessionPath(sessionId: string): string {
	return '/sessions/' + encodeURIComponent(sessionId);
}

function normalizeCitations(payload: Record<string, unknown>): ChatCitation[] {
	const citations = payload.citations ?? payload.citations_json;
	return Array.isArray(citations) ? (citations as ChatCitation[]) : [];
}

function normalizeMessage(message: RawChatMessage): ChatMessage {
	const { citations_json: citationsJson, ...rest } = message;
	return {
		...rest,
		citations: rest.citations ?? citationsJson ?? []
	};
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

export async function getSession(sessionId: string): Promise<ChatSession> {
	return apiRequest<ChatSession>(chatBasePath() + sessionPath(sessionId));
}

export async function deleteSession(sessionId: string): Promise<void> {
	await apiRequest(chatBasePath() + sessionPath(sessionId), { method: 'DELETE' });
}

export async function getMessages(sessionId: string): Promise<ChatMessage[]> {
	const messages = await apiRequest<RawChatMessage[]>(
		chatBasePath() + sessionPath(sessionId) + '/messages'
	);
	return messages.map(normalizeMessage);
}

function resolveHandlers(
	handlersOrMetadata:
		| ChatStreamHandlers
		| ((citations: ChatCitation[]) => void),
	onDeltaOrSignal?: ((content: string) => void) | AbortSignal,
	onDone?: (() => void) | undefined,
	signal?: AbortSignal,
	onError?: (message: string) => void,
	onStatus?: (status: ChatStatus, message?: string) => void
): { handlers: ChatStreamHandlers; signal?: AbortSignal } {
	if (typeof handlersOrMetadata !== 'function') {
		const maybeSignal = onDeltaOrSignal;
		return {
			handlers: handlersOrMetadata,
			signal:
				maybeSignal && typeof maybeSignal !== 'function' && 'aborted' in maybeSignal
					? maybeSignal
					: signal
		};
	}

	return {
		handlers: {
			onMetadata: (metadata) => handlersOrMetadata(metadata.citations),
			onDelta: typeof onDeltaOrSignal === 'function' ? onDeltaOrSignal : undefined,
			onDone: onDone ? () => onDone() : undefined,
			onError: onError ? (message) => onError(message) : undefined,
			onStatus
		},
		signal
	};
}

export async function streamChatMessage(
	sessionId: string,
	query: string,
	category: string,
	handlers: ChatStreamHandlers,
	signal?: AbortSignal
): Promise<void>;
export async function streamChatMessage(
	sessionId: string,
	query: string,
	category: string,
	onMetadata: (citations: ChatCitation[]) => void,
	onDelta: (content: string) => void,
	onDone: () => void,
	signal?: AbortSignal,
	onError?: (message: string) => void,
	onStatus?: (status: ChatStatus, message?: string) => void
): Promise<void>;
export async function streamChatMessage(
	sessionId: string,
	query: string,
	category: string,
	handlersOrMetadata: ChatStreamHandlers | ((citations: ChatCitation[]) => void),
	onDeltaOrSignal?: ((content: string) => void) | AbortSignal,
	onDone?: () => void,
	signal?: AbortSignal,
	onError?: (message: string) => void,
	onStatus?: (status: ChatStatus, message?: string) => void
): Promise<void> {
	const resolved = resolveHandlers(
		handlersOrMetadata,
		onDeltaOrSignal,
		onDone,
		signal,
		onError,
		onStatus
	);
	const response = await fetch(
		apiUrl(chatBasePath() + sessionPath(sessionId) + '/stream'),
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json', ...authHeaders() },
			body: JSON.stringify({ query, category }),
			signal: resolved.signal
		}
	);

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
	const parser = new SseParser();

	const dispatch = (sseEvent: SseEvent) => {
		let payload: Record<string, unknown>;
		try {
			payload = JSON.parse(sseEvent.data) as Record<string, unknown>;
		} catch {
			return;
		}

		if (sseEvent.event === 'status') {
			const status = payload.status ?? payload.phase;
			if (
				status === 'retrieving_sources' ||
				status === 'composing_answer' ||
				status === 'streaming_answer' ||
				status === 'completed'
			) {
				resolved.handlers.onStatus?.(status, typeof payload.message === 'string' ? payload.message : undefined);
			}
		} else if (sseEvent.event === 'metadata') {
			resolved.handlers.onMetadata?.({
				query: typeof payload.query === 'string' ? payload.query : undefined,
				citations: normalizeCitations(payload)
			});
		} else if (sseEvent.event === 'delta') {
			const content = payload.content ?? payload.token;
			if (typeof content === 'string') resolved.handlers.onDelta?.(content);
		} else if (sseEvent.event === 'error') {
			const message = typeof payload.message === 'string' ? payload.message : 'Stream error';
			resolved.handlers.onError?.(message, payload.recoverable !== false);
		} else if (sseEvent.event === 'done') {
			const done: ChatStreamDone = {
				status: typeof payload.status === 'string' ? payload.status : 'completed',
				message_id: typeof payload.message_id === 'string' ? payload.message_id : null
			};
			if (payload.fallback === true) done.fallback = true;
			resolved.handlers.onDone?.(done);
		}
	};

	while (true) {
		const { done, value } = await reader.read();
		if (done) break;
		for (const event of parser.push(decoder.decode(value, { stream: true }))) dispatch(event);
	}
	const remaining = decoder.decode();
	if (remaining) {
		for (const event of parser.push(remaining)) dispatch(event);
	}
	for (const event of parser.flush()) dispatch(event);
}
