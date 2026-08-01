import { apiRequest } from '$lib/api/client';
import type { KnowledgeSearchResult } from './types';

type SearchResponseDto = {
	query: string;
	answer: string;
	details: string;
	source: { id: string; page: number };
	sources: { id: string; title: string; page: number; updated_at: string }[];
	related_faqs: string[];
};

export async function searchKnowledge(
	query: string,
	category: string
): Promise<KnowledgeSearchResult> {
	const result = await apiRequest<SearchResponseDto>('/api/v1/search', {
		method: 'POST',
		body: JSON.stringify({ query, category: category === 'All' ? null : category })
	});

	return {
		...result,
		relatedFaqs: result.related_faqs,
		sources: result.sources.map((source) => ({ ...source, updatedAt: source.updated_at }))
	};
}
