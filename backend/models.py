"""
Pydantic models for the CounterTrade Bot API.
"""

import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MarketContext(BaseModel):
    """Optional market context provided alongside the trader's message."""

    asset: Optional[str] = None
    current_price: Optional[float] = None
    recent_move_pct: Optional[float] = None
    time_horizon: Optional[str] = None
    position_size: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    action_type: Optional[str] = None  # adding, reducing, exiting
    thesis: Optional[str] = None
    invalidation_level: Optional[float] = None


class ChatMessage(BaseModel):
    """Incoming message from the trader."""

    text: str
    market_context: Optional[MarketContext] = None


class EmotionResult(BaseModel):
    """Result of emotion detection."""

    primary_emotion: str
    secondary_emotion: Optional[str] = None
    emotion_intensity: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)


class AnalysisResponse(BaseModel):
    """Full analysis response returned to the frontend."""

    primary_emotion: str
    secondary_emotion: Optional[str] = None
    emotion_intensity: int
    confidence: int
    state_label: str
    recommended_action: str
    conviction: int
    reasoning: str
    distortion_risk: str
    disconfirming_evidence: str
    guardrails: list[str]
    cooldown_minutes: int
    entry_id: int
    cooldown_warning: Optional[str] = None


class JournalEntry(BaseModel):
    """Full journal entry matching the database schema."""

    id: int
    timestamp: datetime
    raw_text: str
    asset: Optional[str] = None
    market_context_json: Optional[dict | str] = None
    primary_emotion: str
    secondary_emotion: Optional[str] = None
    emotion_intensity: int
    emotion_confidence: int
    state_label: str
    recommended_action: str
    conviction: int
    reasoning: str
    risk_flags: Optional[list[str] | str] = None
    distortion_risk: Optional[str] = None
    disconfirming_evidence: Optional[str] = None
    guardrails: Optional[list[str] | str] = None
    cooldown_minutes: int = 0
    user_action_taken: Optional[str] = None
    notes_after_trade: Optional[str] = None
    pnl_after_trade: Optional[float] = None
    outcome_rating: Optional[str] = None
    manual_override: bool = False
    override_action: Optional[str] = None

    class Config:
        from_attributes = True

    @field_validator("guardrails", mode="before")
    @classmethod
    def parse_guardrails(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return [v]
        return v

    @field_validator("risk_flags", mode="before")
    @classmethod
    def parse_risk_flags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return [v]
        return v

    @field_validator("market_context_json", mode="before")
    @classmethod
    def parse_market_context(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v


class ReviewUpdate(BaseModel):
    """Data submitted when reviewing a past trade."""

    outcome_rating: Optional[str] = None  # bot_right, bot_wrong, emotion_wrong, too_aggressive, too_passive
    user_action_taken: Optional[str] = None
    notes_after_trade: Optional[str] = None
    pnl_after_trade: Optional[float] = None


class OverrideRequest(BaseModel):
    """Manual override of a recommendation."""

    entry_id: int
    override_action: str


class StatsResponse(BaseModel):
    """Aggregate statistics from the journal."""

    total_entries: int
    emotion_counts: dict[str, int]
    state_counts: dict[str, int]
    action_counts: dict[str, int]
    avg_intensity: float
    avg_conviction: float
    outcomes: dict[str, int]
    pnl_by_emotion: dict[str, float]
    pnl_by_followed: dict[str, object]
    override_rate: float
    total_pnl: float


class FilterParams(BaseModel):
    """Filter parameters for querying journal entries."""

    emotion: Optional[str] = None
    state: Optional[str] = None
    action: Optional[str] = None
    asset: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
