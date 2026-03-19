"""
Emotion detection engine for the CounterTrade Bot.
Supports rule-based keyword matching (always available) and LLM-based analysis (when available).
"""

import re
from typing import Optional

from backend.models import EmotionResult, MarketContext

# Keyword patterns for each emotion category.
# Each entry is a tuple of (pattern, weight) where weight affects intensity scoring.
EMOTION_KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "anger": [
        (r"\bfurious\b", 15),
        (r"\bscam\b", 12),
        (r"\brigged\b", 14),
        (r"\bmanipulat", 13),
        (r"\bhate\b", 10),
        (r"\bstupid (market|trade)\b", 12),
        (r"\bbullshit\b", 11),
        (r"\bfraud\b", 13),
        (r"\bpissed\b", 12),
        (r"\bangry\b", 10),
        (r"\bunfair\b", 8),
        (r"\bwhat a joke\b", 9),
        (r"\bthis is insane\b", 8),
        (r"\bstopped out\b", 8),
        (r"\bagain\b", 5),
    ],
    "despair": [
        (r"\bhopeless\b", 15),
        (r"\blost everything\b", 18),
        (r"\bno point\b", 14),
        (r"\bgiving up\b", 16),
        (r"\bcan'?t take it\b", 15),
        (r"\bworthless\b", 13),
        (r"\bruin(ed)?\b", 14),
        (r"\bblew (my|the) account\b", 17),
        (r"\bwiped out\b", 16),
        (r"\bnothing left\b", 15),
        (r"\bwant to quit\b", 13),
    ],
    "capitulation": [
        (r"\bsell(ing)? everything\b", 18),
        (r"\bi'?m done\b", 14),
        (r"\bgetting out\b", 13),
        (r"\bcutting all\b", 15),
        (r"\bcan'?t hold anymore\b", 16),
        (r"\bjust sell\b", 12),
        (r"\bclose (all|every)", 14),
        (r"\bmarket sell\b", 15),
        (r"\bdump(ing)? (it|all|every)", 14),
        (r"\bgive up\b", 12),
        (r"\bget me out\b", 14),
        (r"\bneed to sell\b", 13),
        (r"\bsell.{0,10}now\b", 14),
    ],
    "revenge": [
        (r"\bgetting it back\b", 14),
        (r"\bdouble down\b", 15),
        (r"\bmake them pay\b", 14),
        (r"\brevenge\b", 16),
        (r"\bgoing (all in|back in)\b", 17),
        (r"\bwin it back\b", 14),
        (r"\bneed to recover\b", 12),
        (r"\bbet (bigger|more|heavier)\b", 13),
        (r"\bsize up\b", 11),
        (r"\b\dx (size|the size|leverage)\b", 12),
        (r"\byolo\b", 12),
        (r"\bstopped out.{0,20}(back|again|going)\b", 15),
        (r"\bshake.{0,10}out\b", 12),
        (r"\bwon'?t (let|give|stop)\b", 11),
    ],
    "fomo": [
        (r"\bmissing out\b", 14),
        (r"\beveryone (is|was) buying\b", 13),
        (r"\bgoing to (the )?moon\b", 14),
        (r"\bneed to get in\b", 15),
        (r"\bleft behind\b", 13),
        (r"\bfomo\b", 16),
        (r"\blast chance\b", 14),
        (r"\btrain (is )?leaving\b", 12),
        (r"\bstill early\b", 10),
        (r"\beveryone (making|getting) (rich|money)\b", 13),
        (r"\bcan'?t miss this\b", 14),
    ],
    "panic": [
        (r"\bcrash(ed|ing|es)?\b", 14),
        (r"\bflash crash\b", 16),
        (r"\bdump(ed|ing)?\b", 12),
        (r"\brug ?pull\b", 15),
        (r"\beverything (is )?falling\b", 14),
        (r"\bpanic\b", 14),
        (r"\bcollaps", 13),
        (r"\bblack swan\b", 15),
        (r"\bfree fall\b", 14),
        (r"\btanking\b", 12),
        (r"\bplummet", 13),
        (r"\bbloodba?th\b", 12),
        (r"\bdropp(ed|ing)\b", 10),
        (r"\bgoes? to zero\b", 15),
        (r"\b(sell|get out|exit) (everything|all|now)\b", 14),
        (r"\bbefore it", 8),
    ],
    "greed": [
        (r"\beasy money\b", 14),
        (r"\bcan'?t lose\b", 15),
        (r"\bfree money\b", 15),
        (r"\bgoing to retire\b", 14),
        (r"\blambo\b", 13),
        (r"\bto the moon\b", 13),
        (r"\bprint(ing)? money\b", 14),
        (r"\binfinite (money|gains)\b", 15),
        (r"\brisk[- ]free\b", 14),
        (r"\bguaranteed (profit|money|gains)\b", 15),
    ],
    "euphoria": [
        (r"\bgenius\b", 14),
        (r"\bbest trader\b", 15),
        (r"\bcalled it\b", 12),
        (r"\bnailed it\b", 12),
        (r"\bunstoppable\b", 14),
        (r"\bon fire\b", 11),
        (r"\bking of (the )?market\b", 14),
        (r"\bcan do no wrong\b", 15),
        (r"\beverything i touch\b", 13),
        (r"\bwinning streak\b", 12),
        (r"\bi'?m (a )?god\b", 14),
    ],
    "exhaustion": [
        (r"\bso tired\b", 12),
        (r"\bcan'?t think\b", 13),
        (r"\bbeen up all night\b", 14),
        (r"\btoo many trades\b", 13),
        (r"\bburned out\b", 15),
        (r"\bexhausted\b", 14),
        (r"\bneed (a )?break\b", 11),
        (r"\bcan'?t focus\b", 12),
        (r"\boverwhelmed\b", 11),
        (r"\btilt(ed|ing)?\b", 13),
        (r"\bdrained\b", 12),
    ],
    "overconfidence": [
        (r"\bguaranteed\b", 14),
        (r"\b100%\b", 13),
        (r"\bsure thing\b", 14),
        (r"\bno way this fails\b", 16),
        (r"\bcan'?t (go wrong|lose|fail)\b", 15),
        (r"\bimpossible to lose\b", 16),
        (r"\bcannot lose\b", 15),
        (r"\bno risk\b", 14),
        (r"\bno brainer\b", 13),
        (r"\bfree trade\b", 12),
        (r"\bbest trader\b", 14),
        (r"\ball in\b", 11),
        (r"\bleverage\b", 9),
    ],
    "fear": [
        (r"\bscared\b", 12),
        (r"\bafraid\b", 12),
        (r"\bwhat if\b", 8),
        (r"\bworried\b", 10),
        (r"\bnervous\b", 10),
        (r"\banxious\b", 11),
        (r"\bfear(ful)?\b", 11),
        (r"\buneasy\b", 9),
        (r"\bdread\b", 12),
        (r"\bterrif", 14),
        (r"\bfrightened\b", 13),
    ],
}

