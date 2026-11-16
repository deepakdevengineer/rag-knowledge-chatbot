"""
NVIDIA Embedding Service — Uses llama-3.2-nv-embedqa-1b-v2 via NVIDIA API
"""
from openai import OpenAI
from app.config import settings


class EmbeddingService:
    def __init__(self):
        self.client = OpenAI(
            base_url=settings.nvidia_base_url,
            api_key=settings.nvidia_embed_api_key,
        )
        self.model = settings.nvidia_embed_model

    def embed_text(self, text: str, input_type: str = "passage") -> list[float]:
        """Generate embedding for a single text."""
        response = self.client.embeddings.create(
            model=self.model,
            input=[text],
            encoding_format="float",
            extra_body={"input_type": input_type}
        )
        return response.data[0].embedding

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query."""
        return self.embed_text(query, input_type="query")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple document chunks."""
        if not texts:
            return []

        # NVIDIA API batch limit — process in chunks of 50
        all_embeddings = []
        batch_size = 50

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
                encoding_format="float",
                extra_body={"input_type": "passage"}
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings


# Singleton instance
embedding_service = EmbeddingService()
