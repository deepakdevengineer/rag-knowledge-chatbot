import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env from backend directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    # NVIDIA API
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_base_url: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    nvidia_llm_model: str = os.getenv("NVIDIA_LLM_MODEL", "meta/llama3-8b-instruct")
    nvidia_embed_model: str = os.getenv("NVIDIA_EMBED_MODEL", "nvidia/llama-3.2-nv-embedqa-1b-v2")
    nvidia_embed_api_key: str = os.getenv("NVIDIA_EMBED_API_KEY", "")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./ragchat.db")

    # ChromaDB
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    # App Config
    # Bind to localhost by default — the API has no auth, so don't expose it on the network
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "./data/uploads")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    top_k_results: int = int(os.getenv("TOP_K_RESULTS", "5"))
    # Chunks below this cosine similarity are treated as irrelevant
    min_relevance: float = float(os.getenv("MIN_RELEVANCE", "0.3"))
    # How many previous chat messages are sent to the LLM as conversation context
    max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))
    # Comma-separated list of frontend origins allowed by CORS
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")


settings = Settings()
