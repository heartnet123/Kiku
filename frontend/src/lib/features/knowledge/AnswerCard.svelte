<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import type { KnowledgeSearchResult } from './types';

	let { result }: { result: KnowledgeSearchResult } = $props();
</script>

<section class="answer-card" aria-labelledby="answer-title">
	<div class="answer-header">
		<Icon name="sparkle" size={18} className="sparkle" />
		<h2 id="answer-title">Answer</h2>
	</div>
	<div class="answer-copy">
		<h3>{result.answer}</h3>
		<p>{result.details}</p>
	</div>
	<a class="source-chip" href="#sources">
		<span class="document-icon"><Icon name="document" size={16} /></span>
		<strong>{result.source.id}</strong><span class="source-page">Page {result.source.page}</span>
		<Icon name="external" size={16} className="external-icon" />
	</a>
	<div class="answer-divider"></div>
	<div class="sources" id="sources">
		<h3>Sources</h3>
		{#each result.sources as source (source.id)}
			<a class="source-row" href={'#' + source.id}>
				<span class="source-row-icon"><Icon name="document" size={17} /></span>
				<span class="source-row-copy"
					><strong>{source.title}</strong><small>{source.updatedAt}</small></span
				>
				<Icon name="chevron-right" size={16} className="source-row-arrow" />
			</a>
		{/each}
	</div>
</section>

<style>
	.answer-card {
		min-height: 419px;
		padding: 23px 24px 20px;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: #ffffff;
		box-shadow: 0 5px 17px rgba(52, 41, 94, 0.035);
	}
	.answer-header {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	:global(.sparkle) {
		color: var(--color-success);

		line-height: 1;
	}
	h2,
	.sources h3 {
		margin: 0;
		color: var(--color-muted);
		font-size: 11px;
		font-weight: 500;
	}
	.answer-copy {
		margin-top: 20px;
	}
	.answer-copy h3 {
		margin: 0;
		color: var(--color-heading);
		font-size: 20px;
		font-weight: 600;
		letter-spacing: -0.025em;
	}
	.answer-copy p {
		margin: 10px 0 0;
		color: var(--color-subtle);
		font-size: 13px;
		line-height: 1.55;
	}
	.source-chip {
		display: flex;
		align-items: center;
		gap: 10px;
		width: min(100%, 376px);
		min-height: 43px;
		margin-top: 18px;
		padding: 8px 10px;
		border: 1px solid #d7eee5;
		border-radius: var(--radius-control);
		background: #f5fbf9;
		color: var(--color-text);
		font-size: 11px;
		text-decoration: none;
	}
	.source-chip:hover {
		border-color: #adddca;
		background: #eefaf5;
	}
	.document-icon {
		display: grid;
		width: 19px;
		height: 19px;
		flex: 0 0 19px;
		place-items: center;
		color: var(--color-success);
	}
	.source-page {
		margin-left: auto;
		color: var(--color-muted);
		font-size: 10px;
	}
	:global(.external-icon) {
		color: var(--color-muted);
	}
	.answer-divider {
		height: 1px;
		margin: 19px 0 17px;
		background: var(--color-border);
	}
	.sources h3 {
		font-size: 11px;
	}
	.source-row {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-top: 12px;
		color: var(--color-text);
		text-decoration: none;
	}
	.source-row-icon {
		display: grid;
		width: 30px;
		height: 30px;
		flex: 0 0 30px;
		place-items: center;
		border-radius: var(--radius-control);
		background: #f5f1ff;
		color: var(--color-accent);
	}
	.source-row-copy {
		display: grid;
		gap: 3px;
	}
	.source-row-copy strong {
		font-size: 11px;
	}
	.source-row-copy small {
		color: var(--color-muted);
		font-size: 10px;
	}
	:global(.source-row-arrow) {
		margin-left: auto;
		color: var(--color-muted);
	}
</style>
