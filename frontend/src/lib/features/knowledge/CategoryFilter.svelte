<script lang="ts">
	const categories = [
		{ label: 'All', className: 'category-all' },
		{ label: 'Account', className: 'category-account' },
		{ label: 'Billing', className: 'category-billing' },
		{ label: 'Workspace', className: 'category-workspace' },
		{ label: 'Security', className: 'category-security' }
	];

	let { selected, onselect }: { selected: string; onselect: (category: string) => void } = $props();
</script>

<div class="category-list" aria-label="Filter answers by category">
	{#each categories as category (category.label)}
		<button
			class="category {category.className}"
			class:selected={selected === category.label}
			type="button"
			onclick={() => onselect(category.label)}
		>
			{category.label}
		</button>
	{/each}
</div>

<style>
	.category-list {
		display: flex;
		flex-wrap: wrap;
		gap: 9px;
		width: min(100%, 820px);
		margin: 14px auto 0;
	}
	.category {
		min-height: 27px;
		padding: 5px 14px;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-pill);
		color: var(--color-text);
		background: var(--color-surface);
		cursor: pointer;
		font-size: 11px;
		font-weight: 500;
		transition:
			transform 150ms ease,
			box-shadow 150ms ease;
	}
	.category:hover {
		transform: translateY(-1px);
		box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
	}
	.category.selected {
		border-color: var(--color-accent);
		box-shadow: 0 4px 12px var(--color-focus-ring);
	}
	.category-all {
		background: var(--color-primary);
		color: var(--color-primary-fg);
		border-color: var(--color-primary);
	}
	.category-account {
		background: var(--color-warning-soft);
		color: var(--color-warning-fg);
	}
	.category-billing {
		background: var(--color-destructive-soft);
		color: var(--color-destructive-fg);
	}
	.category-workspace {
		background: var(--color-accent-soft);
		color: var(--color-accent);
	}
	.category-security {
		background: var(--color-success-soft);
		color: var(--color-success-fg);
	}
</style>
