# SSE Chat Session Thread Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fullstack, production-grade SSE Chat Session Thread system (ChatGPT/Gemini style) connecting backend Opencode LLM synthesis (`deepseek-v4-flash-free`) with a responsive SvelteKit frontend supporting persistent chat history, live token streaming, typing animation (`▊`), grounded citation accordions, and sidebar thread management.

**Architecture:** Extend backend with `ChatStorageService` (persisting sessions and messages) and `stream_search()` in `KnowledgeSearchService` yielding SSE events (`metadata`, `delta`, `done`, `error`). Build FastAPI router `/api/v1/workspaces/{workspace_id}/chat/sessions` returning `StreamingResponse`. Build Svelte 5 frontend with `chatApi.ts` SSE `fetch` stream reader, `ChatThread.svelte` chat interface, and thread navigation in `Sidebar.svelte`.

**Tech Stack:** Python 3.11, FastAPI, `httpx`, `pytest`, TypeScript, Svelte 5, Vite, Vitest.

## Global Constraints

- Backend test runner: `uv run pytest`
- Frontend test runner: `bun run test` or `npm run test`
- Opencode API endpoint: `https://opencode.ai/zen/v1/chat/completions` with model `deepseek-v4-flash-free`
- SSE Content Type: `text/event-stream` with UTF-8 encoding

---

### Task 1: Backend Domain Models & Chat Storage Service

**Files:**
- Create: `backend/app/domain/chat.py`
- Create: `backend/app/services/chat_storage.py`
- Create: `backend/tests/test_chat_storage.py`

**Interfaces:**
- Consumes: `app.domain.knowledge.CitationDetail`, `app.domain.knowledge.KnowledgeSource`
- Produces: `ChatSession`, `ChatMessage`, `ChatStorageService`

- [ ] **Step 1: Write failing test for ChatStorageService**

```python
# backend/tests/test_chat_storage.py
import pytest
from app.domain.chat import ChatSession, ChatMessage
from app.services.chat_storage import ChatStorageService

def test_chat_storage_crud():
    storage = ChatStorageService()
    workspace_id = "ws_test"
    user_id = "user_123"
    
    # Create session
    session = storage.create_session(workspace_id=workspace_id, user_id=user_id, title="Test Thread")
    assert session.workspace_id == workspace_id
    assert session.title == "Test Thread"
    
    # List sessions
    sessions = storage.list_sessions(workspace_id=workspace_id)
    assert len(sessions) == 1
    assert sessions[0].id == session.id
    
    # Add messages
    user_msg = storage.add_message(session_id=session.id, workspace_id=workspace_id, role="user", content="Hello Kiku")
    asst_msg = storage.add_message(session_id=session.id, workspace_id=workspace_id, role="assistant", content="Hi! How can I help?")
    
    # Retrieve messages
    messages = storage.get_messages(session_id=session.id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    
    # Delete session
    storage.delete_session(session_id=session.id)
    assert len(storage.list_sessions(workspace_id=workspace_id)) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_chat_storage.py`  
Expected: FAIL with "ModuleNotFoundError: No module named 'app.domain.chat'"

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/domain/chat.py`:
```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any

@dataclass
class ChatMessage:
    id: str
    session_id: str
    workspace_id: str
    role: str  # "user" | "assistant"
    content: str
    citations_json: list[dict[str, Any]] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ChatSession:
    id: str
    workspace_id: str
    user_id: str
    title: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

