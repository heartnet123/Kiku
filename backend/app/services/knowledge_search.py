from app.domain.knowledge import KnowledgeResult, KnowledgeSource


class KnowledgeSearchService:
    """Application boundary for workspace-scoped knowledge retrieval."""

    def search(self, workspace_id: str, query: str, category: str | None = None) -> KnowledgeResult:
        normalized_query = query.strip() or "How do I upgrade my plan?"

        return KnowledgeResult(
            query=normalized_query,
            answer=f"[{workspace_id}] You can upgrade your plan anytime.",
            details=f"Workspace '{workspace_id}' knowledge base: Go to Settings > Billing, choose your plan, and confirm.",
            source_id=f"{workspace_id}.docs.billing.upgrade",
            source_page=2,
            sources=(
                KnowledgeSource(
                    id=f"{workspace_id}-billing-guide",
                    title=f"Billing Guide ({workspace_id})",
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