# Maps emotions to trading states, considering context
STATE_MAP: dict[str, str] = {
    "capitulation": "capitulation",
    "panic": "panic-selling",
    "anger": "revenge-trading",
    "revenge": "revenge-trading",
    "fomo": "FOMO-chasing",
    "greed": "greed-top",
    "euphoria": "greed-top",
    "exhaustion": "tilted",
    "overconfidence": "greed-top",
    "fear": "panic-selling",
    "despair": "capitulation",
    "calm": "calm",
}


def _count_emphasis(text: str) -> int:
    """Score additional intensity from exclamation marks, caps, and repetition."""
    score = 0
    # Exclamation marks
    exclamations = text.count("!")
    score += min(exclamations * 3, 15)

    # Proportion of uppercase letters (excluding short texts)
    if len(text) > 10:
        alpha_chars = [c for c in text if c.isalpha()]
        if alpha_chars:
            caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if caps_ratio > 0.5:
                score += int(caps_ratio * 20)

    # Repeated characters (e.g., "noooo", "fuuuck")
    repeated = re.findall(r"(.)\1{2,}", text.lower())
    score += min(len(repeated) * 5, 15)

    # Multiple question marks or exclamation marks in a row
    multi_punct = re.findall(r"[!?]{2,}", text)
    score += min(len(multi_punct) * 4, 12)

    return min(score, 30)  # Cap emphasis bonus


