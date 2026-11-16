"""
Document API Routes — Upload and manage knowledge base documents
"""
import logging
import os
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.models.database import get_db, Document
from app.models.schemas import DocumentResponse, DocumentDeleteResponse
from app.services.doc_processor import doc_processor
from app.services.rag_service import rag_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


def sanitize_filename(filename: str) -> str:
    """Strip directory components and unsafe characters from a client-supplied filename."""
    # Path(...).name alone misses backslashes on POSIX, so normalise them first
    name = Path((filename or "").replace("\\", "/")).name
    name = re.sub(r"[^\w.\- ()]", "_", name).strip(" .")
    return name or "document"


def _index_document(doc: Document, db: Session) -> Document:
    """Extract → chunk → embed → store a document. Marks it ready or failed (never raises)."""
    try:
        chunks = doc_processor.process_file(doc.filepath)
        if not chunks:
            raise ValueError("Could not extract any text from this document")

        # Drop any chunks left over from a previous attempt before re-adding
        rag_service.remove_document(doc.id)
        doc.chunk_count = rag_service.add_document_chunks(chunks, doc.filename, doc.id)
        doc.status = "ready"
        doc.error = None
    except Exception as e:
        logger.exception("Processing failed for document %s", doc.id)
        doc.status = "failed"
        doc.error = str(e)[:500]

    db.commit()
    db.refresh(doc)
    return doc


@router.post("/upload", response_model=DocumentResponse)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a document and process it into the knowledge base.

    Declared as a plain `def` so FastAPI runs it in a threadpool — parsing and the
    embedding API calls are blocking and would otherwise freeze the event loop.
    """
    filename = sanitize_filename(file.filename)

    # Validate file extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext or 'none'}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Validate file size without reading more than the limit into memory
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    file_content = file.file.read(max_bytes + 1)
    file_size = len(file_content)
    if file_size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
        )
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    # Save file to disk
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    filepath = upload_dir / filename
    # Handle duplicate filenames
    counter = 1
    while filepath.exists():
        filepath = upload_dir / f"{Path(filename).stem}_{counter}{ext}"
        counter += 1

    with open(filepath, "wb") as f:
        f.write(file_content)

    # Create DB record
    doc = Document(
        filename=filename,
        filepath=str(filepath),
        file_type=ext.lstrip("."),
        file_size=file_size,
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    doc = _index_document(doc, db)
    if doc.status == "failed":
        # Keep the record + file so the user can retry from the UI
        raise HTTPException(status_code=422, detail=f"Processing error: {doc.error}")

    return doc


@router.get("/", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    """List all uploaded documents."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return docs


@router.post("/{doc_id}/reindex", response_model=DocumentResponse)
def reindex_document(doc_id: int, db: Session = Depends(get_db)):
    """Re-process a document (e.g. after a failed upload or a lost vector store)."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not os.path.exists(doc.filepath):
        raise HTTPException(
            status_code=410,
            detail="Original file is missing on the server. Please delete this document and upload it again."
        )

    doc.status = "processing"
    db.commit()

    doc = _index_document(doc, db)
    if doc.status == "failed":
        raise HTTPException(status_code=422, detail=f"Processing error: {doc.error}")
    return doc


@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    """Delete a document and its chunks from the knowledge base."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from ChromaDB first — if this fails, keep the record so the delete can be retried
    # instead of leaving orphan chunks that keep showing up in answers
    try:
        rag_service.remove_document(doc_id)
    except Exception as e:
        logger.exception("Failed to remove chunks for document %s", doc_id)
        raise HTTPException(status_code=500, detail=f"Could not remove document from vector store: {e}")

    # Remove file from disk (a missing file is fine)
    try:
        if os.path.exists(doc.filepath):
            os.remove(doc.filepath)
    except OSError:
        logger.warning("Could not delete file %s", doc.filepath, exc_info=True)

    # Remove from DB
    db.delete(doc)
    db.commit()

    return DocumentDeleteResponse(message="Document deleted successfully", id=doc_id)
