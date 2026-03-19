"""
Contrarian decision engine for the CounterTrade Bot.
Generates recommendations that counter the trader's emotional bias.
"""

import logging
from typing import Optional

from backend.models import AnalysisResponse, EmotionResult, MarketContext
from backend.rules import get_best_rule, load_rules, match_rules

logger = logging.getLogger(__name__)

# Default decision matrix: state -> (action, conviction_low, conviction_high, cooldown, guardrails)
DEFAULT_DECISIONS: dict[str, dict] = {
    "capitulation": {
        "action": "BUY",
        "conviction_range": (60, 80),
        "cooldown": 0,
        "guardrails": [
            "Only if no new bearish fundamental thesis",
            "Scale in with small position (25-50% of intended size)",
            "Set tight stop loss",
        ],
        "reasoning_template": (
            "You appear to be capitulating. Historically, capitulation marks are "
            "often near local bottoms. The emotional urge to sell everything is "
            "exactly when contrarian buying has the best odds. Consider a small, "
            "measured entry rather than following the panic."
        ),
        "distortion": "Catastrophizing / availability bias",
        "disconfirming": (
            "A genuine structural break (new regulation, insolvency, "
            "fundamental thesis invalidated) would make selling correct."
        ),
    },
    "panic-selling": {
        "action": "WAIT",
        "conviction_range": (50, 70),
        "cooldown": 15,
        "guardrails": [
            "Do not market-sell; use limit orders if you must reduce",
            "Re-evaluate in 15 minutes with fresh eyes",
            "Check if the drop is driven by news or just price action",
        ],
        "reasoning_template": (
            "Panic is driving your decision-making. Market sells during panics "
            "often lock in the worst prices. Wait for volatility to settle before "
            "making any moves. If you must reduce exposure, use limit orders."
        ),
        "distortion": "Amygdala hijack / loss aversion",
        "disconfirming": (
            "If a genuine black swan event is unfolding with confirmed "
            "fundamental damage, quick exits may be warranted."
        ),
    },
    "revenge-trading": {
        "action": "NO_TRADE",
        "conviction_range": (80, 90),
        "cooldown": 30,
        "guardrails": [
            "Mandatory 30-minute cooldown before any trade",
            "Write down your thesis before entering",
            "Size must be equal to or smaller than your standard position",
        ],
        "reasoning_template": (
            "Revenge trading is one of the most destructive patterns. Your "
            "desire to 'win it back' will lead to oversized, poorly-timed trades. "
            "Step away from the screen. No trade made in anger has a positive "
            "expected value."
        ),
        "distortion": "Sunk cost fallacy / ego protection",
        "disconfirming": (
            "If you can write a calm, detailed thesis with clear invalidation "
            "levels, the trade may have merit independent of revenge motivation."
        ),
    },
    "FOMO-chasing": {
        "action": "WAIT",
        "conviction_range": (60, 80),
        "cooldown": 10,
        "guardrails": [
            "Wait for a pullback to enter if you truly want exposure",
            "Size at 50% or less of what your FOMO is telling you",
            "Set a limit buy below current price, not a market buy",
        ],
        "reasoning_template": (
            "FOMO is pushing you to chase. Most FOMO entries happen near local "
            "tops. The fear of missing out is not a trading thesis. If the move "
            "is real, there will be pullbacks to enter. Chasing rarely ends well."
        ),
        "distortion": "Bandwagon effect / fear of regret",
        "disconfirming": (
            "If there is genuine new information (not just price action) that "
            "changes the fundamental picture, entering may be justified."
        ),
    },
    "greed-top": {
        "action": "REDUCE",
        "conviction_range": (60, 75),
        "cooldown": 0,
        "guardrails": [
            "Take partial profits (25-50% of position)",
            "Move stop loss to break-even on remainder",
            "Remember: pigs get slaughtered",
        ],
        "reasoning_template": (
            "Euphoria and greed are peak emotional signals. When everyone feels "
            "like a genius, the market is often near a top. Lock in some profits "
            "now. You don't have to sell everything, but protect your gains."
        ),
        "distortion": "Overconfidence bias / narrative fallacy",
        "disconfirming": (
            "If fundamental metrics (earnings, adoption, on-chain data) still "
            "support further upside with room to grow, holding may be correct."
        ),
    },
    "tilted": {
        "action": "NO_TRADE",
        "conviction_range": (85, 85),
        "cooldown": 60,
        "guardrails": [
            "Close the trading app and take a break",
            "No trades until you've slept / rested",
            "Review your trading journal before resuming",
        ],
        "reasoning_template": (
            "You're showing signs of tilt or exhaustion. Trading while fatigued "
            "is like driving drunk -- your judgment is impaired even if you "
            "don't feel it. Step away completely. The market will be here tomorrow."
        ),
        "distortion": "Decision fatigue / ego depletion",
        "disconfirming": (
            "There is no scenario where trading while tilted is optimal. "
            "Rest first, trade later."
        ),
    },
    "calm": {
        "action": "HOLD",
        "conviction_range": (30, 50),
        "cooldown": 0,
        "guardrails": [
            "Your emotional state is neutral -- trust your own analysis",
            "Proceed with normal risk management",
        ],
        "reasoning_template": (
            "You appear to be in a calm, rational state. This is where your "
            "best trading decisions happen. The bot defers to your own analysis "
            "when emotions aren't distorting judgment."
        ),
        "distortion": "None detected",
        "disconfirming": "N/A -- calm state detected; your own thesis applies.",
    },
    "uncertain": {
        "action": "WAIT",
        "conviction_range": (20, 40),
        "cooldown": 5,
        "guardrails": [
            "Mixed emotional signals detected",
            "Clarify your thesis before acting",
            "Consider journaling your thoughts first",
        ],
        "reasoning_template": (
            "The emotional signals are mixed and hard to read. When you're "
            "uncertain about your own state, it's best to wait. Clarity comes "
            "before conviction."
        ),
        "distortion": "Ambiguity aversion",
        "disconfirming": (
            "If you can articulate a clear thesis with defined risk, "
            "the trade may be worth taking regardless of mixed emotions."
        ),
    },
}


