"""Tests for ChatStorageService — both storage modes.

Two test functions:

  test_chat_storage_crud_memory    — always runs, uses in-memory fallback (no credentials needed)
  test_chat_storage_crud_supabase  — runs only when SUPABASE_URL is set, proves data survives
                                     across fresh service instances (i.e., server restarts)
"""
import uuid
import pytest
from app.core.config import settings
from app.services.chat_storage import ChatStorageService


def test_chat_storage_crud_memory():
    """In-memory fallback: identical contract to the Supabase path, no network required."""
    # Explicit test/demo dependency, never an implicit production fallback.
    storage = ChatStorageService(in_memory=True)
    # Also reset shared dicts so this test is fully isolated
    storage._sessions = {}
    storage._messages = {}

    workspace_id = "ws_test"
    user_id = "user_123"

    # Create session
    session = storage.create_session(workspace_id=workspace_id, user_id=user_id, title="Test Thread")
    assert session.workspace_id == workspace_id
    assert session.title == "Test Thread"

    # List sessions
    sessions = storage.list_sessions(workspace_id=workspace_id, user_id=user_id)
    assert len(sessions) == 1
    assert sessions[0].id == session.id

    # Add messages
    storage.add_message(
        session_id=session.id,
        workspace_id=workspace_id,
        user_id=user_id,
        role="user",
        content="Hello Kiku",
    )
    storage.add_message(
        session_id=session.id,
        workspace_id=workspace_id,
        user_id=user_id,
        role="assistant",
        content="Hi! How can I help?",
    )

    # Retrieve messages
    messages = storage.get_messages(session_id=session.id, workspace_id=workspace_id, user_id=user_id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"

    # Delete session
    storage.delete_session(session_id=session.id, workspace_id=workspace_id, user_id=user_id)
    assert len(storage.list_sessions(workspace_id=workspace_id, user_id=user_id)) == 0


@pytest.mark.skipif(
    not settings.supabase_url or not settings.supabase_service_role_key,
    reason="Supabase service role key not configured — set SUPABASE_SERVICE_ROLE_KEY to run",
)
def test_chat_storage_crud_supabase():
    """Supabase integration: proves data survives a fresh service instance (server restart simulation)."""
    # Use a unique workspace prefix so test data never collides with real data
    workspace_id = f"ws_test_{uuid.uuid4().hex[:8]}"
    user_id = "user_test_integration"
    session_id: str | None = None

    try:
        svc_a = ChatStorageService()
        assert svc_a.client is not None, "Expected Supabase client when SUPABASE_URL is set"

        # --- CREATE ---
        session = svc_a.create_session(workspace_id=workspace_id, user_id=user_id, title="Integration Test")
        session_id = session.id
        assert session.id  # PostgreSQL generated a UUID
        assert session.workspace_id == workspace_id
        assert session.title == "Integration Test"

        # --- PERSIST: read back from a brand-new service instance ---
        svc_b = ChatStorageService()
        sessions = svc_b.list_sessions(workspace_id=workspace_id, user_id=user_id)
        assert len(sessions) == 1
        assert sessions[0].id == session_id

        # --- ADD MESSAGES ---
        msg_user = svc_a.add_message(
            session_id=session_id,
            workspace_id=workspace_id,
            user_id=user_id,
            role="user",
            content="Hello from integration test",
        )
        assert msg_user.id  # DB-generated UUID
        assert msg_user.role == "user"

        msg_asst = svc_a.add_message(
            session_id=session_id,
            workspace_id=workspace_id,
            user_id=user_id,
            role="assistant",
            content="Integration reply",
            citations_json=[{"source_id": "src_1", "snippet": "test snippet"}],
        )
        assert msg_asst.citations_json == [{"source_id": "src_1", "snippet": "test snippet"}]

        # --- AUTO-TITLE: first user message should have updated session title ---
        svc_c = ChatStorageService()
        fetched_session = svc_c.get_session(session_id=session_id, workspace_id=workspace_id, user_id=user_id)
        assert fetched_session is not None
        assert fetched_session.title == "Hello from integration test"

        # --- GET MESSAGES persists across instances ---
        messages = svc_c.get_messages(session_id=session_id, workspace_id=workspace_id, user_id=user_id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

        # --- DELETE (cascade removes messages + citations automatically) ---
        deleted = svc_a.delete_session(session_id=session_id, workspace_id=workspace_id, user_id=user_id)
        assert deleted is True
        session_id = None  # mark as cleaned up

        # Confirm gone
        assert svc_b.get_session(session_id=session.id, workspace_id=workspace_id, user_id=user_id) is None
        assert svc_b.list_sessions(workspace_id=workspace_id, user_id=user_id) == []

    finally:
        # Safety cleanup — runs even if an assertion fails mid-test
        if session_id:
            try:
                ChatStorageService().delete_session(
                    session_id=session_id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                )
            except Exception:
                pass
