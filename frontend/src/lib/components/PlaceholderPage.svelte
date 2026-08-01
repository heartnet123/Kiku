<script lang="ts">
	let { title, description }: { title: string; description: string } = $props();
</script>

<svelte:head
	><title>{title} — Kiku</title><meta name="description" content={description} /></svelte:head
>

<section class="placeholder-page" aria-labelledby="placeholder-title">
	<p class="eyebrow">Kiku workspace</p>
	<h1 id="placeholder-title">{title}</h1>
	<p>{description}</p>
	<span>Connect this module to its API contract when the feature is ready.</span>
</section>

<style>
	.placeholder-page {
		max-width: 680px;
		margin: 0 auto;
		padding: 72px 0;
	}
	.eyebrow {
		margin: 0 0 12px;
		color: var(--color-accent);
		font-size: 12px;
		font-weight: 500;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	h1 {
		margin: 0;
		color: var(--color-heading);
		font-size: clamp(28px, 4vw, 44px);
		letter-spacing: -1.2px;
	}
	p:not(.eyebrow) {
		margin: 16px 0 0;
		color: var(--color-subtle);
		font-size: 17px;
		line-height: 1.6;
	}
	span {
		display: inline-block;
		margin-top: 26px;
		padding: 10px 14px;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-control);
		background: var(--color-surface);
		color: var(--color-muted);
		font-size: 12px;
	}
</style>
