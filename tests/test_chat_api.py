"""Tests for the Research RAG chat API endpoints."""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from app.main import app
from app.core.database import Base, engine, SessionLocal, get_db
from app.models.chat import ChatSession, ChatMessage
from app.services.research_rag_service import RAGAgent, reset_rag_agent


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    # Create a test user for foreign key compliance
    from app.models.user import User
    db = SessionLocal()
    existing = db.query(User).filter(User.firebase_uid == "test-user-123").first()
    if not existing:
        user = User(firebase_uid="test-user-123", email="test@example.com")
        db.add(user)
        db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_agent():
    reset_rag_agent()
    yield


@pytest.fixture
def override_deps():
    """Override FastAPI dependencies for testing."""
    # Override auth to return a test user
    async def mock_get_current_user():
        return {"uid": "test-user-123", "email": "test@example.com"}

    app.dependency_overrides.clear()
    from app.core.security import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


class TestChatSessionsAPI:
    def test_create_session(self, override_deps):
        response = client.post("/api/v1/chat/sessions")
        assert response.status_code == 200, response.text
        data = response.json()
        assert "id" in data
        assert data["title"] == "New Conversation"

    def test_list_sessions(self, override_deps):
        client.post("/api/v1/chat/sessions")
        response = client.get("/api/v1/chat/sessions")
        assert response.status_code == 200, response.text
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_session_not_found(self, override_deps):
        response = client.get("/api/v1/chat/sessions/nonexistent-id")
        assert response.status_code == 404

    def test_delete_session(self, override_deps):
        create_resp = client.post("/api/v1/chat/sessions")
        session_id = create_resp.json()["id"]
        response = client.delete(f"/api/v1/chat/sessions/{session_id}")
        assert response.status_code == 200
        get_resp = client.get(f"/api/v1/chat/sessions/{session_id}")
        assert get_resp.status_code == 404

    def test_delete_session_not_found(self, override_deps):
        response = client.delete("/api/v1/chat/sessions/nonexistent")
        assert response.status_code == 404


class TestChatMessagesAPI:
    @pytest.mark.asyncio
    async def test_send_message_new_session(self, override_deps):
        agent = RAGAgent()
        agent.answer_question = AsyncMock(return_value=("Test answer", []))
        with patch("app.api.chat.get_rag_agent", return_value=agent):
            response = client.post("/api/v1/chat/messages", json={
                "message": "What is the consensus on climate change?",
            })
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["role"] == "assistant"
        assert data["session_id"] is not None
        agent.answer_question.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_existing_session(self, override_deps):
        create_resp = client.post("/api/v1/chat/sessions")
        session_id = create_resp.json()["id"]

        agent = RAGAgent()
        agent.answer_question = AsyncMock(return_value=("Test answer", []))
        with patch("app.api.chat.get_rag_agent", return_value=agent):
            response = client.post("/api/v1/chat/messages", json={
                "session_id": session_id,
                "message": "Show me contradictions",
            })
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["session_id"] == session_id

    def test_send_message_invalid_session(self, override_deps):
        response = client.post("/api/v1/chat/messages", json={
            "session_id": "nonexistent",
            "message": "Hello",
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_send_message_creates_session_with_title(self, override_deps):
        agent = RAGAgent()
        agent.answer_question = AsyncMock(return_value=("Test answer", []))
        long_message = "This is a very long research question that should be truncated"
        with patch("app.api.chat.get_rag_agent", return_value=agent):
            response = client.post("/api/v1/chat/messages", json={
                "message": long_message,
            })
        assert response.status_code == 200, response.text
        session_id = response.json()["session_id"]
        get_resp = client.get(f"/api/v1/chat/sessions/{session_id}")
        assert get_resp.status_code == 200
        assert long_message in get_resp.json()["title"]

    @pytest.mark.asyncio
    async def test_get_session_with_messages(self, override_deps):
        agent = RAGAgent()
        agent.answer_question = AsyncMock(return_value=("Test answer", []))
        with patch("app.api.chat.get_rag_agent", return_value=agent):
            send_resp = client.post("/api/v1/chat/messages", json={
                "message": "What contradictions exist?",
            })
        session_id = send_resp.json()["session_id"]
        get_resp = client.get(f"/api/v1/chat/sessions/{session_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"


class TestRAGAgentWithSources:
    @pytest.mark.asyncio
    async def test_send_message_with_sources(self, override_deps):
        agent = RAGAgent()
        from app.schemas.chat import Source
        agent.answer_question = AsyncMock(return_value=(
            "Found supporting evidence for your claim.",
            [
                Source(doc_id="doc1", filename="paper1.pdf", section="Results",
                       text="The results confirm the hypothesis", confidence=0.85,
                       relation_type="SUPPORT"),
                Source(doc_id="doc2", filename="paper2.pdf", section="Discussion",
                       text="These findings contradict prior work", confidence=0.72,
                       relation_type="CONTRADICT"),
            ],
        ))
        with patch("app.api.chat.get_rag_agent", return_value=agent):
            response = client.post("/api/v1/chat/messages", json={
                "message": "Find evidence for my claim",
            })
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["sources"]) == 2
        assert data["sources"][0]["doc_id"] == "doc1"
        assert data["sources"][1]["relation_type"] == "CONTRADICT"
