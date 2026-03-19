"""
Rule engine for the CounterTrade Bot.
Loads configurable rules from config/rules.json and matches them against
the current emotional state and market context.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.models import EmotionResult, MarketContext

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_PATH = os.path.join(BASE_DIR, "config", "rules.json")


@dataclass
class Rule:
    """A single decision rule."""

    name: str
    conditions: dict[str, Any]
    action: str
    conviction_range: tuple[int, int] = (50, 70)
    guardrails: list[str] = field(default_factory=list)
    cooldown: int = 0
    priority: int = 0


# Default rules used when no config/rules.json exists
DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "name": "capitulation_buy",
        "conditions": {
            "state": "capitulation",
            "intensity_min": 50,
        },
        "action": "BUY",
        "conviction_range": [60, 80],
        "guardrails": [
            "Only if no new bearish fundamental thesis",
            "Scale in with small position (25-50%)",
            "Set tight stop loss",
        ],
        "cooldown": 0,
        "priority": 10,
    },
    {
        "name": "panic_selling_wait",
        "conditions": {
            "state": "panic-selling",
        },
        "action": "WAIT",
        "conviction_range": [50, 70],
        "guardrails": [
            "Do not market-sell",
            "Re-evaluate in 15 minutes",
            "Use limit orders only",
        ],
        "cooldown": 15,
        "priority": 10,
    },
    {
        "name": "revenge_no_trade",
        "conditions": {
            "emotion": "revenge",
        },
        "action": "NO_TRADE",
        "conviction_range": [80, 90],
        "guardrails": [
            "Mandatory 30-minute cooldown",
            "Write down thesis before any trade",
            "Max position size = standard or smaller",
        ],
        "cooldown": 30,
        "priority": 20,
    },
    {
        "name": "revenge_trading_state",
        "conditions": {
            "state": "revenge-trading",
        },
        "action": "NO_TRADE",
        "conviction_range": [80, 90],
        "guardrails": [
            "Mandatory 30-minute cooldown",
            "Write down thesis before any trade",
        ],
        "cooldown": 30,
        "priority": 20,
    },
    {
        "name": "fomo_chasing_wait",
        "conditions": {
            "state": "FOMO-chasing",
        },
        "action": "WAIT",
        "conviction_range": [60, 80],
        "guardrails": [
            "Wait for a pullback",
            "Size at 50% or less",
            "Use limit orders below current price",
        ],
        "cooldown": 10,
        "priority": 10,
    },
    {
        "name": "greed_top_reduce",
        "conditions": {
            "state": "greed-top",
        },
        "action": "REDUCE",
        "conviction_range": [60, 75],
        "guardrails": [
            "Take partial profits (25-50%)",
            "Move stop to break-even",
        ],
        "cooldown": 0,
        "priority": 10,
    },
    {
        "name": "tilted_no_trade",
        "conditions": {
            "state": "tilted",
        },
        "action": "NO_TRADE",
        "conviction_range": [85, 85],
        "guardrails": [
            "Close the trading app",
            "No trades until rested",
            "Review journal before resuming",
        ],
        "cooldown": 60,
        "priority": 15,
    },
    {
        "name": "high_intensity_anger",
        "conditions": {
            "emotion": "anger",
            "intensity_min": 70,
        },
        "action": "NO_TRADE",
        "conviction_range": [75, 90],
        "guardrails": [
            "Step away from the screen",
            "Mandatory cooldown",
        ],
        "cooldown": 30,
        "priority": 15,
    },
    {
        "name": "overconfidence_reduce",
        "conditions": {
            "emotion": "overconfidence",
            "intensity_min": 60,
        },
        "action": "REDUCE",
        "conviction_range": [55, 70],
        "guardrails": [
            "Complete confirmation checklist",
            "List 3 ways this could fail",
        ],
        "cooldown": 0,
        "priority": 10,
    },
    {
        "name": "calm_hold",
        "conditions": {
            "state": "calm",
        },
        "action": "HOLD",
        "conviction_range": [30, 50],
        "guardrails": [
            "Emotional state is neutral -- trust your own analysis",
        ],
        "cooldown": 0,
        "priority": 1,
    },
]


def _parse_rule(data: dict) -> Rule:
    """Parse a dict into a Rule dataclass."""
    conv = data.get("conviction_range", [50, 70])
    return Rule(
        name=data.get("name", "unnamed"),
        conditions=data.get("conditions", {}),
        action=data.get("action", "WAIT"),
        conviction_range=(int(conv[0]), int(conv[1])),
        guardrails=data.get("guardrails", []),
        cooldown=data.get("cooldown", 0),
        priority=data.get("priority", 0),
    )


def load_rules(path: Optional[str] = None) -> list[Rule]:
    """Load rules from a JSON file. Falls back to built-in defaults."""
    path = path or RULES_PATH
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                return [_parse_rule(r) for r in raw]
            logger.warning("rules.json is not a list; using defaults")
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load rules: %s. Using defaults.", exc)
    return [_parse_rule(r) for r in DEFAULT_RULES]


def save_rules(rules_data: list[dict], path: Optional[str] = None) -> None:
    """Save rules to config/rules.json."""
    path = path or RULES_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(rules_data, f, indent=2)


def get_rules_raw(path: Optional[str] = None) -> list[dict]:
    """Return rules as raw dicts (for API serialization)."""
    path = path or RULES_PATH
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                return raw
        except (json.JSONDecodeError, OSError):
            pass
    return list(DEFAULT_RULES)


def match_rules(
    emotion: EmotionResult,
    state: str,
    market_context: Optional[MarketContext] = None,
) -> list[Rule]:
    """Find all rules whose conditions match the current state."""
    rules = load_rules()
    matched: list[Rule] = []

    for rule in rules:
        conds = rule.conditions
        match = True

        # Check emotion condition
        if "emotion" in conds:
            if conds["emotion"] != emotion.primary_emotion:
                match = False

        # Check state condition
        if "state" in conds:
            if conds["state"] != state:
                match = False

        # Check intensity range
        if "intensity_min" in conds:
            if emotion.emotion_intensity < conds["intensity_min"]:
                match = False
        if "intensity_max" in conds:
            if emotion.emotion_intensity > conds["intensity_max"]:
                match = False

        # Check confidence range
        if "confidence_min" in conds:
            if emotion.confidence < conds["confidence_min"]:
                match = False
        if "confidence_max" in conds:
            if emotion.confidence > conds["confidence_max"]:
                match = False

        # Check asset
        if "asset" in conds and market_context:
            if market_context.asset and conds["asset"].lower() != market_context.asset.lower():
                match = False

        if match:
            matched.append(rule)

    return matched


def get_best_rule(matched_rules: list[Rule]) -> Optional[Rule]:
    """Return the highest-priority matched rule."""
    if not matched_rules:
        return None
    return max(matched_rules, key=lambda r: r.priority)
