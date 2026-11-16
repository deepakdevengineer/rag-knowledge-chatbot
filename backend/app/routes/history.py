"""
Chat History API Routes — Manage chat sessions
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db, ChatSession, ChatMessage
from app.models.schemas import SessionResponse, SessionDetailResponse, MessageResponse

router = APIRouter(prefix="/api/history", tags=["History"])


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(db: Session = Depends(get_db)):
    """Get all chat sessions, newest first."""
    sessions = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
    return sessions


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get a specific chat session with all messages."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a chat session and all its messages."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()

    return {"message": "Session deleted successfully", "id": session_id}


@router.delete("/sessions")
def clear_all_sessions(db: Session = Depends(get_db)):
    """Delete all chat sessions."""
    db.query(ChatMessage).delete()
    db.query(ChatSession).delete()
    db.commit()
    return {"message": "All sessions cleared"}
