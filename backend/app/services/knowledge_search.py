from app.domain.knowledge import KnowledgeResult, KnowledgeSource


class KnowledgeSearchService:
    """Application boundary for knowledge retrieval.

    Replace the in-memory result with a repository or search adapter later.
    The HTTP router and frontend contract can remain unchanged.
    """

    def search(self, query: str, category: str | None = None) -> KnowledgeResult:
        normalized_query = query.strip() or "How do I upgrade my plan?"

        return KnowledgeResult(
            query=normalized_query,
            answer="You can upgrade your plan anytime.",
            details="Go to Settings > Billing, choose your new plan, and confirm. Changes take effect immediately.",
            source_id="docs.billing.upgrade",
            source_page=2,
            sources=(
                KnowledgeSource(
                    id="billing-guide",
                    title="Billing Guide",
                    page=1,
                    updated_at="Updated Apr 12, 2024",
                ),
            ),
            related_faqs=(
                "How do I change my plan?",
                "What payment methods do you accept?",
                "Can I downgrade my plan?",
            ),
        )