Create `backend/app/services/chat_storage.py`:
```python
import uuid
from datetime import datetime, timezone
from app.domain.chat import ChatMessage, ChatSession

class ChatStorageService:
    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._messages: dict[str, list[ChatMessage]] = {}

    def create_session(self, workspace_id: str, user_id: str, title: str = "New Chat") -> ChatSession:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        session = ChatSession(id=session_id, workspace_id=workspace_id, user_id=user_id, title=title, created_at=now, updated_at=now)
        self._sessions[session_id] = session
        self._messages[session_id] = []
        return session

    def list_sessions(self, workspace_id: str) -> list[ChatSession]:
        return [s for s in self._sessions.values() if s.workspace_id == workspace_id]

    def get_session(self, session_id: str) -> ChatSession | None:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._messages.pop(session_id, None)
            return True
        return False

    def add_message(self, session_id: str, workspace_id: str, role: str, content: str, citations_json: list[dict] | None = None) -> ChatMessage:
        msg_id = str(uuid.uuid4())
        msg = ChatMessage(id=msg_id, session_id=session_id, workspace_id=workspace_id, role=role, content=content, citations_json=citations_json)
        if session_id not in self._messages:
            self._messages[session_id] = []
        self._messages[session_id].append(msg)
        if session_id in self._sessions:
            self._sessions[session_id].updated_at = datetime.now(timezone.utc)
            if len(self._messages[session_id]) == 1 and role == "user":
                self._sessions[session_id].title = content[:30] + ("..." if len(content) > 30 else "")
        return msg

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        return self._messages.get(session_id, [])

chat_storage_service = ChatStorageService()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_chat_storage.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/chat.py backend/app/services/chat_storage.py backend/tests/test_chat_storage.py
git commit -m "feat(backend): add ChatSession, ChatMessage domains and ChatStorageService"
```

---

### Task 2: Backend Streaming Knowledge Search Service

**Files:**
- Modify: `backend/app/services/knowledge_search.py`
- Create: `backend/tests/test_streaming_search.py`

**Interfaces:**
- Consumes: `KnowledgeSearchService`, `ChatStorageService`
- Produces: `KnowledgeSearchService.stream_search(workspace_id, query, session_id)` yielding SSE string chunks

- [ ] **Step 1: Write failing test for stream_search**

```python
# backend/tests/test_streaming_search.py
import pytest
import json
from app.services.knowledge_search import KnowledgeSearchService
from app.services.chat_storage import chat_storage_service

@pytest.mark.asyncio
async def test_stream_search_yields_events():
    service = KnowledgeSearchService()
    session = chat_storage_service.create_session("ws_acme", "user_1", "Stream Test")
    
    events = []
    async for chunk in service.stream_search("ws_acme", "What is Kiku?", session_id=session.id):
        events.append(chunk)
        
    assert len(events) >= 3
    assert "event: metadata" in events[0]
    assert "event: done" in events[-1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_streaming_search.py`  
Expected: FAIL with "AttributeError: 'KnowledgeSearchService' object has no attribute 'stream_search'"

- [ ] **Step 3: Implement stream_search in KnowledgeSearchService**

Add `stream_search` method to `KnowledgeSearchService` in `backend/app/services/knowledge_search.py`:

