"""
Database layer — SQLAlchemy async engine + RoutingLog model.

Logs every routing decision to PostgreSQL for the dashboard and analytics.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    create_engine,
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


# ── Base ─────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── RoutingLog Table ─────────────────────────────────────────────────────

class RoutingLog(Base):
    """Stores every routing decision for analytics and the dashboard."""

    __tablename__ = "routing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Query
    query = Column(Text, nullable=False)
    query_preview = Column(String(200), nullable=False)  # Truncated for display

    # Classification
    query_type = Column(String(20), nullable=False, index=True)  # factual/reasoning/creative/code
    classification_confidence = Column(Float, nullable=False)
    classification_method = Column(String(10), default="keyword")  # keyword/llm

    # Routing
    mode = Column(String(10), nullable=False, index=True)  # speed/cost/quality
    provider = Column(String(20), nullable=False, index=True)
    model_used = Column(String(100), nullable=False)
    routing_reasoning = Column(Text, nullable=True)

    # Performance
    latency_ms = Column(Float, nullable=False)
    cache_hit = Column(Boolean, default=False)

    # Response
    response_preview = Column(String(500), nullable=True)  # First 500 chars


# ── Engine & Session ─────────────────────────────────────────────────────

_engine: Optional[object] = None
_session_factory: Optional[async_sessionmaker] = None


def _get_engine():
    """Lazily create the async engine."""
    global _engine
    if _engine is None:
        if not settings.database_url:
            return None
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def _get_session_factory():
    """Lazily create the session factory."""
    global _session_factory
    if _session_factory is None:
        engine = _get_engine()
        if engine is None:
            return None
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


async def init_db():
    """Create tables if they don't exist."""
    engine = _get_engine()
    if engine is None:
        logger.warning("DATABASE_URL not configured — logging disabled")
        return False
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created/verified")
        return True
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        return False


async def log_routing_decision(
    query: str,
    query_type: str,
    classification_confidence: float,
    classification_method: str,
    mode: str,
    provider: str,
    model_used: str,
    routing_reasoning: str,
    latency_ms: float,
    cache_hit: bool,
    response: str,
) -> Optional[int]:
    """
    Log a routing decision to PostgreSQL.

    Returns:
        The log entry ID, or None if logging is disabled/failed.
    """
    factory = _get_session_factory()
    if factory is None:
        return None

    try:
        async with factory() as session:
            log_entry = RoutingLog(
                query=query,
                query_preview=query[:200],
                query_type=query_type,
                classification_confidence=classification_confidence,
                classification_method=classification_method,
                mode=mode,
                provider=provider,
                model_used=model_used,
                routing_reasoning=routing_reasoning,
                latency_ms=latency_ms,
                cache_hit=cache_hit,
                response_preview=response[:500] if response else None,
            )
            session.add(log_entry)
            await session.commit()
            logger.debug(f"Logged routing decision #{log_entry.id}")
            return log_entry.id
    except Exception as e:
        logger.error(f"Failed to log routing decision: {e}")
        return None


async def get_recent_logs(limit: int = 50) -> list[dict]:
    """Fetch recent routing logs for the dashboard."""
    factory = _get_session_factory()
    if factory is None:
        return []

    try:
        from sqlalchemy import select, desc
        async with factory() as session:
            result = await session.execute(
                select(RoutingLog)
                .order_by(desc(RoutingLog.timestamp))
                .limit(limit)
            )
            logs = result.scalars().all()
            return [
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "query_preview": log.query_preview,
                    "query_type": log.query_type,
                    "confidence": log.classification_confidence,
                    "method": log.classification_method,
                    "mode": log.mode,
                    "provider": log.provider,
                    "model_used": log.model_used,
                    "latency_ms": round(log.latency_ms, 1),
                    "cache_hit": log.cache_hit,
                    "response_preview": log.response_preview,
                }
                for log in logs
            ]
    except Exception as e:
        logger.error(f"Failed to fetch logs: {e}")
        return []
