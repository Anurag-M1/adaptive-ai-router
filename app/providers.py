"""
LLM provider wrappers — unified interface for calling Groq, OpenAI, and Gemini.
Each provider has a call function that takes a model name and prompt, returns the response text.
Includes automatic fallback: if the primary provider fails, tries the next available one.
"""

import time
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

# ── Model Routing Matrix ─────────────────────────────────────────────────
# Maps (query_type, mode) → (provider, model)

ROUTING_MATRIX: dict[tuple[str, str], tuple[str, str]] = {
    # Speed mode — Groq fast models
    ("factual", "speed"): ("groq", "groq/compound-mini"),
    ("reasoning", "speed"): ("groq", "qwen/qwen3.8-27b"),
    ("creative", "speed"): ("groq", "groq/compound-mini"),
    ("code", "speed"): ("groq", "qwen/qwen3.8-27b"),
    # Cost mode — Groq smallest/cheapest models
    ("factual", "cost"): ("groq", "allam-2-7b"),
    ("reasoning", "cost"): ("groq", "allam-2-7b"),
    ("creative", "cost"): ("groq", "allam-2-7b"),
    ("code", "cost"): ("groq", "allam-2-7b"),
    # Quality mode — Groq largest models (or OpenAI if available)
    ("factual", "quality"): ("groq", "openai/gpt-oss-120b"),
    ("reasoning", "quality"): ("groq", "openai/gpt-oss-120b"),
    ("creative", "quality"): ("groq", "openai/gpt-oss-120b"),
    ("code", "quality"): ("groq", "openai/gpt-oss-120b"),
}

# Fallback chain if a provider is unavailable
FALLBACK_CHAIN = {
    "groq": ["openai", "gemini"],
    "openai": ["groq", "gemini"],
    "gemini": ["groq", "openai"],
}

# Default models per provider (used for fallback)
DEFAULT_MODELS = {
    "groq": "groq/compound-mini",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
}


# ── Provider Call Functions ──────────────────────────────────────────────

async def call_groq(model: str, prompt: str) -> str:
    """Call Groq API."""
    from groq import AsyncGroq

    client = AsyncGroq(api_key=settings.groq_api_key)
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content


async def call_openai(model: str, prompt: str) -> str:
    """Call OpenAI API."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content


async def call_gemini(model: str, prompt: str) -> str:
    """Call Google Gemini API."""
    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text


# Provider dispatch map
_PROVIDERS = {
    "groq": call_groq,
    "openai": call_openai,
    "gemini": call_gemini,
}


# ── Unified Call with Fallback ───────────────────────────────────────────

def select_model(query_type: str, mode: str) -> tuple[str, str]:
    """
    Select the best (provider, model) for a given query type and mode.
    Falls back if the preferred provider has no API key configured.

    Returns:
        (provider, model) tuple
    """
    preferred_provider, preferred_model = ROUTING_MATRIX.get(
        (query_type, mode), ("groq", "llama-3.3-70b-versatile")
    )

    available = settings.available_providers

    # If preferred provider is available, use it
    if preferred_provider in available:
        return preferred_provider, preferred_model

    # Try fallback chain
    for fallback in FALLBACK_CHAIN.get(preferred_provider, []):
        if fallback in available:
            logger.warning(
                f"Provider '{preferred_provider}' unavailable, falling back to '{fallback}'"
            )
            return fallback, DEFAULT_MODELS[fallback]

    # Last resort: use whatever is available
    if available:
        fb = available[0]
        return fb, DEFAULT_MODELS[fb]

    raise RuntimeError(
        "No LLM providers configured! Set at least one of: "
        "GROQ_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY"
    )


async def call_llm(provider: str, model: str, prompt: str) -> tuple[str, float]:
    """
    Call the specified LLM provider with automatic fallback on failure.

    Returns:
        (response_text, latency_ms)
    """
    call_fn = _PROVIDERS.get(provider)
    if not call_fn:
        raise ValueError(f"Unknown provider: {provider}")

    start = time.perf_counter()
    try:
        response = await call_fn(model, prompt)
        latency_ms = (time.perf_counter() - start) * 1000
        return response, latency_ms
    except Exception as e:
        logger.error(f"Provider '{provider}' failed: {e}")
        # Try fallbacks
        for fallback in FALLBACK_CHAIN.get(provider, []):
            if fallback in settings.available_providers:
                fb_fn = _PROVIDERS[fallback]
                fb_model = DEFAULT_MODELS[fallback]
                try:
                    logger.info(f"Trying fallback provider: {fallback}/{fb_model}")
                    start = time.perf_counter()
                    response = await fb_fn(fb_model, prompt)
                    latency_ms = (time.perf_counter() - start) * 1000
                    return response, latency_ms
                except Exception as fb_e:
                    logger.error(f"Fallback '{fallback}' also failed: {fb_e}")
                    continue
        raise RuntimeError(f"All providers failed. Last error: {e}")
