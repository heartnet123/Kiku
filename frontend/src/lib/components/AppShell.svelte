<script lang="ts">
	import Sidebar from './Sidebar.svelte';
	import LoginModal from './LoginModal.svelte';
	import { authModalStore } from '../stores/auth';

	let { children } = $props();
</script>

<div class="app-shell">
	<Sidebar />
	<main class="main-content">
		{@render children()}
	</main>

	{#if $authModalStore.isOpen}
		<LoginModal />
	{/if}
</div>
