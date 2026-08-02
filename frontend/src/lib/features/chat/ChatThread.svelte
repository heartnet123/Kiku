<script lang="ts">
	import type { ChatMessage, ChatCitation } from './types';
	import { streamChatMessage, createSession, getMessages } from './chatApi';
	import KikuMascot from '$lib/components/KikuMascot.svelte';
	import { activeSessionStore } from './chatStore';

	let activeSession = $derived($activeSessionStore);

	let messages = $state<ChatMessage[]>([]);
	let query = $state('');
	let isStreaming = $state(false);
	let abortController: AbortController | null = null;
	let chatContainer: HTMLDivElement;

	$effect(() => {
		if (activeSession) {
			loadMessages(activeSession.id);
		} else {
			messages = [];
		}
	});

	async function loadMessages(sessionId: string) {
		try {
			messages = await getMessages(sessionId);
		} catch {
			messages = [];
		}
	}

	async function handleSend() {
		if (!query.trim() || isStreaming) return;
		const userText = query.trim();
		query = '';

		let currentSession = activeSession;
		if (!currentSession) {
			try {
				currentSession = await createSession(userText.slice(0, 30));
				activeSessionStore.set(currentSession);
			} catch {
				return;
			}
		}

		const userMsg: ChatMessage = {
			id: String(Date.now()),
			session_id: currentSession.id,
			role: 'user',
			content: userText,
			created_at: new Date().toISOString()
		};

		const assistantMsg: ChatMessage = {
			id: String(Date.now() + 1),
			session_id: currentSession.id,
			role: 'assistant',
			content: '',
			citations: [],
			created_at: new Date().toISOString()
		};

		messages = [...messages, userMsg, assistantMsg];
		isStreaming = true;
		abortController = new AbortController();

		try {
			await streamChatMessage(
				currentSession.id,
				userText,
				'All',
				(citations) => {
					assistantMsg.citations = citations;
					messages = [...messages];
				},
				(delta) => {
					assistantMsg.content += delta;
					messages = [...messages];
					scrollToBottom();
				},
				() => {
					isStreaming = false;
				},
				abortController.signal
			);
		} catch {
			isStreaming = false;
		}
	}

	function handleStop() {
		if (abortController) {
			abortController.abort();
			isStreaming = false;
		}
	}

	function scrollToBottom() {
		if (chatContainer) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
		}
	}
</script>

<div class="chat-thread-container" bind:this={chatContainer}>
	{#if messages.length === 0}
		<div class="empty-state">
			<KikuMascot className="mascot-large" />
			<h2>Hi there! How can I help today? 👋</h2>
			<p>Ask anything about your workspace sources and documents.</p>
		</div>
	{:else}
		<div class="messages-list">
			{#each messages as msg}
				<div class="message-row {msg.role}">
					{#if msg.role === 'assistant'}
						<div class="avatar"><KikuMascot className="avatar-art" /></div>
					{/if}
					<div class="bubble">
						<p>{msg.content}{#if isStreaming && msg.role === 'assistant' && msg.id === messages[messages.length - 1].id}<span class="cursor">▊</span>{/if}</p>
						{#if msg.citations && msg.citations.length > 0}
							<details class="citations-accordion">
								<summary>📚 Grounded Sources ({msg.citations.length})</summary>
								{#each msg.citations as cite}
									<div class="cite-card">
										<strong>{cite.title}</strong> — {cite.location}
										<p class="snippet">"{cite.snippet}"</p>
									</div>
								{/each}
							</details>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}

	<div class="input-bar-container">
		<form onsubmit={(e) => { e.preventDefault(); handleSend(); }}>
			<input bind:value={query} placeholder="Message Kiku..." disabled={isStreaming} />
			{#if isStreaming}
				<button type="button" class="stop-btn" onclick={handleStop}>Stop</button>
			{:else}
				<button type="submit" class="send-btn">Send</button>
			{/if}
		</form>
	</div>
</div>

<style>
	.chat-thread-container { display: flex; flex-direction: column; height: 100%; min-height: 480px; overflow-y: auto; padding: 20px; position: relative; }
	.empty-state { text-align: center; margin: auto; padding: 40px 0; }
	.empty-state h2 { margin-top: 16px; font-weight: 600; color: #111827; }
	.empty-state p { color: #6b7280; font-size: 14px; margin-top: 4px; }
	.messages-list { display: flex; flex-direction: column; gap: 16px; margin-bottom: 80px; }
	.message-row { display: flex; gap: 12px; max-width: 85%; }
	.message-row.user { align-self: flex-end; flex-direction: row-reverse; }
	.message-row.user .bubble { background: #6366f1; color: white; border-radius: 16px 16px 2px 16px; }
	.message-row.assistant .bubble { background: #f3f4f6; color: #1f2937; border-radius: 16px 16px 16px 2px; }
	.bubble { padding: 12px 16px; line-height: 1.5; font-size: 14px; }
	.cursor { display: inline-block; animation: blink 1s infinite; color: #6366f1; }
	@keyframes blink { 50% { opacity: 0; } }
	.citations-accordion { margin-top: 8px; font-size: 12px; }
	.cite-card { background: white; padding: 8px; border-radius: 6px; margin-top: 4px; border: 1px solid #e5e7eb; }
	.cite-card .snippet { color: #4b5563; font-style: italic; margin-top: 2px; }
	.input-bar-container { position: sticky; bottom: 0; background: white; padding: 12px 0; border-top: 1px solid #f3f4f6; }
	form { display: flex; gap: 8px; }
	input { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #d1d5db; font-size: 14px; }
	button { padding: 12px 20px; border-radius: 8px; border: none; cursor: pointer; font-weight: 500; }
	.send-btn { background: #6366f1; color: white; }
	.stop-btn { background: #ef4444; color: white; }
	:global(.mascot-large) { width: 64px; height: 64px; }
	:global(.avatar-art) { width: 32px; height: 32px; border-radius: 50%; }
</style>
