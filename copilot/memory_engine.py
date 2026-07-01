from __future__ import annotations

from collections import Counter
from typing import Any

from .demo_data import REQUIRED_DISCLAIMER


def _top_values(items: list[dict[str, Any]], key: str, limit: int = 3) -> list[str]:
    values = [str(item.get(key) or "").strip().upper() for item in items if str(item.get(key) or "").strip()]
    return [value for value, _count in Counter(values).most_common(limit)]


def _top_text(items: list[dict[str, Any]], key: str, fallback: str) -> str:
    values = [str(item.get(key) or "").strip() for item in items if str(item.get(key) or "").strip()]
    if not values:
        return fallback
    return Counter(values).most_common(1)[0][0]


def build_memory_summary(
    *,
    journal_entries: list[dict[str, Any]],
    strategies: list[dict[str, Any]],
    paper_trades: list[dict[str, Any]],
    risk_rules: dict[str, Any],
    preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preferences = preferences or {}
    symbols = _top_values(journal_entries + paper_trades, "symbol")
    setups = _top_values(journal_entries, "setup_type")
    mistake = _top_text(journal_entries, "mistakes", "Add more journal notes to detect a repeated mistake.")
    paper_focus = _top_text(paper_trades, "strategy", "Save paper plans to identify practice focus.")
    strategy_names = _top_values(strategies, "name")
    max_trades = risk_rules.get("max_trades_per_day", 3)
    max_losses = risk_rules.get("max_losses_per_day", 2)
    stop_required = "stop required" if risk_rules.get("require_stop_loss", True) else "stop not required"

    cards = [
        {
            "label": "Profile",
            "value": f"{preferences.get('experience_level', 'beginner')} / {preferences.get('risk_style', 'conservative')}",
            "detail": preferences.get("learning_goal") or "Personalization starts with onboarding preferences.",
        },
        {
            "label": "Most reviewed symbols",
            "value": ", ".join(symbols) if symbols else "No symbol pattern yet",
            "detail": "Built from journal entries and paper plans.",
        },
        {
            "label": "Repeated mistake",
            "value": mistake,
            "detail": "Use this as a review prompt, not a judgment.",
        },
        {
            "label": "Favorite setups",
            "value": ", ".join(setups) if setups else "No setup pattern yet",
            "detail": "This becomes more useful as the journal grows.",
        },
        {
            "label": "Paper practice focus",
            "value": paper_focus,
            "detail": "Based on saved paper trade plans.",
        },
        {
            "label": "Saved strategies",
            "value": ", ".join(strategy_names) if strategy_names else "No saved strategy yet",
            "detail": "Strategy Builder saves will appear here.",
        },
        {
            "label": "Risk guardrail",
            "value": f"{max_trades} trades/day, {max_losses} losses/day, {stop_required}",
            "detail": "Personal risk rules from Settings.",
        },
    ]

    next_reviews = [
        "Before any new setup, write entry, stop, target, and invalidation first.",
        f"Review this repeated mistake: {mistake}",
        "Compare the next paper plan against your saved strategy rules.",
    ]

    context = (
        f"Preferences: experience={preferences.get('experience_level', 'beginner')}; "
        f"markets={preferences.get('markets', [])}; risk_style={preferences.get('risk_style', 'conservative')}; "
        f"learning_goal={preferences.get('learning_goal', '')}. "
        f"User memory summary: reviewed symbols={symbols or 'none yet'}; "
        f"setups={setups or 'none yet'}; repeated mistake={mistake}; "
        f"paper focus={paper_focus}; risk guardrail={max_trades} trades/day and {max_losses} losses/day."
    )

    return {
        "ok": True,
        "mode": "demo-local-memory",
        "cards": cards,
        "next_reviews": next_reviews,
        "copilot_context": context,
        "disclaimer": REQUIRED_DISCLAIMER,
    }
