"""
Notification support for the CounterTrade Bot.
Sends alerts via Telegram and desktop notifications when dangerous
emotional states are detected.
"""

import logging
import subprocess
import sys
from typing import Any, Optional

import httpx

from backend.llm import load_settings

logger = logging.getLogger(__name__)

# States and intensity thresholds that trigger notifications
ALERT_STATES = {"capitulation", "revenge-trading", "FOMO-chasing", "panic-selling"}
INTENSITY_THRESHOLD = 80


def should_notify(state_label: str, emotion_intensity: int) -> bool:
    """Determine if a notification should be sent based on state and intensity."""
    if state_label in ALERT_STATES:
        return True
    if emotion_intensity > INTENSITY_THRESHOLD:
        return True
    return False


async def send_telegram(message: str, chat_id: str, bot_token: str) -> bool:
    """
    Send a message via the Telegram Bot API.
    Returns True on success, False on failure.
    """
    if not chat_id or not bot_token:
        logger.debug("Telegram credentials not configured; skipping.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("Telegram notification sent successfully.")
                return True
            logger.warning("Telegram API returned %s: %s", resp.status_code, resp.text[:200])
            return False
    except Exception as exc:
        logger.warning("Failed to send Telegram notification: %s", exc)
        return False


def send_desktop_notification(title: str, message: str) -> bool:
    """
    Send a desktop notification using available system tools.
    Tries notify-send (Linux), osascript (macOS), or falls back silently.
    """
    try:
        if sys.platform == "linux":
            subprocess.run(
                ["notify-send", title, message],
                timeout=5,
                check=False,
                capture_output=True,
            )
            return True
        elif sys.platform == "darwin":
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(
                ["osascript", "-e", script],
                timeout=5,
                check=False,
                capture_output=True,
            )
            return True
        elif sys.platform == "win32":
            # PowerShell toast notification
            ps_cmd = (
                f"[Windows.UI.Notifications.ToastNotificationManager, "
                f"Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
                f"$template = [Windows.UI.Notifications.ToastNotificationManager]::"
                f"GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::"
                f"ToastText02); "
                f"$text = $template.GetElementsByTagName('text'); "
                f"$text[0].AppendChild($template.CreateTextNode('{title}')); "
                f"$text[1].AppendChild($template.CreateTextNode('{message}')); "
                f"$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
                f"[Windows.UI.Notifications.ToastNotificationManager]::"
                f"CreateToastNotifier('CounterTrade Bot').Show($toast)"
            )
            subprocess.run(
                ["powershell", "-Command", ps_cmd],
                timeout=10,
                check=False,
                capture_output=True,
            )
            return True
        else:
            logger.debug("Desktop notifications not supported on %s", sys.platform)
            return False
    except Exception as exc:
        logger.debug("Desktop notification failed: %s", exc)
        return False


def _format_alert_message(analysis: dict) -> str:
    """Format an analysis response into a notification message."""
    state = analysis.get("state_label", "unknown")
    emotion = analysis.get("primary_emotion", "unknown")
    intensity = analysis.get("emotion_intensity", 0)
    action = analysis.get("recommended_action", "WAIT")
    conviction = analysis.get("conviction", 0)
    cooldown = analysis.get("cooldown_minutes", 0)

    lines = [
        f"*CounterTrade Bot Alert*",
        f"State: {state}",
        f"Emotion: {emotion} (intensity {intensity}/100)",
        f"Recommendation: *{action}* (conviction {conviction}/100)",
    ]
    if cooldown > 0:
        lines.append(f"Cooldown: {cooldown} minutes")

    guardrails = analysis.get("guardrails", [])
    if guardrails:
        lines.append("Guardrails:")
        for g in guardrails[:3]:
            lines.append(f"  - {g}")

    return "\n".join(lines)


async def notify_if_needed(analysis: dict, config: Optional[dict] = None) -> dict[str, bool]:
    """
    Check if a notification should be sent and dispatch it.
    Returns a dict indicating which channels were notified.
    """
    state = analysis.get("state_label", "")
    intensity = analysis.get("emotion_intensity", 0)

    result = {"telegram": False, "desktop": False, "should_notify": False}

    if not should_notify(state, intensity):
        return result

    result["should_notify"] = True

    if config is None:
        config = load_settings()

    message = _format_alert_message(analysis)

    # Telegram
    if config.get("notifications_enabled", False):
        token = config.get("telegram_bot_token", "")
        chat_id = config.get("telegram_chat_id", "")
        if token and chat_id:
            result["telegram"] = await send_telegram(message, chat_id, token)

    # Desktop (always try if state is dangerous)
    title = f"CounterTrade: {state}"
    plain_msg = (
        f"{analysis.get('primary_emotion', '')} detected "
        f"(intensity {intensity}). "
        f"Recommendation: {analysis.get('recommended_action', 'WAIT')}"
    )
    result["desktop"] = send_desktop_notification(title, plain_msg)

    return result
