"""
RAG Chatbot — FastAPI Main Entry Point
"""
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import logging
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from app.config import settings
from app.models.database import create_tables, SessionLocal, Document
from app.routes import chat, documents, history
from app.services.rag_service import rag_service
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")
# chromadb 0.5.x telemetry is disabled but still logs a noisy posthog error on every call
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)


def sync_documents_with_vector_store():
    """Mark documents as failed if their chunks are missing from ChromaDB (e.g. vector store was reset)."""
    db = SessionLocal()
    try:
        for doc in db.query(Document).filter(Document.status.in_(["ready", "processing"])).all():
            stored = rag_service.count_document_chunks(doc.id)
            if doc.status == "processing" or stored == 0:
                # "processing" here means the server stopped mid-upload
                doc.status = "failed"
                doc.error = "Document chunks are missing from the vector store. Re-index or upload it again."
                logger.warning("Document %s (%s) has no chunks in ChromaDB - marked failed", doc.id, doc.filename)
            elif stored != doc.chunk_count:
                doc.chunk_count = stored
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and upload directory on startup."""
    create_tables()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    sync_documents_with_vector_store()
    if not settings.nvidia_api_key or not settings.nvidia_embed_api_key:
        logger.warning("NVIDIA_API_KEY / NVIDIA_EMBED_API_KEY is not set — chat and uploads will fail")
    logger.info("LLM: %s", settings.nvidia_llm_model)
    logger.info("Embeddings: %s", settings.nvidia_embed_model)
    logger.info("ChromaDB: %s (%d chunks)", settings.chroma_persist_dir, rag_service.collection.count())
    yield

# Create FastAPI app
app = FastAPI(
    title="RAG Knowledge Base Chatbot",
    description="AI-powered chatbot that answers questions from your uploaded documents using RAG (Retrieval-Augmented Generation)",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(history.router)


@app.get("/")
def root():
    return {
        "message": "🤖 RAG Knowledge Base Chatbot API",
        "docs": "/docs",
        "version": "1.1.0",
    }


@app.get("/api/health")
def health():
    return {"status": "healthy", "message": "API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