def detect_emotion_rule_based(text: str) -> EmotionResult:
    """
    Detect the trader's emotional state using keyword matching.
    Returns the primary emotion, optional secondary, intensity, and confidence.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for emotion, patterns in EMOTION_KEYWORDS.items():
        total_score = 0
        for pattern, weight in patterns:
            matches = re.findall(pattern, text_lower)
            total_score += len(matches) * weight
        if total_score > 0:
            scores[emotion] = total_score

    if not scores:
        return EmotionResult(
            primary_emotion="calm",
            secondary_emotion=None,
            emotion_intensity=10,
            confidence=40,
        )

    # Sort by score descending
    sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = sorted_emotions[0]
    secondary = sorted_emotions[1] if len(sorted_emotions) > 1 else None

    # Calculate intensity: base from keyword scores + emphasis bonus
    emphasis_bonus = _count_emphasis(text)
    raw_intensity = min(primary[1] + emphasis_bonus, 100)
    intensity = max(10, min(raw_intensity, 100))

    # Confidence is higher when one emotion dominates
    if secondary and secondary[1] > 0:
        dominance_ratio = primary[1] / (primary[1] + secondary[1])
        confidence = int(dominance_ratio * 80) + 10
    else:
        confidence = min(70 + primary[1], 95)

    return EmotionResult(
        primary_emotion=primary[0],
        secondary_emotion=secondary[0] if secondary and secondary[1] >= 8 else None,
        emotion_intensity=intensity,
        confidence=min(confidence, 95),
    )


def map_emotion_to_state(
    emotion: EmotionResult,
    market_context: Optional[MarketContext] = None,
) -> str:
    """
    Map detected emotion to a trading state, optionally using market context
    for more nuanced classification.
    """
    primary = emotion.primary_emotion

    # Refine state based on context
    if market_context:
        # Panic + actively selling -> panic-selling
        if primary == "panic" and market_context.action_type == "exiting":
            return "panic-selling"

        # Anger + loss context -> revenge-trading
        if primary == "anger" and market_context.unrealized_pnl is not None and market_context.unrealized_pnl < 0:
            return "revenge-trading"

        # FOMO + buying -> FOMO-chasing
        if primary == "fomo" and market_context.action_type == "adding":
            return "FOMO-chasing"

    # If secondary emotion present, check for mixed states
    if emotion.secondary_emotion:
        sec = emotion.secondary_emotion
        if primary in ("anger", "despair") and sec in ("revenge", "anger"):
            return "revenge-trading"
        if primary in ("greed", "euphoria") and sec in ("overconfidence", "greed", "euphoria"):
            return "greed-top"
        if primary in ("fear", "panic") and sec in ("despair", "capitulation"):
            return "capitulation"

    # Mixed signals with low confidence
    if emotion.confidence < 35:
        return "uncertain"

    return STATE_MAP.get(primary, "uncertain")


def detect_emotion(
    text: str,
    market_context: Optional[MarketContext] = None,
    use_llm: bool = False,
) -> tuple[EmotionResult, str]:
    """
    Main entry point for emotion detection.
    Returns (EmotionResult, state_label).

    If use_llm is True, attempts LLM-based analysis first (handled in llm.py),
    falling back to rule-based if unavailable.
    """
    emotion = detect_emotion_rule_based(text)
    state = map_emotion_to_state(emotion, market_context)
    return emotion, state
