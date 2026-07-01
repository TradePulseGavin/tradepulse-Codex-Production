from __future__ import annotations

from typing import Any

import requests

from .config import settings
from .demo_data import REQUIRED_DISCLAIMER, build_copilot_response, symbol_snapshot


SYSTEM_PROMPT = """You are TradePulse, a trading research and education copilot.
You must never give direct buy, sell, enter, exit, hold, or position-size instructions.
Frame every answer as research context, setup quality, risk review, journaling, and education.
Mention uncertainty, event/news risk, invalidation, and the need for the user to make their own final decision.
Keep the answer concise and beginner-readable.
"""


def _safe_response_text(text: str) -> str:
    replacements = {
        "you should buy": "a bullish thesis would still need review before any decision",
        "you should sell": "a bearish thesis would still need review before any decision",
        "buy now": "review the bullish factors",
        "sell now": "review the bearish factors",
        "enter now": "review entry conditions",
        "exit now": "review exit conditions",
    }
    cleaned = text.strip()
    lowered = cleaned.lower()
    for phrase, replacement in replacements.items():
        if phrase in lowered:
            cleaned = cleaned.replace(phrase, replacement)
            cleaned = cleaned.replace(phrase.title(), replacement)
            lowered = cleaned.lower()
    if "not financial advice" not in lowered and "research" not in lowered:
        cleaned += "\n\nThis is research context only, not financial advice or a trade instruction."
    return cleaned


def _prompt_payload(payload: dict[str, Any]) -> list[dict[str, str]]:
    symbol = str(payload.get("symbol") or "SPY").upper()
    timeframe = str(payload.get("timeframe") or "5m")
    asset_type = str(payload.get("asset_type") or "Stock")
    message = str(payload.get("message") or "Summarize this chart like I am a beginner.")
    memory = str(payload.get("memory") or "No user memory summary yet.")
    snapshot = symbol_snapshot(symbol)
    user_content = (
        f"User question: {message}\n"
        f"Symbol: {symbol}\n"
        f"Asset type: {asset_type}\n"
        f"Timeframe: {timeframe}\n"
        f"Current research snapshot: {snapshot}\n"
        f"Personalization memory: {memory}\n"
        f"Required disclaimer: {REQUIRED_DISCLAIMER}\n"
        "Answer with: trend context, bullish factors, bearish/risk factors, questions to check, and one beginner explanation."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def openai_research_response(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    if not settings.openai_api_key:
        fallback = build_copilot_response(payload)
        fallback["ai_provider"] = "Safe mock response"
        return fallback

    fallback = build_copilot_response(payload)
    try:
        response = requests.post(
            f"{settings.openai_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_model,
                "messages": _prompt_payload(payload),
                "temperature": 0.25,
                "max_tokens": 700,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not text:
            raise ValueError("OpenAI returned an empty response.")
        fallback["response"] = _safe_response_text(text)
        fallback["mode"] = "openai-research"
        fallback["ai_provider"] = f"OpenAI ({settings.openai_model})"
        fallback["confidence"] = min(float(fallback.get("confidence") or 0.68), 0.72)
        return fallback
    except Exception as exc:
        fallback["mode"] = "mock-ai-fallback"
        fallback["ai_provider"] = "Safe mock response"
        fallback["warning"] = f"OpenAI fallback used: {exc}"
        return fallback
