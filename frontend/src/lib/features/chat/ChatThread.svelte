<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { goto } from '$app/navigation';
	import KikuMascot from '$lib/components/KikuMascot.svelte';
	import { createSession, getMessages, streamChatMessage } from './chatApi';
	import { consumeInitialQuery, storeInitialQuery } from './initialQuery';
	import { requireAuth } from '$lib/stores/auth';
	import type { ChatMessage } from './types';

	let { sessionId = null }: { sessionId?: string | null } = $props();
	let messages = $state<ChatMessage[]>([]);
	let query = $state('');
	let isStreaming = $state(false);
	let statusMessage = $state('');
	let errorMessage = $state<string | null>(null);
	let abortController: AbortController | null = null;
	let streamingAssistantId = $state<string | null>(null);
	let chatContainer: HTMLElement;
	let loadVersion = 0;

	$effect(() => {
		const currentSessionId = sessionId;
		loadVersion += 1;
		const version = loadVersion;

		if (!currentSessionId) {
			messages = [];
			statusMessage = '';
			errorMessage = null;
			return;
		}

		void loadSession(currentSessionId, version);
	});

	function localId(prefix: string): string {
		return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
	}

	async function loadSession(currentSessionId: string, version: number) {
		try {
			messages = await getMessages(currentSessionId);
		} catch (error) {
			if (version !== loadVersion || sessionId !== currentSessionId) return;
			errorMessage = error instanceof Error ? error.message : 'Unable to load this chat.';
			return;
		}

		if (version !== loadVersion || sessionId !== currentSessionId) return;
		const initialQuery = consumeInitialQuery(currentSessionId);
		if (initialQuery) await streamForSession(currentSessionId, initialQuery);
	}

	async function handleSend() {
		if (!query.trim() || isStreaming) return;
		const userText = query.trim();

		requireAuth(async () => {
			query = '';

			if (!sessionId) {
				try {
					const session = await createSession(userText.slice(0, 80));
					storeInitialQuery(session.id, userText);
					await goto(`/chat/${encodeURIComponent(session.id)}`);
				} catch (error) {
					errorMessage = error instanceof Error ? error.message : 'Unable to start a chat.';
				}
				return;
			}

			await streamForSession(sessionId, userText);
		});
	}

	async function streamForSession(currentSessionId: string, userText: string) {
		if (isStreaming) return;

		const userMessage: ChatMessage = {
			id: localId('user'),
			session_id: currentSessionId,
			role: 'user',
			content: userText,
			created_at: new Date().toISOString()
		};
		const assistantMessage: ChatMessage = {
			id: localId('assistant'),
			session_id: currentSessionId,
			role: 'assistant',
			content: '',
			citations: [],
			created_at: new Date().toISOString()
		};

		streamingAssistantId = assistantMessage.id;
		messages = [...messages, userMessage, assistantMessage];
		isStreaming = true;
		statusMessage = '';
		errorMessage = null;
		const controller = new AbortController();
		abortController = controller;
		let completed = false;

		try {
			await streamChatMessage(
				currentSessionId,
				userText,
				'All',
				{
					onStatus: (nextStatus, message) => {
						statusMessage = message ?? nextStatus.replaceAll('_', ' ');
					},
					onMetadata: (metadata) => {
						assistantMessage.citations = metadata.citations;
						messages = [...messages];
					},
					onDelta: (content) => {
						assistantMessage.content += content;
						messages = [...messages];
						scrollToBottom();
					},
					onError: (message, recoverable) => {
						errorMessage = recoverable ? `The synthesis service reported: ${message}` : message;
					},
					onDone: (result) => {
						completed = result.status === 'completed';
						if (result.message_id) assistantMessage.id = result.message_id;
						statusMessage = result.status === 'completed' ? 'Answer complete.' : result.status;
						messages = [...messages];
					}
				},
				controller.signal
			);
		} catch (error) {
			if (!controller.signal.aborted) {
				errorMessage = error instanceof Error ? error.message : 'Chat stream failed.';
			}
		} finally {
			if (!completed) removeStreamingAssistant();
			isStreaming = false;
			if (abortController === controller) abortController = null;
			streamingAssistantId = null;
			if (completed) {
				try {
					messages = await getMessages(currentSessionId);
				} catch {
					// Keep the completed optimistic response if the refresh request fails.
				}
			}
		}
	}

	function removeStreamingAssistant() {
		if (!streamingAssistantId) return;
		messages = messages.filter((message) => message.id !== streamingAssistantId);
	}

	function handleStop() {
		if (!abortController) return;
		abortController.abort();
		removeStreamingAssistant();
		isStreaming = false;
		statusMessage = 'Generation stopped. The partial response was not saved.';
		streamingAssistantId = null;
		abortController = null;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			void handleSend();
		}
	}

	function scrollToBottom() {
		if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
	}
