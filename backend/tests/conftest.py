"""
Test setup: point the app at a throwaway database / vector store / upload dir and
replace the NVIDIA embedding + LLM calls with deterministic fakes (no network, no API key).
"""
import hashlib
import math
import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

# Must happen before anything imports app.config (load_dotenv won't override these)
_TMP = tempfile.mkdtemp(prefix="ragchat-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP, 'test.db').as_posix()}"
os.environ["CHROMA_PERSIST_DIR"] = str(Path(_TMP, "chroma"))
os.environ["UPLOAD_DIR"] = str(Path(_TMP, "uploads"))
os.environ["MIN_RELEVANCE"] = "0.3"
os.environ["MAX_HISTORY_MESSAGES"] = "4"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.models.database import Base, engine  # noqa: E402
from app.services import embedding_service as emb_module, llm_service as llm_module  # noqa: E402
from app.services.rag_service import rag_service  # noqa: E402

DIM = 128


def fake_embed(text: str) -> list[float]:
    """Bag-of-words hashing embedding — texts sharing words get high cosine similarity."""
    vec = [0.0] * DIM
    for word in re.findall(r"\w+", text.lower()):
        vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class FakeLLM:
    def __init__(self):
        self.calls = []

    def generate(self, prompt, system_prompt=None, temperature=0.2, history=None):
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "history": history})
        if "short title" in prompt:
            return "Test Title"
        return "Fake answer."

    def generate_stream(self, prompt, system_prompt=None, temperature=0.2, history=None):
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "history": history})
        yield "Fake "
        yield "streamed answer — नमस्ते"

    def generate_title(self, text):
        return "Test Title"


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr(emb_module.embedding_service, "embed_query", fake_embed)
    monkeypatch.setattr(emb_module.embedding_service, "embed_documents", lambda texts: [fake_embed(t) for t in texts])
    for name in ("generate", "generate_stream", "generate_title"):
        monkeypatch.setattr(llm_module.llm_service, name, getattr(llm, name))
    return llm


@pytest.fixture
def client():
    # Fresh database and vector store for every test
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as c:
        existing = rag_service.collection.get(include=[])["ids"]
        if existing:
            rag_service.collection.delete(ids=existing)
        yield c
