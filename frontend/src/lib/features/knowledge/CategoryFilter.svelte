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
		border: 1px solid transparent;
		border-radius: var(--radius-pill);
		color: #313852;
		cursor: pointer;
		font-size: 11px;
		font-weight: 500;
	}
	.category:hover {
		transform: translateY(-1px);
		box-shadow: 0 4px 10px rgba(61, 43, 110, 0.08);
	}
	.category.selected {
		border-color: rgba(111, 63, 202, 0.12);
		box-shadow: 0 4px 12px rgba(111, 63, 202, 0.12);
	}
	.category-all {
		background: #895ddd;
		color: var(--color-heading);
	}
	.category-account {
		background: #fff0e3;
	}
	.category-billing {
		background: #ffe4e6;
	}
	.category-workspace {
		background: #f0eaff;
	}
	.category-security {
		background: #e1f7f1;
	}
</style>
