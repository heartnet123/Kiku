# Design Specification: SSE Chat Session Thread (Fullstack ChatGPT/Gemini Grade)

**Date**: 2026-08-02  
**Branch**: `feature/sse-chat-session-thread`  
**Target Components**: Backend FastAPI SSE Router, KnowledgeSearchService Opencode LLM Streaming, Supabase Chat Storage, SvelteKit ChatGPT-style Chat UI & SSE Client Service.

---

## 1. Executive Summary

This design specification details the integration of Opencode LLM synthesis (`deepseek-v4-flash-free` via Opencode API) with a fullstack-grade, real-time Server-Sent Events (SSE) chat session system. It builds upon recent backend commits (`dfe0739`, `39ab070`, `721baf2`) to provide a multi-turn, grounded RAG chat experience with persistent session threads, streaming text generation with typing animation (`▊`), grounded citation accordions, and full session CRUD in the frontend sidebar.

---

## 2. Architecture & Data Flow

```text
[ Frontend: Svelte 5 / SvelteKit ]
  │
  ├─ Sidebar.svelte (List, Create, Select, Delete Threads)
  ├─ ChatThread.svelte (Stream tokens, Citation Accordion, Auto-scroll)
  │
  └─ (SSE Stream via POST fetch + ReadableStream reader)
        │
        ▼
[ Backend: FastAPI (`app/api/v1/routes/chat.py`) ]
  │
  ├─ ChatService (`app/services/chat_service.py`)
  ├─ ChatStorage (`app/services/chat_storage.py`)
  └─ KnowledgeSearchService (`app/services/knowledge_search.py`)
        │
        ▼ (RAG Vector Chunks + Recent History)
[ Opencode LLM API (`deepseek-v4-flash-free`) ] (SSE stream=True)
```

---

## 3. Database Schema Extension (Supabase Data Dictionary)

The existing Supabase Data Dictionary (`workspaces`, `workspace_members`, `documents`, `document_versions`, `document_chunks`, `citations`) is extended with two new tables:

### 3.1 `chat_sessions`
| Column | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | ✅ | Primary Key |
| `workspace_id` | `uuid` | ✅ | Foreign Key → `workspaces.id` |
| `user_id` | `uuid` | ✅ | Foreign Key → `auth.users.id` |
| `title` | `text` | ✅ | Thread title (auto-generated from 1st user query) |
| `metadata` | `jsonb` | ❌ | Custom thread metadata |
| `created_at` | `timestamptz` | ✅ | Creation timestamp |
| `updated_at` | `timestamptz` | ✅ | Last update timestamp |

### 3.2 `chat_messages`
| Column | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | ✅ | Primary Key |
| `session_id` | `uuid` | ✅ | Foreign Key → `chat_sessions.id` (ON DELETE CASCADE) |
| `workspace_id` | `uuid` | ✅ | Foreign Key → `workspaces.id` |
| `role` | `text` | ✅ | Role: `user` or `assistant` |
| `content` | `text` | ✅ | Text content of the message |
| `citations_json` | `jsonb` | ❌ | Citation details & source metadata array |
| `created_at` | `timestamptz` | ✅ | Message timestamp |

---

## 4. Backend API Endpoints & SSE Streaming Protocol

### 4.1 REST API Routes (`/api/v1/workspaces/{workspace_id}/chat`)
- `POST /sessions`: Create a new chat session.
- `GET /sessions`: List chat sessions for workspace.
- `GET /sessions/{session_id}`: Get chat session details & message history.
- `DELETE /sessions/{session_id}`: Delete a chat session.
- `POST /sessions/{session_id}/stream`: Stream answer to user message via SSE.

### 4.2 SSE Event Payload Format
The stream endpoint emits typed JSON events over `text/event-stream`:

1. **`event: metadata`** (Emitted immediately after vector retrieval):
   ```json
   {
     "citations": [
       {
         "source_id": "doc_123",
         "title": "Kiku Refund Policy.pdf",
         "version": 1,
         "location": "Page 2, Section 3",
         "snippet": "Refunds are processed within 14 business days..."
       }
     ],
     "sources": [...]
   }
   ```
2. **`event: delta`** (Emitted chunk-by-chunk from Opencode LLM API):
   ```json
   {
     "content": "To request a refund, "
   }
   ```
3. **`event: done`** (Emitted when synthesis completes):
   ```json
   {
     "message_id": "msg_789",
     "status": "completed"
   }
   ```
4. **`event: error`** (Emitted if retrieval or LLM connection fails):
   ```json
   {
     "error": "Failed to connect to synthesis engine"
   }
   ```

---

## 5. Multi-Turn RAG Context Assembly

When a user submits a query to an existing session:
1. `KnowledgeSearchService` retrieves the top 5 matching `document_chunks` for `workspace_id`.
2. `ChatStorageService` fetches the last 6 messages in `session_id`.
3. System prompt is constructed:
   - System directive: "You are a precise knowledge synthesis assistant. Answer strictly based on context. If context is insufficient, state clearly that evidence was not found."
   - Context block: Formatted passages with source title & page/section locations.
   - Dialogue turns: Formatted prior user/assistant turns.
   - User query: New user prompt.

---

## 6. Frontend UI Components (ChatGPT/Gemini Grade)

### 6.1 `Sidebar.svelte`
- Displays **Chat Threads** section.
- **"+ New Chat"** action button.
- List of active threads with selection state and delete button.

### 6.2 `ChatThread.svelte` & `AnswerCard.svelte`
- Full-height chat container with scrollable message stream.
- User messages rendered as distinct clean cards.
- Assistant messages streaming text real-time with blinking cursor (`▊`).
- Expandable grounded citation drawer/accordion displaying source titles, page numbers, snippets, and version badges.
- Bottom sticky prompt input with auto-grow textarea, Send button, and **Stop Generating** button (`AbortController`).

### 6.3 `chatApi.ts`
- Custom `fetch` SSE reader parsing `ReadableStream` line by line.
- Native error handling & automatic fallback message on connection failure.

---

## 7. Verification & Testing Plan

1. **Backend Tests**:
   - Unit tests for `ChatStorageService` (session creation, message history, deletion).
   - Integration tests for `/api/v1/workspaces/{workspace_id}/chat/sessions` endpoints.
   - Mock tests for `stream_search()` SSE response generator using `httpx` async mocks.
2. **Frontend Verification**:
   - Verify creation of new chat session.
   - Verify live token streaming and typing animation.
   - Verify citation drawer rendering.
   - Verify thread deletion and switching.
