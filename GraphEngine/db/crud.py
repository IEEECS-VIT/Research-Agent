# crud.py
from GraphEngine.db.connection import SessionLocal
from GraphEngine.db.models import Node, Edge
from GraphEngine.utils.helpers import (
    map_semantics_to_flag,
    infer_semantic_dimensions,
)


def create_node(node_id, node_type, version_id=1):
    db = SessionLocal()
    try:
        node = Node(
            node_id=node_id,
            node_type=node_type,
            version_id=version_id
        )
        db.add(node)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[CRUD] Error creating node: {e}")
    finally:
        db.close()


def create_edge(data):
    db = SessionLocal()
    try:
        # Ensure backward-compatible flag if not provided
        if "flag" not in data or not data.get("flag"):
            from GraphEngine.utils.helpers import map_semantics_to_flag
            relation = data.get("relation_type")
            confidence_state = data.get("confidence_state")
            data["flag"] = map_semantics_to_flag(relation, confidence_state)

        # Normalize semantic dimensions from legacy inputs when possible.
        if not data.get("relation_type") or not data.get("confidence_state") or not data.get("verifier_state"):
            from GraphEngine.utils.helpers import infer_semantic_dimensions
            inferred = infer_semantic_dimensions(
                flag=data.get("flag"),
                confidence=data.get("confidence"),
                verifier_status=data.get("verifier_status"),
            )
            if not data.get("relation_type"):
                data["relation_type"] = inferred.get("relation_type")
            if not data.get("confidence_state"):
                data["confidence_state"] = inferred.get("confidence_state")
            if not data.get("verifier_state"):
                data["verifier_state"] = inferred.get("verifier_state")

        edge = Edge(**data)
        db.add(edge)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[CRUD] Error creating edge: {e}")
    finally:
        db.close()


def upsert_edge(source_id: str, target_id: str, edge_data: dict) -> bool:
    """
    Create or update an edge between two nodes.
    
    Args:
        source_id: Source node ID (claim ID from source doc).
        target_id: Target node ID (claim ID from retrieved doc).
        edge_data: Dict with fields: support_score, contradiction_score, confidence,
                   verifier_status, flag (optional), user_override (optional).
    
    Returns:
        True if successful, False otherwise.
    """
    db = SessionLocal()
    try:
        # Check if edge already exists
        existing = db.query(Edge).filter(
            Edge.source_id == source_id,
            Edge.target_id == target_id
        ).first()
        
        if existing:
            # Update existing edge semantic dimensions
            existing.support_score = edge_data.get("support_score", existing.support_score)
            existing.contradiction_score = edge_data.get("contradiction_score", existing.contradiction_score)
            existing.confidence = edge_data.get("confidence", existing.confidence)

            # New semantic fields
            if not edge_data.get("relation_type") or not edge_data.get("confidence_state") or not edge_data.get("verifier_state"):
                from GraphEngine.utils.helpers import infer_semantic_dimensions
                inferred = infer_semantic_dimensions(
                    flag=edge_data.get("flag"),
                    confidence=edge_data.get("confidence", existing.confidence),
                    verifier_status=edge_data.get("verifier_status", existing.verifier_status),
                )
            else:
                inferred = {}

            existing.relation_type = edge_data.get("relation_type") or inferred.get("relation_type") or existing.relation_type
            existing.confidence_state = edge_data.get("confidence_state") or inferred.get("confidence_state") or existing.confidence_state
            existing.verifier_state = edge_data.get("verifier_state") or inferred.get("verifier_state") or existing.verifier_state

            # Keep old verifier_status for compatibility
            existing.verifier_status = edge_data.get("verifier_status", existing.verifier_status)

            # Maintain backward-compatible flag if provided or synthesize
            if edge_data.get("flag"):
                existing.flag = edge_data.get("flag")
            else:
                from GraphEngine.utils.helpers import map_semantics_to_flag
                existing.flag = map_semantics_to_flag(existing.relation_type, existing.confidence_state)

            # Don't override user_override unless explicitly set
            if "user_override" in edge_data:
                existing.user_override = edge_data.get("user_override")

            db.commit()
        else:
            # Create new edge
            # Synthesize flag if not present
            if not edge_data.get("flag"):
                from GraphEngine.utils.helpers import map_semantics_to_flag
                edge_data["flag"] = map_semantics_to_flag(edge_data.get("relation_type"), edge_data.get("confidence_state"))

            if not edge_data.get("relation_type") or not edge_data.get("confidence_state") or not edge_data.get("verifier_state"):
                from GraphEngine.utils.helpers import infer_semantic_dimensions
                inferred = infer_semantic_dimensions(
                    flag=edge_data.get("flag"),
                    confidence=edge_data.get("confidence"),
                    verifier_status=edge_data.get("verifier_status"),
                )
                if not edge_data.get("relation_type"):
                    edge_data["relation_type"] = inferred.get("relation_type")
                if not edge_data.get("confidence_state"):
                    edge_data["confidence_state"] = inferred.get("confidence_state")
                if not edge_data.get("verifier_state"):
                    edge_data["verifier_state"] = inferred.get("verifier_state")

            edge = Edge(
                source_id=source_id,
                target_id=target_id,
                support_score=edge_data.get("support_score", 0.0),
                contradiction_score=edge_data.get("contradiction_score", 0.0),
                confidence=edge_data.get("confidence", 0.0),

                relation_type=edge_data.get("relation_type"),
                confidence_state=edge_data.get("confidence_state"),
                verifier_state=edge_data.get("verifier_state"),

                verifier_status=edge_data.get("verifier_status", "CONFIRMED"),
                flag=edge_data.get("flag", None),
                user_override=edge_data.get("user_override", False),
            )
            db.add(edge)
            db.commit()
        
        return True
    except Exception as e:
        db.rollback()
        print(f"[CRUD] Error upserting edge: {e}")
        return False
    finally:
        db.close()


