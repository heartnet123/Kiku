import type { KnowledgeSearchResult } from './types';

export const defaultKnowledgeResult: KnowledgeSearchResult = {
	query: 'How do I upgrade my plan?',
	answer: 'You can upgrade your plan anytime.',
	details:
		'Go to Settings > Billing, choose your new plan, and confirm. Changes take effect immediately.',
	source: { id: 'docs.billing.upgrade', page: 2 },
	sources: [
		{ id: 'billing-guide', title: 'Billing Guide', page: 1, updatedAt: 'Updated Apr 12, 2024' }
	],
	relatedFaqs: [
		'How do I change my plan?',
		'What payment methods do you accept?',
		'Can I downgrade my plan?'
	]
};