```python
    async def stream_search(
        self, workspace_id: str, query: str, session_id: str | None = None, category: str | None = None
    ):
        """Async generator streaming SSE events (metadata, delta, done, error)."""
        import json
        from app.services.chat_storage import chat_storage_service

        normalized_query = query.strip() or "General inquiry"
        matched_chunks = self.storage.search_chunks(
            workspace_id=workspace_id, query=normalized_query, category=category, top_k=5
        )

        citations_payload = []
        if matched_chunks:
            top_chunk = matched_chunks[0]
            source_doc = self.storage.get_source(workspace_id, top_chunk["source_id"])
            source_title = source_doc.title if source_doc else f"Source '{top_chunk['source_id']}'"
            citations_payload.append({
                "source_id": top_chunk["source_id"],
                "title": source_title,
                "version": top_chunk["source_version"],
                "location": top_chunk["location"],
                "snippet": top_chunk["text"][:300],
            })

        # Yield event: metadata
        metadata_data = json.dumps({"citations": citations_payload, "query": normalized_query})
        yield f"event: metadata\ndata: {metadata_data}\n\n"

        # Record user message if session_id provided
        if session_id:
            chat_storage_service.add_message(session_id, workspace_id, "user", normalized_query)

        # Call Opencode LLM synthesis stream (or fallback)
        synthesized_text = ""
        try:
            endpoint = f"{self.api_base_url}/chat/completions"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            context_parts = [
                f"[{idx+1}] Source: {c.get('metadata', {}).get('source_title', c.get('source_id'))} ({c.get('location')})\n{c.get('text')}"
                for idx, c in enumerate(matched_chunks)
            ]
            context_str = "\n\n".join(context_parts) if context_parts else "No document chunks available."

            history_parts = []
            if session_id:
                past_msgs = chat_storage_service.get_messages(session_id)[-6:-1]
                for m in past_msgs:
                    history_parts.append(f"{m.role.capitalize()}: {m.content}")
            history_str = "\n".join(history_parts)

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a precise knowledge synthesis assistant. Answer strictly based on provided context.",
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context_str}\n\nHistory:\n{history_str}\n\nQuestion: {query}",
                    },
                ],
                "temperature": 0.2,
                "stream": True,
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk_obj = json.loads(data_str)
                                    delta = chunk_obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if delta:
                                        synthesized_text += delta
                                        delta_data = json.dumps({"content": delta})
                                        yield f"event: delta\ndata: {delta_data}\n\n"
                                except Exception:
                                    pass
                    else:
                        fallback = f"Based on knowledge sources: {matched_chunks[0]['text'][:200]}" if matched_chunks else "No relevant information found."
                        synthesized_text = fallback
                        delta_data = json.dumps({"content": fallback})
                        yield f"event: delta\ndata: {delta_data}\n\n"
        except Exception:
            fallback = f"Based on knowledge sources: {matched_chunks[0]['text'][:200]}" if matched_chunks else "No relevant information found."
            synthesized_text = fallback
            delta_data = json.dumps({"content": fallback})
            yield f"event: delta\ndata: {delta_data}\n\n"

        # Record assistant message
        if session_id and synthesized_text:
            chat_storage_service.add_message(session_id, workspace_id, "assistant", synthesized_text, citations_json=citations_payload)

        done_data = json.dumps({"status": "completed"})
        yield f"event: done\ndata: {done_data}\n\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_streaming_search.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/knowledge_search.py backend/tests/test_streaming_search.py
git commit -m "feat(backend): add stream_search method to KnowledgeSearchService for SSE streaming"
```

---

### Task 3: Backend FastAPI Chat SSE Endpoints & Router

**Files:**
- Create: `backend/app/api/v1/routes/chat.py`
- Create: `backend/tests/test_chat_routes.py`
- Modify: `backend/app/main.py:1-40`

**Interfaces:**
- Consumes: `ChatStorageService`, `KnowledgeSearchService`
- Produces: `/api/v1/workspaces/{workspace_id}/chat/sessions` endpoints

- [ ] **Step 1: Write failing test for chat routes**

```python
# backend/tests/test_chat_routes.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_session_crud_routes():
    # Create session
    resp = client.post("/api/v1/workspaces/ws_acme/chat/sessions", json={"title": "My Chat"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "My Chat"
    session_id = data["id"]
    
    # List sessions
    list_resp = client.get("/api/v1/workspaces/ws_acme/chat/sessions")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1
    
    # Delete session
    del_resp = client.delete(f"/api/v1/workspaces/ws_acme/chat/sessions/{session_id}")
    assert del_resp.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_chat_routes.py`  
Expected: FAIL 404

- [ ] **Step 3: Implement chat routes and register in main.py**

