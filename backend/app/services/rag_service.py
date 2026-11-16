"""
RAG Service — Core pipeline: embedding → ChromaDB → retrieval → LLM response
"""
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"  # Suppress ChromaDB telemetry warnings

import json
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service

SOURCES_PREFIX = "|||SOURCES|||"

CONTEXT_SYSTEM_PROMPT = """You are a helpful and precise AI assistant for answering questions based on provided context.

**Instructions:**
1.  **Analyze the Context:** Carefully read the provided knowledge base context.
2.  **Answer from Context:** Base your answer *exclusively* on this context. Do not use any outside knowledge.
3.  **Handle Insufficient Information:** If the context does not contain the answer, state clearly that the information is not available in the provided documents. Do not try to guess.
4.  **Cite Sources:** After answering, mention the source filename(s) you used.
5.  **Format Output:** Use Markdown for readability (e.g., lists, bolding).
"""

GENERAL_SYSTEM_PROMPT = """You are a friendly and helpful conversational AI assistant.
The user is asking a question, but there is no relevant information in the knowledge base.
Respond conversationally and naturally. Do not mention the knowledge base or context.
"""


class RAGService:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )
        self.top_k = settings.top_k_results
        self.min_relevance = settings.min_relevance

    def add_document_chunks(self, chunks: list[str], filename: str, doc_id: int) -> int:
        """Embed and store document chunks in ChromaDB."""
        if not chunks:
            return 0

        # Generate embeddings via NVIDIA API
        embeddings = embedding_service.embed_documents(chunks)

        # Prepare IDs and metadata
        ids = [f"doc{doc_id}_chunk{i}" for i in range(len(chunks))]
        metadatas = [{"filename": filename, "doc_id": str(doc_id), "chunk_index": i} for i in range(len(chunks))]

        # Store in ChromaDB (upsert so re-indexing a document replaces its old chunks)
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

        return len(chunks)

    def remove_document(self, doc_id: int):
        """Remove all chunks for a document from ChromaDB."""
        self.collection.delete(where={"doc_id": str(doc_id)})

    def count_document_chunks(self, doc_id: int) -> int:
        """Number of chunks stored in ChromaDB for a document."""
        return len(self.collection.get(where={"doc_id": str(doc_id)}, include=[])["ids"])

    def retrieve_relevant_chunks(self, query: str) -> list[dict]:
        """Find the most relevant chunks for a query, dropping ones below the relevance threshold."""
        total = self.collection.count()
        if total == 0:
            return []

        # Embed the query
        query_embedding = embedding_service.embed_query(query)

        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(self.top_k, total),
        )

        # Format results
        sources = []
        for i in range(len(results["documents"][0])):
            score = round(1 - results["distances"][0][i], 4)  # cosine: 1 = perfect match
            if score < self.min_relevance:
                continue
            sources.append({
                "chunk_text": results["documents"][0][i],
                "filename": results["metadatas"][0][i]["filename"],
                "relevance_score": score,
            })

        return sources

    def _build_prompts(self, query: str, sources: list[dict]) -> tuple[str, str]:
        """Return (system_prompt, user_prompt) depending on whether context was found."""
        if not sources:
            return GENERAL_SYSTEM_PROMPT, query

        context = "\n\n---\n\n".join(f"[Source: {s['filename']}]\n{s['chunk_text']}" for s in sources)
        user_prompt = f"""**Knowledge Base Context:**
---
{context}
---

**User Query:**
{query}
"""
        return CONTEXT_SYSTEM_PROMPT, user_prompt

    def generate_answer(self, query: str, history: list = None) -> dict:
        """Full RAG pipeline: retrieve context → build prompt → generate answer."""
        sources = self.retrieve_relevant_chunks(query)
        system_prompt, user_prompt = self._build_prompts(query, sources)
        answer = llm_service.generate(user_prompt, system_prompt=system_prompt, history=history)

        return {
            "answer": answer,
            "sources": sources,
        }

    def generate_answer_stream(self, query: str, history: list = None):
        """Streaming RAG pipeline — yields a sources marker (if any) followed by answer chunks."""
        sources = self.retrieve_relevant_chunks(query)
        system_prompt, user_prompt = self._build_prompts(query, sources)

        if sources:
            yield f"{SOURCES_PREFIX}{json.dumps(sources)}"

        for token in llm_service.generate_stream(user_prompt, system_prompt=system_prompt, history=history):
            yield token


# Singleton instance
rag_service = RAGService()
