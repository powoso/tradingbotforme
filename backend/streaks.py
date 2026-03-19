"""
Emotional streak and pattern detection for the CounterTrade Bot.
Analyzes recent journal entries to identify dangerous patterns
like consecutive emotional states, escalating intensity, or
repeated behavior.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from backend.database import get_entries, JournalEntryDB

logger = logging.getLogger(__name__)

# Dangerous emotional groups
DANGER_EMOTIONS = {"anger", "revenge", "panic", "despair", "capitulation"}
FOMO_EMOTIONS = {"fomo", "greed", "euphoria", "overconfidence"}
NEGATIVE_STATES = {"revenge-trading", "panic-selling", "FOMO-chasing", "tilted", "capitulation", "greed-top"}


def analyze_streaks(entries: list[JournalEntryDB]) -> dict[str, Any]:
    """
    Analyze a list of journal entries for emotional patterns and streaks.
    Returns a dict with streak info, pattern warnings, and insights.
    """
    if not entries:
        return {
            "current_streak": None,
            "longest_streak": None,
            "patterns": [],
            "warnings": [],
            "emotional_trend": "neutral",
            "intensity_trend": "stable",
            "recent_emotions": [],
        }

    # Sort by timestamp descending (most recent first)
    sorted_entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)

    # --- Current streak (consecutive same emotion) ---
    current_streak = _get_current_streak(sorted_entries)

    # --- Longest streak ---
    longest_streak = _get_longest_streak(sorted_entries)

    # --- Pattern detection ---
    patterns = _detect_patterns(sorted_entries)

    # --- Warnings ---
    warnings = _generate_warnings(sorted_entries, current_streak, patterns)

    # --- Emotional trend (last 5 entries vs previous 5) ---
    emotional_trend = _get_emotional_trend(sorted_entries)

    # --- Intensity trend ---
    intensity_trend = _get_intensity_trend(sorted_entries)

    # --- Recent emotions for display ---
    recent_emotions = [
        {
            "emotion": e.primary_emotion,
            "intensity": e.emotion_intensity,
            "state": e.state_label,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "action": e.recommended_action,
        }
        for e in sorted_entries[:10]
    ]

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "patterns": patterns,
        "warnings": warnings,
        "emotional_trend": emotional_trend,
        "intensity_trend": intensity_trend,
        "recent_emotions": recent_emotions,
    }


def _get_current_streak(entries: list[JournalEntryDB]) -> Optional[dict]:
    """Get the current streak of consecutive same emotions."""
    if not entries:
        return None

    current_emotion = entries[0].primary_emotion
    count = 1
    total_intensity = entries[0].emotion_intensity

    for e in entries[1:]:
        if e.primary_emotion == current_emotion:
            count += 1
            total_intensity += e.emotion_intensity
        else:
            break

    if count < 2:
        return None

    return {
        "emotion": current_emotion,
        "count": count,
        "avg_intensity": round(total_intensity / count, 1),
        "is_dangerous": current_emotion in DANGER_EMOTIONS or current_emotion in FOMO_EMOTIONS,
    }


def _get_longest_streak(entries: list[JournalEntryDB]) -> Optional[dict]:
    """Find the longest streak of any single emotion."""
    if not entries:
        return None

    # Sort chronologically for streak detection
    chronological = sorted(entries, key=lambda e: e.timestamp)

    best_emotion = chronological[0].primary_emotion
    best_count = 1
    current_emotion = chronological[0].primary_emotion
    current_count = 1

    for e in chronological[1:]:
        if e.primary_emotion == current_emotion:
            current_count += 1
        else:
            if current_count > best_count:
                best_count = current_count
                best_emotion = current_emotion
            current_emotion = e.primary_emotion
            current_count = 1

    if current_count > best_count:
        best_count = current_count
        best_emotion = current_emotion

    if best_count < 2:
        return None

    return {
        "emotion": best_emotion,
        "count": best_count,
    }


def _detect_patterns(entries: list[JournalEntryDB]) -> list[dict]:
    """Detect behavioral patterns in recent entries."""
    patterns = []
    recent = entries[:10]

    if len(recent) < 3:
        return patterns

    # Pattern: Escalating intensity
    intensities = [e.emotion_intensity for e in recent[:5]]
    if len(intensities) >= 3:
        if all(intensities[i] >= intensities[i + 1] for i in range(len(intensities) - 1)):
            patterns.append({
                "type": "escalating_intensity",
                "label": "Escalating Emotions",
                "description": "Your emotional intensity has been increasing with each entry.",
                "severity": "high" if intensities[0] > 70 else "medium",
            })

    # Pattern: Flip-flopping (alternating emotions)
    emotions = [e.primary_emotion for e in recent[:6]]
    if len(emotions) >= 4:
        unique_last_4 = len(set(emotions[:4]))
        if unique_last_4 >= 3:
            patterns.append({
                "type": "flip_flopping",
                "label": "Emotional Whiplash",
                "description": "You're cycling through different emotions rapidly. This suggests uncertainty.",
                "severity": "medium",
            })

    # Pattern: Revenge cycle (anger -> trade -> anger)
    danger_count = sum(1 for e in recent[:5] if e.primary_emotion in DANGER_EMOTIONS)
    if danger_count >= 3:
        patterns.append({
            "type": "danger_cycle",
            "label": "Danger Zone",
            "description": f"{danger_count} of your last 5 entries show dangerous emotional states.",
            "severity": "high",
        })

    # Pattern: FOMO spiral
    fomo_count = sum(1 for e in recent[:5] if e.primary_emotion in FOMO_EMOTIONS)
    if fomo_count >= 3:
        patterns.append({
            "type": "fomo_spiral",
            "label": "FOMO Spiral",
            "description": f"{fomo_count} of your last 5 entries show FOMO/greed emotions.",
            "severity": "high",
        })

    # Pattern: Ignoring bot advice
    overrides = sum(1 for e in recent[:5] if e.manual_override)
    if overrides >= 3:
        patterns.append({
            "type": "ignoring_advice",
            "label": "Ignoring the Bot",
            "description": f"You've overridden {overrides} of the last 5 recommendations.",
            "severity": "medium",
        })

    # Pattern: High frequency trading
    if len(recent) >= 3:
        timestamps = [e.timestamp for e in recent[:3] if e.timestamp]
        if len(timestamps) >= 3:
            time_span = (timestamps[0] - timestamps[2]).total_seconds()
            if time_span < 1800:  # 3 entries in 30 minutes
                patterns.append({
                    "type": "rapid_fire",
                    "label": "Rapid Fire",
                    "description": "You've made 3+ entries in under 30 minutes. Slow down.",
                    "severity": "high",
                })

    return patterns


def _generate_warnings(
    entries: list[JournalEntryDB],
    current_streak: Optional[dict],
    patterns: list[dict],
) -> list[str]:
    """Generate human-readable warnings based on streaks and patterns."""
    warnings = []

    if current_streak and current_streak["is_dangerous"]:
        warnings.append(
            f"You're on a {current_streak['count']}-entry streak of "
            f"{current_streak['emotion']} (avg intensity: {current_streak['avg_intensity']}). "
            f"Consider stepping away."
        )

    for p in patterns:
        if p["severity"] == "high":
            warnings.append(p["description"])

    # Check if last entry was high intensity
    if entries and entries[0].emotion_intensity > 80:
        warnings.append(
            f"Your last entry showed very high emotional intensity "
            f"({entries[0].emotion_intensity}/100). Tread carefully."
        )

    return warnings


def _get_emotional_trend(entries: list[JournalEntryDB]) -> str:
    """Determine if emotions are trending positive, negative, or neutral."""
    if len(entries) < 4:
        return "neutral"

    recent = entries[:3]
    older = entries[3:6]

    if not older:
        return "neutral"

    recent_danger = sum(1 for e in recent if e.primary_emotion in DANGER_EMOTIONS | FOMO_EMOTIONS)
    older_danger = sum(1 for e in older if e.primary_emotion in DANGER_EMOTIONS | FOMO_EMOTIONS)

    if recent_danger > older_danger:
        return "worsening"
    elif recent_danger < older_danger:
        return "improving"
    return "stable"


def _get_intensity_trend(entries: list[JournalEntryDB]) -> str:
    """Determine if emotional intensity is trending up, down, or stable."""
    if len(entries) < 4:
        return "stable"

    recent_avg = sum(e.emotion_intensity for e in entries[:3]) / 3
    older_avg = sum(e.emotion_intensity for e in entries[3:6]) / max(len(entries[3:6]), 1)

    diff = recent_avg - older_avg
    if diff > 10:
        return "rising"
    elif diff < -10:
        return "falling"
    return "stable"
