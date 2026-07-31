import pytest

from app.core.database import Base, SessionLocal, engine
from app.models.document import Document, ProcessingStatus, SourceType
from app.models.user import User


@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_user(setup_db, db_session):
    user = User(
        firebase_uid="test-user",
        email="test@example.com",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_document_model_creation(setup_db, db_session, test_user):
    doc = Document(
        user_id=test_user.firebase_uid,
        filename="test.pdf",
        original_filename="test.pdf",
        source_type=SourceType.DRAFT.value,
    )
    db_session.add(doc)
    db_session.commit()

    assert doc.id is not None
    assert doc.processing_status == ProcessingStatus.PENDING.value
    assert doc.source_type == "draft"


def test_document_processing_status(setup_db, db_session):
    user = User(firebase_uid="test-user-2", email="test2@example.com")
    db_session.add(user)
    db_session.commit()

    doc = Document(
        user_id=user.firebase_uid,
        filename="paper.pdf",
        original_filename="paper.pdf",
        source_type=SourceType.PAPER.value,
        processing_status=ProcessingStatus.PROCESSING.value,
    )
    db_session.add(doc)
    db_session.commit()

    assert doc.processing_status == ProcessingStatus.PROCESSING.value
