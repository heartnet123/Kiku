<script lang="ts">
	import CategoryFilter from './CategoryFilter.svelte';
	import AnswerCard from './AnswerCard.svelte';
	import RelatedFaqs from './RelatedFaqs.svelte';
	import SearchBar from './SearchBar.svelte';
	import { searchKnowledge } from './api';
	import { defaultKnowledgeResult } from './data';
	import type { KnowledgeSearchResult } from './types';
	import KikuMascot from '$lib/components/KikuMascot.svelte';

	let query = $state(defaultKnowledgeResult.query);
	let selectedCategory = $state('All');
	let result = $state<KnowledgeSearchResult>(defaultKnowledgeResult);
	let statusMessage = $state('');
	let isSearching = $state(false);

	async function handleSearch(event: SubmitEvent) {
		event.preventDefault();
		const normalizedQuery = query.trim() || defaultKnowledgeResult.query;
		query = normalizedQuery;
		isSearching = true;
		statusMessage = '';
		try {
			result = await searchKnowledge(normalizedQuery, selectedCategory);
		} catch {
			statusMessage = 'Showing the demo answer while the API is unavailable.';
		} finally {
			isSearching = false;
		}
	}

	function selectFaq(question: string) {
		query = question;
		statusMessage = '';
	}
</script>

<svelte:head>
	<title>Kiku — Your AI assistant</title>
	<meta
		name="description"
		content="Ask Kiku anything and find the right answer from your team's sources."
	/>
</svelte:head>

<div class="workspace">
	<header class="welcome-block">
		<h1>Hi there! How can I help? <span aria-hidden="true">👋</span></h1>
		<p>Search or ask anything. Kiku will find the right answer.</p>
	</header>
	<SearchBar bind:value={query} onsubmit={handleSearch} />
	<CategoryFilter
		selected={selectedCategory}
		onselect={(category) => (selectedCategory = category)}
	/>
	<div class="content-grid" aria-busy={isSearching}>
		<AnswerCard {result} />
		<RelatedFaqs questions={result.relatedFaqs} onselect={selectFaq} />
	</div>
	<p class="search-status" aria-live="polite">
		{statusMessage || 'Showing an answer for “' + result.query + '”'}
	</p>
	<button class="floating-mascot" type="button" aria-label="Ask Kiku a question"
		><KikuMascot className="floating-mascot-art" /></button
	>
</div>

<style>
	.welcome-block {
		margin-bottom: 28px;
		text-align: center;
	}
	.welcome-block h1 {
		margin: 0;
		color: var(--color-heading);
		font-size: clamp(23px, 2.1vw, 29px);
		font-weight: 600;
		letter-spacing: -0.04em;
	}
	.welcome-block h1 span {
		font-size: 0.92em;
	}
	.welcome-block p {
		margin: 9px 0 0;
		color: var(--color-muted);
		font-size: 13px;
	}
	.content-grid {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 247px;
		gap: 19px;
		margin-top: 24px;
	}
	.search-status {
		margin: 18px 0 0;
		color: var(--color-muted);
		font-size: 10px;
		text-align: center;
	}
	.floating-mascot {
		position: fixed;
		right: 25px;
		bottom: 22px;
		display: grid;
		width: 60px;
		height: 60px;
		place-items: center;
		padding: 7px;
		border: 1px solid #ffa9b6;
		border-radius: 50%;
		background: #ffffff;
		box-shadow: 0 8px 18px rgba(78, 52, 113, 0.13);
		cursor: pointer;
	}
	.floating-mascot:hover {
		transform: translateY(-2px);
	}
	:global(.floating-mascot-art) {
		width: 100%;
		height: 100%;
	}
	@media (max-width: 900px) {
		.content-grid {
			grid-template-columns: minmax(0, 1fr);
		}
		:global(.faq-list) {
			display: grid;
			grid-template-columns: repeat(3, minmax(0, 1fr));
			gap: 16px;
		}
		:global(.faq-row) {
			border-bottom: 0;
		}
	}
	@media (max-width: 640px) {
		.content-grid {
			margin-top: 24px;
		}
		.welcome-block h1 {
			font-size: 24px;
		}
		:global(.faq-list) {
			display: block;
		}
		:global(.faq-row) {
			border-bottom: 1px solid #eceaf1;
		}
		.floating-mascot {
			right: 16px;
			bottom: 16px;
			width: 55px;
			height: 55px;
		}
	}
</style>
