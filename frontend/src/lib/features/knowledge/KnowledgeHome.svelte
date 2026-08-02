<script lang="ts">
	import ChatThread from '$lib/features/chat/ChatThread.svelte';
</script>

<svelte:head>
	<title>Kiku — Your AI Assistant</title>
	<meta
		name="description"
		content="Ask Kiku anything and find the right answer from your team's sources."
	/>
</svelte:head>

<div class="workspace-chat">
	<ChatThread />
</div>

<style>
	.workspace-chat {
		height: calc(100vh - 100px);
		max-width: 960px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
	}
</style>
