import json
from pathlib import Path

from app.config import settings
from app.models.database import SessionLocal, Document
from app.routes.documents import sanitize_filename
from app.services.rag_service import rag_service

POSTGRES_TEXT = (
    "PostgreSQL is a powerful open source object-relational database system. "
    "PostgreSQL uses and extends the SQL language with many features that safely store "
    "and scale complicated data workloads. The origins of PostgreSQL date back to 1986."
)


def upload(client, name="postgres.txt", content=POSTGRES_TEXT.encode()):
    return client.post("/api/documents/upload", files={"file": (name, content, "text/plain")})


def parse_sse(body: str) -> list[dict]:
    return [json.loads(e[6:]) for e in body.split("\n\n") if e.startswith("data: ")]


# --- Documents ---

def test_upload_list_and_delete(client):
    res = upload(client)
    assert res.status_code == 200, res.text
    doc = res.json()
    assert doc["status"] == "ready"
    assert doc["chunk_count"] >= 1
    assert rag_service.count_document_chunks(doc["id"]) == doc["chunk_count"]

    assert [d["id"] for d in client.get("/api/documents/").json()] == [doc["id"]]

    assert client.delete(f"/api/documents/{doc['id']}").status_code == 200
    assert client.get("/api/documents/").json() == []
    assert rag_service.count_document_chunks(doc["id"]) == 0


def test_upload_rejects_bad_type_and_empty_file(client):
    assert upload(client, name="evil.exe").status_code == 400
    assert upload(client, content=b"").status_code == 400


def test_upload_rejects_too_large(client, monkeypatch):
    monkeypatch.setattr(settings, "max_file_size_mb", 0)
    assert upload(client).status_code == 400


def test_sanitize_filename_blocks_path_traversal():
    assert sanitize_filename("../../etc/passwd.txt") == "passwd.txt"
    assert sanitize_filename("..\\..\\app\\main.txt") == "main.txt"
    assert sanitize_filename("my file (1).pdf") == "my file (1).pdf"
    assert sanitize_filename("") == "document"


def test_upload_with_traversal_name_stays_in_upload_dir(client):
    res = upload(client, name="../../escape.txt")
    assert res.status_code == 200
    with SessionLocal() as db:
        path = Path(db.get(Document, res.json()["id"]).filepath).resolve()
    assert path.parent == Path(settings.upload_dir).resolve()


def test_failed_processing_can_be_reindexed(client, monkeypatch):
    from app.services import embedding_service as emb

    def boom(texts):
        raise RuntimeError("embedding API down")

    real = emb.embedding_service.embed_documents
    monkeypatch.setattr(emb.embedding_service, "embed_documents", boom)
    res = upload(client)
    assert res.status_code == 422
    assert "embedding API down" in res.json()["detail"]

    doc = client.get("/api/documents/").json()[0]
    assert doc["status"] == "failed"

    monkeypatch.setattr(emb.embedding_service, "embed_documents", real)
    res = client.post(f"/api/documents/{doc['id']}/reindex")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"
    assert res.json()["error"] is None


def test_delete_keeps_record_when_vector_store_fails(client, monkeypatch):
    doc = upload(client).json()

    def boom(doc_id):
        raise RuntimeError("chroma down")

    monkeypatch.setattr(rag_service, "remove_document", boom)
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 500
    assert len(client.get("/api/documents/").json()) == 1


# --- Retrieval ---

def test_irrelevant_query_returns_no_sources(client, fakes):
    upload(client)
    assert rag_service.retrieve_relevant_chunks("hello there") == []
    assert rag_service.retrieve_relevant_chunks("What is PostgreSQL database?")


def test_chat_uses_context_only_when_relevant(client, fakes):
    upload(client)

    res = client.post("/api/chat/", json={"query": "What is PostgreSQL?"})
    assert res.status_code == 200
    assert res.json()["sources"]
    assert "Knowledge Base Context" in fakes.calls[-1]["prompt"]

    res = client.post("/api/chat/", json={"query": "hi"})
    assert res.json()["sources"] == []
    assert fakes.calls[-1]["prompt"] == "hi"


# --- Chat ---

def test_chat_validation(client):
    assert client.post("/api/chat/", json={"query": "   "}).status_code == 400
    assert client.post("/api/chat/", json={"query": "hi", "session_id": 999}).status_code == 404


def test_stream_saves_messages_and_title(client):
    res = client.post("/api/chat/stream", json={"query": "Hello"})
    assert res.status_code == 200
    events = parse_sse(res.text)

    tokens = "".join(e["content"] for e in events if e["type"] == "token")
    assert tokens == "Fake streamed answer — नमस्ते"
    assert events[-1]["type"] == "done"
    session_id = events[-1]["session_id"]

    session = client.get(f"/api/history/sessions/{session_id}").json()
    assert session["title"] == "Test Title"
    assert [m["role"] for m in session["messages"]] == ["user", "assistant"]
    assert session["messages"][1]["content"] == tokens


def test_history_is_limited_and_shared_by_both_endpoints(client, fakes):
    session_id = client.post("/api/chat/", json={"query": "q1"}).json()["session_id"]
    for q in ("q2", "q3", "q4"):
        client.post("/api/chat/", json={"query": q, "session_id": session_id})

    history = fakes.calls[-1]["history"]
    assert len(history) == settings.max_history_messages  # 4 in tests
    assert history[-1] == {"role": "assistant", "content": "Fake answer."}

    client.post("/api/chat/stream", json={"query": "q5", "session_id": session_id})
    assert len(fakes.calls[-1]["history"]) == settings.max_history_messages


def test_active_session_moves_to_top(client):
    first = client.post("/api/chat/", json={"query": "first"}).json()["session_id"]
    second = client.post("/api/chat/", json={"query": "second"}).json()["session_id"]
    client.post("/api/chat/", json={"query": "again", "session_id": first})

    ids = [s["id"] for s in client.get("/api/history/sessions").json()]
    assert ids == [first, second]


# --- Startup consistency check ---

def test_startup_marks_documents_without_vectors_failed(client):
    from app.main import sync_documents_with_vector_store

    doc = upload(client).json()
    rag_service.remove_document(doc["id"])  # simulate a lost/reset vector store

    sync_documents_with_vector_store()
    doc = client.get("/api/documents/").json()[0]
    assert doc["status"] == "failed"
    assert "missing" in doc["error"]
