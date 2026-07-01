from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import ROOT_DIR
from .demo_data import DEMO_WATCHLIST, JOURNAL_ENTRIES, RISK_RULES


DATA_DIR = ROOT_DIR / "data"
STATE_PATH = DATA_DIR / "demo_state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict[str, Any]:
    watchlist_id = "demo-watchlist"
    return {
        "watchlists": [
            {
                "id": watchlist_id,
                "name": "Demo Watchlist",
                "created_at": now_iso(),
                "items": [
                    {
                        "id": f"demo-{item['symbol'].lower()}",
                        "watchlist_id": watchlist_id,
                        "symbol": item["symbol"],
                        "asset_type": item["asset_type"].lower(),
                        "notes": item["setup_note"],
                        "created_at": now_iso(),
                    }
                    for item in DEMO_WATCHLIST
                ],
            }
        ],
        "journal_entries": [
            dict(item, id=f"demo-journal-{idx + 1}", created_at=now_iso())
            for idx, item in enumerate(JOURNAL_ENTRIES)
        ],
        "risk_rules": dict(RISK_RULES),
        "dashboard_layout": {"mode": "command", "hidden_panels": []},
        "strategies": [],
        "alerts": [],
        "session_plans": [],
        "risk_scenarios": [],
        "paper_trades": [],
        "screenshot_reviews": [],
        "data_requests": [],
        "support_tickets": [],
        "preferences": {
            "experience_level": "beginner",
            "markets": ["stocks", "etfs"],
            "platforms": ["TradingView"],
            "risk_style": "conservative",
            "default_symbols": "SPY,QQQ,NVDA,TSLA",
            "learning_goal": "Build disciplined paper-trading habits first.",
        },
        "school_progress": {},
        "usage_events": [],
        "activity": {"last_seen_at": now_iso(), "last_dashboard_snapshot": {}},
    }


def load_state() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        state = _default_state()
        save_state(state)
        return state
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        state = _default_state()
        save_state(state)
        return state

    defaults = _default_state()
    changed = False
    for key, value in defaults.items():
        if key not in state:
            state[key] = value
            changed = True
    for idx, entry in enumerate(state.get("journal_entries") or []):
        if "id" not in entry:
            entry["id"] = f"demo-journal-{idx + 1}"
            changed = True
        if "created_at" not in entry:
            entry["created_at"] = now_iso()
            changed = True
    if changed:
        save_state(state)
    return state


def save_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = STATE_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(STATE_PATH)


def get_dashboard_layout() -> dict[str, Any]:
    return deepcopy(load_state().get("dashboard_layout") or {})


