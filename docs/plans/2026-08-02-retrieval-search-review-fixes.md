# Retrieval Search Review Fixes Implementation Plan

## Approach

Harden the existing top-level search alias without changing the workspace-scoped
search contract used by the frontend. A user with one membership keeps automatic
workspace selection; a user with multiple memberships receives an explicit
conflict response and must use the workspace-scoped endpoint. Add regression
coverage for ambiguous, revoked, and single-workspace alias authorization.

## Repository Findings

- [`backend/app/api/v1/routes/search.py:61`](E:/webappgithub/kiku/backend/app/api/v1/routes/search.py:61) — `get_user_workspace_id` currently returns the first matching membership from `DEMO_MEMBERSHIPS`, so multi-workspace selection depends on dictionary insertion order.
- [`backend/app/api/v1/routes/search.py:69`](E:/webappgithub/kiku/backend/app/api/v1/routes/search.py:69) — `require_alias_member_context` already performs an explicit membership check and can remain the authorization boundary.
- [`frontend/src/lib/features/knowledge/api.ts:21`](E:/webappgithub/kiku/frontend/src/lib/features/knowledge/api.ts:21) — the frontend uses `/api/v1/workspaces/{workspace_id}/search`, so the alias change does not alter the primary UI request path.
- [`backend/tests/test_retrieval_search.py:154`](E:/webappgithub/kiku/backend/tests/test_retrieval_search.py:154) — the current alias test covers only a missing token and does not cover revoked or ambiguous memberships.
- `git diff --check` reports an extra blank line at [`backend/app/api/v1/routes/search.py:89`](E:/webappgithub/kiku/backend/app/api/v1/routes/search.py:89); [`backend/app/services/ingestion_pipeline.py:140`](E:/webappgithub/kiku/backend/app/services/ingestion_pipeline.py:140) also contains an unused source-level category variable.

## Scope

### In

- Make top-level alias workspace selection deterministic by rejecting ambiguous multi-membership requests with HTTP 409.
- Preserve automatic selection for exactly one membership and preserve the existing 403 behavior when no membership exists.
- Add regression tests for multi-membership ambiguity, single-workspace selection, and revoked/no-membership access.
- Remove the unused local category calculation and the introduced trailing blank line.
- Commit the plan and implementation separately with explicit file staging.

### Out

- No frontend changes, API changes to `/api/v1/workspaces/{workspace_id}/search`, or new persistence layer.
- No redesign of authentication/session storage or production database membership ownership.
- No broad query-tokenization or search-ranking changes; punctuation normalization remains a follow-up recommendation.

## Decisions And Assumptions

- **Decision:** Treat multiple memberships as an ambiguous alias request and return HTTP 409 with guidance to use the workspace-scoped endpoint. This prevents silently returning another workspace's answer.
- **Decision:** Keep the existing fallback to `ws_acme` for users with no membership so `require_member` remains the single source of the final 403 authorization decision.
- **Assumption:** The top-level alias is a compatibility convenience for single-workspace users; the frontend's explicit workspace route is the canonical multi-workspace contract.
- **Assumption:** Existing in-memory `DEMO_MEMBERSHIPS` behavior is intentional for this repository's test/demo mode.

## Data And Control Flow

1. `search_knowledge_alias` resolves `User` through `get_current_user`.
2. `get_user_workspace_id` collects all workspace IDs for that user.
3. Zero IDs retain the `ws_acme` fallback, and `require_member` rejects the request with 403.
4. One ID is passed to `require_member`, preserving current automatic selection.
5. More than one ID raises 409 before retrieval, preventing an arbitrary workspace choice.
6. Authorized requests continue through `KnowledgeSearchService.search`; no storage or frontend response shape changes.

## Commit Plan

### Commit 1: `docs(plan): record search alias review remediation`

**Purpose:** Preserve the repository-aware implementation strategy and acceptance matrix before source changes.

**Likely files:**
- Create: `docs/plans/2026-08-02-retrieval-search-review-fixes.md`

**Tasks:**
- [ ] Add this plan with scope, decisions, commit boundaries, and verification evidence.

**Verification:**
- Command/check: `git diff --check -- docs/plans/2026-08-02-retrieval-search-review-fixes.md`
- Expected evidence: plan is readable, self-contained, and contains no product-source edits.

### Commit 2: `fix(backend): reject ambiguous search alias workspace`

**Purpose:** Prevent wrong-workspace answers and lock the authorization behavior with regression tests.

**Likely files:**
- Modify: `backend/app/api/v1/routes/search.py:61-89`
- Modify: `backend/app/services/ingestion_pipeline.py:140`
- Test: `backend/tests/test_retrieval_search.py:154-186`

**Tasks:**
- [ ] Raise HTTP 409 when the alias user has multiple memberships; retain one-membership selection and no-membership 403 behavior.
- [ ] Extend the endpoint contract test with multi-membership, single-other-workspace, and revoked/no-membership cases.
- [ ] Remove the unused `category` local and trailing blank line introduced by the PR.

**Verification:**
- Command/check: `backend/.venv/Scripts/python.exe -m pytest`
- Expected evidence: all backend tests pass, including the new alias authorization cases.
- Command/check: `backend/.venv/Scripts/python.exe -m compileall -q app tests`
- Expected evidence: no Python compilation errors.
- Command/check: `git diff --check`
- Expected evidence: no whitespace errors.

## Acceptance And DoD Matrix

| Requirement | Satisfied by | Verification | Expected evidence |
|---|---|---|---|
| Multi-membership alias never silently chooses a workspace | Commit 2 | Alias contract test with two memberships | HTTP 409 with explicit workspace-selection guidance |
| Single-membership automatic selection remains compatible | Commit 2 | Alias contract test with only `ws_globex` membership | HTTP 200 and response details scoped to `ws_globex` |
| Revoked/no-membership users cannot query through a stale token | Commit 2 | Alias contract test after removing membership | HTTP 403 from `require_member` |
| Existing retrieval/category/no-evidence behavior remains intact | Commit 2 | Full backend pytest suite | All tests pass |
| No syntax or introduced whitespace errors | Commit 2 | Compileall and `git diff --check` | Both commands exit successfully |
| Unrelated frontend/environment failures are not mixed into this fix | Commit 2 | `git status`, changed-file inspection | Only planned backend files plus plan are staged |

## Failure Modes And Safeguards

- **Ambiguous memberships:** Return 409 before retrieval; do not guess or leak a workspace answer.
- **No memberships with a valid token:** Preserve the existing fallback and `require_member` 403.
- **Regression in workspace-scoped route:** Leave its dependency contract and response path untouched; full backend tests cover it.
- **Unrelated dirty files:** Stage only the plan and explicitly named backend files; inspect staged diff before each commit.

## Migration And Rollback

- No schema or persistent data migration is required.
- Roll back Commit 2 to restore the prior alias behavior; Commit 1 is documentation-only and independently reversible.
- A future session-aware active-workspace selector can replace the 409 policy without changing the workspace-scoped endpoint.

## Final Validation

- [ ] Commit the plan with explicit staging.
- [ ] Implement and test the backend fix.
- [ ] Run targeted and full backend validation.
- [ ] Inspect `git status`, staged diff, and commit contents.
- [ ] Confirm no frontend files or unrelated changes are included.
