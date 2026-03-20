"""
SQLAlchemy + SQLite database layer for CounterTrade Bot.
Stores journal entries with emotion analysis, recommendations, and trade outcomes.
"""

import json
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "countertrade.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class JournalEntryDB(Base):
    """SQLAlchemy model for journal entries."""

    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw_text = Column(String, nullable=False)
    asset = Column(String, nullable=True)
    market_context_json = Column(Text, nullable=True)
    primary_emotion = Column(String, nullable=False)
    secondary_emotion = Column(String, nullable=True)
    emotion_intensity = Column(Integer, nullable=False)
    emotion_confidence = Column(Integer, nullable=False)
    state_label = Column(String, nullable=False)
    recommended_action = Column(String, nullable=False)
    conviction = Column(Integer, nullable=False)
    reasoning = Column(Text, nullable=False)
    risk_flags = Column(Text, nullable=True)
    distortion_risk = Column(String, nullable=True)
    disconfirming_evidence = Column(Text, nullable=True)
    guardrails = Column(Text, nullable=True)
    cooldown_minutes = Column(Integer, default=0)
    user_action_taken = Column(String, nullable=True)
    notes_after_trade = Column(Text, nullable=True)
    pnl_after_trade = Column(Float, nullable=True)
    outcome_rating = Column(String, nullable=True)
    manual_override = Column(Boolean, default=False)
    override_action = Column(String, nullable=True)


def init_db() -> None:
    """Create all tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Get a new database session."""
    return SessionLocal()


def create_entry(data: dict) -> JournalEntryDB:
    """Create a new journal entry and return it."""
    session = get_session()
    try:
        # Serialize list/dict fields to JSON strings
        if "guardrails" in data and isinstance(data["guardrails"], list):
            data["guardrails"] = json.dumps(data["guardrails"])
        if "risk_flags" in data and isinstance(data["risk_flags"], list):
            data["risk_flags"] = json.dumps(data["risk_flags"])
        if "market_context_json" in data and isinstance(data["market_context_json"], dict):
            data["market_context_json"] = json.dumps(data["market_context_json"])

        entry = JournalEntryDB(**data)
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry
    finally:
        session.close()


