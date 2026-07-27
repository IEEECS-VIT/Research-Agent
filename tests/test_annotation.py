import os
import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from app.main import app
from app.core.database import Base, engine, SessionLocal
from app.models.document import Document, SourceType, ProcessingStatus
from app.models.analysis import AnalysisSession, ComparisonResult as AnalysisComparisonResult
from ingestion_pipeline.file_utils import extract_doi
from app.services.draft_annotation_service import annotate_document_text, generate_draft_annotations


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


@pytest.fixture
def override_deps():
    """Override FastAPI dependencies for testing."""
    async def mock_get_current_user():
        return {"uid": "test-user-123", "email": "test@example.com"}

    app.dependency_overrides.clear()
    from app.core.security import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_doi_extraction():
    # Test valid DOI in various text positions
    text1 = "This paper has DOI: 10.1000/xyz123 and discusses important research."
    assert extract_doi(text1) == "10.1000/xyz123"

    text2 = "10.1145/3318464 is the primary DOI for this book chapter."
    assert extract_doi(text2) == "10.1145/3318464"

    # Test punctuation cleaning
    text3 = "Look at 10.1016/j.cell.2023.01.001."
    assert extract_doi(text3) == "10.1016/j.cell.2023.01.001"

    # Test invalid DOI
    text4 = "There is no valid identifier here. 10.abc/def"
    assert extract_doi(text4) is None


def test_inline_document_annotation_exact():
    original = "The proposed model achieves state of the art results. It works efficiently on small devices."
    annotations = {
        "The proposed model achieves state of the art results.": "<!-- [ALERT] Contradicts... -->"
    }
    annotated = annotate_document_text(original, annotations)
    expected = "The proposed model achieves state of the art results.\n<!-- [ALERT] Contradicts... --> It works efficiently on small devices."
    assert annotated == expected


def test_inline_document_annotation_fuzzy():
    original = "The proposed network model achieves SOTA results on ImageNet. It works efficiently."
    annotations = {
        "proposed model achieves SOTA results on ImageNet": "<!-- [ALERT] Contradicts... -->"
    }
    annotated = annotate_document_text(original, annotations)
    assert "<!-- [ALERT] Contradicts... -->" in annotated


class TestAnnotationAPI:
    def test_annotate_endpoint_not_found(self, override_deps):
        # Request annotation for non-existent document
        response = client.post("/api/v1/documents/nonexistent-id/annotate")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found or unauthorized"

    def test_annotate_endpoint_wrong_type(self, override_deps):
        db = SessionLocal()
        doc = Document(
            id="test-doc-paper",
            user_id="test-user-123",
            filename="paper.pdf",
            original_filename="paper.pdf",
            source_type=SourceType.PAPER.value,
            processing_status=ProcessingStatus.COMPLETED.value
        )
        db.add(doc)
        db.commit()
        db.close()

        response = client.post("/api/v1/documents/test-doc-paper/annotate")
        assert response.status_code == 400
        assert response.json()["detail"] == "Only draft documents can be annotated"

    @patch("app.api.annotation.generate_draft_annotations", new_callable=AsyncMock)
    def test_annotate_endpoint_success(self, mock_generate, override_deps):
        db = SessionLocal()
        doc = Document(
            id="test-doc-draft",
            user_id="test-user-123",
            filename="draft.md",
            original_filename="draft.md",
            source_type=SourceType.DRAFT.value,
            processing_status=ProcessingStatus.COMPLETED.value
        )
        db.add(doc)
        db.commit()
        db.close()

        mock_generate.return_value = "Annotated Draft Content"

        response = client.post("/api/v1/documents/test-doc-draft/annotate")
        assert response.status_code == 200
        assert response.text == "Annotated Draft Content"
        assert response.headers["Content-Type"] == "text/markdown; charset=utf-8"
        assert "Content-Disposition" in response.headers
        assert "attachment; filename=\"draft_annotated.md\"" in response.headers["Content-Disposition"]


def test_generate_draft_annotations_uses_comparison_rows(tmp_path, override_deps):
    draft_path = tmp_path / "draft.md"
    draft_path.write_text("The model always works on every input. The second sentence stays unchanged.", encoding="utf-8")

    db = SessionLocal()
    session = AnalysisSession(id="session-1", user_id="test-user-123", name="session", status="completed")
    draft = Document(
        id="draft-doc-1",
        user_id="test-user-123",
        filename="draft.md",
        original_filename="draft.md",
        file_path=str(draft_path),
        source_type=SourceType.DRAFT.value,
        processing_status=ProcessingStatus.COMPLETED.value,
    )
    paper = Document(
        id="paper-doc-1",
        user_id="test-user-123",
        filename="paper.md",
        original_filename="paper.md",
        doi="10.1234/example.doi",
        source_type=SourceType.PAPER.value,
        processing_status=ProcessingStatus.COMPLETED.value,
    )
    comparison = AnalysisComparisonResult(
        session_id=session.id,
        source_doc_id=draft.id,
        target_doc_id=paper.id,
        source_section="intro",
        target_section="results",
        source_text="The model always works on every input.",
        target_text="The model fails on out-of-distribution inputs.",
        support_score=0.1,
        contradiction_score=0.9,
        confidence=0.95,
        verifier_status="CONFIRMED",
        relation_type="CONTRADICT",
        confidence_state="HIGH_CONFIDENCE",
    )

    db.add(session)
    db.add(draft)
    db.add(paper)
    db.commit()

    db.add(comparison)
    db.commit()

    with patch("app.services.draft_annotation_service.generate_alternative_rephrasing", new_callable=AsyncMock) as mock_rewrite:
        mock_rewrite.return_value = "The model works under controlled inputs."
        annotated = asyncio.run(generate_draft_annotations(db, draft.id, "test-user-123"))

    db.close()

    assert "[WARNING: RISK OF OVERCLAIMING]" in annotated
    assert "Contradicted by: paper.md" in annotated
    assert "DOI: 10.1234/example.doi" in annotated
    assert "Evidence: \"The model fails on out-of-distribution inputs.\"" in annotated
    assert "Suggested Rewrite: \"The model works under controlled inputs.\"" in annotated
