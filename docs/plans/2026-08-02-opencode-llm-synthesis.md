# Implementation Plan: Opencode LLM Synthesis Layer

**Date**: 2026-08-02  
**Branch**: `feature/opencode-llm-synthesis`  
**Target Component**: Component 3 — Semantic Retrieval & Opencode LLM Synthesis Layer

## Objective
Upgrade Kiku's search service (`KnowledgeSearchService`) to synthesize knowledge answers using **Opencode API (`https://opencode.ai/zen/v1/chat/completions`)** with model **`deepseek-v4-flash-free`** and RAG context grounding, replacing the prototype string formatting template.

## Verified Codebase Context
- `backend/app/core/config.py:1-12`: Application settings.
- `backend/app/services/knowledge_search.py:1-84`: Current knowledge retrieval service.
- `backend/app/schemas/knowledge.py:47-54`: `SearchResponse` schema.
- `backend/app/api/v1/routes/search.py:1-92`: Knowledge search HTTP endpoint.

## Scope & Non-Goals
- **In-Scope**:
  - Add Opencode API & OpenAI Embedding settings to `config.py`.
  - Wire Opencode Chat Completions API (`deepseek-v4-flash-free`) with strict RAG system prompt into `KnowledgeSearchService`.
  - Handle explicit no-evidence responses when no chunks match.
  - Add fallback error handling when Opencode API fails/timeouts.
  - Add comprehensive unit & integration tests.
- **Out-of-Scope**:
  - Supabase vector schema migrations (Component 2).
  - Front-end citation drawer modifications (Component 5).
  - Unrelated edits to `frontend/src/lib/components/AppShell.svelte`.

## Proposed Commit Boundaries

1. `feat(backend): add Opencode API and OpenAI embedding configurations`
   - Files: `backend/app/core/config.py`
2. `feat(backend): integrate Opencode LLM synthesis in KnowledgeSearchService`
   - Files: `backend/app/services/knowledge_search.py`
3. `test(backend): add tests for Opencode LLM synthesis and search service`
   - Files: `backend/tests/test_opencode_search.py`

## Verification Matrix
- `uv run pytest backend/tests/test_knowledge_search.py`: Verify existing search service tests.
- `uv run pytest backend/tests/test_opencode_search.py`: Verify Opencode LLM synthesis, mock responses, and fallback behavior.
- `uv run pytest`: Verify entire backend test suite passes without regressions.
