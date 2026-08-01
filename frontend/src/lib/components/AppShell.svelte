<script lang="ts">
	import Sidebar from './Sidebar.svelte';
	import DemoLoginModal from './DemoLoginModal.svelte';
	import { authStore } from '../stores/workspace';
	import './layout.css';

	let { children } = $props();
</script>

<div class="app-shell">
	<Sidebar />
	<main class="main-content">
		{@render children()}
	</main>

	{#if !$authStore.isAuthenticated}
		<DemoLoginModal />
	{/if}
</div>
