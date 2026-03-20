"""
FastAPI application for the CounterTrade Bot.
Provides the REST API, serves the frontend, and orchestrates the analysis pipeline.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import (
    create_entry,
    export_entries_csv,
    get_active_cooldown,
    get_entries,
    get_entry_by_id,
    get_portfolio_summary,
    get_stats,
    init_db,
    update_entry,
)
from backend.decision import generate_recommendation
from backend.emotion import detect_emotion, detect_emotion_rule_based, map_emotion_to_state
from backend.llm import (
    analyze_with_llm,
    check_llm_health,
    get_llm_recommendation,
    load_settings,
    save_settings,
)
from backend.models import (
    AnalysisResponse,
    ChatMessage,
    EmotionResult,
    JournalEntry,
    OverrideRequest,
    ReviewUpdate,
    StatsResponse,
)
from backend.notify import notify_if_needed
from backend.prices import get_prices, get_trending, get_fear_greed_index
from backend.rules import get_rules_raw, save_rules
from backend.streaks import analyze_streaks

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("countertrade")

# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    logger.info("Initializing database...")
    init_db()
    logger.info("CounterTrade Bot API ready.")
    yield


app = FastAPI(
    title="CounterTrade Bot",
    description="Emotional counter-trading assistant API",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static files (frontend)
# ---------------------------------------------------------------------------
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    from fastapi.responses import FileResponse

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(msg: ChatMessage):
    """
    Main analysis endpoint.
    Takes the trader's message, detects emotion, generates a contrarian
    recommendation, stores in the journal, and returns the full analysis.
    """
    text = msg.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message text cannot be empty.")

    market_context = msg.market_context

    # --- Step 1: Emotion detection ---
    # Try LLM first, fall back to rule-based
    llm_emotion = None
    llm_state = None
    try:
        llm_result = await analyze_with_llm(text, market_context)
        if llm_result:
            llm_emotion = EmotionResult(
                primary_emotion=llm_result.get("primary_emotion", "calm"),
                secondary_emotion=llm_result.get("secondary_emotion"),
                emotion_intensity=int(llm_result.get("emotion_intensity", 50)),
                confidence=int(llm_result.get("confidence", 50)),
            )
            llm_state = llm_result.get("state_label")
    except Exception as exc:
        logger.warning("LLM emotion analysis failed: %s", exc)

    # Rule-based (always run for comparison / fallback)
    rule_emotion = detect_emotion_rule_based(text)
    rule_state = map_emotion_to_state(rule_emotion, market_context)

    # Use LLM result if available and has reasonable confidence, else rule-based
    if llm_emotion and llm_emotion.confidence >= 40:
        emotion = llm_emotion
        state = llm_state or rule_state
    else:
        emotion = rule_emotion
        state = rule_state

    # --- Step 2: Generate recommendation ---
    llm_rec = None
    try:
        llm_rec = await get_llm_recommendation(emotion, state, market_context)
    except Exception as exc:
        logger.warning("LLM recommendation failed: %s", exc)

    result = generate_recommendation(
        emotion=emotion,
        state=state,
        market_context=market_context,
        llm_recommendation=llm_rec,
    )

    # --- Step 3: Store in database ---
    entry_data = {
        "raw_text": text,
        "asset": market_context.asset if market_context else None,
        "market_context_json": market_context.model_dump() if market_context else None,
        "primary_emotion": result["primary_emotion"],
        "secondary_emotion": result.get("secondary_emotion"),
        "emotion_intensity": result["emotion_intensity"],
        "emotion_confidence": result["confidence"],
        "state_label": result["state_label"],
        "recommended_action": result["recommended_action"],
        "conviction": result["conviction"],
        "reasoning": result["reasoning"],
        "distortion_risk": result.get("distortion_risk"),
        "disconfirming_evidence": result.get("disconfirming_evidence"),
        "guardrails": result.get("guardrails", []),
        "cooldown_minutes": result.get("cooldown_minutes", 0),
    }

    try:
        entry = create_entry(entry_data)
        entry_id = entry.id
    except Exception as exc:
        logger.error("Failed to save journal entry: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save analysis.") from exc

    # --- Step 4: Notify if needed ---
    try:
        await notify_if_needed(result)
    except Exception as exc:
        logger.warning("Notification dispatch failed: %s", exc)

    # --- Check for active cooldown ---
    cooldown_warning = None
    active_cd = get_active_cooldown()
    if active_cd and active_cd.get("entry_id") != entry_id:
        mins = active_cd["remaining_seconds"] // 60
        secs = active_cd["remaining_seconds"] % 60
        cooldown_warning = (
            f"You have an active cooldown ({mins}m {secs}s remaining) "
            f"from a previous {active_cd['state_label']} state. "
            f"Consider waiting before acting."
        )

    # --- Build response ---
    return AnalysisResponse(
        primary_emotion=result["primary_emotion"],
        secondary_emotion=result.get("secondary_emotion"),
        emotion_intensity=result["emotion_intensity"],
        confidence=result["confidence"],
        state_label=result["state_label"],
        recommended_action=result["recommended_action"],
        conviction=result["conviction"],
        reasoning=result["reasoning"],
        distortion_risk=result.get("distortion_risk", ""),
        disconfirming_evidence=result.get("disconfirming_evidence", ""),
        guardrails=result.get("guardrails", []),
        cooldown_minutes=result.get("cooldown_minutes", 0),
        entry_id=entry_id,
        cooldown_warning=cooldown_warning,
    )


@app.get("/api/journal")
async def list_journal(
    emotion: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    asset: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get journal entries with optional filters and pagination."""
    entries = get_entries(
        emotion=emotion,
        state=state,
        action=action,
        asset=asset,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return [JournalEntry.model_validate(e) for e in entries]


@app.get("/api/journal/export")
async def export_journal(
    emotion: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    asset: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """Export journal entries as a CSV file."""
    from fastapi.responses import Response

    csv_data = export_entries_csv(
        emotion=emotion,
        state=state,
        action=action,
        asset=asset,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=countertrade_journal.csv"},
    )


@app.get("/api/journal/{entry_id}")
async def get_journal_entry(entry_id: int):
    """Get a single journal entry by ID."""
    entry = get_entry_by_id(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    return JournalEntry.model_validate(entry)


@app.put("/api/journal/{entry_id}/review")
async def review_entry(entry_id: int, review: ReviewUpdate):
    """Update a journal entry with post-trade review data."""
    existing = get_entry_by_id(entry_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Journal entry not found.")

    update_data = review.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No review data provided.")

    updated = update_entry(entry_id, update_data)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update entry.")
    return JournalEntry.model_validate(updated)


@app.post("/api/journal/{entry_id}/override")
async def override_entry(entry_id: int, override: OverrideRequest):
    """Manual override of a recommendation."""
    existing = get_entry_by_id(entry_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Journal entry not found.")

    updated = update_entry(
        entry_id,
        {
            "manual_override": True,
            "override_action": override.override_action,
        },
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to apply override.")
    return JournalEntry.model_validate(updated)


@app.get("/api/stats", response_model=StatsResponse)
async def stats():
    """Get aggregate statistics from the journal."""
    return get_stats()


@app.get("/api/rules")
async def get_rules():
    """Get the current rule set."""
    return get_rules_raw()


@app.put("/api/rules")
async def update_rules(rules: list[dict]):
    """Replace the current rule set."""
    try:
        save_rules(rules)
        return {"status": "ok", "rules_count": len(rules)}
    except Exception as exc:
        logger.error("Failed to save rules: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save rules.") from exc


@app.get("/api/settings")
async def get_settings():
    """Get current application settings (sensitive fields redacted)."""
    settings = load_settings()
    # Redact sensitive fields for the frontend
    safe = dict(settings)
    if safe.get("telegram_bot_token"):
        safe["telegram_bot_token"] = "***" + safe["telegram_bot_token"][-4:]
    return safe


@app.put("/api/settings")
async def update_settings(new_settings: dict):
    """Update application settings."""
    current = load_settings()

    # Don't overwrite token with the redacted version
    if "telegram_bot_token" in new_settings:
        if new_settings["telegram_bot_token"].startswith("***"):
            new_settings.pop("telegram_bot_token")

    current.update(new_settings)
    try:
        save_settings(current)
        return {"status": "ok"}
    except Exception as exc:
        logger.error("Failed to save settings: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save settings.") from exc


@app.get("/api/prices")
async def prices(symbols: Optional[str] = Query(None)):
    """Get live crypto prices. Comma-separated symbols or defaults."""
    sym_list = symbols.split(",") if symbols else None
    return await get_prices(sym_list)


@app.get("/api/prices/trending")
async def trending():
    """Get trending coins from CoinGecko."""
    return await get_trending()


@app.get("/api/prices/fear-greed")
async def fear_greed():
    """Get the Crypto Fear & Greed Index."""
    return await get_fear_greed_index()


@app.get("/api/streaks")
async def streaks():
    """Get emotional streak analysis from recent journal entries."""
    entries = get_entries(limit=50)
    return analyze_streaks(entries)


@app.get("/api/cooldown")
async def cooldown():
    """Check if there's an active cooldown from a recent analysis."""
    result = get_active_cooldown()
    if result:
        return result
    return {"active": False}


@app.get("/api/portfolio")
async def portfolio():
    """Get portfolio summary grouped by asset."""
    return get_portfolio_summary()


@app.get("/api/health")
async def health():
    """Health check including LLM availability."""
    llm_status = await check_llm_health()
    return {
        "status": "ok",
        "llm": llm_status,
        "database": "ok",
    }
