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
        # Crypto slang
        (r"\bwtf\b", 11),
        (r"\bbs\b", 8),
        (r"\bfk|fck|fuk\b", 12),
        (r"\bthis is trash\b", 10),
        (r"\bgarbage\b", 9),
        (r"\brug(ged)?\b", 14),
        (r"\binsiders?\b", 12),
        (r"\bwhale.{0,10}(dump|manipulat|scam)", 14),
        (r"\brobbed\b", 13),
        (r"\bfucking?\b", 10),
        (r"\bshit(coin|show)?\b", 10),
        (r"\bponzi\b", 14),
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
        # Crypto slang
        (r"\brekt\b", 16),
        (r"\bgot rekt\b", 18),
        (r"\bholding bags?\b", 13),
        (r"\bbag ?hold", 14),
        (r"\bdown bad\b", 15),
        (r"\bunder ?water\b", 13),
        (r"\bliquidat", 17),
        (r"\bgot liquidated\b", 18),
        (r"\bmargin call\b", 16),
        (r"\baccount.{0,10}(zero|gone|empty|blown)", 17),
        (r"\bwrecked\b", 15),
        (r"\bdestroyed\b", 14),
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
        # Crypto slang
        (r"\bcapitulat", 16),
        (r"\bpaper hands?\b", 13),
        (r"\bweak hands?\b", 12),
        (r"\bsurrender\b", 14),
        (r"\bthrowing in the towel\b", 15),
        (r"\bclosing (my )?position", 14),
        (r"\bexiting (the )?(market|trade|position)", 14),
        (r"\bi quit\b", 15),
        (r"\bnever (trad|invest|buy)", 16),
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
        # Crypto slang
        (r"\bmax leverage\b", 16),
        (r"\b100x\b", 15),
        (r"\b50x\b", 14),
        (r"\b(10|20|25)x\b", 12),
        (r"\bcross margin\b", 13),
        (r"\ball in.{0,10}(now|this|on)", 16),
        (r"\bneed.{0,10}(back|recover|make up)", 13),
        (r"\btilted.{0,10}(but|going|still)", 14),
        (r"\bfull send\b", 13),
        (r"\bape(ing)? (in|into)\b", 14),
        (r"\bdegen (mode|play|bet)", 14),
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
        # Crypto slang
        (r"\bwagmi\b", 13),
        (r"\bngmi\b", 11),
        (r"\bape in\b", 14),
        (r"\bsend(ing)? it\b", 12),
        (r"\bpump(ing|ed)?\b", 12),
        (r"\bgreen candle", 11),
        (r"\bbreaking (out|up|ath|high)", 13),
        (r"\bnew (ath|all[- ]time[- ]high)\b", 14),
        (r"\bparabolic\b", 14),
        (r"\bmooning\b", 14),
        (r"\brocket\b", 11),
        (r"\blambo\b", 12),
        (r"\b(my |)friends? (are |)(all )?(making|buying|in)\b", 13),
        (r"\btwitter.{0,10}(bullish|buying|pump)", 12),
        (r"\bct.{0,5}(is |)(bullish|pumping|buying)", 12),
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
        # Crypto slang
        (r"\bser\b", 6),
        (r"\bnuke(d)?\b", 14),
        (r"\bred candle", 11),
        (r"\bcascading liquidat", 16),
        (r"\bdepegg?ed\b", 15),
        (r"\bbank run\b", 15),
        (r"\binsolvency?\b", 15),
        (r"\bwinding down\b", 13),
        (r"\bexploit(ed)?\b", 14),
        (r"\bhack(ed)?\b", 14),
        (r"\bdrain(ed)?\b", 13),
        (r"\bcontagion\b", 14),
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
        # Crypto slang
        (r"\b(10|100|1000)x\b", 14),
        (r"\bgem\b", 10),
        (r"\balpha\b", 9),
        (r"\bearly\b", 8),
        (r"\blife[- ]?changing\b", 14),
        (r"\bgenerational\b", 13),
        (r"\bretire (early|young)\b", 14),
        (r"\bmulti[- ]?bagger\b", 13),
        (r"\bmoon ?bag\b", 12),
        (r"\bdiamonds?\b", 10),
        (r"\brich\b", 10),
        (r"\bwealth\b", 9),
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
        # Crypto slang
        (r"\bchad\b", 11),
        (r"\bbased\b", 9),
        (r"\bwe'?re (all )?gonna make it\b", 13),
        (r"\bup only\b", 13),
        (r"\bsuper ?cycle\b", 14),
        (r"\bcant stop winning\b", 14),
        (r"\bevery trade.{0,10}(hits|wins|prints)", 15),
        (r"\bfeel (like )?(a )?god\b", 14),
        (r"\bking\b", 9),
        (r"\blegend\b", 10),
        (r"\bcrush(ing|ed)? it\b", 12),
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
        # Crypto slang
        (r"\bstaring at charts\b", 12),
        (r"\bcan'?t sleep\b", 13),
        (r"\b(24|48) hours?\b", 10),
        (r"\bscreen time\b", 10),
        (r"\bglued to (the )?screen\b", 13),
        (r"\bovertrading?\b", 14),
        (r"\btoo many (tabs|charts|positions)\b", 12),
        (r"\bburnt?\b", 11),
        (r"\bmentally\b", 10),
        (r"\bnothing makes sense\b", 12),
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
        # Crypto slang
        (r"\bmax size\b", 13),
        (r"\bfull port\b", 14),
        (r"\bport(folio)? (all|100%|entire)", 14),
        (r"\bslam(ming)?( it)?\b", 12),
        (r"\bcan'?t go tits up\b", 16),
        (r"\bliterally free money\b", 16),
        (r"\binsider (info|knowledge)\b", 15),
        (r"\bi know (the|a) guy\b", 12),
        (r"\btrust me\b", 11),
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
        # Crypto slang
        (r"\buncertain\b", 9),
        (r"\bsidelined\b", 8),
        (r"\bstay(ing)? out\b", 8),
        (r"\btoo risky\b", 10),
        (r"\bdon'?t trust\b", 10),
        (r"\bcould (crash|dump|tank|drop)", 11),
        (r"\bbear (market|trap|flag)", 11),
        (r"\bdeath cross\b", 13),
        (r"\brecession\b", 12),
        (r"\bregulat", 10),
    ],
}

