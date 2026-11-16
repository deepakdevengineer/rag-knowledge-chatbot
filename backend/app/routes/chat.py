"""
Chat API Routes — Chat with RAG knowledge base
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.models.database import get_db, SessionLocal, ChatSession, ChatMessage, utcnow
from app.models.schemas import ChatRequest, ChatResponse, SourceInfo
from app.services.rag_service import rag_service, SOURCES_PREFIX
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Regenerate the session title every N messages so it follows the conversation
TITLE_REFRESH_EVERY = 6


def _start_turn(request: ChatRequest, db: Session) -> tuple[ChatSession, list[dict], bool]:
    """Validate the request, get/create the session, load recent history and save the user message."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if request.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        is_new_session = False
    else:
        session = ChatSession()
        db.add(session)
        db.commit()
        db.refresh(session)
        is_new_session = True

    # Only the most recent messages are sent to the LLM so long chats don't overflow its context
    recent = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id.desc())
        .limit(settings.max_history_messages)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in reversed(recent)]

    db.add(ChatMessage(session_id=session.id, role="user", content=request.query))
    db.commit()

    return session, history, is_new_session


def _finish_turn(db: Session, session_id: int, query: str, answer: str, sources: list[dict], is_new_session: bool):
    """Save the assistant message, bump the session's updated_at and refresh its title when due."""
    db.add(ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer,
        sources=json.dumps([{
            "filename": s["filename"],
            "chunk_text": s["chunk_text"][:200],
            "relevance_score": s["relevance_score"],
        } for s in sources]),
    ))

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session:
        # Touch the session so the sidebar (sorted by updated_at) shows it first
        session.updated_at = utcnow()

        message_count = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
        if is_new_session or session.title == "New Chat" or message_count % TITLE_REFRESH_EVERY == 0:
            session.title = llm_service.generate_title(f"User: {query}\nAssistant: {answer[:300]}")

    db.commit()


@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a message and get RAG-powered response."""
    session, history, is_new_session = _start_turn(request, db)

    result = rag_service.generate_answer(request.query, history=history)
    _finish_turn(db, session.id, request.query, result["answer"], result["sources"], is_new_session)

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceInfo(**s) for s in result["sources"]],
        session_id=session.id,
    )


@router.post("/stream")
def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a message and get streaming RAG-powered response (Server-Sent Events)."""
    session, history, is_new_session = _start_turn(request, db)
    # Capture before entering the generator — the request-scoped db session is closed by then
    session_id = session.id

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    def event_stream():
        full_answer = ""
        sources = []

        try:
            for token in rag_service.generate_answer_stream(request.query, history=history):
                if token.startswith(SOURCES_PREFIX):
                    sources = json.loads(token[len(SOURCES_PREFIX):])
                    yield sse({"type": "sources", "sources": sources})
                    continue
                full_answer += token
                yield sse({"type": "token", "content": token})
        except Exception:
            logger.exception("Streaming failed for session %s", session_id)
            error_text = "\n\n⚠️ **Error:** Something went wrong while generating the answer. Please try again."
            full_answer += error_text
            yield sse({"type": "token", "content": error_text})

        # Use a fresh session to save the message
        db_session = SessionLocal()
        try:
            _finish_turn(db_session, session_id, request.query, full_answer, sources, is_new_session)
        except Exception:
            db_session.rollback()
            logger.exception("Error saving chat history for session %s", session_id)
        finally:
            db_session.close()

        yield sse({"type": "done", "session_id": session_id})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
