"""
Query classifier — determines the type of incoming query.

Stage 1: Keyword-based heuristic (fast, no API call)
Stage 2: LLM-powered classification via Groq (more accurate, with keyword fallback)
"""

import re
import json
import logging
from typing import Literal

QueryType = Literal["factual", "reasoning", "creative", "code"]

logger = logging.getLogger(__name__)


# ── Keyword patterns (Stage 1 — always available as fallback) ────────────

_CODE_PATTERNS = re.compile(
    r"\b(code|function|debug|error|traceback|implement|refactor|script|program|"
    r"class\b|def\b|import|syntax|compile|runtime|api|endpoint|algorithm|"
    r"regex|sql|html|css|javascript|python|java|rust|golang|typescript|"
    r"react|docker|kubernetes|git|bash|terminal|cli|npm|pip)\b",
    re.IGNORECASE,
)

_CREATIVE_PATTERNS = re.compile(
    r"\b(write|story|poem|creative|imagine|fiction|song|lyrics|essay|"
    r"blog|article|draft|compose|narrative|metaphor|describe\s+a|"
    r"generate\s+a|brainstorm|idea|slogan|tagline|script|dialogue)\b",
    re.IGNORECASE,
)

_REASONING_PATTERNS = re.compile(
    r"\b(why|explain|analyze|compare|contrast|evaluate|reason|cause|"
    r"effect|implication|consequence|pros?\s+and\s+cons?|trade.?off|"
    r"should\s+i|difference\s+between|how\s+does|think\s+through|"
    r"step\s+by\s+step|logic|argument|debate|critical|assessment)\b",
    re.IGNORECASE,
)


def classify_query_keywords(text: str) -> dict:
    """
    Classify a query using keyword heuristics (fast, zero API cost).

    Returns:
        dict with keys: type, confidence, reasoning, method
    """
    # Score each category
    code_hits = len(_CODE_PATTERNS.findall(text))
    creative_hits = len(_CREATIVE_PATTERNS.findall(text))
    reasoning_hits = len(_REASONING_PATTERNS.findall(text))

    scores = {
        "code": code_hits * 2,  # Code keywords are strong signals
        "creative": creative_hits * 1.5,
        "reasoning": reasoning_hits * 1.5,
        "factual": 1,  # Default baseline
    }

    # Pick the highest scoring type
    best_type = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = scores[best_type] / total if total > 0 else 0.5

    # Build reasoning
    if best_type == "factual":
        reasoning = "No strong code/creative/reasoning signals detected; defaulting to factual."
    else:
        reasoning = f"Detected {best_type} keywords ({scores[best_type]:.0f} signal strength)."

    return {
        "type": best_type,
        "confidence": round(min(confidence, 1.0), 2),
        "reasoning": reasoning,
        "method": "keyword",
    }


# ── LLM-powered classification (Stage 2) ────────────────────────────────

_CLASSIFICATION_PROMPT = """You are a query classifier. Classify the user's query into exactly ONE of these categories:

- **factual**: Simple factual questions, lookups, definitions, "what is X", "who is Y"
- **reasoning**: Analytical thinking, comparisons, cause-effect, "why", "explain how", multi-step logic
- **creative**: Writing tasks, storytelling, brainstorming, generating content, poems, essays
- **code**: Programming, debugging, code generation, technical implementation, DevOps

Respond with ONLY valid JSON (no markdown, no explanation):
{{"type": "<factual|reasoning|creative|code>", "confidence": <0.0-1.0>, "reasoning": "<one sentence why>"}}

User query: {query}"""


async def classify_query_llm(text: str) -> dict:
    """
    Classify a query using a fast LLM call (Groq llama-3.1-8b).
    Falls back to keyword classification if LLM call fails.

    Returns:
        dict with keys: type, confidence, reasoning, method
    """
    from app.config import settings

    # Need at least one provider for LLM classification
    if not settings.available_providers:
        logger.info("No LLM providers available, falling back to keyword classifier")
        return classify_query_keywords(text)

    try:
        # Use the fastest available provider for classification
        if "groq" in settings.available_providers:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=settings.groq_api_key)
            response = await client.chat.completions.create(
                model="groq/compound-mini",  # Fast model for classification
                messages=[{"role": "user", "content": _CLASSIFICATION_PROMPT.format(query=text)}],
                temperature=0.1,  # Low temp for consistent classification
                max_tokens=100,
            )
            raw = response.choices[0].message.content.strip()

        elif "openai" in settings.available_providers:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": _CLASSIFICATION_PROMPT.format(query=text)}],
                temperature=0.1,
                max_tokens=100,
            )
            raw = response.choices[0].message.content.strip()

        elif "gemini" in settings.available_providers:
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            response = await client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=_CLASSIFICATION_PROMPT.format(query=text),
            )
            raw = response.text.strip()

        else:
            return classify_query_keywords(text)

        # Parse the JSON response
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(raw)

        # Validate the response
        valid_types = {"factual", "reasoning", "creative", "code"}
        if result.get("type") not in valid_types:
            logger.warning(f"LLM returned invalid type: {result.get('type')}, falling back")
            return classify_query_keywords(text)

        return {
            "type": result["type"],
            "confidence": round(min(max(float(result.get("confidence", 0.8)), 0.0), 1.0), 2),
            "reasoning": result.get("reasoning", "LLM classification"),
            "method": "llm",
        }

    except Exception as e:
        logger.warning(f"LLM classification failed ({e}), falling back to keyword classifier")
        return classify_query_keywords(text)


# ── Unified classifier (auto-selects best method) ───────────────────────

async def classify_query(text: str) -> dict:
    """
    Classify a query using the best available method.
    Tries LLM classification first, falls back to keywords.

    Returns:
        dict with keys: type, confidence, reasoning, method
    """
    return await classify_query_llm(text)