def get_entries(
    emotion: Optional[str] = None,
    state: Optional[str] = None,
    action: Optional[str] = None,
    asset: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[JournalEntryDB]:
    """Get journal entries with optional filters and pagination."""
    session = get_session()
    try:
        query = session.query(JournalEntryDB)

        if emotion:
            query = query.filter(JournalEntryDB.primary_emotion == emotion)
        if state:
            query = query.filter(JournalEntryDB.state_label == state)
        if action:
            query = query.filter(JournalEntryDB.recommended_action == action)
        if asset:
            query = query.filter(JournalEntryDB.asset == asset)
        if date_from:
            query = query.filter(JournalEntryDB.timestamp >= date_from)
        if date_to:
            query = query.filter(JournalEntryDB.timestamp <= date_to)

        entries = (
            query.order_by(JournalEntryDB.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        # Detach from session
        session.expunge_all()
        return entries
    finally:
        session.close()


def get_entry_by_id(entry_id: int) -> Optional[JournalEntryDB]:
    """Get a single journal entry by ID."""
    session = get_session()
    try:
        entry = session.query(JournalEntryDB).filter(JournalEntryDB.id == entry_id).first()
        if entry:
            session.expunge(entry)
        return entry
    finally:
        session.close()


def update_entry(entry_id: int, data: dict) -> Optional[JournalEntryDB]:
    """Update a journal entry with the given data."""
    session = get_session()
    try:
        entry = session.query(JournalEntryDB).filter(JournalEntryDB.id == entry_id).first()
        if not entry:
            return None

        for key, value in data.items():
            if hasattr(entry, key) and value is not None:
                if key in ("guardrails", "risk_flags") and isinstance(value, list):
                    value = json.dumps(value)
                setattr(entry, key, value)

        session.commit()
        session.refresh(entry)
        session.expunge(entry)
        return entry
    finally:
        session.close()


def get_active_cooldown() -> Optional[dict]:
    """Check if there's an active cooldown from a recent journal entry."""
    session = get_session()
    try:
        # Find the most recent entry with a cooldown
        entry = (
            session.query(JournalEntryDB)
            .filter(JournalEntryDB.cooldown_minutes > 0)
            .order_by(JournalEntryDB.timestamp.desc())
            .first()
        )
        if not entry:
            return None

        from datetime import timedelta

        cooldown_end = entry.timestamp + timedelta(minutes=entry.cooldown_minutes)
        now = datetime.utcnow()
        if now < cooldown_end:
            remaining_seconds = int((cooldown_end - now).total_seconds())
            return {
                "active": True,
                "entry_id": entry.id,
                "started_at": entry.timestamp.isoformat(),
                "cooldown_minutes": entry.cooldown_minutes,
                "expires_at": cooldown_end.isoformat(),
                "remaining_seconds": remaining_seconds,
                "state_label": entry.state_label,
                "primary_emotion": entry.primary_emotion,
            }
        return None
    finally:
        session.close()


def get_portfolio_summary() -> list[dict]:
    """Get a summary of positions by asset from journal entries."""
    session = get_session()
    try:
        entries = (
            session.query(JournalEntryDB)
            .filter(JournalEntryDB.asset.isnot(None))
            .filter(JournalEntryDB.asset != "")
            .order_by(JournalEntryDB.timestamp.desc())
            .all()
        )

        asset_data: dict[str, dict] = {}
        for e in entries:
            asset = e.asset.upper()
            if asset not in asset_data:
                asset_data[asset] = {
                    "asset": asset,
                    "total_entries": 0,
                    "total_pnl": 0.0,
                    "last_emotion": e.primary_emotion,
                    "last_state": e.state_label,
                    "last_action": e.recommended_action,
                    "last_timestamp": e.timestamp.isoformat(),
                    "emotions": {},
                    "actions": {},
                }
            d = asset_data[asset]
            d["total_entries"] += 1
            if e.pnl_after_trade is not None:
                d["total_pnl"] += e.pnl_after_trade
            d["emotions"][e.primary_emotion] = d["emotions"].get(e.primary_emotion, 0) + 1
            d["actions"][e.recommended_action] = d["actions"].get(e.recommended_action, 0) + 1

        result = sorted(asset_data.values(), key=lambda x: x["total_entries"], reverse=True)
        for item in result:
            item["total_pnl"] = round(item["total_pnl"], 2)
        return result
    finally:
        session.close()


def export_entries_csv(
    emotion: Optional[str] = None,
    state: Optional[str] = None,
    action: Optional[str] = None,
    asset: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> str:
    """Export journal entries as CSV string."""
    import csv
    import io

    entries = get_entries(
        emotion=emotion,
        state=state,
        action=action,
        asset=asset,
        date_from=date_from,
        date_to=date_to,
        limit=10000,
        offset=0,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Timestamp", "Asset", "Raw Text", "Primary Emotion",
        "Secondary Emotion", "Intensity", "Confidence", "State",
        "Recommended Action", "Conviction", "Cooldown (min)",
        "Manual Override", "Override Action", "User Action Taken",
        "P/L After Trade", "Outcome Rating", "Notes",
    ])

    for e in entries:
        guardrails_str = ""
        if e.guardrails:
            try:
                guardrails_str = "; ".join(json.loads(e.guardrails))
            except (json.JSONDecodeError, TypeError):
                guardrails_str = str(e.guardrails)

        writer.writerow([
            e.id,
            e.timestamp.isoformat() if e.timestamp else "",
            e.asset or "",
            e.raw_text or "",
            e.primary_emotion or "",
            e.secondary_emotion or "",
            e.emotion_intensity,
            e.emotion_confidence,
            e.state_label or "",
            e.recommended_action or "",
            e.conviction,
            e.cooldown_minutes,
            "Yes" if e.manual_override else "No",
            e.override_action or "",
            e.user_action_taken or "",
            e.pnl_after_trade if e.pnl_after_trade is not None else "",
            e.outcome_rating or "",
            e.notes_after_trade or "",
        ])

    return output.getvalue()


def get_stats() -> dict:
    """Compute aggregate statistics from journal entries."""
    session = get_session()
    try:
        entries = session.query(JournalEntryDB).all()

        if not entries:
            return {
                "total_entries": 0,
                "emotion_counts": {},
                "state_counts": {},
                "action_counts": {},
                "avg_intensity": 0,
                "avg_conviction": 0,
                "outcomes": {},
                "pnl_by_emotion": {},
                "pnl_by_followed": {"followed": 0.0, "ignored": 0.0},
                "override_rate": 0.0,
                "total_pnl": 0.0,
            }

        emotion_counts: dict[str, int] = {}
        state_counts: dict[str, int] = {}
        action_counts: dict[str, int] = {}
        outcomes: dict[str, int] = {}
        pnl_by_emotion: dict[str, float] = {}
        pnl_followed = 0.0
        pnl_followed_count = 0
        pnl_ignored = 0.0
        pnl_ignored_count = 0
        total_pnl = 0.0
        intensity_sum = 0
        conviction_sum = 0
        override_count = 0

        for e in entries:
            emotion_counts[e.primary_emotion] = emotion_counts.get(e.primary_emotion, 0) + 1
            state_counts[e.state_label] = state_counts.get(e.state_label, 0) + 1
            action_counts[e.recommended_action] = action_counts.get(e.recommended_action, 0) + 1
            intensity_sum += e.emotion_intensity
            conviction_sum += e.conviction

            if e.outcome_rating:
                outcomes[e.outcome_rating] = outcomes.get(e.outcome_rating, 0) + 1

            if e.pnl_after_trade is not None:
                total_pnl += e.pnl_after_trade
                pnl_by_emotion[e.primary_emotion] = (
                    pnl_by_emotion.get(e.primary_emotion, 0.0) + e.pnl_after_trade
                )
                # Determine if user followed the bot's advice
                if e.user_action_taken and e.user_action_taken.lower() == e.recommended_action.lower():
                    pnl_followed += e.pnl_after_trade
                    pnl_followed_count += 1
                elif e.user_action_taken:
                    pnl_ignored += e.pnl_after_trade
                    pnl_ignored_count += 1

            if e.manual_override:
                override_count += 1

        n = len(entries)
        return {
            "total_entries": n,
            "emotion_counts": emotion_counts,
            "state_counts": state_counts,
            "action_counts": action_counts,
            "avg_intensity": round(intensity_sum / n, 1) if n else 0,
            "avg_conviction": round(conviction_sum / n, 1) if n else 0,
            "outcomes": outcomes,
            "pnl_by_emotion": pnl_by_emotion,
            "pnl_by_followed": {
                "followed": round(pnl_followed, 2),
                "followed_count": pnl_followed_count,
                "ignored": round(pnl_ignored, 2),
                "ignored_count": pnl_ignored_count,
            },
            "override_rate": round(override_count / n * 100, 1) if n else 0.0,
            "total_pnl": round(total_pnl, 2),
        }
    finally:
        session.close()
