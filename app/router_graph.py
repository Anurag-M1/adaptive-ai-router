"""
LangGraph routing decision graph.

Flow: classify → select_model → check_cache →(hit)→ END
                                            →(miss)→ call_llm → store_cache → log_decision → END
"""

import time
import logging
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END

from app.classifier import classify_query
from app.providers import select_model, call_llm

logger = logging.getLogger(__name__)


# ── Graph State ──────────────────────────────────────────────────────────

class RouterState(TypedDict):
    """Shared state flowing through the routing graph."""

    # Input
    query: str
    mode: str  # "speed" | "cost" | "quality"

    # Classification
    query_type: str
    classification_confidence: float
    classification_reasoning: str
    classification_method: str  # "keyword" or "llm"

    # Routing
    provider: str
    model: str
    routing_reasoning: str

    # Output
    response: str
    latency_ms: float
    cache_hit: bool

    # Logging
    log_id: Optional[int]

    # Error
    error: Optional[str]


# ── Node Functions ───────────────────────────────────────────────────────

async def classify_node(state: RouterState) -> dict:
    """Classify the incoming query using LLM or keyword fallback."""
    result = await classify_query(state["query"])
    return {
        "query_type": result["type"],
        "classification_confidence": result["confidence"],
        "classification_reasoning": result["reasoning"],
        "classification_method": result.get("method", "keyword"),
    }


def select_model_node(state: RouterState) -> dict:
    """Select the best model based on query type and mode."""
    provider, model = select_model(state["query_type"], state["mode"])

    method_label = "LLM" if state.get("classification_method") == "llm" else "keyword"
    reasoning = (
        f"Query classified as '{state['query_type']}' "
        f"via {method_label} analysis "
        f"(confidence: {state['classification_confidence']:.0%}). "
        f"Mode is '{state['mode']}'. "
        f"Routing to {provider}/{model}."
    )

    return {
        "provider": provider,
        "model": model,
        "routing_reasoning": reasoning,
    }


def check_cache_node(state: RouterState) -> dict:
    """Check Qdrant for semantically similar past queries."""
    try:
        from app.cache import cache

        hit = cache.check_cache(state["query"], state["mode"])
        if hit:
            return {
                "response": hit.response,
                "model_used": hit.model_used,
                "provider": hit.provider,
                "routing_reasoning": hit.routing_reasoning,
                "latency_ms": 0,  # Will be overwritten with total time
                "cache_hit": True,
                "error": None,
            }
    except Exception as e:
        logger.warning(f"Cache check failed: {e}")

    return {"cache_hit": False}


def cache_routing(state: RouterState) -> str:
    """Decide whether to use cached response or call LLM."""
    if state.get("cache_hit"):
        return "log_decision"
    return "call_llm"


async def call_llm_node(state: RouterState) -> dict:
    """Call the selected LLM provider."""
    try:
        response, latency_ms = await call_llm(
            state["provider"], state["model"], state["query"]
        )
        return {
            "response": response,
            "latency_ms": latency_ms,
            "cache_hit": False,
            "error": None,
        }
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {
            "response": f"Error: All LLM providers failed. {str(e)}",
            "latency_ms": 0,
            "cache_hit": False,
            "error": str(e),
        }


def store_cache_node(state: RouterState) -> dict:
    """Store the LLM response in Qdrant cache for future use."""
    if state.get("error"):
        return {}  # Don't cache errors

    try:
        from app.cache import cache

        cache.store_in_cache(
            query=state["query"],
            response=state["response"],
            model_used=state["model"],
            provider=state["provider"],
            query_type=state["query_type"],
            mode=state["mode"],
            latency_ms=state["latency_ms"],
        )
    except Exception as e:
        logger.warning(f"Cache store failed: {e}")

    return {}


async def log_decision_node(state: RouterState) -> dict:
    """Log the routing decision to PostgreSQL (non-blocking)."""
    try:
        from app.database import log_routing_decision

        log_id = await log_routing_decision(
            query=state["query"],
            query_type=state["query_type"],
            classification_confidence=state["classification_confidence"],
            classification_method=state.get("classification_method", "keyword"),
            mode=state["mode"],
            provider=state["provider"],
            model_used=state["model"],
            routing_reasoning=state["routing_reasoning"],
            latency_ms=state["latency_ms"],
            cache_hit=state.get("cache_hit", False),
            response=state.get("response", ""),
        )
        return {"log_id": log_id}
    except Exception as e:
        logger.warning(f"Logging failed (non-fatal): {e}")
        return {"log_id": None}


# ── Build the Graph ──────────────────────────────────────────────────────

def build_router_graph() -> StateGraph:
    """
    Construct and compile the LangGraph routing decision graph.

    Flow:
      START → classify → select_model → check_cache
        → (cache hit)  → log_decision → END
        → (cache miss) → call_llm → store_cache → log_decision → END
    """
    workflow = StateGraph(RouterState)

    # Add nodes
    workflow.add_node("classify", classify_node)
    workflow.add_node("select_model", select_model_node)
    workflow.add_node("check_cache", check_cache_node)
    workflow.add_node("call_llm", call_llm_node)
    workflow.add_node("store_cache", store_cache_node)
    workflow.add_node("log_decision", log_decision_node)

    # Wire edges
    workflow.add_edge(START, "classify")
    workflow.add_edge("classify", "select_model")
    workflow.add_edge("select_model", "check_cache")

    # Conditional: cache hit → log, cache miss → call LLM
    workflow.add_conditional_edges(
        "check_cache",
        cache_routing,
        {
            "log_decision": "log_decision",
            "call_llm": "call_llm",
        },
    )

    workflow.add_edge("call_llm", "store_cache")
    workflow.add_edge("store_cache", "log_decision")
    workflow.add_edge("log_decision", END)

    return workflow.compile()


# Singleton compiled graph
router_graph = build_router_graph()
