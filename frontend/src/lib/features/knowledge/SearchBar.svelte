<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';

	let {
		value = $bindable(''),
		onsubmit
	}: { value?: string; onsubmit?: (event: SubmitEvent) => void } = $props();
</script>

<form class="search-form" role="search" {onsubmit}>
	<Icon name="search" size={18} className="search-icon" />
	<input
		bind:value
		aria-label="Search or ask anything"
		placeholder="How do I upgrade my plan?"
		type="search"
	/>
	<button class="search-button" type="submit" aria-label="Search"
		><Icon name="search" size={17} /></button
	>
</form>

<style>
	.search-form {
		display: flex;
		width: min(100%, 820px);
		height: 51px;
		align-items: center;
		margin: 0 auto;
		padding: 5px 6px 5px 16px;
		border: 1px solid var(--color-border-strong);
		border-radius: var(--radius-control);
		background: var(--color-surface);
		box-shadow: 0 7px 20px rgba(0, 0, 0, 0.04);
	}
	.search-form:focus-within {
		border-color: var(--color-primary);
		box-shadow: 0 8px 24px var(--color-focus-ring);
	}
	:global(.search-icon) {
		flex: 0 0 18px;
		color: var(--color-muted);
	}
	input {
		width: 100%;
		min-width: 0;
		padding: 0 12px;
		border: 0;
		outline: 0;
		background: transparent;
		color: var(--color-text);
		font-size: 13px;
	}
	input::placeholder {
		color: var(--color-muted);
		opacity: 1;
	}
	.search-button {
		display: grid;
		width: 34px;
		height: 34px;
		flex: 0 0 34px;
		place-items: center;
		border: 0;
		border-radius: var(--radius-control);
		background: var(--color-primary);
		color: var(--color-primary-fg);
		cursor: pointer;
	}
	.search-button:hover {
		background: var(--color-primary-hover);
	}
</style>