Create `backend/app/api/v1/routes/chat.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import AuthenticatedMemberContext, require_member
from app.services.chat_storage import chat_storage_service, ChatStorageService
from app.services.knowledge_search import KnowledgeSearchService

router = APIRouter(prefix="/workspaces/{workspace_id}/chat", tags=["chat"])

class CreateSessionRequest(BaseModel):
    title: str = "New Chat"

class StreamMessageRequest(BaseModel):
    query: str
    category: str | None = None

@router.post("/sessions")
async def create_session(
    workspace_id: str,
    req: CreateSessionRequest,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    session = chat_storage_service.create_session(workspace_id, ctx.membership.user_id, req.title)
    return session

@router.get("/sessions")
async def list_sessions(
    workspace_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    return chat_storage_service.list_sessions(workspace_id)

@router.get("/sessions/{session_id}/messages")
async def get_messages(
    workspace_id: str,
    session_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    return chat_storage_service.get_messages(session_id)

@router.delete("/sessions/{session_id}")
async def delete_session(
    workspace_id: str,
    session_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    success = chat_storage_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}

@router.post("/sessions/{session_id}/stream")
async def stream_message(
    workspace_id: str,
    session_id: str,
    req: StreamMessageRequest,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    search_service = KnowledgeSearchService()
    generator = search_service.stream_search(
        workspace_id=workspace_id, query=req.query, session_id=session_id, category=req.category
    )
    return StreamingResponse(generator, media_type="text/event-stream")
```

Register router in `backend/app/main.py`:
Add `from app.api.v1.routes.chat import router as chat_router` and `app.include_router(chat_router, prefix="/api/v1")`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_chat_routes.py`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/routes/chat.py backend/app/main.py backend/tests/test_chat_routes.py
git commit -m "feat(backend): register FastAPI SSE chat session endpoints and streaming route"
```

---

### Task 4: Frontend SSE Client API & Types

**Files:**
- Create: `frontend/src/lib/features/chat/types.ts`
- Create: `frontend/src/lib/features/chat/chatApi.ts`

**Interfaces:**
- Consumes: Backend `/api/v1/workspaces/{workspace_id}/chat`
- Produces: `streamChatMessage`, `createChatSession`, `listChatSessions`, `deleteChatSession`

- [ ] **Step 1: Create chat types in frontend**

Create `frontend/src/lib/features/chat/types.ts`:
```typescript
export interface ChatCitation {
	source_id: string;
	title: string;
	version: number;
	location: string;
	snippet: string;
}

export interface ChatMessage {
	id: string;
	session_id: string;
	role: 'user' | 'assistant';
	content: string;
	citations?: ChatCitation[];
	created_at: string;
}

export interface ChatSession {
	id: string;
	workspace_id: string;
	user_id: string;
	title: string;
	created_at: string;
	updated_at: string;
}
```

- [ ] **Step 2: Create chat API service with fetch SSE reader**

Create `frontend/src/lib/features/chat/chatApi.ts`:
```typescript
import type { ChatSession, ChatMessage, ChatCitation } from './types';

const API_BASE = '/api/v1/workspaces/ws_acme/chat';

export async function createSession(title: str = 'New Chat'): Promise<ChatSession> {
	const res = await fetch(`${API_BASE}/sessions`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ title })
	});
	return res.json();
}

export async function listSessions(): Promise<ChatSession[]> {
	const res = await fetch(`${API_BASE}/sessions`);
	return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
	await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function getMessages(sessionId: string): Promise<ChatMessage[]> {
	const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
	return res.json();
}

export async function streamChatMessage(
	sessionId: string,
	query: string,
	category: string,
	onMetadata: (citations: ChatCitation[]) => void,
	onDelta: (content: string) => void,
	onDone: () => void,
	signal?: AbortSignal
): Promise<void> {
	const response = await fetch(`${API_BASE}/sessions/${sessionId}/stream`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ query, category }),
		signal
	});

	if (!response.body) return;
	const reader = response.body.getReader();
	const decoder = new TextDecoder('utf-8');
	let buffer = '';

	while (true) {
		const { done, value } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true });
		const parts = buffer.split('\n\n');
		buffer = parts.pop() || '';

		for (const part of parts) {
			const lines = part.split('\n');
			let eventType = '';
			let dataStr = '';
			for (const line of lines) {
				if (line.startsWith('event: ')) eventType = line.slice(7).strip() if typeof line.slice === 'function' else line.substring(7).trim();
				else if (line.startsWith('data: ')) dataStr = line.substring(6).trim();
			}
			if (eventType === 'metadata') {
				try {
					const meta = JSON.parse(dataStr);
					onMetadata(meta.citations || []);
				} catch {}
			} else if (eventType === 'delta') {
				try {
					const delta = JSON.parse(dataStr);
					onDelta(delta.content || '');
				} catch {}
			} else if (eventType === 'done') {
				onDone();
			}
		}
	}
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/features/chat/types.ts frontend/src/lib/features/chat/chatApi.ts
git commit -m "feat(frontend): add chat session TypeScript types and SSE streaming API client"
```

