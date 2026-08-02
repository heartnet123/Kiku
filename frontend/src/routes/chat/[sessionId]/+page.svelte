<script lang="ts">
	import { page } from '$app/state';
	import ChatThread from '$lib/features/chat/ChatThread.svelte';
</script>

<svelte:head>
	<title>Kiku — Chat</title>
	<meta name="description" content="Continue a durable Kiku chat session." />
</svelte:head>

<div class="workspace-chat">
	<ChatThread sessionId={page.params.sessionId} />
</div>

<style>
	.workspace-chat {
		min-height: calc(100vh / var(--ui-scale));
	}
</style>
