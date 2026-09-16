"""
Qdrant semantic cache layer.

Embeds queries using FastEmbed (sentence-transformers/all-MiniLM-L6-v2)
and stores them in Qdrant. Before calling an LLM, checks for semantically
similar past queries — if similarity > threshold, returns cached response.
"""

import logging
import hashlib
from typing import Optional
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "query_cache"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.92  # Above this → cache hit
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension


@dataclass
class CacheHit:
    """Result from a cache hit."""
    response: str
    model_used: str
    provider: str
    query_type: str
    mode: str
    routing_reasoning: str
    score: float


class QdrantCache:
    """Semantic cache backed by Qdrant + FastEmbed."""

    def __init__(self):
        self._client = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the Qdrant client and create collection if needed."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import VectorParams, Distance

            self._client = QdrantClient(url=settings.qdrant_url, timeout=5)

            # Check if collection exists
            collections = self._client.get_collections().collections
            exists = any(c.name == COLLECTION_NAME for c in collections)

            if not exists:
                self._client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIM,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"✅ Created Qdrant collection '{COLLECTION_NAME}'")
            else:
                logger.info(f"✅ Qdrant collection '{COLLECTION_NAME}' exists")

            self._initialized = True
            return True

        except Exception as e:
            logger.warning(f"⚠️  Qdrant init failed: {e}")
            self._initialized = False
            return False

    def _embed(self, text: str) -> list[float]:
        """Embed text using FastEmbed."""
        from fastembed import TextEmbedding

        # Use a module-level cached embedding model
        if not hasattr(self, '_embedding_model'):
            self._embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL)

        embeddings = list(self._embedding_model.embed([text]))
        return embeddings[0].tolist()

    def _make_id(self, text: str) -> str:
        """Generate a deterministic point ID from text."""
        return hashlib.md5(text.encode()).hexdigest()

    def check_cache(self, query: str, mode: str) -> Optional[CacheHit]:
        """
        Check for semantically similar past queries.

        Returns CacheHit if similarity > threshold, else None.
        """
        if not self._initialized or not self._client:
            return None

        try:
            query_vector = self._embed(query)

            results = self._client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=1,
            )

            if results.points:
                top = results.points[0]
                if top.score >= SIMILARITY_THRESHOLD:
                    payload = top.payload
                    # Only return cache hit if the mode matches
                    if payload.get("mode") == mode:
                        logger.info(
                            f"🎯 Cache hit! score={top.score:.3f}, "
                            f"original='{payload.get('query_preview', '')[:50]}'"
                        )
                        return CacheHit(
                            response=payload["response"],
                            model_used=payload["model_used"],
                            provider=payload["provider"],
                            query_type=payload["query_type"],
                            mode=payload["mode"],
                            routing_reasoning=f"Cache hit (similarity: {top.score:.3f}). "
                                             f"Original query: '{payload.get('query_preview', '')}'",
                            score=top.score,
                        )

            return None

        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
            return None

    def store_in_cache(
        self,
        query: str,
        response: str,
        model_used: str,
        provider: str,
        query_type: str,
        mode: str,
        latency_ms: float,
    ) -> bool:
        """Store a query+response in the cache."""
        if not self._initialized or not self._client:
            return False

        try:
            from qdrant_client.models import PointStruct

            query_vector = self._embed(query)
            point_id = self._make_id(query + mode)

            self._client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=query_vector,
                        payload={
                            "query": query,
                            "query_preview": query[:200],
                            "response": response,
                            "model_used": model_used,
                            "provider": provider,
                            "query_type": query_type,
                            "mode": mode,
                            "latency_ms": latency_ms,
                        },
                    )
                ],
            )
            logger.debug(f"Cached query: '{query[:50]}...'")
            return True

        except Exception as e:
            logger.warning(f"Cache store failed: {e}")
            return False


# Singleton cache instance
cache = QdrantCache()
