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
