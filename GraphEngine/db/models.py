# models.py
from sqlalchemy import Column, Integer, String, Float, Boolean
from GraphEngine.db.connection import Base

class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True)
    node_id = Column(String, unique=True)
    node_type = Column(String)
    version_id = Column(String)  # Ingestion pipeline stores version_id as str e.g. "0", "1"


class Edge(Base):
    __tablename__ = "edges"

    id = Column(Integer, primary_key=True)
    source_id = Column(String)
    target_id = Column(String)

    support_score = Column(Float)
    contradiction_score = Column(Float)
    confidence = Column(Float)

    # Semantic dimensions (new)
    relation_type = Column(String, nullable=True)        # SUPPORT | CONTRADICT | MIXED
    confidence_state = Column(String, nullable=True)     # HIGH_CONFIDENCE | LOW_CONFIDENCE | REVIEW_REQUIRED
    verifier_state = Column(String, nullable=True)       # CONFIRMED | REJECTED | SCOPE_MISMATCH

    # Backwards-compatible overloaded field (deprecated)
    flag = Column(String, nullable=True)
    verifier_status = Column(String, nullable=True)
    user_override = Column(Boolean, default=False)