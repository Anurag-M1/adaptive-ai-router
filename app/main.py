"""
Adaptive AI Model Router — FastAPI Application

An intelligent LLM routing service that classifies queries and routes them
to the optimal model based on Speed / Cost / Quality mode selection.
"""

import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import RouteRequest, RouteResponse, HealthResponse
from app.router_graph import router_graph

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Track active stages
_active_stages = ["routing_endpoint", "llm_classifier"]


# ── Lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    providers = settings.available_providers
    if not providers:
        logger.warning(
            "⚠️  No LLM provider API keys configured! "
            "Set GROQ_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY in .env"
        )
    else:
        logger.info(f"✅ Available LLM providers: {', '.join(providers)}")

    # Initialize database (Stage 3)
    try:
        from app.database import init_db
        db_ok = await init_db()
        if db_ok:
            _active_stages.append("postgres_logging")
            logger.info("✅ PostgreSQL logging active")
        else:
            logger.warning("⚠️  PostgreSQL not available — logging disabled")
    except Exception as e:
        logger.warning(f"⚠️  Database init skipped: {e}")

    # Initialize Qdrant cache (Stage 4)
    try:
        from app.cache import cache
        cache_ok = await cache.initialize()
        if cache_ok:
            _active_stages.append("qdrant_cache")
            logger.info("✅ Qdrant semantic cache active")
        else:
            logger.warning("⚠️  Qdrant not available — caching disabled")
    except Exception as e:
        logger.warning(f"⚠️  Qdrant init skipped: {e}")

    logger.info("🚀 Adaptive AI Model Router is ready")
    yield
    logger.info("👋 Shutting down")


# ── App ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Adaptive AI Model Router",
    description=(
        "Intelligent LLM routing service that classifies queries and routes them "
        "to the optimal model based on Speed / Cost / Quality mode."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health check — shows available providers and active stages."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        available_providers=settings.available_providers,
        stages_active=_active_stages,
    )


@app.post("/route", response_model=RouteResponse, tags=["Routing"])
async def route_query(request: RouteRequest):
    """
    Route a query to the optimal LLM model.

    Classifies the query type (factual/reasoning/creative/code),
    selects the best model based on the chosen mode (speed/cost/quality),
    and returns the LLM response along with routing metadata.
    """
    start_time = time.perf_counter()

    try:
        # Run the LangGraph routing pipeline
        result = await router_graph.ainvoke({
            "query": request.query,
            "mode": request.mode,
            "query_type": "",
            "classification_confidence": 0.0,
            "classification_reasoning": "",
            "classification_method": "",
            "provider": "",
            "model": "",
            "routing_reasoning": "",
            "response": "",
            "latency_ms": 0.0,
            "cache_hit": False,
            "log_id": None,
            "error": None,
        })

        total_latency = (time.perf_counter() - start_time) * 1000

        if result.get("error"):
            raise HTTPException(status_code=502, detail=result["error"])

        logger.info(
            f"✅ Routed '{request.query[:50]}...' → "
            f"{result['provider']}/{result['model']} "
            f"({result['query_type']}, {request.mode}) "
            f"in {total_latency:.0f}ms"
        )

        return RouteResponse(
            response=result["response"],
            model_used=result["model"],
            provider=result["provider"],
            query_type=result["query_type"],
            mode=request.mode,
            routing_reasoning=result["routing_reasoning"],
            latency_ms=round(total_latency, 2),
            cache_hit=result.get("cache_hit", False),
            confidence=result.get("classification_confidence", 1.0),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Routing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs", tags=["Dashboard"])
async def get_logs(limit: int = 50):
    """Fetch recent routing decision logs for the dashboard."""
    try:
        from app.database import get_recent_logs
        logs = await get_recent_logs(limit=limit)
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        logger.warning(f"Logs endpoint failed: {e}")
        return {"logs": [], "count": 0, "error": str(e)}


@app.get("/models", tags=["System"])
async def list_models():
    """List the model routing matrix — shows which model handles each query type + mode combo."""
    from app.providers import ROUTING_MATRIX

    matrix = {}
    for (query_type, mode), (provider, model) in ROUTING_MATRIX.items():
        if query_type not in matrix:
            matrix[query_type] = {}
        matrix[query_type][mode] = {
            "provider": provider,
            "model": model,
            "available": provider in settings.available_providers,
        }

    return {
        "routing_matrix": matrix,
        "available_providers": settings.available_providers,
    }
