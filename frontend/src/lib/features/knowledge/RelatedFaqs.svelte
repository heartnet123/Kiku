<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';

	let { questions, onselect }: { questions: string[]; onselect: (question: string) => void } =
		$props();
</script>

<aside class="related-card" aria-labelledby="related-title">
	<h2 id="related-title">Related FAQs</h2>
	<div class="faq-list">
		{#each questions as question (question)}
			<button class="faq-row" type="button" onclick={() => onselect(question)}>
				<span>{question}</span><Icon name="chevron-right" size={15} />
			</button>
		{/each}
	</div>
</aside>

<style>
	.related-card {
		align-self: start;
		padding: 22px 18px 9px;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: #ffffff;
		box-shadow: 0 5px 17px rgba(52, 41, 94, 0.035);
	}
	h2 {
		margin: 0;
		color: var(--color-muted);
		font-size: 11px;
		font-weight: 500;
	}
	.faq-list {
		margin-top: 16px;
	}
	.faq-row {
		display: flex;
		width: 100%;
		align-items: center;
		gap: 8px;
		padding: 13px 0;
		border: 0;
		border-bottom: 1px solid var(--color-border);
		background: transparent;
		color: var(--color-subtle);
		cursor: pointer;
		font-size: 11px;
		text-align: left;
	}
	.faq-row:first-child {
		padding-top: 0;
	}
	.faq-row:last-child {
		border-bottom: 0;
	}
	.faq-row:hover {
		color: var(--color-accent);
	}
	.faq-row span {
		max-width: 170px;
	}
	.faq-row :global(iconify-icon) {
		margin-left: auto;
		flex: 0 0 15px;
		color: var(--color-muted);
	}
</style>
