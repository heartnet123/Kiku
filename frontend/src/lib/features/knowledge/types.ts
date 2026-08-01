export type KnowledgeSource = {
	id: string;
	title: string;
	page: number;
	updatedAt: string;
};

export type KnowledgeSearchResult = {
	query: string;
	answer: string;
	details: string;
	source: {
		id: string;
		page: number;
		title?: string;
		version?: number;
		location?: string;
		snippet?: string;
	};
	sources: KnowledgeSource[];
	relatedFaqs: string[];
};
