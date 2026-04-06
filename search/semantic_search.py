"""
Semantic Search — ChromaDB-backed vector store for content discovery.
Indexes both original and rewritten content so users can search by
meaning rather than exact keywords.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings


class SemanticSearch:
    """
    Wraps a ChromaDB persistent collection.
    • add_content   — index a piece of content with metadata
    • search        — similarity search by natural-language query
    • search_by_url — filter results to a specific source URL
    """

    def __init__(self, collection_name: str = "echowrite_content"):
        self.client = chromadb.PersistentClient(
            path=str(settings.CHROMA_DB_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    def add_content(
        self,
        content: str,
        metadata: Dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> str:
        """
        Add *content* to the vector index.  Returns the document id used.
        Metadata values are coerced to ChromaDB-safe types (str/int/float/bool).
        """
        if not content.strip():
            raise ValueError("Cannot index empty content")

        doc_id = doc_id or self._make_id(content)
        safe_meta = self._safe_metadata(metadata or {})
        safe_meta.setdefault("indexed_at", datetime.now().isoformat())
        safe_meta.setdefault("content_length", len(content))

        # ChromaDB chokes on very long documents — chunk if necessary
        chunks = self._chunk(content, max_chars=8000)
        ids = []
        for i, chunk in enumerate(chunks):
            cid = f"{doc_id}_chunk{i}" if len(chunks) > 1 else doc_id
            chunk_meta = {**safe_meta, "chunk_index": i, "total_chunks": len(chunks)}
            self.collection.upsert(
                ids=[cid],
                documents=[chunk],
                metadatas=[chunk_meta],
            )
            ids.append(cid)

        return doc_id

    def add_version(
        self,
        version_id: str,
        url: str,
        original: str,
        rewritten: str,
        style: str = "unknown",
        quality_score: float = 0.0,
    ):
        """Convenience: index both original and rewritten text for a version."""
        base_meta = {
            "version_id": version_id,
            "url": url,
            "style": style,
            "quality_score": quality_score,
        }
        self.add_content(
            original,
            metadata={**base_meta, "content_type": "original"},
            doc_id=f"{version_id}_orig",
        )
        self.add_content(
            rewritten,
            metadata={**base_meta, "content_type": "rewritten"},
            doc_id=f"{version_id}_rewritten",
        )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Similarity search.  Returns list of dicts with keys:
          id, content (snippet), metadata, distance
        """
        kwargs: dict = {
            "query_texts": [query],
            "n_results": min(n_results, self.collection.count() or 1),
        }
        if filters:
            kwargs["where"] = self._safe_metadata(filters)

        try:
            results = self.collection.query(**kwargs)
        except Exception as e:
            print(f"⚠️  ChromaDB query error: {e}")
            return []

        hits: List[Dict[str, Any]] = []
        if results and results["ids"] and results["ids"][0]:
            for idx in range(len(results["ids"][0])):
                doc = results["documents"][0][idx] if results["documents"] else ""
                hits.append(
                    {
                        "id": results["ids"][0][idx],
                        "content": doc[:500] + "..." if len(doc) > 500 else doc,
                        "metadata": results["metadatas"][0][idx] if results["metadatas"] else {},
                        "distance": results["distances"][0][idx] if results["distances"] else None,
                    }
                )
        return hits

    def search_by_url(self, url: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """Return all indexed content originating from *url*."""
        return self.search("", n_results=n_results, filters={"url": url})

    def search_by_style(self, style: str, query: str = "", n_results: int = 5) -> List[Dict[str, Any]]:
        """Filter search results to a specific writing style."""
        return self.search(query or f"{style} content", n_results=n_results, filters={"style": style})

    # ------------------------------------------------------------------
    # Stats & maintenance
    # ------------------------------------------------------------------
    def get_statistics(self) -> Dict[str, Any]:
        count = self.collection.count()
        return {
            "total_documents": count,
            "collection_name": self.collection.name,
        }

    def delete_version(self, version_id: str):
        """Remove all chunks belonging to a version."""
        try:
            self.collection.delete(where={"version_id": version_id})
        except Exception as e:
            print(f"⚠️  Delete failed: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _make_id(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    @staticmethod
    def _safe_metadata(meta: dict) -> dict:
        """ChromaDB only accepts str | int | float | bool values."""
        safe: dict = {}
        for k, v in meta.items():
            if isinstance(v, (str, int, float, bool)):
                safe[k] = v
            elif v is None:
                safe[k] = ""
            else:
                safe[k] = str(v)
        return safe

    @staticmethod
    def _chunk(text: str, max_chars: int = 8000) -> List[str]:
        if len(text) <= max_chars:
            return [text]
        chunks = []
        while text:
            chunks.append(text[:max_chars])
            text = text[max_chars:]
        return chunks
