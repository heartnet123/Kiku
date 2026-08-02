import pytest
import json
from app.services.knowledge_search import KnowledgeSearchService
from app.services.chat_storage import chat_storage_service

@pytest.mark.anyio
async def test_stream_search_yields_events():
    service = KnowledgeSearchService()
    session = chat_storage_service.create_session("ws_acme", "user_1", "Stream Test")
    
    events = []
    async for chunk in service.stream_search("ws_acme", "What is Kiku?", session_id=session.id):
        events.append(chunk)
        
    assert len(events) >= 3
    assert any("event: metadata" in e for e in events)
    assert "event: done" in events[-1]
