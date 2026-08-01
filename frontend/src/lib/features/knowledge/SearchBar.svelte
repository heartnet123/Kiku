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
		border: 1px solid #dedcea;
		border-radius: var(--radius-control);
		background: #ffffff;
		box-shadow: 0 7px 20px rgba(53, 38, 103, 0.05);
	}
	.search-form:focus-within {
		border-color: #ad8ce9;
		box-shadow: 0 8px 24px rgba(104, 70, 184, 0.1);
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
		background: #895ddd;
		color: var(--color-heading);
		cursor: pointer;
	}
	.search-button:hover {
		background: #7546cc;
	}
</style>
