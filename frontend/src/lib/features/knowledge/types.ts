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
	source: { id: string; page: number };
	sources: KnowledgeSource[];
	relatedFaqs: string[];
};