---

### Task 5: Frontend ChatGPT-Style Chat Thread Component

**Files:**
- Create: `frontend/src/lib/features/chat/ChatThread.svelte`
- Modify: `frontend/src/lib/features/knowledge/KnowledgeHome.svelte`

**Interfaces:**
- Consumes: `streamChatMessage`, `createSession`, `listSessions`
- Produces: ChatGPT/Gemini conversational streaming thread UI

- [ ] **Step 1: Create ChatThread.svelte component**

Create `frontend/src/lib/features/chat/ChatThread.svelte`:
```svelte
<script lang="ts">
	import { onMount } from 'svelte';
	import type { ChatMessage, ChatCitation, ChatSession } from './types';
	import { streamChatMessage, createSession, getMessages } from './chatApi';
	import KikuMascot from '$lib/components/KikuMascot.svelte';

	let { activeSession = $bindable<ChatSession | null>(null) } = $props();

	let messages = $state<ChatMessage[]>([]);
	let query = $state('');
	let isStreaming = $state(false);
	let abortController: AbortController | null = null;
	let chatContainer: HTMLDivElement;

	$effect(() => {
		if (activeSession) {
			loadMessages(activeSession.id);
		}
	});

	async function loadMessages(sessionId: string) {
		try {
			messages = await getMessages(sessionId);
		} catch {
			messages = [];
		}
	}

	async function handleSend() {
		if (!query.trim() || isStreaming) return;
		const userText = query.trim();
		query = '';

		if (!activeSession) {
			activeSession = await createSession(userText.slice(0, 30));
		}

		const userMsg: ChatMessage = {
			id: String(Date.now()),
			session_id: activeSession.id,
			role: 'user',
			content: userText,
			created_at: new Date().toISOString()
		};

		const assistantMsg: ChatMessage = {
			id: String(Date.now() + 1),
			session_id: activeSession.id,
			role: 'assistant',
			content: '',
			citations: [],
			created_at: new Date().toISOString()
		};

		messages = [...messages, userMsg, assistantMsg];
		isStreaming = true;
		abortController = new AbortController();

		try {
			await streamChatMessage(
				activeSession.id,
				userText,
				'All',
				(citations) => {
					assistantMsg.citations = citations;
					messages = [...messages];
				},
				(delta) => {
					assistantMsg.content += delta;
					messages = [...messages];
					scrollToBottom();
				},
				() => {
					isStreaming = false;
				},
				abortController.signal
			);
		} catch {
			isStreaming = false;
		}
	}

	function handleStop() {
		if (abortController) {
			abortController.abort();
			isStreaming = false;
		}
	}

	function scrollToBottom() {
		if (chatContainer) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
		}
	}
</script>

<div class="chat-thread-container" bind:this={chatContainer}>
	{#if messages.length === 0}
		<div class="empty-state">
			<KikuMascot className="mascot-large" />
			<h2>Hi there! How can I help today? 👋</h2>
			<p>Ask anything about your workspace sources and documents.</p>
		</div>
	{:else}
		<div class="messages-list">
			{#each messages as msg}
				<div class="message-row {msg.role}">
					{#if msg.role === 'assistant'}
						<div class="avatar"><KikuMascot className="avatar-art" /></div>
					{/if}
					<div class="bubble">
						<p>{msg.content}{#if isStreaming && msg.role === 'assistant' && msg.id === messages[messages.length - 1].id}<span class="cursor">▊</span>{/if}</p>
						{#if msg.citations && msg.citations.length > 0}
							<details class="citations-accordion">
								<summary>📚 Grounded Sources ({msg.citations.length})</summary>
								{#each msg.citations as cite}
									<div class="cite-card">
										<strong>{cite.title}</strong> — {cite.location}
										<p class="snippet">"{cite.snippet}"</p>
									</div>
								{/each}
							</details>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}

	<div class="input-bar-container">
		<form onsubmit={(e) => { e.preventDefault(); handleSend(); }}>
			<input bind:value={query} placeholder="Message Kiku..." disabled={isStreaming} />
			{#if isStreaming}
				<button type="button" class="stop-btn" onclick={handleStop}>Stop</button>
			{:else}
				<button type="submit" class="send-btn">Send</button>
			{/if}
		</form>
	</div>
</div>

<style>
	.chat-thread-container { display: flex; flex-direction: column; height: 100%; overflow-y: auto; padding: 20px; }
	.empty-state { text-align: center; margin: auto; }
	.messages-list { display: flex; flex-direction: column; gap: 16px; margin-bottom: 80px; }
	.message-row { display: flex; gap: 12px; max-width: 80%; }
	.message-row.user { align-self: flex-end; flex-direction: row-reverse; }
	.message-row.user .bubble { background: #6366f1; color: white; border-radius: 16px 16px 2px 16px; }
	.message-row.assistant .bubble { background: #f3f4f6; color: #1f2937; border-radius: 16px 16px 16px 2px; }
	.bubble { padding: 12px 16px; line-height: 1.5; font-size: 14px; }
	.cursor { display: inline-block; animation: blink 1s infinite; color: #6366f1; }
	@keyframes blink { 50% { opacity: 0; } }
	.citations-accordion { margin-top: 8px; font-size: 12px; }
	.cite-card { background: white; padding: 8px; border-radius: 6px; margin-top: 4px; border: 1px solid #e5e7eb; }
	.input-bar-container { position: sticky; bottom: 0; background: white; padding: 12px 0; }
	form { display: flex; gap: 8px; }
	input { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #d1d5db; }
	button { padding: 12px 20px; border-radius: 8px; border: none; cursor: pointer; }
	.send-btn { background: #6366f1; color: white; }
	.stop-btn { background: #ef4444; color: white; }
</style>
```

