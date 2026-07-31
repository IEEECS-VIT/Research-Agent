from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.services.document_service import (
    delete_document,
    get_document,
    get_user_documents,
    upload_document,
)
from app.services.ingestion_service import process_document

router = APIRouter(prefix="/documents", tags=["Documents"])

CURRENT_VERSION = 0


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    global CURRENT_VERSION
    doc = await upload_document(
        db=db,
        user_id=current_user["uid"],
        file=file,
        source_type=source_type,
        version_id=str(CURRENT_VERSION),
    )

    if background_tasks:
        background_tasks.add_task(process_document, db, doc)

    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.original_filename,
        source_type=doc.source_type,
        version_id=doc.version_id,
        total_sections=doc.total_sections,
        processing_status=doc.processing_status,
        created_at=doc.created_at,
    )


@router.post("/roll-version")
async def roll_version(
    current_user: dict = Depends(get_current_user),
):
    global CURRENT_VERSION
    CURRENT_VERSION += 1
    return {"message": "Version rolled", "new_version_id": CURRENT_VERSION}


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    source_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    documents, total = get_user_documents(
        db=db,
        user_id=current_user["uid"],
        skip=skip,
        limit=limit,
        source_type=source_type,
    )

    return DocumentListResponse(
        documents=[
            DocumentUploadResponse(
                id=doc.id,
                filename=doc.original_filename,
                source_type=doc.source_type,
                version_id=doc.version_id,
                total_sections=doc.total_sections,
                processing_status=doc.processing_status,
                created_at=doc.created_at,
            )
            for doc in documents
        ],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document_detail(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = get_document(db=db, document_id=document_id, user_id=current_user["uid"])
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.original_filename,
        source_type=doc.source_type,
        version_id=doc.version_id,
        total_sections=doc.total_sections,
        processing_status=doc.processing_status,
        created_at=doc.created_at,
        error_message=doc.error_message,
    )


@router.delete("/{document_id}")
async def remove_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = get_document(db=db, document_id=document_id, user_id=current_user["uid"])
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document(db=db, document=doc)
    return {"message": "Document deleted"}
