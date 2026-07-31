import logging
import re
from collections.abc import Iterable

from google.genai import types
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.analysis import ComparisonResult as AnalysisComparisonResult
from app.models.document import Document
from GraphEngine.utils.gemini_client import _get_client

logger = logging.getLogger(__name__)
settings = get_settings()


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences while handling basic punctuation boundaries."""
    if not text:
        return []
    sentences = re.split(r"(?<=[\.\?!])\s+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def annotate_document_text(
    original_text: str,
    annotations_map: dict[str, str] | Iterable[tuple[str, str]],
) -> str:
    """Inject comments inline immediately below matched sentences (exact or fuzzy)."""
    annotated_text = original_text
    annotation_items = (
        annotations_map.items() if isinstance(annotations_map, dict) else annotations_map
    )

    for claim_text, comment_block in annotation_items:
        claim_text_clean = " ".join(claim_text.strip().split())
        if not claim_text_clean:
            continue

        if claim_text_clean in annotated_text:
            annotated_text = annotated_text.replace(
                claim_text_clean, f"{claim_text_clean}\n{comment_block}"
            )
            continue

        sentences = split_into_sentences(annotated_text)
        best_match = None
        max_overlap = 0.0

        claim_words = set(claim_text_clean.lower().split())
        for sentence in sentences:
            if len(sentence) < 15:
                continue

            sentence_clean = " ".join(sentence.strip().split())
            sentence_words = set(sentence_clean.lower().split())
            union = claim_words.union(sentence_words)
            similarity = (
                len(claim_words.intersection(sentence_words)) / len(union) if union else 0.0
            )

            if similarity > max_overlap and similarity >= 0.60:
                max_overlap = similarity
                best_match = sentence_clean

        if best_match:
            annotated_text = annotated_text.replace(best_match, f"{best_match}\n{comment_block}")

    return annotated_text


async def generate_alternative_rephrasing(claim_text: str, contradicting_evidence: str) -> str:
    """Call Gemini to generate a qualified version of a contradicted claim."""
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set. Re-phrasing skipped.")
        return claim_text

    prompt = f"""You are a scientific writing assistant. A researcher has written the following claim in their draft, but it is contradicted by existing literature.

Original Claim: "{claim_text}"
Contradicting Evidence: "{contradicting_evidence}"

Task: Rewrite the Original Claim to add logical qualifiers (e.g. "under low-temperature conditions", "when using specific optimization parameters", "in the context of deep learning models") so that it aligns more accurately with the boundaries of the existing literature (the Contradicting Evidence) without losing the original assertion's core value.

Return ONLY the rewritten sentence. Do not include any explanation, quotes, prefix, or extra text."""

    try:
        client = _get_client()
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
            ),
        )
        return (response.text or "").strip().strip('"') or claim_text
    except Exception as e:
        logger.error("LLM re-phrasing generation failed: %s", e)
        return claim_text


def _is_actionable_contradiction(result: AnalysisComparisonResult) -> bool:
    relation_type = (result.relation_type or "").upper()
    confidence_state = (result.confidence_state or "").upper()
    verifier_status = (result.verifier_status or "").upper()

    return relation_type == "CONTRADICT" and (
        confidence_state == "HIGH_CONFIDENCE" or verifier_status == "REJECTED"
    )


def _read_document_text(document: Document) -> str:
    if not document.file_path:
        raise ValueError("Document file path is missing.")

    with open(document.file_path, encoding="utf-8", errors="ignore") as file_handle:
        return file_handle.read()


def _paper_reference_label(document: Document | None, fallback_id: str) -> str:
    if not document:
        return fallback_id
    return document.original_filename or document.filename or fallback_id


def _paper_reference_doi(document: Document | None) -> str | None:
    if not document:
        return None
    return document.doi or None


async def generate_draft_annotations(db: Session, draft_id: str, user_id: str) -> str:
    """Generate annotated document text from stored comparison results."""
    document = (
        db.query(Document)
        .filter(
            Document.id == draft_id,
            Document.user_id == user_id,
            Document.source_type == "draft",
        )
        .first()
    )

    if not document:
        raise ValueError("Draft document not found or unauthorized.")

    draft_content = _read_document_text(document)

    comparison_rows = (
        db.query(AnalysisComparisonResult)
        .filter(AnalysisComparisonResult.source_doc_id == draft_id)
        .order_by(AnalysisComparisonResult.created_at.asc())
        .all()
    )

    if not comparison_rows:
        logger.info("No comparison rows found for draft %s.", draft_id)
        return draft_content

    target_doc_ids = {row.target_doc_id for row in comparison_rows if row.target_doc_id}
    target_documents = (
        db.query(Document).filter(Document.id.in_(target_doc_ids)).all() if target_doc_ids else []
    )
    target_document_map = {
        target_document.id: target_document for target_document in target_documents
    }

    annotations: list[tuple[str, str]] = []
    for row in comparison_rows:
        if not _is_actionable_contradiction(row):
            continue

        source_claim = (row.source_text or "").strip()
        paper_claim = (row.target_text or "").strip()
        if not source_claim or not paper_claim:
            continue

        target_document = target_document_map.get(row.target_doc_id)
        paper_title = _paper_reference_label(target_document, row.target_doc_id)
        paper_doi = _paper_reference_doi(target_document)

        suggested_rewrite = await generate_alternative_rephrasing(source_claim, paper_claim)
        comment_lines = [
            "<!-- ",
            "[WARNING: RISK OF OVERCLAIMING]",
            f"Contradicted by: {paper_title}",
            f"DOI: {paper_doi}" if paper_doi else "DOI: Not found",
            f'Evidence: "{paper_claim}"',
            f'Suggested Rewrite: "{suggested_rewrite}"',
            "-->",
        ]
        annotations.append((source_claim, "\n".join(comment_lines)))

    if not annotations:
        logger.info("No actionable contradictions found for draft %s.", draft_id)
        return draft_content

    return annotate_document_text(draft_content, annotations)