- [ ] **Step 2: Modify KnowledgeHome.svelte to embed ChatThread**

Update `frontend/src/lib/features/knowledge/KnowledgeHome.svelte` to import `ChatThread.svelte` as the primary interface.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/features/chat/ChatThread.svelte frontend/src/lib/features/knowledge/KnowledgeHome.svelte
git commit -m "feat(frontend): add ChatGPT/Gemini style ChatThread component with live token streaming & citations"
```

---

### Task 6: Frontend Sidebar Chat History Thread Integration

**Files:**
- Modify: `frontend/src/lib/components/Sidebar.svelte`

**Interfaces:**
- Consumes: `listSessions`, `createSession`, `deleteSession`
- Produces: Interactive sidebar chat thread selection list

- [ ] **Step 1: Add thread history section to Sidebar.svelte**

Update `frontend/src/lib/components/Sidebar.svelte`:
1. Import `listSessions`, `createSession`, `deleteSession` from `$lib/features/chat/chatApi`.
2. Add a **Chats** section in the sidebar with a "+ New Chat" button.
3. Render thread titles with click handlers to switch active session.
4. Render trash icon to delete threads.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/components/Sidebar.svelte
git commit -m "feat(frontend): integrate chat sessions history list & creation in Sidebar"
```

---

## Verification Plan

### Automated Tests
- Run backend unit & endpoint tests:
  `uv run pytest backend/tests/test_chat_storage.py backend/tests/test_streaming_search.py backend/tests/test_chat_routes.py`

### Manual Verification
- Start FastAPI dev server and Vite frontend dev server.
- Click "+ New Chat" in sidebar.
- Type a query ("What is Kiku's refund policy?") and submit.
- Verify live token streaming with blinking cursor (`▊`).
- Expand **Grounded Sources** accordion to verify citations.
- Click "Stop" button mid-generation to verify abort functionality.
