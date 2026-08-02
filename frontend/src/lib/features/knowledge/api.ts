import { apiRequest } from '$lib/api/client';
import { getCurrentWorkspaceId } from '$lib/stores/workspace';
import type { KnowledgeSearchResult } from './types';

type SearchResponseDto = {
	query: string;
	answer: string;
	details: string;
	source: {
		id: string;
		page: number;
		title?: string | null;
		version?: number | null;
		location?: string | null;
		snippet?: string | null;
	};
	sources: { id: string; title: string; page: number; updated_at: string }[];
	related_faqs: string[];
};

export async function searchKnowledge(
	query: string,
	category: string,
	workspaceId?: string
): Promise<KnowledgeSearchResult> {
	const activeWorkspaceId = workspaceId || getCurrentWorkspaceId() || 'ws_acme';
	const result = await apiRequest<SearchResponseDto>(
		`/api/v1/workspaces/${activeWorkspaceId}/search`,
		{
			method: 'POST',
			body: JSON.stringify({ query, category: category === 'All' ? null : category })
		}
	);

	return {
		...result,
		source: {
			id: result.source?.id || '',
			page: result.source?.page || 1,
			title: result.source?.title || undefined,
			version: result.source?.version || undefined,
			location: result.source?.location || undefined,
			snippet: result.source?.snippet || undefined
		},
		relatedFaqs: result.related_faqs || [],
		sources: (result.sources || []).map((source) => ({ ...source, updatedAt: source.updated_at }))
	};
}
