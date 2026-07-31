import os
from datetime import UTC
from unittest.mock import patch

import pytest

os.environ["GEMINI_API_KEY"] = "test-key"


@pytest.fixture(autouse=True)
def reset_agent():
    from app.services.research_rag_service import reset_rag_agent

    reset_rag_agent()
    yield


class TestIntentClassification:
    def _make_agent(self):
        from app.services.research_rag_service import RAGAgent

        return RAGAgent()

    def test_rule_based_contradictions(self):
        agent = self._make_agent()
        intent = agent._rule_based_intent("What contradictions exist in my graph?")
        assert intent == "graph_contradictions"

    def test_rule_based_consensus(self):
        agent = self._make_agent()
        intent = agent._rule_based_intent("What is the consensus among my papers?")
        assert intent == "graph_consensus"

    def test_rule_based_reliability(self):
        agent = self._make_agent()
        intent = agent._rule_based_intent("How reliable is claim X?")
        assert intent == "graph_claim_reliability"

    def test_rule_based_summary(self):
        agent = self._make_agent()
        intent = agent._rule_based_intent("Summarize the knowledge graph")
        assert intent == "graph_summary"

    def test_rule_based_literature_search(self):
        agent = self._make_agent()
        intent = agent._rule_based_intent(
            "Find papers that support the claim that coffee causes cancer"
        )
        assert intent == "literature_search"

    def test_rule_based_explore(self):
        agent = self._make_agent()
        intent = agent._rule_based_intent("What is the relation between paper A and paper B?")
        assert intent == "graph_explore"

    def test_rule_based_general(self):
        agent = self._make_agent()
        intent = agent._rule_based_intent("Hello, how are you?")
        assert intent == "general"

    @pytest.mark.asyncio
    async def test_classify_intent_fallback_to_rules(self):
        from app.services.research_rag_service import RAGAgent

        agent = RAGAgent()
        intent = await agent.classify_intent("Show me all contradictions")
        assert intent == "graph_contradictions"


class TestRAGAgentGeneral:
    @pytest.mark.asyncio
    async def test_answer_question_no_graph(self):
        from app.services.research_rag_service import RAGAgent

        agent = RAGAgent()
        with patch.object(agent, "_graph", None):
            answer, sources = await agent.answer_question("Hello")
            assert isinstance(answer, str)
            assert isinstance(sources, list)

    @pytest.mark.asyncio
    async def test_answer_contradictions_no_graph(self):
        from app.services.research_rag_service import RAGAgent

        agent = RAGAgent()
        with patch.object(agent, "_graph", None):
            answer, sources = await agent.answer_question(
                "What contradictions exist in my knowledge graph?"
            )
            assert "empty" in answer.lower() or "unavailable" in answer.lower()
            assert isinstance(sources, list)

    @pytest.mark.asyncio
    async def test_literature_search_no_llm(self):
        from app.services.research_rag_service import RAGAgent

        agent = RAGAgent()
        with patch.object(agent, "_llm_client", None), patch.object(agent, "_graph", None):
            answer, sources = await agent._literature_search("What papers support claim X?")
            assert isinstance(answer, str)
            assert isinstance(sources, list)

    def test_reset_agent(self):
        from app.services.research_rag_service import get_rag_agent, reset_rag_agent

        agent1 = get_rag_agent()
        reset_rag_agent()
        agent2 = get_rag_agent()
        assert agent1 is not agent2


class TestChatSchema:
    def test_source_model(self):
        from app.schemas.chat import Source

        s = Source(doc_id="doc1", filename="test.pdf", confidence=0.85)
        assert s.doc_id == "doc1"
        assert s.filename == "test.pdf"
        assert s.confidence == 0.85
        assert s.relation_type is None

    def test_message_response_model(self):
        from datetime import datetime

        from app.schemas.chat import MessageResponse, Source

        now = datetime.now(UTC)
        msg = MessageResponse(
            id="msg1",
            session_id="session1",
            role="assistant",
            content="Test answer",
            sources=[Source(doc_id="doc1")],
            created_at=now,
        )
        assert msg.id == "msg1"
        assert len(msg.sources) == 1
        assert msg.sources[0].doc_id == "doc1"

    def test_send_message_request(self):
        from app.schemas.chat import SendMessageRequest

        req = SendMessageRequest(message="Hello")
        assert req.message == "Hello"
        assert req.session_id is None

        req2 = SendMessageRequest(session_id="s1", message="Hi")
        assert req2.session_id == "s1"
        assert req2.message == "Hi"


class TestChatModel:
    def test_chat_session_model(self):
        from app.models.chat import ChatSession

        session = ChatSession(user_id="user1", title="Test")
        assert session.user_id == "user1"
        assert session.title == "Test"

    def test_chat_session_str_id(self):
        import uuid

        from app.models.chat import ChatSession

        session = ChatSession(id=str(uuid.uuid4()), user_id="user2")
        assert session.id is not None
        assert len(session.id) > 10

    def test_chat_message_model(self):
        from app.models.chat import ChatMessage

        msg = ChatMessage(
            session_id="session1",
            role="user",
            content="Hello",
            sources=[{"doc_id": "doc1", "confidence": 0.9}],
        )
        assert msg.session_id == "session1"
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.sources == [{"doc_id": "doc1", "confidence": 0.9}]