def get_edges():
    db = SessionLocal()
    try:
        edges = db.query(Edge).all()
        return edges
    except Exception as e:
        print(f"[CRUD] Error retrieving edges: {e}")
        return []
    finally:
        db.close()


def get_edge_direct(p1: str, p2: str):
    """Return the first edge directly connecting p1 and p2 in either direction.

    Uses a targeted WHERE clause instead of loading every edge into Python memory.
    Returns the Edge ORM object or None if no direct edge exists.
    """
    db = SessionLocal()
    try:
        from sqlalchemy import or_, and_
        return (
            db.query(Edge)
            .filter(
                or_(
                    and_(Edge.source_id == p1, Edge.target_id == p2),
                    and_(Edge.source_id == p2, Edge.target_id == p1),
                )
            )
            .first()
        )
    except Exception as e:
        print(f"[CRUD] get_edge_direct error: {e}")
        return None
    finally:
        db.close()


def bulk_upsert_edges(records: list[tuple[str, str, dict]]) -> int:
    """Persist a list of edges in a single SQLite transaction.

    This is significantly faster than calling upsert_edge() in a loop because
    it opens exactly one DB session, issues one batch-fetch for existing edges,
    and commits everything in a single transaction instead of N round-trips.

    Args:
        records: List of (source_id, target_id, edge_data) tuples.  The
                 edge_data dict must contain at minimum the keys expected by
                 upsert_edge (support_score, contradiction_score, confidence,
                 verifier_status, relation_type, confidence_state,
                 verifier_state, flag, user_override).

    Returns:
        Number of edges successfully written (inserted or updated).
    """
    if not records:
        return 0

    db = SessionLocal()
    try:
        # Collect all (source_id, target_id) pairs we need to check
        source_ids = list({r[0] for r in records})
        target_ids = list({r[1] for r in records})

        # Single query to fetch all potentially matching existing edges.
        existing_edges = db.query(Edge).filter(
            Edge.source_id.in_(source_ids),
            Edge.target_id.in_(target_ids),
        ).all()

        # Build a lookup dict for O(1) existence checks
        existing_map: dict[tuple[str, str], Edge] = {
            (e.source_id, e.target_id): e for e in existing_edges
        }

        written = 0
        for source_id, target_id, edge_data in records:
            try:
                # Ensure flag is present
                if not edge_data.get("flag"):
                    edge_data["flag"] = map_semantics_to_flag(
                        edge_data.get("relation_type"),
                        edge_data.get("confidence_state"),
                    )

                key = (source_id, target_id)
                if key in existing_map:
                    # UPDATE path
                    ex = existing_map[key]
                    ex.support_score = edge_data.get("support_score", ex.support_score)
                    ex.contradiction_score = edge_data.get("contradiction_score", ex.contradiction_score)
                    ex.confidence = edge_data.get("confidence", ex.confidence)
                    ex.relation_type = edge_data.get("relation_type") or ex.relation_type
                    ex.confidence_state = edge_data.get("confidence_state") or ex.confidence_state
                    ex.verifier_state = edge_data.get("verifier_state") or ex.verifier_state
                    ex.verifier_status = edge_data.get("verifier_status", ex.verifier_status)
                    ex.flag = edge_data.get("flag") or map_semantics_to_flag(ex.relation_type, ex.confidence_state)
                    if "user_override" in edge_data:
                        ex.user_override = edge_data["user_override"]
                else:
                    # INSERT path
                    new_edge = Edge(
                        source_id=source_id,
                        target_id=target_id,
                        support_score=edge_data.get("support_score", 0.0),
                        contradiction_score=edge_data.get("contradiction_score", 0.0),
                        confidence=edge_data.get("confidence", 0.0),
                        relation_type=edge_data.get("relation_type"),
                        confidence_state=edge_data.get("confidence_state"),
                        verifier_state=edge_data.get("verifier_state"),
                        verifier_status=edge_data.get("verifier_status", "CONFIRMED"),
                        flag=edge_data.get("flag"),
                        user_override=edge_data.get("user_override", False),
                    )
                    db.add(new_edge)
                    existing_map[key] = new_edge  # prevent duplicate inserts
                written += 1
            except Exception as exc:
                print(f"[CRUD] bulk_upsert_edges: skipping edge ({source_id} -> {target_id}): {exc}")

        db.commit()
        return written

    except Exception as e:
        db.rollback()
        print(f"[CRUD] bulk_upsert_edges transaction failed: {e}")
        return 0
    finally:
        db.close()