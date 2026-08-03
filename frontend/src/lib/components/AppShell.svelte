<script lang="ts">
	import Sidebar from './Sidebar.svelte';
	import LoginModal from './LoginModal.svelte';
	import { authStore } from '../stores/auth';

	let { children } = $props();
</script>

<div class="app-shell">
	<Sidebar />
	<main class="main-content">
		{@render children()}
	</main>

	{#if !$authStore.isAuthenticated && !$authStore.isRehydrating}
		<LoginModal />
	{/if}
</div>
