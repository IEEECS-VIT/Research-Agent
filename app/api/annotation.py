import io
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.document import Document
from app.services.draft_annotation_service import generate_draft_annotations

router = APIRouter(prefix="/documents", tags=["Annotations"])


@router.post("/{document_id}/annotate")
async def annotate_draft(
    document_id: str,
    as_json: bool = Query(
        False, description="Return annotated markdown as JSON instead of a file attachment."
    ),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check authorization and retrieve document filename
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user["uid"])
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or unauthorized")

    if doc.source_type != "draft":
        raise HTTPException(status_code=400, detail="Only draft documents can be annotated")

    try:
        annotated_content = await generate_draft_annotations(db, document_id, current_user["uid"])

        original_name = doc.original_filename or doc.filename or "document"
        annotated_filename = f"{Path(original_name).stem}_annotated.md"

        if as_json:
            return JSONResponse(
                content={
                    "document_id": document_id,
                    "filename": annotated_filename,
                    "content": annotated_content,
                }
            )

        file_stream = io.BytesIO(annotated_content.encode("utf-8"))

        return StreamingResponse(
            file_stream,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{annotated_filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate annotation: {str(e)}")
