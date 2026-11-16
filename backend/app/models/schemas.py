from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


# --- Chat Schemas ---

class ChatRequest(BaseModel):
    query: str = Field(..., max_length=4000)
    session_id: Optional[int] = None


class SourceInfo(BaseModel):
    filename: str
    chunk_text: str
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    session_id: int


# --- Document Schemas ---

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error: Optional[str] = None
    created_at: datetime


class DocumentDeleteResponse(BaseModel):
    message: str
    id: int


# --- Chat History Schemas ---

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    sources: str
    created_at: datetime


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class SessionDetailResponse(SessionResponse):
    messages: list[MessageResponse]
