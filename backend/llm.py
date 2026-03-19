"""
LLM integration for the CounterTrade Bot.
Supports Ollama and LM Studio backends. Falls back to rule-based analysis
when no LLM is available.
"""

import json
import logging
import os
from typing import Any, Optional

import httpx

from backend.models import EmotionResult, MarketContext

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_PATH = os.path.join(BASE_DIR, "config", "settings.json")

# Defaults when no settings file exists
DEFAULT_SETTINGS: dict[str, Any] = {
    "llm_backend": "ollama",  # "ollama" or "lmstudio"
    "ollama_url": "http://localhost:11434/api/generate",
    "lmstudio_url": "http://localhost:1234/v1/chat/completions",
    "model_name": "llama3",
    "llm_timeout": 30,
    "use_llm": True,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "notifications_enabled": False,
}


def load_settings() -> dict[str, Any]:
    """Load settings from config/settings.json, creating defaults if missing."""
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r") as f:
                stored = json.load(f)
            # Merge with defaults so new keys are always present
            merged = {**DEFAULT_SETTINGS, **stored}
            return merged
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read settings: %s. Using defaults.", exc)
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict[str, Any]) -> None:
    """Persist settings to config/settings.json."""
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)


def _build_emotion_prompt(text: str, market_context: Optional[MarketContext]) -> str:
    """Build the prompt for emotion analysis."""
    ctx_section = ""
    if market_context:
        ctx_parts = []
        if market_context.asset:
            ctx_parts.append(f"Asset: {market_context.asset}")
        if market_context.current_price is not None:
            ctx_parts.append(f"Current price: {market_context.current_price}")
        if market_context.recent_move_pct is not None:
            ctx_parts.append(f"Recent move: {market_context.recent_move_pct}%")
        if market_context.unrealized_pnl is not None:
            ctx_parts.append(f"Unrealized P/L: {market_context.unrealized_pnl}")
        if market_context.action_type:
            ctx_parts.append(f"Planned action: {market_context.action_type}")
        if market_context.thesis:
            ctx_parts.append(f"Thesis: {market_context.thesis}")
        if ctx_parts:
            ctx_section = "\n\nMarket context:\n" + "\n".join(ctx_parts)

    return f"""You are an expert trading psychologist analyzing a trader's emotional state.
Analyze the following message from a trader and determine their emotional state.

Trader's message:
\"{text}\"{ctx_section}

Respond ONLY with valid JSON (no markdown, no explanation) in this exact format:
{{
  "primary_emotion": "<one of: anger, despair, capitulation, revenge, fomo, panic, greed, euphoria, exhaustion, overconfidence, fear, calm>",
  "secondary_emotion": "<same options or null>",
  "emotion_intensity": <0-100>,
  "confidence": <0-100>,
  "state_label": "<one of: capitulation, panic-selling, revenge-trading, FOMO-chasing, greed-top, tilted, calm, uncertain>"
}}"""


def _build_recommendation_prompt(
    emotion: EmotionResult,
    state: str,
    market_context: Optional[MarketContext],
    rules: Optional[list[dict]] = None,
) -> str:
    """Build the prompt for generating a trading recommendation."""
    ctx_section = ""
    if market_context:
        ctx_section = f"""
Market context:
- Asset: {market_context.asset or 'unknown'}
- Price: {market_context.current_price or 'unknown'}
- Recent move: {market_context.recent_move_pct or 'unknown'}%
- Unrealized P/L: {market_context.unrealized_pnl or 'unknown'}
- Planned action: {market_context.action_type or 'unknown'}
- Thesis: {market_context.thesis or 'none provided'}
- Invalidation: {market_context.invalidation_level or 'not set'}"""

    rules_section = ""
    if rules:
        rules_section = "\n\nApplicable rules:\n" + json.dumps(rules, indent=2)

    return f"""You are the CounterTrade Bot, an emotional counter-trading assistant.
A trader is experiencing the following emotional state:
- Primary emotion: {emotion.primary_emotion}
- Secondary emotion: {emotion.secondary_emotion or 'none'}
- Intensity: {emotion.emotion_intensity}/100
- Detected state: {state}
{ctx_section}{rules_section}

Your job is to provide a contrarian recommendation that counters the trader's emotional bias.
If the trader is panic-selling, you might recommend holding or buying.
If the trader is FOMO-chasing, you might recommend waiting or selling.

Respond ONLY with valid JSON:
{{
  "recommended_action": "<BUY|SELL|HOLD|WAIT|REDUCE|NO_TRADE>",
  "conviction": <0-100>,
  "reasoning": "<2-4 sentences explaining why>",
  "distortion_risk": "<cognitive distortion at play>",
  "disconfirming_evidence": "<what would prove the trader's impulse correct>",
  "guardrails": ["<list of specific guardrails/conditions>"],
  "cooldown_minutes": <0-60>
}}"""