def _apply_guardrails(
    emotion: EmotionResult,
    state: str,
    action: str,
    conviction: int,
    cooldown: int,
    guardrails: list[str],
) -> tuple[str, int, int, list[str]]:
    """Apply mandatory guardrails that override other logic."""
    # Force cooldown on anger/revenge
    if emotion.primary_emotion in ("anger", "revenge") and cooldown < 30:
        cooldown = 30
        if "Mandatory 30-minute cooldown before any trade" not in guardrails:
            guardrails.append("Mandatory 30-minute cooldown before any trade")

    # Low conviction -> always HOLD or WAIT
    if conviction < 40 and action not in ("HOLD", "WAIT", "NO_TRADE"):
        action = "WAIT"
        guardrails.append("Conviction too low for active trade; defaulting to WAIT")

    # High intensity -> document thesis
    if emotion.emotion_intensity > 80:
        doc_guard = "Document your thesis in writing before any action"
        if doc_guard not in guardrails:
            guardrails.append(doc_guard)

    # Overconfidence -> checklist
    if emotion.primary_emotion == "overconfidence" or (
        emotion.secondary_emotion == "overconfidence"
    ):
        check_guard = "Complete a confirmation checklist: 3 reasons this trade could fail"
        if check_guard not in guardrails:
            guardrails.append(check_guard)

    # Universal disclaimer
    disclaimer = "Emotional inversion is a heuristic, not a guaranteed edge"
    if disclaimer not in guardrails:
        guardrails.append(disclaimer)

    return action, conviction, cooldown, guardrails


def generate_recommendation(
    emotion: EmotionResult,
    state: str,
    market_context: Optional[MarketContext] = None,
    llm_recommendation: Optional[dict] = None,
) -> dict:
    """
    Generate a contrarian recommendation based on emotional state.

    If an LLM recommendation is provided, it is used as the base and
    guardrails are still applied. Otherwise, the rule engine and default
    decision matrix are used.

    Returns a dict suitable for constructing an AnalysisResponse (minus entry_id).
    """
    # --- Try rule engine first ---
    try:
        rules = load_rules()
        matched = match_rules(emotion, state, market_context)
        best_rule = get_best_rule(matched) if matched else None
    except Exception as exc:
        logger.warning("Rule engine error: %s. Using defaults.", exc)
        best_rule = None

    # --- LLM recommendation takes priority if available ---
    if llm_recommendation:
        action = llm_recommendation.get("recommended_action", "WAIT")
        conviction = int(llm_recommendation.get("conviction", 50))
        reasoning = llm_recommendation.get("reasoning", "")
        distortion = llm_recommendation.get("distortion_risk", "")
        disconfirming = llm_recommendation.get("disconfirming_evidence", "")
        guardrails = llm_recommendation.get("guardrails", [])
        cooldown = int(llm_recommendation.get("cooldown_minutes", 0))
    elif best_rule:
        action = best_rule.action
        conv_low, conv_high = best_rule.conviction_range
        # Scale conviction by emotion intensity
        intensity_factor = emotion.emotion_intensity / 100.0
        conviction = int(conv_low + (conv_high - conv_low) * intensity_factor)
        guardrails = list(best_rule.guardrails)
        cooldown = best_rule.cooldown

        # Fall back to default matrix for reasoning/distortion/disconfirming
        defaults = DEFAULT_DECISIONS.get(state, DEFAULT_DECISIONS["uncertain"])
        reasoning = defaults["reasoning_template"]
        distortion = defaults["distortion"]
        disconfirming = defaults["disconfirming"]
    else:
        # Use default decision matrix
        defaults = DEFAULT_DECISIONS.get(state, DEFAULT_DECISIONS["uncertain"])
        action = defaults["action"]
        conv_low, conv_high = defaults["conviction_range"]
        intensity_factor = emotion.emotion_intensity / 100.0
        conviction = int(conv_low + (conv_high - conv_low) * intensity_factor)
        guardrails = list(defaults["guardrails"])
        cooldown = defaults["cooldown"]
        reasoning = defaults["reasoning_template"]
        distortion = defaults["distortion"]
        disconfirming = defaults["disconfirming"]

    # --- Enrich reasoning with market context ---
    if market_context and market_context.asset:
        reasoning += f" (Asset: {market_context.asset})"
    if market_context and market_context.recent_move_pct is not None:
        reasoning += f" Recent move: {market_context.recent_move_pct}%."

    # --- Apply mandatory guardrails ---
    action, conviction, cooldown, guardrails = _apply_guardrails(
        emotion, state, action, conviction, cooldown, guardrails
    )

    return {
        "primary_emotion": emotion.primary_emotion,
        "secondary_emotion": emotion.secondary_emotion,
        "emotion_intensity": emotion.emotion_intensity,
        "confidence": emotion.confidence,
        "state_label": state,
        "recommended_action": action,
        "conviction": conviction,
        "reasoning": reasoning,
        "distortion_risk": distortion,
        "disconfirming_evidence": disconfirming,
        "guardrails": guardrails,
        "cooldown_minutes": cooldown,
    }
