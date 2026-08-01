<script lang="ts">
	import AppShell from '$lib/components/AppShell.svelte';
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" type="image/svg+xml" href={favicon} />
	<link rel="apple-touch-icon" href="/kiku-icon.png" />
</svelte:head>

<AppShell>
	{@render children()}
</AppShell>
