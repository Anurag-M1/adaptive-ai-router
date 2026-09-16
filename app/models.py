"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


# ── Request ──────────────────────────────────────────────────────────────

class RouteRequest(BaseModel):
    """Incoming routing request."""

    query: str = Field(..., min_length=1, max_length=4000, description="The user query to route")
    mode: Literal["speed", "cost", "quality"] = Field(
        default="speed",
        description="Routing mode: speed (fastest), cost (cheapest), quality (best output)",
    )


# ── Response ─────────────────────────────────────────────────────────────

class RouteResponse(BaseModel):
    """Response from the routing pipeline."""

    response: str = Field(..., description="The LLM-generated response")
    model_used: str = Field(..., description="Which model handled this query")
    provider: str = Field(..., description="LLM provider (groq, openai, gemini)")
    query_type: str = Field(..., description="Classified query type")
    mode: str = Field(..., description="The routing mode used")
    routing_reasoning: str = Field(..., description="Why this model was selected")
    latency_ms: float = Field(..., description="End-to-end latency in milliseconds")
    cache_hit: bool = Field(default=False, description="Whether response came from cache")
    confidence: float = Field(default=1.0, description="Classification confidence (0-1)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Health ───────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "0.1.0"
    available_providers: list[str] = []
    stages_active: list[str] = []