</script>

<svelte:head>
	<title>{sessionId ? 'Kiku — Chat' : 'Kiku — New Chat'}</title>
</svelte:head>

<section class="chat-thread-container" aria-label="Chat with Kiku" bind:this={chatContainer}>
	<div class="chat-content">
		{#if messages.length === 0}
			<div class="empty-state">
				<KikuMascot className="mascot-large" />
				<h2>Hi there! How can I help today? 👋</h2>
				<p>Ask anything about your workspace sources and documents.</p>
			</div>
		{:else}
			<div class="messages-list" aria-live="polite" aria-atomic="false">
				{#each messages as message (message.id)}
					<div class="message-row {message.role}">
						{#if message.role === 'assistant'}
							<div class="avatar" aria-hidden="true"><KikuMascot className="avatar-art" /></div>
						{/if}
						<div class="bubble">
							<p>
								{message.content}{#if isStreaming && message.id === streamingAssistantId}<span
										class="cursor"
										aria-hidden="true">▊</span
									>{/if}
							</p>
							{#if message.citations && message.citations.length > 0}
								<details class="citations-accordion">
									<summary>Grounded sources ({message.citations.length})</summary>
									{#each message.citations as citation (JSON.stringify( [citation.source_id, citation.version, citation.location] ))}
										<div class="cite-card">
											<strong>{citation.title}</strong>
											<span>{citation.location} · v{citation.version}</span>
											<p class="snippet">“{citation.snippet}”</p>
										</div>
									{/each}
								</details>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<div class="live-status" aria-live="polite" aria-atomic="true">{statusMessage}</div>
		{#if errorMessage}
			<div class="error-state" role="alert">{errorMessage}</div>
		{/if}
	</div>

	<div class="input-bar-container">
		<form
			onsubmit={(event) => {
				event.preventDefault();
				void handleSend();
			}}
		>
			<textarea
				bind:value={query}
				aria-label="Message Kiku"
				placeholder="Message Kiku..."
				rows="1"
				disabled={isStreaming}
				onkeydown={handleKeydown}></textarea>
			{#if isStreaming}
				<button type="button" class="stop-btn" aria-label="Stop generating" onclick={handleStop}
					>Stop</button
				>
			{:else}
				<button type="submit" class="send-btn" aria-label="Send message" disabled={!query.trim()}
					>Send</button
				>
			{/if}
		</form>
		<p class="input-hint">Enter to send · Shift+Enter for a new line</p>
	</div>
</section>

<style>
	.chat-thread-container {
		display: flex;
		min-height: calc(100vh - 32px);
		flex-direction: column;
		background: var(--color-bg);
	}
	.chat-content {
		width: min(100% - 48px, 960px);
		margin: 0 auto;
		padding: 40px 0 128px;
	}
	.empty-state {
		display: grid;
		min-height: 54vh;
		place-content: center;
		justify-items: center;
		text-align: center;
	}
	.empty-state h2 {
		margin: 18px 0 4px;
		color: var(--color-heading);
		font-size: 24px;
		font-weight: 650;
	}
	.empty-state p {
		margin: 0;
		color: var(--color-muted);
	}
	.messages-list {
		display: flex;
		flex-direction: column;
		gap: 18px;
	}
	.message-row {
		display: flex;
		max-width: 86%;
		align-items: flex-start;
		gap: 10px;
	}
	.message-row.user {
		align-self: flex-end;
		flex-direction: row-reverse;
	}
	.message-row.user .bubble {
		border-color: transparent;
		border-radius: 18px 18px 4px 18px;
		background: var(--color-accent);
		color: white;
	}
	.message-row.assistant .bubble {
		border-radius: 18px 18px 18px 4px;
		background: var(--color-surface);
	}
	.bubble {
		border: 1px solid var(--color-border);
		padding: 13px 16px;
		color: var(--color-text);
		line-height: 1.6;
	}
	.bubble p {
		margin: 0;
		white-space: pre-wrap;
	}
	.avatar {
		width: 30px;
		flex: 0 0 30px;
		padding-top: 4px;
	}
	:global(.avatar-art) {
		width: 30px;
		height: 30px;
		border-radius: 50%;
	}
	:global(.mascot-large) {
		width: 72px;
		height: 72px;
	}
	.cursor {
		display: inline-block;
		color: var(--color-accent);
		animation: blink 1s infinite;
	}
	@keyframes blink {
		50% {
			opacity: 0;
		}
	}
	.citations-accordion {
		margin-top: 11px;
		border-top: 1px solid var(--color-border);
		padding-top: 9px;
		color: var(--color-subtle);
		font-size: 12px;
	}
	.citations-accordion summary {
		cursor: pointer;
		font-weight: 650;
	}
	.cite-card {
		display: grid;
		gap: 2px;
		margin-top: 8px;
		border: 1px solid var(--color-border);
		border-radius: 10px;
		background: var(--color-surface-soft);
		padding: 9px;
	}
	.cite-card strong {
		color: var(--color-heading);
	}
	.cite-card span {
		color: var(--color-muted);
		font-size: 11px;
	}
	.cite-card .snippet {
		color: var(--color-subtle);
		font-style: italic;
	}
	.live-status {
		min-height: 22px;
		margin-top: 14px;
		color: var(--color-muted);
		font-size: 12px;
	}
	.error-state {
		margin-top: 8px;
		border: 1px solid var(--color-destructive-border);
		border-radius: 10px;
		background: var(--color-destructive-soft);
		padding: 10px 12px;
		color: var(--color-destructive-fg);
		font-size: 13px;
	}
	.input-bar-container {
		position: sticky;
		bottom: 0;
		width: min(100% - 48px, 960px);
		margin: auto auto 0;
		border-top: 1px solid var(--color-border);
		background: color-mix(in srgb, var(--color-bg) 92%, transparent);
		padding: 14px 0 18px;
		backdrop-filter: blur(10px);
	}
	form {
		display: flex;
		align-items: flex-end;
		gap: 9px;
	}
	textarea {
		min-height: 46px;
		max-height: 160px;
		flex: 1;
		resize: vertical;
		border: 1px solid var(--color-border-strong);
		border-radius: var(--radius-control);
		background: var(--color-surface);
		padding: 12px 14px;
		color: var(--color-text);
		outline: none;
	}
	textarea:focus {
		border-color: var(--color-accent);
		box-shadow: 0 0 0 3px var(--color-focus-ring);
	}
	button {
		min-height: 46px;
		border: 0;
		border-radius: var(--radius-control);
		padding: 0 18px;
		cursor: pointer;
		font-weight: 650;
	}
	button:disabled {
		cursor: not-allowed;
		opacity: 0.5;
	}
	.send-btn {
		background: var(--color-accent);
		color: var(--color-primary-fg);
	}
	.stop-btn {
		background: var(--color-destructive);
		color: var(--color-primary-fg);
	}
	.input-hint {
		margin: 6px 2px 0;
		color: var(--color-muted);
		font-size: 11px;
	}
	@media (max-width: 640px) {
		.chat-content,
		.input-bar-container {
			width: min(100% - 28px, 560px);
		}
		.message-row {
			max-width: 94%;
		}
	}
</style>
