# RAG Chatbot Backend

## Quick Start

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure — copy the example and add your NVIDIA API keys
copy .env.example .env

# Run the server
python -m app.main
```

Server will start at: http://127.0.0.1:8000
API docs: http://127.0.0.1:8000/docs

## Configuration

All settings live in `.env` (see `.env.example`). Useful knobs:

| Variable | Default | Purpose |
|---|---|---|
| `MIN_RELEVANCE` | `0.3` | Chunks below this cosine similarity are ignored, so small talk isn't answered from unrelated documents |
| `MAX_HISTORY_MESSAGES` | `10` | Previous messages sent to the LLM as conversation context |
| `APP_HOST` | `127.0.0.1` | The API has no auth — keep it on localhost |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Allowed frontend origins |

## Documents

- Failed documents keep their file and show the error; retry with `POST /api/documents/{id}/reindex` (the UI has a retry button).
- On startup, documents whose chunks are missing from ChromaDB are marked `failed`.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Tests use a temporary database/vector store and fake the NVIDIA API — no key or network needed.