def _parse_json_response(text: str) -> Optional[dict]:
    """Extract and parse JSON from an LLM response, handling markdown fences."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Try to find JSON object in the text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


async def _call_ollama(prompt: str, settings: dict) -> Optional[str]:
    """Call the Ollama API and return the response text."""
    url = settings.get("ollama_url", DEFAULT_SETTINGS["ollama_url"])
    model = settings.get("model_name", DEFAULT_SETTINGS["model_name"])
    timeout = settings.get("llm_timeout", DEFAULT_SETTINGS["llm_timeout"])

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3},
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
    except Exception as exc:
        logger.warning("Ollama call failed: %s", exc)
        return None


async def _call_lmstudio(prompt: str, settings: dict) -> Optional[str]:
    """Call the LM Studio OpenAI-compatible API and return the response text."""
    url = settings.get("lmstudio_url", DEFAULT_SETTINGS["lmstudio_url"])
    model = settings.get("model_name", DEFAULT_SETTINGS["model_name"])
    timeout = settings.get("llm_timeout", DEFAULT_SETTINGS["llm_timeout"])

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return None
    except Exception as exc:
        logger.warning("LM Studio call failed: %s", exc)
        return None


async def _call_llm(prompt: str, settings: Optional[dict] = None) -> Optional[str]:
    """Route to the configured LLM backend."""
    if settings is None:
        settings = load_settings()
    backend = settings.get("llm_backend", "ollama")
    if backend == "lmstudio":
        return await _call_lmstudio(prompt, settings)
    return await _call_ollama(prompt, settings)


async def analyze_with_llm(
    text: str,
    market_context: Optional[MarketContext] = None,
) -> Optional[dict]:
    """
    Use the configured LLM to analyze emotional state.
    Returns a dict with primary_emotion, secondary_emotion, intensity, confidence,
    state_label -- or None if the LLM is unavailable.
    """
    settings = load_settings()
    if not settings.get("use_llm", True):
        return None

    prompt = _build_emotion_prompt(text, market_context)
    raw = await _call_llm(prompt, settings)
    if not raw:
        return None

    parsed = _parse_json_response(raw)
    if not parsed:
        logger.warning("Could not parse LLM emotion response: %s", raw[:200])
        return None

    # Validate required fields
    required = ["primary_emotion", "emotion_intensity", "confidence"]
    if all(k in parsed for k in required):
        return parsed
    logger.warning("LLM response missing required fields: %s", list(parsed.keys()))
    return None


async def get_llm_recommendation(
    emotion: EmotionResult,
    state: str,
    market_context: Optional[MarketContext] = None,
    rules: Optional[list[dict]] = None,
) -> Optional[dict]:
    """
    Use the configured LLM to generate a trading recommendation.
    Returns a dict with recommended_action, conviction, reasoning, etc.
    or None if the LLM is unavailable.
    """
    settings = load_settings()
    if not settings.get("use_llm", True):
        return None

    prompt = _build_recommendation_prompt(emotion, state, market_context, rules)
    raw = await _call_llm(prompt, settings)
    if not raw:
        return None

    parsed = _parse_json_response(raw)
    if not parsed:
        logger.warning("Could not parse LLM recommendation response: %s", raw[:200])
        return None

    if "recommended_action" in parsed:
        return parsed
    logger.warning("LLM recommendation missing recommended_action")
    return None


async def check_llm_health() -> dict[str, Any]:
    """Check if the configured LLM backend is reachable."""
    settings = load_settings()
    backend = settings.get("llm_backend", "ollama")
    result: dict[str, Any] = {
        "backend": backend,
        "model": settings.get("model_name", "unknown"),
        "available": False,
    }

    try:
        if backend == "ollama":
            # Ollama has a simple tags endpoint
            base = settings.get("ollama_url", DEFAULT_SETTINGS["ollama_url"])
            health_url = base.rsplit("/", 2)[0] + "/api/tags"
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(health_url)
                result["available"] = resp.status_code == 200
        else:
            # LM Studio - try the models endpoint
            base = settings.get("lmstudio_url", DEFAULT_SETTINGS["lmstudio_url"])
            health_url = base.rsplit("/", 2)[0] + "/v1/models"
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(health_url)
                result["available"] = resp.status_code == 200
    except Exception as exc:
        logger.debug("LLM health check failed: %s", exc)
        result["available"] = False

    return result
