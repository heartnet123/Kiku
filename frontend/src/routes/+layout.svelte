<script lang="ts">
	import { onMount } from 'svelte';
	import AppShell from '$lib/components/AppShell.svelte';
	import { initFromServer, rehydrateAuth } from '$lib/stores/auth';
	import { initTheme } from '$lib/stores/theme';
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children, data } = $props();

	// Pre-hydrate store from SSR auth state and workspaces.
	$effect(() => {
		if (data.authState) {
			initFromServer(data.authState, data.workspaces ?? []);
		}
	});

	onMount(async () => {
		initTheme();
		// Always call rehydrateAuth to populate workspaces from /me.
		// When SSR already set the cookie, /me succeeds without sessionStorage.
		await rehydrateAuth();
	});
</script>

<svelte:head>
	<link rel="icon" type="image/svg+xml" href={favicon} />
	<link rel="apple-touch-icon" href="/kiku-icon.png" />
</svelte:head>

<AppShell>
	{@render children()}
</AppShell>