# Emoji patterns for emotion detection
EMOJI_PATTERNS: dict[str, list[tuple[str, int]]] = {
    "anger": [("😤", 12), ("🤬", 14), ("😡", 13), ("💢", 11), ("🖕", 13)],
    "despair": [("😭", 14), ("💀", 12), ("☠️", 12), ("🪦", 13), ("😢", 10)],
    "panic": [("🚨", 12), ("⚠️", 10), ("📉", 11), ("🔴", 9), ("😱", 14), ("💥", 11)],
    "fomo": [("🚀", 13), ("🌙", 12), ("🔥", 11), ("💎", 10), ("🤑", 12), ("📈", 11)],
    "greed": [("🤑", 14), ("💰", 12), ("💵", 11), ("🏦", 10), ("💎🙌", 13)],
    "euphoria": [("🎉", 11), ("🏆", 12), ("👑", 12), ("🐐", 11), ("🔥", 10), ("💪", 10)],
    "exhaustion": [("😴", 12), ("😵", 13), ("🥱", 10), ("😫", 12), ("😩", 11)],
    "fear": [("😰", 12), ("😨", 12), ("🥶", 10), ("😬", 9), ("🫣", 10)],
    "capitulation": [("🏳️", 14), ("📉", 10), ("💸", 12), ("🗑️", 11)],
    "overconfidence": [("🧠", 10), ("👆", 9), ("💯", 12), ("🎯", 11)],
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


def _count_emoji_scores(text: str) -> dict[str, int]:
    """Score emotions from emoji usage in the text."""
    scores: dict[str, int] = {}
    for emotion, patterns in EMOJI_PATTERNS.items():
        for emoji_char, weight in patterns:
            count = text.count(emoji_char)
            if count > 0:
                scores[emotion] = scores.get(emotion, 0) + count * weight
    return scores


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

    # Add emoji scores
    emoji_scores = _count_emoji_scores(text)
    for emotion, score in emoji_scores.items():
        scores[emotion] = scores.get(emotion, 0) + score

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