def save_dashboard_layout(layout: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    state["dashboard_layout"] = dict(layout, updated_at=now_iso())
    save_state(state)
    return deepcopy(state["dashboard_layout"])


def get_risk_rules() -> dict[str, Any]:
    return deepcopy(load_state().get("risk_rules") or dict(RISK_RULES))


def save_risk_rules(rules: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    merged = dict(state.get("risk_rules") or {})
    merged.update({key: value for key, value in rules.items() if value is not None})
    merged["updated_at"] = now_iso()
    state["risk_rules"] = merged
    save_state(state)
    return deepcopy(merged)


def list_journal_entries() -> list[dict[str, Any]]:
    entries = load_state().get("journal_entries") or []
    return deepcopy(sorted(entries, key=lambda item: item.get("created_at", ""), reverse=True))


def add_journal_entry(entry: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    saved = dict(entry)
    saved.setdefault("id", str(uuid4()))
    saved.setdefault("created_at", now_iso())
    state.setdefault("journal_entries", []).append(saved)
    save_state(state)
    return deepcopy(saved)


def list_strategies() -> list[dict[str, Any]]:
    return deepcopy(load_state().get("strategies") or [])


def add_strategy(strategy: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    saved = dict(strategy)
    saved.setdefault("id", str(uuid4()))
    saved.setdefault("created_at", now_iso())
    state.setdefault("strategies", []).append(saved)
    save_state(state)
    return deepcopy(saved)


def list_alerts() -> list[dict[str, Any]]:
    alerts = load_state().get("alerts") or []
    return deepcopy(sorted(alerts, key=lambda item: item.get("created_at", ""), reverse=True))


def add_alert(alert: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    saved = dict(alert)
    saved.setdefault("id", str(uuid4()))
    saved.setdefault("enabled", True)
    saved.setdefault("created_at", now_iso())
    state.setdefault("alerts", []).append(saved)
    save_state(state)
    return deepcopy(saved)


def save_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state = load_state()
    state["alerts"] = list(alerts)
    save_state(state)
    return deepcopy(state["alerts"])


def list_session_plans() -> list[dict[str, Any]]:
    plans = load_state().get("session_plans") or []
    return deepcopy(sorted(plans, key=lambda item: item.get("created_at", ""), reverse=True))


def add_session_plan(plan: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    saved = dict(plan)
    saved.setdefault("id", str(uuid4()))
    saved.setdefault("status", "planned")
    saved.setdefault("created_at", now_iso())
    state.setdefault("session_plans", []).append(saved)
    save_state(state)
    return deepcopy(saved)


def list_risk_scenarios() -> list[dict[str, Any]]:
    scenarios = load_state().get("risk_scenarios") or []
    return deepcopy(sorted(scenarios, key=lambda item: item.get("created_at", ""), reverse=True))


def add_risk_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    saved = dict(scenario)
    saved.setdefault("id", str(uuid4()))
    saved.setdefault("created_at", now_iso())
    state.setdefault("risk_scenarios", []).append(saved)
    save_state(state)
    return deepcopy(saved)


def list_paper_trades() -> list[dict[str, Any]]:
    trades = load_state().get("paper_trades") or []
    return deepcopy(sorted(trades, key=lambda item: item.get("created_at", ""), reverse=True))


def add_paper_trade(trade: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    saved = dict(trade)
    saved.setdefault("id", str(uuid4()))
    saved.setdefault("created_at", now_iso())
    state.setdefault("paper_trades", []).append(saved)
    save_state(state)
    return deepcopy(saved)


def update_paper_trade_review(trade_id: str | None, review: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    trades = state.setdefault("paper_trades", [])
    target = None
    if trade_id:
        target = next((item for item in trades if str(item.get("id")) == str(trade_id)), None)
    if target is None and trades:
        target = sorted(trades, key=lambda item: item.get("created_at", ""), reverse=True)[0]
    if target is None:
        return {}
    target.update({key: value for key, value in review.items() if value is not None})
    target["updated_at"] = now_iso()
    if target.get("status") == "reviewed" and not target.get("reviewed_at"):
        target["reviewed_at"] = now_iso()
    save_state(state)
    return deepcopy(target)


def list_screenshot_reviews() -> list[dict[str, Any]]:
    reviews = load_state().get("screenshot_reviews") or []
    return deepcopy(sorted(reviews, key=lambda item: item.get("created_at", ""), reverse=True))


def add_screenshot_review(review: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    saved = dict(review)
    saved.setdefault("id", str(uuid4()))
    saved.setdefault("created_at", now_iso())
    state.setdefault("screenshot_reviews", []).append(saved)
    save_state(state)
    return deepcopy(saved)


def list_watchlists() -> list[dict[str, Any]]:
    return deepcopy(load_state().get("watchlists") or [])


def add_watchlist(payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    watchlist = {
        "id": str(uuid4()),
        "name": payload.get("name") or "New Watchlist",
        "created_at": now_iso(),
        "items": [],
    }
    state.setdefault("watchlists", []).append(watchlist)
    save_state(state)
    return deepcopy(watchlist)


def add_watchlist_item(payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    watchlists = state.setdefault("watchlists", [])
    if not watchlists:
        watchlists.append({"id": str(uuid4()), "name": "Demo Watchlist", "created_at": now_iso(), "items": []})
    watchlist_id = payload.get("watchlist_id") or watchlists[0]["id"]
    target = next((item for item in watchlists if item["id"] == watchlist_id), watchlists[0])
    symbol = str(payload.get("symbol") or "").strip().upper()
    existing = next((item for item in target.get("items", []) if item.get("symbol") == symbol), None)
    if existing:
        existing["asset_type"] = payload.get("asset_type") or existing.get("asset_type") or "stock"
        existing["notes"] = payload.get("notes") or existing.get("notes") or ""
        existing["updated_at"] = now_iso()
        save_state(state)
        return deepcopy(existing)

    saved = {
        "id": str(uuid4()),
        "watchlist_id": target["id"],
        "symbol": symbol,
        "asset_type": payload.get("asset_type") or "stock",
        "notes": payload.get("notes") or "",
        "created_at": now_iso(),
    }
    if saved["symbol"]:
        target.setdefault("items", []).append(saved)
        save_state(state)
    return deepcopy(saved)


def get_activity() -> dict[str, Any]:
    return deepcopy(load_state().get("activity") or {})


def save_activity(payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    activity = dict(state.get("activity") or {})
    activity.update(payload)
    activity["last_seen_at"] = now_iso()
    state["activity"] = activity
    save_state(state)
    return deepcopy(activity)


def get_preferences() -> dict[str, Any]:
    return deepcopy(load_state().get("preferences") or {})


def save_preferences(payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    preferences = dict(state.get("preferences") or {})
    preferences.update({key: value for key, value in payload.items() if value is not None})
    preferences["updated_at"] = now_iso()
    state["preferences"] = preferences
    save_state(state)
    return deepcopy(preferences)


def get_school_progress() -> dict[str, Any]:
    return deepcopy(load_state().get("school_progress") or {})


def save_school_progress(payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    progress = dict(state.get("school_progress") or {})
    lesson_key = str(payload.get("lesson_key") or payload.get("lesson") or "").strip()
    if not lesson_key:
        lesson_key = "demo_lesson"
    saved = {
        "lesson_key": lesson_key,
        "lesson": payload.get("lesson") or lesson_key.replace("_", " ").title(),
        "status": payload.get("status") or "completed",
        "quiz_score": payload.get("quiz_score"),
        "updated_at": now_iso(),
    }
    progress[lesson_key] = saved
    state["school_progress"] = progress
    save_state(state)
    return deepcopy(saved)


def list_usage_events(kind: str | None = None) -> list[dict[str, Any]]:
    events = load_state().get("usage_events") or []
    if kind:
        events = [item for item in events if item.get("kind") == kind]
    return deepcopy(sorted(events, key=lambda item: item.get("created_at", ""), reverse=True))


def record_usage_event(kind: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    state = load_state()
    saved = {
        "id": str(uuid4()),
        "kind": kind,
        "metadata": metadata or {},
        "created_at": now_iso(),
    }
    state.setdefault("usage_events", []).append(saved)
    save_state(state)
    return deepcopy(saved)


def list_data_requests() -> list[dict[str, Any]]:
    requests = load_state().get("data_requests") or []
    return deepcopy(sorted(requests, key=lambda item: item.get("created_at", ""), reverse=True))


def add_data_request(payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    saved = {
        "id": str(uuid4()),
        "request_type": payload.get("request_type") or "export",
        "email": payload.get("email") or "",
        "user_id": payload.get("user_id") or "",
        "status": "received",
        "notes": payload.get("notes") or "",
        "created_at": now_iso(),
    }
    state.setdefault("data_requests", []).append(saved)
    save_state(state)
    return deepcopy(saved)


def list_support_tickets() -> list[dict[str, Any]]:
    tickets = load_state().get("support_tickets") or []
    return deepcopy(sorted(tickets, key=lambda item: item.get("created_at", ""), reverse=True))


def add_support_ticket(payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    saved = {
        "id": str(uuid4()),
        "category": payload.get("category") or "general",
        "email": payload.get("email") or "",
        "subject": payload.get("subject") or "",
        "message": payload.get("message") or "",
        "status": "received",
        "created_at": now_iso(),
    }
    state.setdefault("support_tickets", []).append(saved)
    save_state(state)
    return deepcopy(saved)
