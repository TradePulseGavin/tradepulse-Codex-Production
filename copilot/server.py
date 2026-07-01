from __future__ import annotations

from importlib.util import find_spec
from typing import Any

from fastapi import Body, FastAPI, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .ai_provider import openai_research_response
from .config import ROOT_DIR, settings
from .demo_data import (
    DEMO_MODE_LABEL,
    REQUIRED_DISCLAIMER,
    build_dashboard,
    build_scanner,
    build_strategy,
    build_trade_checklist,
    build_weekly_review,
)
from .local_store import (
    add_alert,
    add_data_request,
    add_journal_entry,
    add_risk_scenario,
    add_screenshot_review,
    add_session_plan,
    add_strategy,
    add_support_ticket,
    add_watchlist,
    add_watchlist_item,
    get_activity,
    get_dashboard_layout,
    get_preferences,
    get_risk_rules,
    get_school_progress,
    add_paper_trade,
    list_alerts,
    list_data_requests,
    list_journal_entries,
    list_paper_trades,
    list_risk_scenarios,
    list_screenshot_reviews,
    list_session_plans,
    list_strategies,
    list_support_tickets,
    list_usage_events,
    list_watchlists,
    load_state,
    record_usage_event,
    save_activity,
    save_dashboard_layout,
    save_preferences,
    save_risk_rules,
    save_alerts,
    save_school_progress,
    now_iso,
    update_paper_trade_review,
)
from .market_data import chart_data, quote_snapshot
from .memory_engine import build_memory_summary
from .news_engine import build_news_brief
from .storage import latest_snapshots, save_snapshot
from .strategy_engine import scan_symbols
from .supabase_store import store

app = FastAPI(title="TradePulse", version="2.0.0-demo-command-center")

PLAN_LABELS = {
    "free": "Free",
    "pro": "Pro",
    "elite": "Elite",
    "all_access": "All Access",
}
PAID_PLANS = {"pro", "elite", "all_access"}
PLAN_PRICES = {
    "free": "$0/mo",
    "pro": "$15/mo",
    "elite": "$25/mo",
    "all_access": "$50/mo",
}
PLAN_DESCRIPTIONS = {
    "free": "Preview the workflow and learn the basics.",
    "pro": "Core research workspace for disciplined paper-trading habits.",
    "elite": "Advanced workspace features without the full AI/data bundle.",
    "all_access": "Full TradePulse access, including the most advanced AI and data tools.",
}
PLAN_FEATURE_COPY = {
    "free": ["Basic dashboard preview", "Starter market context", "Limited chart preview", "Beginner education preview"],
    "pro": ["Watchlists and scanner", "News research and alerts", "Paper planner and journal", "Session prep and review center"],
    "elite": ["Everything in Pro", "Live chart workspace", "Advanced scanner layout", "Full school and dashboard customization"],
    "all_access": ["Everything in Elite", "AI memory and advanced Copilot", "Screenshot analyzer", "Strategy builder and future premium data tools"],
}
PLAN_LIMITS: dict[str, dict[str, int | str]] = {
    "free": {
        "watchlist_symbols": 5,
        "scanner_runs_per_day": 3,
        "alerts": 0,
        "journal_entries": 5,
        "paper_plans": 5,
        "copilot_prompts_per_day": 5,
        "screenshot_reviews": 0,
        "saved_strategies": 0,
    },
    "pro": {
        "watchlist_symbols": 50,
        "scanner_runs_per_day": 75,
        "alerts": 25,
        "journal_entries": 250,
        "paper_plans": 250,
        "copilot_prompts_per_day": 50,
        "screenshot_reviews": 0,
        "saved_strategies": 0,
    },
    "elite": {
        "watchlist_symbols": 150,
        "scanner_runs_per_day": 250,
        "alerts": 100,
        "journal_entries": 1000,
        "paper_plans": 1000,
        "copilot_prompts_per_day": 150,
        "screenshot_reviews": 0,
        "saved_strategies": 0,
    },
    "all_access": {
        "watchlist_symbols": "Unlimited",
        "scanner_runs_per_day": "Unlimited",
        "alerts": "Unlimited",
        "journal_entries": "Unlimited",
        "paper_plans": "Unlimited",
        "copilot_prompts_per_day": "Highest fair use",
        "screenshot_reviews": "Included",
        "saved_strategies": "Included",
    },
}
USAGE_LABELS = {
    "watchlist_symbols": "Watchlist symbols",
    "scanner_runs_per_day": "Scanner runs today",
    "alerts": "Saved alerts",
    "journal_entries": "Journal entries",
    "paper_plans": "Paper plans",
    "copilot_prompts_per_day": "Copilot prompts today",
    "screenshot_reviews": "Screenshot reviews",
    "saved_strategies": "Saved strategies",
}
ACTION_LIMIT_KEYS = {
    "watchlist_symbol": "watchlist_symbols",
    "scanner_run": "scanner_runs_per_day",
    "alert": "alerts",
    "journal_entry": "journal_entries",
    "paper_plan": "paper_plans",
    "copilot_prompt": "copilot_prompts_per_day",
    "screenshot_review": "screenshot_reviews",
    "saved_strategy": "saved_strategies",
}
PLAN_ORDER = ("free", "pro", "elite", "all_access")
PUBLIC_SITEMAP_PATHS = ("/", "/pricing", "/support", "/risk-disclosure", "/privacy", "/terms")

# Needed so the Chrome extension can read prompts from the hosted/local dashboard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        accepts_html = "text/html" in request.headers.get("accept", "")
        if accepts_html or not request.url.path.startswith("/api/"):
            return _render_template("not_found.html", status_code=404)
        return JSONResponse({"ok": False, "error": "Not found", "path": request.url.path}, status_code=404)
    return JSONResponse({"ok": False, "error": str(exc.detail)}, status_code=exc.status_code)


static_dir = ROOT_DIR / "static"
templates_dir = ROOT_DIR / "templates"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def _parse_symbols(symbols: str | None) -> list[str]:
    if not symbols:
        return list(settings.default_symbols)
    parsed = [s.strip().upper().replace("$", "") for s in symbols.split(",") if s.strip()]
    return parsed or list(settings.default_symbols)


def _safe_error_payload(kind: str, error: Exception, symbols: list[str] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "kind": kind,
        "symbols": symbols or list(settings.default_symbols),
        "summary": f"{kind.title()} hit an error, but TradePulse is still running.",
        "error": str(error),
        "tip": "If this is a data error, check your internet/API keys or try fewer symbols like SPY,QQQ.",
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _base_url(request: Request) -> str:
    if settings.app_base_url:
        return settings.app_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def _render_template(name: str, status_code: int = 200, **context: Any) -> HTMLResponse:
    """Small template renderer using simple {{ key }} replacements.

    This keeps the Render-safe behavior from the existing app while allowing
    stable pages before the full backend auth/data layer is upgraded.
    """
    template_path = templates_dir / name
    html = template_path.read_text(encoding="utf-8")
    defaults = {
        "app_name": settings.app_name,
        "support_email": settings.support_email or "Add APP_SUPPORT_EMAIL before public launch",
        "default_symbols": ",".join(settings.default_symbols),
        "stripe_publishable_key": settings.stripe_publishable_key or "",
        "supabase_url": settings.supabase_url or "",
        "supabase_publishable_key": settings.supabase_publishable_key or "",
        "pro_price": "$15/mo",
        "elite_price": "$25/mo",
        "all_access_price": "$50/mo",
        "demo_mode_label": DEMO_MODE_LABEL,
        "required_disclaimer": REQUIRED_DISCLAIMER,
        "owner_mode_note": "Owner emails are evaluated server-side through /api/access.",
        "replay_mode": "false",
        "last_updated": "June 30, 2026",
    }
    defaults.update({k: "" if v is None else str(v) for k, v in context.items()})
    for key, value in defaults.items():
        html = html.replace("{{ " + key + " }}", value)
    return HTMLResponse(html, status_code=status_code)


def _page(name: str, **context: Any) -> HTMLResponse:
    return _render_template(name, **context)


def _plan_features(plan: str) -> dict[str, bool]:
    normalized = plan.lower()
    paid = normalized in PAID_PLANS
    elite_or_higher = normalized in {"elite", "all_access"}
    full = normalized == "all_access"
    return {
        "dashboard": True,
        "watchlist": paid,
        "journal": paid,
        "scanner": paid,
        "alerts": paid,
        "paper_trade": paid,
        "session_prep": paid,
        "live_charts": elite_or_higher,
        "advanced_scanner": elite_or_higher,
        "advanced_layouts": elite_or_higher,
        "school_full": elite_or_higher,
        "copilot_memory": full,
        "screenshot_analyzer": full,
        "strategy_builder": full,
        "full_ai_data": full,
    }


def _plan_limits(plan: str) -> dict[str, int | str]:
    return dict(PLAN_LIMITS.get(plan.lower(), PLAN_LIMITS["free"]))


def _today_usage_count(kind: str) -> int:
    today = now_iso()[:10]
    return sum(1 for item in list_usage_events(kind) if str(item.get("created_at", "")).startswith(today))


def _today_supabase_usage_count(kind: str, token: str) -> int:
    today = now_iso()[:10]
    rows = store.select("usage_events", f"select=kind,created_at&kind=eq.{kind}&order=created_at.desc&limit=1000", auth_token=token)
    return sum(1 for item in rows if str(item.get("created_at", "")).startswith(today))


def _record_usage(kind: str, metadata: dict[str, Any] | None = None, payload: dict[str, Any] | None = None, authorization: str | None = None) -> dict[str, Any]:
    payload = payload or {}
    token = _bearer_token(authorization)
    user_id = payload.get("user_id")
    if token and settings.supabase_publishable_key and settings.supabase_url and user_id:
        try:
            return store.insert("usage_events", {"user_id": user_id, "kind": kind, "metadata": metadata or {}}, auth_token=token)
        except Exception:
            pass
    return record_usage_event(kind, metadata)


def _watchlist_symbol_count(watchlists: list[dict[str, Any]]) -> int:
    symbols: set[str] = set()
    for watchlist in watchlists:
        items = watchlist.get("items") or watchlist.get("watchlist_items") or []
        for item in items:
            symbol = str(item.get("symbol") or "").strip().upper()
            if symbol:
                symbols.add(symbol)
    return len(symbols)


def _demo_usage_counts() -> dict[str, int]:
    state = load_state()
    return {
        "watchlist_symbols": _watchlist_symbol_count(state.get("watchlists") or []),
        "scanner_runs_per_day": _today_usage_count("scanner_run"),
        "alerts": len(state.get("alerts") or []),
        "journal_entries": len(state.get("journal_entries") or []),
        "paper_plans": len(state.get("paper_trades") or []),
        "copilot_prompts_per_day": _today_usage_count("copilot_prompt"),
        "screenshot_reviews": len(state.get("screenshot_reviews") or []),
        "saved_strategies": len(state.get("strategies") or []),
    }


def _supabase_usage_counts(token: str) -> dict[str, int]:
    watchlists = store.select("watchlists", "select=*,watchlist_items(*)&order=created_at.asc", auth_token=token)
    return {
        "watchlist_symbols": _watchlist_symbol_count(watchlists),
        "scanner_runs_per_day": _today_supabase_usage_count("scanner_run", token),
        "alerts": len(store.select("alert_rules", "select=id&limit=1000", auth_token=token)),
        "journal_entries": len(store.select("trade_journal", "select=id&limit=1000", auth_token=token)),
        "paper_plans": len(store.select("paper_trades", "select=id&limit=1000", auth_token=token)),
        "copilot_prompts_per_day": _today_supabase_usage_count("copilot_prompt", token),
        "screenshot_reviews": len(store.select("screenshot_reviews", "select=id&limit=1000", auth_token=token)),
        "saved_strategies": len(store.select("strategy_rules", "select=id&limit=1000", auth_token=token)),
    }


def _usage_meter(key: str, used: int, limit: int | str) -> dict[str, Any]:
    upgrade_plan = _upgrade_plan_for_limit("free", key, used + 1)
    if isinstance(limit, int):
        remaining = max(0, limit - used)
        if limit <= 0:
            percent = 100 if used else 0
            status = "Upgrade required"
        else:
            percent = min(100, round((used / limit) * 100))
            status = "At limit" if used >= limit else "Close" if percent >= 80 else "OK"
        return {
            "key": key,
            "label": USAGE_LABELS.get(key, key.replace("_", " ").title()),
            "used": used,
            "limit": limit,
            "remaining": remaining,
            "percent": percent,
            "status": status,
            "limited": True,
            "at_limit": limit <= 0 or used >= limit,
            "upgrade_plan": upgrade_plan,
        }
    return {
        "key": key,
        "label": USAGE_LABELS.get(key, key.replace("_", " ").title()),
        "used": used,
        "limit": limit,
        "remaining": "Included",
        "percent": 0,
        "status": str(limit),
        "limited": False,
        "at_limit": False,
        "upgrade_plan": None,
    }


def _upgrade_plan_for_limit(plan: str, limit_key: str, projected: int) -> str | None:
    visible_plan = plan if plan in PLAN_ORDER else "free"
    try:
        start = PLAN_ORDER.index(visible_plan) + 1
    except ValueError:
        start = 1
    for candidate in PLAN_ORDER[start:]:
        candidate_limit = _plan_limits(candidate).get(limit_key)
        if not isinstance(candidate_limit, int) or projected <= candidate_limit:
            return candidate
    return None


def _limit_check(action: str, plan: str, increment: int = 1, counts: dict[str, int] | None = None) -> dict[str, Any]:
    visible_plan = plan if plan in PLAN_ORDER else "free"
    limit_key = ACTION_LIMIT_KEYS.get(action, action)
    counts = counts or _demo_usage_counts()
    used = int(counts.get(limit_key, 0))
    limit = _plan_limits(visible_plan).get(limit_key, "Included")
    projected = used + max(0, increment)
    upgrade_plan = _upgrade_plan_for_limit(visible_plan, limit_key, projected)
    if isinstance(limit, int):
        allowed = projected <= limit if limit > 0 else False
        percent = 100 if limit <= 0 else min(100, round((projected / limit) * 100))
        status = "allowed" if allowed and percent < 80 else "near_limit" if allowed else "upgrade_needed"
        message = (
            f"{USAGE_LABELS.get(limit_key, limit_key)} would be {projected}/{limit} on {PLAN_LABELS.get(visible_plan, 'Free')}."
            if allowed
            else f"{USAGE_LABELS.get(limit_key, limit_key)} would exceed the {PLAN_LABELS.get(visible_plan, 'Free')} limit of {limit}."
        )
    else:
        allowed = True
        percent = 0
        status = "included"
        message = f"{USAGE_LABELS.get(limit_key, limit_key)} is {limit} on {PLAN_LABELS.get(visible_plan, 'Free')}."
    return {
        "action": action,
        "limit_key": limit_key,
        "plan": visible_plan,
        "plan_label": PLAN_LABELS.get(visible_plan, "Free"),
        "used": used,
        "increment": increment,
        "projected": projected,
        "limit": limit,
        "allowed": allowed,
        "soft_demo": True,
        "status": status,
        "percent": percent,
        "upgrade_plan": upgrade_plan,
        "upgrade_label": PLAN_LABELS.get(upgrade_plan, "") if upgrade_plan else "",
        "message": message,
    }


def _payload_plan(payload: dict[str, Any] | None, default: str = "all_access") -> str:
    if not payload:
        return default
    plan = str(payload.get("plan") or default).strip().lower()
    return plan if plan in PLAN_ORDER else default


def _mentions(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _screenshot_demo_analysis(
    payload: dict[str, Any],
    filename: str,
    platform: str,
    symbol: str,
    limit_check: dict[str, Any],
) -> dict[str, Any]:
    notes = str(payload.get("notes") or "").strip()
    text = notes.lower()
    tags: list[str] = []
    score = 5

    if _mentions(text, ("uptrend", "higher high", "higher low", "breakout", "bull", "above vwap")):
        trend_summary = f"{symbol or 'This chart'} has bullish context in your notes. Treat the screenshot as a planning review: confirm trend, distance from VWAP, and invalidation before considering any paper setup."
        tags.append("Bullish context")
        score += 1
    elif _mentions(text, ("downtrend", "lower high", "lower low", "breakdown", "bear", "below vwap")):
        trend_summary = f"{symbol or 'This chart'} has bearish context in your notes. Review whether the move is clean or already extended before using it for a paper-trade plan."
        tags.append("Bearish context")
        score += 1
    elif _mentions(text, ("range", "chop", "sideways", "consolidation")):
        trend_summary = f"{symbol or 'This chart'} looks range-focused from your notes. Prioritize support/resistance levels and avoid forcing a trend read."
        tags.append("Range context")
    elif notes:
        trend_summary = f"{filename} was saved from {platform}. The demo review uses your notes as context and asks for the missing chart evidence before any paper plan."
    else:
        trend_summary = f"{filename} was saved from {platform}. Add chart notes next time so the review can connect levels, indicators, and risk more tightly."

    if _mentions(text, ("support", "resistance", "prior high", "prior low", "supply", "demand", "level")):
        support_resistance = "Your notes reference levels. Mark the nearest support, resistance, prior high/low, and the exact invalidation level before calling the setup clean."
        tags.append("Levels noted")
        score += 1
    else:
        support_resistance = "Levels are not explicit yet. Add nearest support, resistance, VWAP, and prior high/low to make the review decision-ready."

    indicators = [name for name in ("vwap", "ema", "rsi", "volume", "macd") if name in text]
    if indicators:
        indicator_notes = "Indicators mentioned: " + ", ".join(indicators).upper() + ". Confirm they support the setup instead of only decorating the chart."
        tags.append("Indicators noted")
        score += 1
    else:
        indicator_notes = "No indicators were named. If the screenshot shows VWAP, EMA, RSI, or volume, write what each one is confirming or warning against."

    if _mentions(text, ("extended", "chase", "fomo", "late", "spike", "breakout")):
        risk_of_chasing = "Chasing risk is elevated from your notes. Wait for confirmation, a pullback, or a clearer invalidation area in paper practice."
        tags.append("Chasing risk")
        score -= 1
    else:
        risk_of_chasing = "Chasing risk cannot be judged from metadata alone. Compare entry distance to VWAP/support and skip paper entries with unclear invalidation."

    if _mentions(text, ("news", "earnings", "fed", "cpi", "fomc", "headline")):
        tags.append("News risk")
        score -= 1

    questions = [
        "Where is invalidation on the screenshot?",
        "What level would prove the setup is not working?",
        "Is price extended from VWAP or the nearest support/resistance?",
    ]
    if not _mentions(text, ("volume", "vol")):
        questions.append("Does volume confirm the move or warn against it?")
    if not _mentions(text, ("news", "earnings", "fed", "cpi", "fomc", "headline")):
        questions.append("Is there any headline or event risk before this paper setup?")

    setup_quality = max(1, min(10, score))
    tags = list(dict.fromkeys(tags)) or ["Needs more notes"]
    return {
        "ok": True,
        "mode": "demo-local",
        "review_type": "metadata-assisted demo review",
        "ai_provider": "Safe demo screenshot reviewer",
        "image_ai_connected": False,
        "filename": filename,
        "platform": platform,
        "symbol": symbol,
        "trend_summary": trend_summary,
        "support_resistance": support_resistance,
        "indicator_notes": indicator_notes,
        "risk_of_chasing": risk_of_chasing,
        "setup_quality": setup_quality,
        "review_tags": tags,
        "journal_prompt": "Save the screenshot with one sentence for trend, one for levels, one for invalidation, and one mistake to avoid.",
        "confirmation_questions": questions[:5],
        "beginner_explanation": "This demo review does not inspect image pixels yet. It turns your screenshot notes into a safer chart-review checklist until real image AI is connected.",
        "limit_check": limit_check,
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _usage_payload(plan: str, counts: dict[str, int], mode: str = "demo-local") -> dict[str, Any]:
    visible_plan = plan if plan in {"free", *PAID_PLANS} else "free"
    limits = _plan_limits(visible_plan)
    items = []
    for key in limits:
        item = _usage_meter(key, int(counts.get(key, 0)), limits[key])
        item["upgrade_plan"] = _upgrade_plan_for_limit(visible_plan, key, int(counts.get(key, 0)) + 1)
        item["upgrade_label"] = PLAN_LABELS.get(item["upgrade_plan"], "") if item["upgrade_plan"] else ""
        items.append(item)
    numeric_items = [item for item in items if item["limited"] and isinstance(item["limit"], int) and item["limit"] > 0]
    closest = max(numeric_items, key=lambda item: item["percent"], default=None)
    at_limit = [item for item in items if item["at_limit"] and item["used"] > 0]
    return {
        "ok": True,
        "mode": mode,
        "plan": visible_plan,
        "plan_label": PLAN_LABELS.get(visible_plan, "Free"),
        "plan_price": PLAN_PRICES.get(visible_plan, "$0/mo"),
        "counts": counts,
        "limits": limits,
        "items": items,
        "closest_limit": closest,
        "at_limit": at_limit,
        "summary": "All tracked usage is inside this plan." if not at_limit else "One or more tracked features is at the current plan limit.",
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _plan_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": plan_id,
            "label": PLAN_LABELS[plan_id],
            "price": PLAN_PRICES[plan_id],
            "description": PLAN_DESCRIPTIONS[plan_id],
            "features": PLAN_FEATURE_COPY[plan_id],
            "feature_flags": _plan_features(plan_id),
            "limits": _plan_limits(plan_id),
            "checkout_plan": plan_id if plan_id in PAID_PLANS else None,
        }
        for plan_id in ("free", "pro", "elite", "all_access")
    ]


def _launch_item(
    group: str,
    title: str,
    ready: bool,
    ready_text: str,
    next_step: str,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "group": group,
        "title": title,
        "ready": ready,
        "status": "Ready" if ready else "Needed",
        "required_for_public_launch": required,
        "body": ready_text if ready else next_step,
        "next_step": next_step,
    }


def _launch_checklist_payload() -> dict[str, Any]:
    supabase_public = bool(settings.supabase_url and settings.supabase_publishable_key)
    stripe_core = bool(settings.stripe_secret_key and settings.stripe_price_id_pro)
    stripe_all_prices = bool(settings.stripe_price_id_pro and settings.stripe_price_id_elite and settings.stripe_price_id_all_access)
    stripe_webhook = bool(settings.stripe_secret_key and settings.stripe_webhook_secret)
    stripe_customer_portal = bool(settings.stripe_secret_key and store.configured)
    news_or_data = bool(settings.finnhub_api_key or settings.alpha_vantage_api_key or settings.newsapi_key)
    items = [
        _launch_item("Accounts", "Supabase login keys", supabase_public, "Signup/login can run through Supabase.", "Add SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in Render."),
        _launch_item("Accounts", "Server persistence key", store.configured, "The server can sync subscriptions and user-owned rows.", "Add SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY."),
        _launch_item("Billing", "Stripe checkout core", stripe_core, "Pro checkout has the required Stripe secret and price.", "Add STRIPE_SECRET_KEY and STRIPE_PRICE_ID_PRO."),
        _launch_item("Billing", "All plan prices", stripe_all_prices, "Pro, Elite, and All Access price IDs are configured.", "Add STRIPE_PRICE_ID_PRO, STRIPE_PRICE_ID_ELITE, and STRIPE_PRICE_ID_ALL_ACCESS."),
        _launch_item("Billing", "Stripe webhook", stripe_webhook, "Webhook signature verification can sync active subscriptions.", "Add STRIPE_WEBHOOK_SECRET and point Stripe to /billing/webhook."),
        _launch_item("Billing", "Stripe customer portal", stripe_customer_portal, "Manage Billing can request Stripe customer portal sessions for saved subscribers.", "Add STRIPE_SECRET_KEY and SUPABASE_SECRET_KEY, then enable the Stripe customer portal in Stripe."),
        _launch_item("Access", "Owner bypass", bool(settings.owner_emails), "Owner emails can receive All Access while testing.", "Add OWNER_EMAILS for admin testing.", required=False),
        _launch_item("AI", "OpenAI research key", bool(settings.openai_api_key), f"Real AI research responses can use {settings.openai_model}.", "Add OPENAI_API_KEY when you are ready to upgrade beyond safe mock responses.", required=False),
        _launch_item("Data", "Real market data switch", settings.enable_real_market_data, "Chart routes can request real research candles with demo fallback.", "Set ENABLE_REAL_MARKET_DATA=true after provider testing.", required=False),
        _launch_item("Data", "Keyed data/news providers", news_or_data, "At least one keyed news/data provider is configured.", "Add FINNHUB_API_KEY, ALPHA_VANTAGE_API_KEY, or NEWSAPI_KEY for richer research context.", required=False),
        _launch_item("Safety", "Broker execution disabled", not settings.enable_broker_orders, "Broker order execution is disabled for public testing.", "Keep ENABLE_BROKER_ORDERS=false before launch."),
        _launch_item("Safety", "Security headers", True, "Basic browser safety headers are added to every response.", "Keep X-Content-Type-Options, X-Frame-Options, Referrer-Policy, and Permissions-Policy enabled."),
        _launch_item("Safety", "Legal pages", True, "Risk disclosure, privacy, and terms pages are present.", "Review placeholder legal text with a qualified professional before public launch."),
        _launch_item("Safety", "Account data controls", True, "Account export and data request endpoints are present for demo and production wiring.", "Keep privacy export and deletion request routes available before launch."),
        _launch_item("Safety", "Support ticket intake", True, "Support requests can be captured safely in demo mode.", "Connect the support form to email or a helpdesk before scaling paid traffic.", required=False),
        _launch_item("Safety", "Support contact", bool(settings.support_email), "A public support email is configured for account, billing, and privacy questions.", "Add APP_SUPPORT_EMAIL before public paid launch."),
        _launch_item("Product", "Plan catalog", True, "Free, Pro, Elite, and All Access are exposed through /api/plans.", "Connect Stripe prices before charging real customers."),
        _launch_item("Product", "Usage meters", True, "Account usage meters compare saved activity against the active plan.", "Connect real server-side metering before strict enforcement."),
        _launch_item("Product", "Demo backup export", True, "Demo data can be exported before moving into real persistence.", "Use Settings > Export demo data before switching storage modes.", required=False),
    ]
    required_items = [item for item in items if item["required_for_public_launch"]]
    ready_required = sum(1 for item in required_items if item["ready"])
    ready_total = sum(1 for item in items if item["ready"])
    blockers = [item for item in required_items if not item["ready"]]
    score = round((ready_required / max(1, len(required_items))) * 100)
    mode = "launch-ready" if not blockers else "demo-ready"
    return {
        "ok": True,
        "mode": mode,
        "score": score,
        "summary": "Ready for public launch checks." if not blockers else "Stable demo mode is ready; production services still need connection.",
        "required_ready": ready_required,
        "required_total": len(required_items),
        "ready_total": ready_total,
        "item_total": len(items),
        "blockers": blockers,
        "items": items,
        "plans": _plan_catalog(),
        "safe_notes": [
            "Keep broker execution disabled for public testing.",
            "Use demo/delayed data labels until real provider keys are configured and tested.",
            "AI output must stay framed as research, education, journaling, and risk review.",
            "Review legal pages before accepting real paying customers.",
        ],
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _business_plan_payload() -> dict[str, Any]:
    launch = _launch_checklist_payload()
    assumed_cost_floor = 250
    return {
        "ok": True,
        "mode": launch["mode"],
        "generated_at": now_iso(),
        "positioning": {
            "category": "Demo-first trading research workspace",
            "promise": "Help self-directed traders organize research, plan paper trades, journal decisions, and review risk without executing trades.",
            "boundary": REQUIRED_DISCLAIMER,
        },
        "audience": [
            "Beginner and intermediate traders who need structure before using real money.",
            "Active learners who want watchlists, session prep, alerts, paper planning, and journal review in one place.",
            "Users who value risk controls, education, and transparent demo/live-data labeling.",
        ],
        "offer": {
            "plans": _plan_catalog(),
            "upgrade_logic": "Free previews the workflow, Pro unlocks the core workspace, Elite adds advanced workspace features, and All Access includes the full AI/data toolset.",
            "full_access_plan": "all_access",
        },
        "unit_economics": {
            "assumptions": [
                "Use Stripe subscriptions for monthly recurring revenue.",
                "Keep broker execution disabled during public testing to reduce compliance and safety risk.",
                "Treat AI, market data, hosting, Supabase, support, and legal review as the main early cost buckets.",
            ],
            "monthly_cost_floor": assumed_cost_floor,
            "break_even_examples": [
                {"plan": "Pro", "price": "$15/mo", "subscribers_needed": (assumed_cost_floor + 14) // 15},
                {"plan": "Elite", "price": "$25/mo", "subscribers_needed": (assumed_cost_floor + 24) // 25},
                {"plan": "All Access", "price": "$50/mo", "subscribers_needed": (assumed_cost_floor + 49) // 50},
            ],
            "note": "Planning math is a simple operating model, not accounting, tax, legal, or financial advice.",
        },
        "launch_milestones": [
            {"stage": "Stable demo", "goal": "Keep every core page working with safe demo data.", "status": "Ready"},
            {"stage": "Private beta", "goal": "Connect Supabase auth, support email, Stripe test mode, and owner access.", "status": "Next"},
            {"stage": "Paid beta", "goal": "Verify checkout, webhooks, plan gates, billing portal, and support workflows.", "status": "Next"},
            {"stage": "AI upgrade", "goal": "Connect real AI after safety prompts, usage limits, and user-facing labels are stable.", "status": "Later"},
            {"stage": "Data upgrade", "goal": "Add tested provider keys and keep demo fallback when providers fail.", "status": "Later"},
        ],
        "customer_success": [
            "Make Support visible from pricing, account, privacy, and risk pages.",
            "Keep account export and deletion requests reviewed instead of automatic.",
            "Use onboarding preferences to guide the first dashboard experience.",
            "Measure activation through session prep, paper plans, journal entries, and return visits.",
        ],
        "risk_controls": [
            *launch["safe_notes"],
            "Do not market TradePulse as a signal service, broker, automated trader, or financial advisor.",
            "Keep public copy focused on research, education, journaling, paper practice, and risk review.",
        ],
        "current_blockers": launch["blockers"],
        "next_actions": [
            item["next_step"] for item in launch["blockers"][:5]
        ] or ["Keep validation green and prepare a production environment review."],
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _setup_item(
    group: str,
    key: str,
    label: str,
    ready: bool,
    required: bool,
    ready_text: str,
    missing_text: str,
) -> dict[str, Any]:
    return {
        "group": group,
        "key": key,
        "label": label,
        "ready": ready,
        "required": required,
        "status": "Ready" if ready else "Needed",
        "body": ready_text if ready else missing_text,
        "missing_text": missing_text,
    }


def _production_setup_payload(request: Request | None = None) -> dict[str, Any]:
    base = _base_url(request) if request else (settings.app_base_url or "http://127.0.0.1:8000")
    supabase_public = bool(settings.supabase_url and settings.supabase_publishable_key)
    supabase_server = bool(settings.supabase_url and settings.supabase_secret_key)
    stripe_core = bool(settings.stripe_secret_key and settings.stripe_price_id_pro)
    stripe_all_prices = bool(settings.stripe_price_id_pro and settings.stripe_price_id_elite and settings.stripe_price_id_all_access)
    stripe_webhook = bool(settings.stripe_secret_key and settings.stripe_webhook_secret)
    openai_ready = bool(settings.openai_api_key)
    keyed_news = bool(settings.finnhub_api_key or settings.alpha_vantage_api_key or settings.newsapi_key)
    yfinance_ready = bool(find_spec("yfinance"))
    items = [
        _setup_item("Accounts", "SUPABASE_URL", "Supabase project URL", bool(settings.supabase_url), True, "Supabase URL is configured.", "Add SUPABASE_URL from your Supabase project settings."),
        _setup_item("Accounts", "SUPABASE_PUBLISHABLE_KEY", "Supabase public key", bool(settings.supabase_publishable_key), True, "Login/signup can load the public Supabase client.", "Add SUPABASE_PUBLISHABLE_KEY or SUPABASE_ANON_KEY."),
        _setup_item("Accounts", "SUPABASE_SECRET_KEY", "Supabase service key", bool(settings.supabase_secret_key), True, "Server persistence and Stripe subscription sync can write protected rows.", "Add SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY in Render only."),
        _setup_item("Billing", "STRIPE_SECRET_KEY", "Stripe secret key", bool(settings.stripe_secret_key), True, "Stripe checkout and portal requests can be created server-side.", "Add STRIPE_SECRET_KEY."),
        _setup_item("Billing", "STRIPE_PRICE_ID_PRO", "Pro price", bool(settings.stripe_price_id_pro), True, "Pro checkout has a Stripe price ID.", "Add STRIPE_PRICE_ID_PRO for the $15/mo plan."),
        _setup_item("Billing", "STRIPE_PRICE_ID_ELITE", "Elite price", bool(settings.stripe_price_id_elite), True, "Elite checkout has a Stripe price ID.", "Add STRIPE_PRICE_ID_ELITE for the $25/mo plan."),
        _setup_item("Billing", "STRIPE_PRICE_ID_ALL_ACCESS", "All Access price", bool(settings.stripe_price_id_all_access), True, "All Access checkout has a Stripe price ID.", "Add STRIPE_PRICE_ID_ALL_ACCESS for the $50/mo plan."),
        _setup_item("Billing", "STRIPE_WEBHOOK_SECRET", "Stripe webhook secret", bool(settings.stripe_webhook_secret), True, "Stripe webhook signatures can be verified.", f"Create a Stripe webhook for {base}/billing/webhook and add STRIPE_WEBHOOK_SECRET."),
        _setup_item("AI", "OPENAI_API_KEY", "OpenAI research key", openai_ready, False, f"Copilot can call OpenAI using {settings.openai_model}.", "Add OPENAI_API_KEY when you are ready to replace safe mock responses."),
        _setup_item("AI", "OPENAI_MODEL", "OpenAI model", bool(settings.openai_model), False, f"Model is set to {settings.openai_model}.", "Set OPENAI_MODEL if you want to override the default."),
        _setup_item("Market Data", "ENABLE_REAL_MARKET_DATA", "Real market data switch", settings.enable_real_market_data, False, "Chart routes can request real research candles with demo fallback.", "Keep false until provider behavior is tested, then set ENABLE_REAL_MARKET_DATA=true."),
        _setup_item("Market Data", "YFINANCE_RUNTIME", "YFinance runtime", yfinance_ready, False, "YFinance package is installed for research candles and quotes.", "Install yfinance or keep demo candles active."),
        _setup_item("Market Data", "NEWS_PROVIDER_KEYS", "News provider keys", keyed_news, False, "At least one keyed news provider is configured.", "Add FINNHUB_API_KEY, ALPHA_VANTAGE_API_KEY, or NEWSAPI_KEY for richer news context."),
        _setup_item("Safety", "APP_BASE_URL", "Public app URL", bool(settings.app_base_url), True, "Public base URL is configured for redirects and sitemap URLs.", "Set APP_BASE_URL to the deployed Render URL or custom domain."),
        _setup_item("Safety", "APP_SUPPORT_EMAIL", "Support email", bool(settings.support_email), True, "Support, privacy, and billing pages show a real contact.", "Add APP_SUPPORT_EMAIL before public paid launch."),
        _setup_item("Safety", "OWNER_EMAILS", "Owner emails", bool(settings.owner_emails), False, "Owner/admin accounts can receive All Access while testing.", "Add OWNER_EMAILS for admin testing."),
        _setup_item("Safety", "ENABLE_BROKER_ORDERS", "Broker orders disabled", not settings.enable_broker_orders, True, "Broker execution is disabled.", "Set ENABLE_BROKER_ORDERS=false for public testing."),
    ]
    required_items = [item for item in items if item["required"]]
    ready_required = sum(1 for item in required_items if item["ready"])
    ready_total = sum(1 for item in items if item["ready"])
    blockers = [item for item in required_items if not item["ready"]]
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(item["group"], []).append(item)
    private_beta_ready = supabase_public and bool(settings.support_email) and not settings.enable_broker_orders
    paid_beta_ready = private_beta_ready and supabase_server and stripe_core and stripe_all_prices and stripe_webhook
    return {
        "ok": True,
        "mode": "production-ready" if not blockers else "setup-needed",
        "score": round((ready_required / max(1, len(required_items))) * 100),
        "required_ready": ready_required,
        "required_total": len(required_items),
        "ready_total": ready_total,
        "item_total": len(items),
        "groups": groups,
        "items": items,
        "blockers": blockers,
        "private_beta_ready": private_beta_ready,
        "paid_beta_ready": paid_beta_ready,
        "urls": {
            "app_base_url": base,
            "stripe_webhook_url": f"{base}/billing/webhook",
            "supabase_redirect_url": f"{base}/auth/confirmed",
            "password_reset_url": f"{base}/reset-password",
        },
        "checkout_paths": {
            "pro": "/billing/checkout?plan=pro",
            "elite": "/billing/checkout?plan=elite",
            "all_access": "/billing/checkout?plan=all_access",
        },
        "runtime_modes": {
            "accounts": "supabase" if supabase_public else "demo-local",
            "persistence": "supabase" if supabase_server else "demo-local",
            "billing": "stripe" if stripe_core else "safe-placeholder",
            "ai": "openai" if openai_ready else "safe-mock",
            "market_data": "real-enabled" if settings.enable_real_market_data else "demo-fallback",
        },
        "next_actions": [item["missing_text"] for item in blockers[:6]]
        or ["Run a final hosted smoke test, then start private beta with broker execution still disabled."],
        "safe_notes": [
            "Do not paste secret keys into chat or frontend files.",
            "Keep all secret keys in Render environment variables.",
            "Run the Supabase migration before testing paid accounts.",
            "Keep broker execution disabled for this launch phase.",
            "Treat AI and data outputs as research and education only.",
        ],
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _bearer_token(authorization: str | None) -> str | None:
    if not isinstance(authorization, str):
        return None
    if not authorization:
        return None
    prefix = "Bearer "
    if authorization.startswith(prefix):
        token = authorization[len(prefix) :].strip()
        return token or None
    return None


def _demo_persistence_response(kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "mode": "demo-local",
        "kind": kind,
        "item": payload or {},
        "message": "Saved in demo mode. Add Supabase credentials and run the MVP migration for real persistence.",
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _only(payload: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key in allowed and value is not None and value != ""}


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


SCHOOL_QUIZZES: dict[str, list[dict[str, Any]]] = {
    "trading_basics": [
        {
            "question": "What should be defined before a trade is reviewed as planned?",
            "choices": ["Only the target", "Entry, stop, target, and invalidation", "A social media headline"],
            "answer_index": 1,
            "explanation": "A plan is reviewable when the setup, risk, and invalidation are written down first.",
        }
    ],
    "candlesticks": [
        {
            "question": "What is the safer research interpretation of one large green candle?",
            "choices": ["Automatic buy signal", "Momentum that still needs context", "Proof risk is gone"],
            "answer_index": 1,
            "explanation": "A single candle can show momentum, but trend, volume, VWAP, and news risk still matter.",
        }
    ],
    "support_and_resistance": [
        {
            "question": "Why do traders mark support and resistance?",
            "choices": ["To predict perfectly", "To plan reaction areas and risk", "To remove the need for stops"],
            "answer_index": 1,
            "explanation": "Levels are planning areas, not guarantees.",
        }
    ],
    "vwap": [
        {
            "question": "What does VWAP help estimate intraday?",
            "choices": ["Company earnings", "Volume-weighted fair price", "Guaranteed reversal points"],
            "answer_index": 1,
            "explanation": "VWAP combines price and volume to show a commonly watched intraday fair-price area.",
        }
    ],
    "ema": [
        {
            "question": "What is a moving average best used for in this app?",
            "choices": ["Trend context", "Guaranteed entries", "Ignoring news"],
            "answer_index": 0,
            "explanation": "Moving averages help organize trend context; they do not make decisions for you.",
        }
    ],
    "rsi_and_atr": [
        {
            "question": "What does ATR help you think about?",
            "choices": ["Typical movement size", "Whether a stock is good", "Exact profit targets"],
            "answer_index": 0,
            "explanation": "ATR is useful for volatility context, especially stop distance and position sizing.",
        }
    ],
    "risk_reward_and_stop_loss": [
        {
            "question": "Why is a stop loss part of the review checklist?",
            "choices": ["It guarantees a small loss", "It defines when the idea is invalid", "It predicts the next candle"],
            "answer_index": 1,
            "explanation": "A stop is tied to invalidation; slippage and gaps can still happen.",
        }
    ],
    "iv_greeks_spreads_and_open_interest": [
        {
            "question": "What can high implied volatility do to options?",
            "choices": ["Make premiums expensive", "Remove theta risk", "Guarantee liquidity"],
            "answer_index": 0,
            "explanation": "High IV can make contracts expensive even when the direction idea is reasonable.",
        }
    ],
    "tick_size_tick_value_margin_and_sessions": [
        {
            "question": "Why check futures tick value before sizing?",
            "choices": ["It shows the dollar impact of movement", "It guarantees margin approval", "It replaces a stop"],
            "answer_index": 0,
            "explanation": "Tick value turns price movement into dollars, which is essential for risk planning.",
        }
    ],
    "journaling_and_discipline": [
        {
            "question": "What is the main purpose of the journal?",
            "choices": ["Prove every trade was right", "Find repeatable patterns and mistakes", "Avoid reviewing losses"],
            "answer_index": 1,
            "explanation": "The journal is for pattern recognition and improvement, not self-punishment.",
        }
    ],
}


def _lesson_key(lesson: str) -> str:
    key = "".join(char.lower() if char.isalnum() else "_" for char in lesson)
    while "__" in key:
        key = key.replace("__", "_")
    return key.strip("_") or "lesson"


def _weekly_review_from_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    base = build_weekly_review()
    wins = [item for item in entries if str(item.get("result", "")).lower() == "win"]
    losses = [item for item in entries if str(item.get("result", "")).lower() == "loss"]
    pnl_values = []
    for item in entries:
        try:
            pnl_values.append(float(item.get("pnl") or 0))
        except (TypeError, ValueError):
            pass
    repeated = {}
    for item in entries:
        mistake = str(item.get("mistakes") or item.get("setup_type") or "").strip()
        if mistake:
            repeated[mistake] = repeated.get(mistake, 0) + 1
    most_repeated = max(repeated, key=repeated.get) if repeated else "Add more entries to detect a pattern."
    base["entries"] = entries
    base["weekly_review"] = {
        "total_trades": len(entries),
        "wins": len(wins),
        "losses": len(losses),
        "best_setup": "VWAP bounce" if entries else "Add trades to find your best setup.",
        "worst_habit": most_repeated,
        "average_win_loss": round(sum(pnl_values) / len(pnl_values), 2) if pnl_values else "Not enough P/L data yet.",
        "most_repeated_mistake": most_repeated,
        "focus_next_week": "Define invalidation and avoid chasing extended candles.",
    }
    return base


def _watchlist_symbols(watchlists: list[dict[str, Any]] | None = None) -> list[str]:
    symbols = []
    for watchlist in watchlists or list_watchlists():
        for item in watchlist.get("items", []):
            symbol = str(item.get("symbol") or "").strip().upper()
            if symbol and symbol not in symbols:
                symbols.append(symbol)
    return symbols


def _dashboard_with_local_state() -> dict[str, Any]:
    data = build_dashboard()
    watchlists = list_watchlists()
    symbols = _watchlist_symbols(watchlists)
    if symbols:
        data["watchlist"] = [quote_snapshot(symbol, live=settings.enable_real_market_data) for symbol in symbols]
        data["scanner"] = build_scanner(symbols)
    entries = list_journal_entries()
    review = _weekly_review_from_entries(entries)["weekly_review"]
    data["journal_summary"] = {
        "total_trades": review["total_trades"],
        "wins": review["wins"],
        "losses": review["losses"],
        "demo_pnl": round(sum(_number(item.get("pnl")) for item in entries), 2),
        "best_setup": review["best_setup"],
        "worst_habit": review["worst_habit"],
        "focus": review["focus_next_week"],
    }
    data["saved_watchlists"] = watchlists
    data["risk_rules"] = get_risk_rules()
    data["dashboard_layout"] = get_dashboard_layout()
    data["activity"] = get_activity()
    data["memory_summary"] = _memory_summary()
    data["alert_summary"] = _alert_payload()
    data["session_prep"] = _session_prep_payload()
    data["preferences"] = get_preferences()
    return data


def _memory_summary() -> dict[str, Any]:
    return build_memory_summary(
        journal_entries=list_journal_entries(),
        strategies=list_strategies(),
        paper_trades=list_paper_trades(),
        risk_rules=get_risk_rules(),
        preferences=get_preferences(),
    )


def _evaluate_alert(alert: dict[str, Any]) -> dict[str, Any]:
    symbol = str(alert.get("symbol") or "SPY").upper()
    alert_type = str(alert.get("alert_type") or "price").lower()
    operator = str(alert.get("operator") or "above").lower()
    target = _number(alert.get("target_value"))
    snapshot = quote_snapshot(symbol, live=False)
    price = _number(snapshot.get("price"))
    triggered = False
    if alert_type == "price":
        if operator == "above":
            triggered = price >= target
        elif operator == "below":
            triggered = price <= target
        elif operator == "near":
            triggered = target > 0 and abs(price - target) / target <= 0.01
    elif alert_type == "score":
        score = _number(snapshot.get("tradepulse_score"))
        triggered = score >= target if operator in {"above", "near"} else score <= target
    elif alert_type == "news":
        triggered = str(snapshot.get("news_risk") or "").lower() in {"high", "medium"}
    elif alert_type == "risk":
        rules = get_risk_rules()
        triggered = bool(rules.get("require_stop_loss", True))
    message = (
        f"{symbol} alert is ready for review. Current demo price is {price}; "
        f"condition is {alert_type} {operator} {target or alert.get('target_value') or ''}."
    )
    if not triggered:
        message = f"{symbol} alert is not triggered in the current demo snapshot."
    return dict(alert, triggered=triggered, current_price=price, snapshot=snapshot, message=message, disclaimer=REQUIRED_DISCLAIMER)


def _alert_payload() -> dict[str, Any]:
    alerts = list_alerts()
    evaluated = [_evaluate_alert(alert) for alert in alerts if alert.get("enabled", True)]
    triggered = [alert for alert in evaluated if alert.get("triggered")]
    return {
        "ok": True,
        "mode": "demo-local",
        "items": alerts,
        "evaluated": evaluated,
        "triggered": triggered,
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _session_prep_payload(items: list[dict[str, Any]] | None = None, mode: str = "demo-local") -> dict[str, Any]:
    plans = items if items is not None else list_session_plans()
    preferences = get_preferences()
    rules = get_risk_rules()
    memory = _memory_summary()
    alert_payload = _alert_payload()
    symbols = _watchlist_symbols()
    if not symbols:
        symbols = _parse_symbols(str(preferences.get("default_symbols") or "SPY,QQQ,NVDA"))
    focus_symbols = symbols[:5]
    max_trades = rules.get("max_trades_per_day") or 3
    max_losses = rules.get("max_losses_per_day") or 2
    avoid_news = rules.get("avoid_news_minutes") or 15
    risk_style = preferences.get("risk_style") or "conservative"
    learning_goal = preferences.get("learning_goal") or "Build disciplined paper-trading habits first."
    triggered = alert_payload.get("triggered") or []
    next_reviews = memory.get("next_reviews") or []
    suggested = {
        "session_goal": learning_goal,
        "focus_symbols": ",".join(focus_symbols),
        "market_notes": "Start with broad-market context, then review watchlist names one by one.",
        "risk_notes": f"{risk_style.title()} mode: cap paper plans at {max_trades} for the day and pause after {max_losses} losses.",
        "rules_for_today": [
            "Write the setup, stop, target, and invalidation before saving a paper plan.",
            f"Check scheduled news and wait at least {avoid_news} minutes around high-impact events.",
            "Use alerts and screenshots as review prompts, not trade instructions.",
        ],
        "avoid_conditions": [
            "Chasing large candles far from VWAP without written invalidation.",
            "Adding a plan after emotional losses or missed moves.",
            "Treating any score, alert, or AI note as financial advice.",
        ],
        "pre_trade_checks": next_reviews[:3]
        or ["Confirm trend context.", "Confirm stop distance.", "Confirm the reason is specific enough to review later."],
        "alerts_to_review": [
            f"{item.get('symbol', 'Alert')}: {item.get('message', 'Review condition')}" for item in triggered[:3]
        ],
    }
    return {
        "ok": True,
        "mode": mode,
        "items": plans,
        "latest": plans[0] if plans else None,
        "suggested_plan": suggested,
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _review_center_payload() -> dict[str, Any]:
    prep = _session_prep_payload()
    alerts = _alert_payload()
    paper_trades = list_paper_trades()
    risk_scenarios = list_risk_scenarios()
    screenshot_reviews = list_screenshot_reviews()
    entries = list_journal_entries()
    weekly = _weekly_review_from_entries(entries)["weekly_review"]
    progress = get_school_progress()
    next_lesson = None
    for module in build_dashboard().get("school_modules", []):
        key = _lesson_key(str(module.get("lesson") or "lesson"))
        saved = progress.get(key) or {}
        if saved.get("status") != "completed":
            next_lesson = dict(module, lesson_key=key)
            break
    triggered = alerts.get("triggered") or []
    latest_prep = prep.get("latest")
    latest_trade = paper_trades[0] if paper_trades else None
    reviewed_trades = [item for item in paper_trades if item.get("status") == "reviewed"]
    journalized_trades = [item for item in reviewed_trades if item.get("journal_entry_id") or item.get("journalized_at")]
    latest_risk = risk_scenarios[0] if risk_scenarios else None
    latest_shot = screenshot_reviews[0] if screenshot_reviews else None
    latest_trade_body = "No paper plans yet. Use the planner only after prep is written."
    latest_trade_status = "Empty"
    if latest_trade:
        latest_trade_status = latest_trade.get("status", "planned").title()
        if latest_trade.get("journal_entry_id") or latest_trade.get("journalized_at"):
            latest_trade_body = f"{latest_trade.get('symbol', 'Paper plan')} has been reviewed and sent to the journal."
            latest_trade_status = "Journaled"
        elif latest_trade.get("status") == "reviewed":
            latest_trade_body = f"{latest_trade.get('symbol', 'Paper plan')} is reviewed and ready for journal follow-up."
            latest_trade_status = "Journal ready"
        else:
            latest_trade_body = f"{latest_trade.get('symbol', 'Paper plan')} needs a practice review after paper execution."
    tasks = [
        {
            "title": "Write session prep",
            "body": "Review watchlist, risk limits, and avoid conditions before saving any paper plan.",
            "status": "Saved" if latest_prep else "Ready",
            "href": "/session-prep",
        },
        {
            "title": "Review triggered alerts",
            "body": f"{len(triggered)} alert condition(s) need review." if triggered else "No triggered demo alerts right now.",
            "status": "Review now" if triggered else "Clear",
            "href": "/alerts",
        },
        {
            "title": "Run risk lab",
            "body": (
                f"Latest saved scenario: {latest_risk.get('symbol', 'Scenario')} risk ${latest_risk.get('planned_risk', 0)}."
                if latest_risk
                else "Calculate risk before turning an idea into a paper plan."
            ),
            "status": "Saved" if latest_risk else "Ready",
            "href": "/risk-lab",
        },
        {
            "title": "Check latest paper plan",
            "body": latest_trade_body,
            "status": latest_trade_status,
            "href": "/paper-trade",
        },
        {
            "title": "Capture chart context",
            "body": (
                f"Latest screenshot review: {latest_shot.get('symbol') or latest_shot.get('filename') or 'chart'}."
                if latest_shot
                else "Add a screenshot review when a setup is worth studying."
            ),
            "status": "Saved" if latest_shot else "Ready",
            "href": "/screenshot-analyzer",
        },
        {
            "title": "Journal discipline check",
            "body": f"{weekly.get('total_trades', 0)} journal entries. Next focus: {weekly.get('focus_next_week')}",
            "status": f"{weekly.get('wins', 0)}W / {weekly.get('losses', 0)}L",
            "href": "/journal",
        },
        {
            "title": "Continue learning path",
            "body": (
                f"Next lesson: {next_lesson.get('lesson')}."
                if next_lesson
                else "All current demo lessons are complete."
            ),
            "status": next_lesson.get("track", "Complete") if next_lesson else "Complete",
            "href": "/school",
        },
    ]
    return {
        "ok": True,
        "mode": "demo-local",
        "metrics": {
            "saved_prep_plans": len(prep.get("items") or []),
            "triggered_alerts": len(triggered),
            "paper_plans": len(paper_trades),
            "risk_scenarios": len(risk_scenarios),
            "journal_entries": len(entries),
            "screenshot_reviews": len(screenshot_reviews),
            "reviewed_paper_plans": len(reviewed_trades),
            "journalized_paper_plans": len(journalized_trades),
        },
        "tasks": tasks,
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _progress_payload() -> dict[str, Any]:
    prep = list_session_plans()
    risk_scenarios = list_risk_scenarios()
    paper_trades = list_paper_trades()
    reviewed_trades = [item for item in paper_trades if item.get("status") == "reviewed"]
    journalized_trades = [item for item in reviewed_trades if item.get("journal_entry_id") or item.get("journalized_at")]
    entries = list_journal_entries()
    screenshots = list_screenshot_reviews()
    progress = get_school_progress()
    modules = build_dashboard().get("school_modules", [])
    completed_lessons = sum(1 for item in progress.values() if item.get("status") == "completed")
    weekly = _weekly_review_from_entries(entries)["weekly_review"]
    score = 0
    score += 15 if prep else 0
    score += 15 if risk_scenarios else 0
    score += 20 if paper_trades else 0
    score += 15 if reviewed_trades else 0
    score += 15 if journalized_trades else 0
    score += 10 if screenshots else 0
    score += 10 if completed_lessons else 0
    next_lesson = None
    for module in modules:
        key = _lesson_key(str(module.get("lesson") or "lesson"))
        saved = progress.get(key) or {}
        if saved.get("status") != "completed":
            next_lesson = dict(module, lesson_key=key)
            break
    actions = []
    if not prep:
        actions.append({"title": "Write today's prep", "body": "Set focus symbols, risk limits, and avoid conditions.", "href": "/session-prep"})
    if not risk_scenarios:
        actions.append({"title": "Run one risk scenario", "body": "Check paper sizing before saving a practice plan.", "href": "/risk-lab"})
    unreviewed = next((item for item in paper_trades if item.get("status") != "reviewed"), None)
    if unreviewed:
        actions.append({"title": "Review latest paper plan", "body": f"{unreviewed.get('symbol', 'Paper plan')} is waiting for a practice review.", "href": "/paper-trade"})
    reviewed_unjournaled = next((item for item in reviewed_trades if not item.get("journal_entry_id") and not item.get("journalized_at")), None)
    if reviewed_unjournaled:
        actions.append({"title": "Send review to journal", "body": f"{reviewed_unjournaled.get('symbol', 'Paper plan')} is reviewed but not linked to a journal entry.", "href": "/paper-trade"})
    if not screenshots:
        actions.append({"title": "Capture chart context", "body": "Save one screenshot review for later pattern study.", "href": "/screenshot-analyzer"})
    if next_lesson:
        actions.append({"title": "Continue school", "body": f"Next lesson: {next_lesson.get('lesson')}.", "href": "/school"})
    if not actions:
        actions.append({"title": "Keep the loop steady", "body": "Prep, risk, paper review, journal, screenshots, and learning all have demo evidence.", "href": "/review-center"})
    milestones = [
        {"label": "Session prep", "value": len(prep), "status": "Started" if prep else "Ready"},
        {"label": "Risk scenarios", "value": len(risk_scenarios), "status": "Started" if risk_scenarios else "Ready"},
        {"label": "Paper plans", "value": len(paper_trades), "status": f"{len(reviewed_trades)} reviewed"},
        {"label": "Journal links", "value": len(journalized_trades), "status": "Linked" if journalized_trades else "Ready"},
        {"label": "Journal entries", "value": len(entries), "status": f"{weekly.get('wins', 0)}W / {weekly.get('losses', 0)}L"},
        {"label": "Screenshots", "value": len(screenshots), "status": "Saved" if screenshots else "Ready"},
        {"label": "Lessons", "value": f"{completed_lessons}/{len(modules)}", "status": "Learning"},
    ]
    return {
        "ok": True,
        "mode": "demo-local",
        "readiness_score": min(score, 100),
        "milestones": milestones,
        "next_actions": actions[:5],
        "weekly_review": weekly,
        "latest": {
            "prep": prep[0] if prep else None,
            "risk": risk_scenarios[0] if risk_scenarios else None,
            "paper_trade": paper_trades[0] if paper_trades else None,
            "journal_entry": entries[0] if entries else None,
            "screenshot": screenshots[0] if screenshots else None,
            "next_lesson": next_lesson,
        },
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _onboarding_checklist_payload() -> dict[str, Any]:
    preferences = get_preferences()
    watchlists = list_watchlists()
    symbol_count = _watchlist_symbol_count(watchlists)
    session_plans = list_session_plans()
    risk_scenarios = list_risk_scenarios()
    paper_trades = list_paper_trades()
    journal_entries = list_journal_entries()
    school_progress = get_school_progress()
    profile_ready = bool(preferences.get("learning_goal") and preferences.get("default_symbols"))
    items = [
        {
            "key": "profile",
            "title": "Save your learning profile",
            "body": "Experience level, markets, platforms, symbols, and goal are saved.",
            "ready": profile_ready,
            "href": "/onboarding",
        },
        {
            "key": "watchlist",
            "title": "Confirm your watchlist",
            "body": f"{symbol_count} symbol(s) are saved for research.",
            "ready": symbol_count > 0,
            "href": "/watchlists",
        },
        {
            "key": "session_prep",
            "title": "Write session prep",
            "body": "Create the plan before looking for paper trades.",
            "ready": bool(session_plans),
            "href": "/session-prep",
        },
        {
            "key": "risk_lab",
            "title": "Run a risk scenario",
            "body": "Check risk before saving a paper plan.",
            "ready": bool(risk_scenarios),
            "href": "/risk-lab",
        },
        {
            "key": "paper_plan",
            "title": "Save a paper plan",
            "body": "Practice planning without broker execution.",
            "ready": bool(paper_trades),
            "href": "/paper-trade",
        },
        {
            "key": "journal",
            "title": "Add a journal entry",
            "body": "Capture lessons and mistakes for review.",
            "ready": bool(journal_entries),
            "href": "/journal",
        },
        {
            "key": "learning",
            "title": "Finish a school lesson",
            "body": f"{len(school_progress)} lesson progress item(s) saved.",
            "ready": bool(school_progress),
            "href": "/school",
        },
    ]
    completed = sum(1 for item in items if item["ready"])
    next_item = next((item for item in items if not item["ready"]), items[-1])
    return {
        "ok": True,
        "mode": "demo-local",
        "completed": completed,
        "total": len(items),
        "score": round(completed / max(1, len(items)) * 100),
        "items": [
            dict(item, status="Done" if item["ready"] else "Next" if item is next_item else "Open")
            for item in items
        ],
        "next_item": next_item,
        "message": "Use this checklist to turn the demo into a guided first session.",
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _demo_export_payload() -> dict[str, Any]:
    state = load_state()
    counts = {
        "watchlists": len(state.get("watchlists") or []),
        "journal_entries": len(state.get("journal_entries") or []),
        "paper_trades": len(state.get("paper_trades") or []),
        "session_plans": len(state.get("session_plans") or []),
        "risk_scenarios": len(state.get("risk_scenarios") or []),
        "alerts": len(state.get("alerts") or []),
        "screenshot_reviews": len(state.get("screenshot_reviews") or []),
        "strategies": len(state.get("strategies") or []),
        "school_progress_items": len(state.get("school_progress") or {}),
        "usage_events": len(state.get("usage_events") or []),
        "data_requests": len(state.get("data_requests") or []),
        "support_tickets": len(state.get("support_tickets") or []),
    }
    return {
        "ok": True,
        "mode": "demo-local",
        "app": settings.app_name,
        "exported_at": now_iso(),
        "counts": counts,
        "state": state,
        "note": "Demo backup only. It does not include API keys, Stripe secrets, broker credentials, or live brokerage data.",
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _account_export_payload(email: str | None = None, user_id: str | None = None, authorization: str | None = None) -> dict[str, Any]:
    token = _bearer_token(authorization)
    export = _demo_export_payload()
    mode = "demo-local"
    if token and settings.supabase_url and settings.supabase_publishable_key:
        mode = "account-authenticated"
    normalized_email = str(email or "").strip().lower()
    normalized_user_id = str(user_id or "").strip()
    def owned(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered = []
        for item in items:
            item_email = str(item.get("email") or "").strip().lower()
            item_user_id = str(item.get("user_id") or "").strip()
            if normalized_user_id and item_user_id and normalized_user_id == item_user_id:
                filtered.append(item)
            elif normalized_email and item_email and normalized_email == item_email:
                filtered.append(item)
        return filtered

    full_state = export["state"]
    data_requests = owned(list_data_requests())
    support_tickets = owned(list_support_tickets())
    account_state = {
        "watchlists": full_state.get("watchlists") or [],
        "journal_entries": full_state.get("journal_entries") or [],
        "risk_rules": full_state.get("risk_rules") or {},
        "dashboard_layout": full_state.get("dashboard_layout") or {},
        "strategies": full_state.get("strategies") or [],
        "alerts": full_state.get("alerts") or [],
        "session_plans": full_state.get("session_plans") or [],
        "risk_scenarios": full_state.get("risk_scenarios") or [],
        "paper_trades": full_state.get("paper_trades") or [],
        "screenshot_reviews": full_state.get("screenshot_reviews") or [],
        "preferences": full_state.get("preferences") or {},
        "school_progress": full_state.get("school_progress") or {},
        "usage_events": full_state.get("usage_events") or [],
        "activity": full_state.get("activity") or {},
        "data_requests": data_requests,
        "support_tickets": support_tickets,
    }
    counts = {
        "watchlists": len(account_state["watchlists"]),
        "journal_entries": len(account_state["journal_entries"]),
        "paper_trades": len(account_state["paper_trades"]),
        "session_plans": len(account_state["session_plans"]),
        "risk_scenarios": len(account_state["risk_scenarios"]),
        "alerts": len(account_state["alerts"]),
        "screenshot_reviews": len(account_state["screenshot_reviews"]),
        "strategies": len(account_state["strategies"]),
        "school_progress_items": len(account_state["school_progress"]),
        "usage_events": len(account_state["usage_events"]),
        "data_requests": len(data_requests),
        "support_tickets": len(support_tickets),
    }
    return {
        "ok": True,
        "mode": mode,
        "app": settings.app_name,
        "exported_at": now_iso(),
        "account": {
            "email": email or "",
            "user_id": user_id or "",
            "support_email": settings.support_email or "Add APP_SUPPORT_EMAIL before public launch",
        },
        "counts": counts,
        "state": account_state,
        "data_requests": data_requests,
        "support_tickets": support_tickets,
        "secrets_included": False,
        "note": "Account export includes TradePulse demo/local account data currently available to this app and only matching support/data request records for the supplied account. It does not include API keys, Stripe secrets, payment card numbers, broker credentials, or live brokerage data.",
        "next_steps": [
            "Use this file for demo backup or support review.",
            "For a real hosted account, request deletion or correction from the Account page so support has a review record.",
        ],
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _risk_lab_calculation(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    rules = get_risk_rules()
    account_size = _number(payload.get("account_size")) or 5000
    risk_percent = _number(payload.get("risk_percent"))
    rule_max_risk = _number(rules.get("max_risk_per_trade")) or 75
    max_risk_dollars = _number(payload.get("max_risk_dollars")) or (account_size * risk_percent / 100 if risk_percent else rule_max_risk)
    entry = _number(payload.get("entry"))
    stop = _number(payload.get("stop"))
    target = _number(payload.get("target"))
    planned_size = abs(_number(payload.get("planned_size") or payload.get("quantity")))
    per_unit_risk = abs(entry - stop) if entry and stop else 0
    target_reward = abs(target - entry) if entry and target else 0
    suggested_size = int(max_risk_dollars / per_unit_risk) if per_unit_risk > 0 and max_risk_dollars > 0 else 0
    planned_risk = round(planned_size * per_unit_risk, 2) if planned_size and per_unit_risk else 0
    reward_to_risk = round(target_reward / per_unit_risk, 2) if per_unit_risk and target_reward else 0
    effective_risk_percent = round(max_risk_dollars / account_size * 100, 2) if account_size else 0
    flags = []
    if not entry or not stop:
        flags.append("Entry and stop are required before risk can be reviewed.")
    if rules.get("require_stop_loss", True) and not stop:
        flags.append("Saved risk rules require a stop before planning.")
    if planned_size and suggested_size and planned_size > suggested_size:
        flags.append("Planned size is above the demo risk limit.")
    if planned_risk and planned_risk > max_risk_dollars:
        flags.append("Planned dollar risk is above the current limit.")
    if reward_to_risk and reward_to_risk < 1:
        flags.append("Target reward is smaller than planned risk; review whether the practice setup is worth saving.")
    if not flags:
        flags.append("Scenario is inside the current demo risk inputs.")
    return {
        "symbol": str(payload.get("symbol") or "SPY").upper(),
        "asset_type": payload.get("asset_type") or "Stock",
        "account_size": round(account_size, 2),
        "risk_percent": effective_risk_percent,
        "max_risk_dollars": round(max_risk_dollars, 2),
        "entry": entry,
        "stop": stop,
        "target": target,
        "planned_size": planned_size,
        "per_unit_risk": round(per_unit_risk, 4),
        "target_reward_per_unit": round(target_reward, 4),
        "suggested_max_size": suggested_size,
        "planned_risk": planned_risk,
        "reward_to_risk": reward_to_risk,
        "within_rules": not any("above" in flag or "required" in flag for flag in flags),
        "flags": flags,
        "rules_snapshot": rules,
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _risk_lab_payload(calculation: dict[str, Any] | None = None, mode: str = "demo-local") -> dict[str, Any]:
    return {
        "ok": True,
        "mode": mode,
        "rules": get_risk_rules(),
        "calculation": calculation or _risk_lab_calculation({"symbol": "SPY", "entry": 550, "stop": 547.5, "target": 555, "planned_size": 10}),
        "items": list_risk_scenarios(),
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _paper_review_payload(trade: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    entry = _number(trade.get("entry") or payload.get("entry"))
    exit_price = _number(payload.get("exit_price") or payload.get("exit"))
    size = _number(trade.get("position_size") or payload.get("position_size"))
    direction = str(trade.get("direction") or payload.get("direction") or "Long").lower()
    pnl = payload.get("pnl")
    if pnl in {"", None} and entry and exit_price and size:
        pnl_value = (entry - exit_price) * size if direction == "short" else (exit_price - entry) * size
        pnl = round(pnl_value, 2)
    pnl_number = _number(pnl)
    result = payload.get("result") or ("Win" if pnl_number > 0 else "Loss" if pnl_number < 0 else "Breakeven")
    review_notes = payload.get("review_notes") or payload.get("notes") or ""
    lesson = payload.get("lesson_learned") or payload.get("lesson") or "Review whether the plan matched the written setup and risk rules."
    mistake_tags = payload.get("mistake_tags") or payload.get("mistakes") or ""
    status = payload.get("status") or "reviewed"
    review = {
        "status": status,
        "exit_price": exit_price or payload.get("exit_price"),
        "pnl": pnl,
        "result": result,
        "review_notes": review_notes,
        "lesson_learned": lesson,
        "mistake_tags": mistake_tags,
        "reviewed_at": payload.get("reviewed_at"),
    }
    journal_prefill = {
        "symbol": trade.get("symbol"),
        "asset_type": trade.get("asset_type"),
        "direction": trade.get("direction"),
        "entry_price": trade.get("entry"),
        "exit_price": review["exit_price"],
        "stop_loss": trade.get("stop"),
        "target_price": trade.get("target"),
        "position_size": trade.get("position_size"),
        "result": result,
        "pnl": pnl,
        "setup_type": trade.get("strategy") or "Paper practice",
        "entry_reason": trade.get("reason"),
        "exit_reason": review_notes,
        "mistakes": mistake_tags,
        "lesson_learned": lesson,
        "ai_summary": "Paper practice reviewed in TradePulse demo mode.",
    }
    return {
        "review": review,
        "journal_prefill": journal_prefill,
        "summary": f"{trade.get('symbol', 'Paper plan')} marked {result}. Review saved for journaling and pattern tracking.",
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def _journal_entry_from_paper_trade(trade: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
    review_notes = trade.get("review_notes") or "Paper practice reviewed from the saved plan."
    lesson = trade.get("lesson_learned") or "Compare the practice result with the original plan before repeating the setup."
    ai_summary = (
        f"Paper practice for {trade.get('symbol', 'the setup')} was journaled from the reviewed demo plan. "
        "Use this as review evidence only; it is not a trade recommendation."
    )
    entry = {
        "symbol": str(trade.get("symbol") or "PAPER").upper(),
        "asset_type": trade.get("asset_type"),
        "direction": trade.get("direction"),
        "entry_price": trade.get("entry"),
        "exit_price": trade.get("exit_price"),
        "stop_loss": trade.get("stop"),
        "target_price": trade.get("target"),
        "position_size": trade.get("position_size"),
        "result": trade.get("result") or "Breakeven",
        "pnl": trade.get("pnl") or 0,
        "setup_type": trade.get("strategy") or "Paper practice",
        "entry_reason": trade.get("reason"),
        "exit_reason": review_notes,
        "mistakes": trade.get("mistake_tags") or "",
        "lesson_learned": lesson,
        "ai_summary": ai_summary,
        "source_type": "paper_trade",
        "source_id": trade.get("id"),
    }
    if user_id:
        entry["user_id"] = user_id
    return entry


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request) -> HTMLResponse:
    return _page("landing.html")


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt(request: Request) -> PlainTextResponse:
    base = _base_url(request)
    return PlainTextResponse(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")


@app.get("/favicon.ico")
async def favicon() -> RedirectResponse:
    return RedirectResponse("/static/favicon.svg", status_code=307)


@app.get("/sitemap.xml")
async def sitemap_xml(request: Request) -> Response:
    base = _base_url(request)
    urls = "\n".join(f"  <url><loc>{base}{path}</loc></url>" for path in PUBLIC_SITEMAP_PATHS)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n'
    return Response(content=xml, media_type="application/xml")


@app.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request) -> HTMLResponse:
    return _page("pricing.html")


@app.get("/support", response_class=HTMLResponse)
async def support(request: Request) -> HTMLResponse:
    return _page("support.html")


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request) -> HTMLResponse:
    return _render_template(
        "auth.html",
        auth_mode="login",
        auth_title="Log in to TradePulse",
        auth_button="Log in",
        auth_switch_text="Need an account?",
        auth_switch_href="/signup",
        auth_switch_label="Create one",
    )


@app.get("/signup", response_class=HTMLResponse)
async def signup(request: Request) -> HTMLResponse:
    return _render_template(
        "auth.html",
        auth_mode="signup",
        auth_title="Create your TradePulse account",
        auth_button="Create account",
        auth_switch_text="Already have an account?",
        auth_switch_href="/login",
        auth_switch_label="Log in",
    )


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password(request: Request) -> HTMLResponse:
    return _page("forgot_password.html")


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password(request: Request) -> HTMLResponse:
    return _page("reset_password.html")


@app.get("/auth/confirmed", response_class=HTMLResponse)
async def auth_confirmed(request: Request) -> HTMLResponse:
    return _page("auth_confirmed.html")


@app.get("/account", response_class=HTMLResponse)
async def account(request: Request) -> HTMLResponse:
    return _page("account.html")


@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding(request: Request) -> HTMLResponse:
    return _page("onboarding.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return _page("dashboard.html")


@app.get("/watchlists", response_class=HTMLResponse)
async def watchlists_page(request: Request) -> HTMLResponse:
    return _page("watchlists.html")


@app.get("/news", response_class=HTMLResponse)
async def news_page(request: Request) -> HTMLResponse:
    return _page("news.html")


@app.get("/scanner", response_class=HTMLResponse)
async def scanner_page(request: Request) -> HTMLResponse:
    return _page("scanner.html")


@app.get("/live-charts", response_class=HTMLResponse)
async def live_charts(request: Request) -> HTMLResponse:
    return _page("live_charts.html")


@app.get("/copilot", response_class=HTMLResponse)
async def copilot(request: Request) -> HTMLResponse:
    return _page("copilot.html")


@app.get("/screenshot-analyzer", response_class=HTMLResponse)
async def screenshot_analyzer(request: Request) -> HTMLResponse:
    return _page("screenshot_analyzer.html")


@app.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request) -> HTMLResponse:
    return _page("alerts.html")


@app.get("/session-prep", response_class=HTMLResponse)
async def session_prep(request: Request) -> HTMLResponse:
    return _page("session_prep.html")


@app.get("/review-center", response_class=HTMLResponse)
async def review_center(request: Request) -> HTMLResponse:
    return _page("review_center.html")


@app.get("/progress", response_class=HTMLResponse)
async def progress(request: Request) -> HTMLResponse:
    return _page("progress.html")


@app.get("/risk-lab", response_class=HTMLResponse)
async def risk_lab(request: Request) -> HTMLResponse:
    return _page("risk_lab.html")


@app.get("/paper-trade", response_class=HTMLResponse)
async def paper_trade(request: Request) -> HTMLResponse:
    return _page("paper_trade.html")


@app.get("/journal", response_class=HTMLResponse)
async def journal(request: Request) -> HTMLResponse:
    return _page("journal.html")


@app.get("/journal/replay", response_class=HTMLResponse)
async def journal_replay(request: Request) -> HTMLResponse:
    return _page("journal.html", replay_mode="true")


@app.get("/school", response_class=HTMLResponse)
async def school(request: Request) -> HTMLResponse:
    return _page("school.html")


@app.get("/strategy-builder", response_class=HTMLResponse)
async def strategy_builder(request: Request) -> HTMLResponse:
    return _page("strategy_builder.html")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    return _page("settings.html")


@app.get("/launch-center", response_class=HTMLResponse)
async def launch_center_page(request: Request) -> HTMLResponse:
    return _page("launch_center.html")


@app.get("/business-plan", response_class=HTMLResponse)
async def business_plan_page(request: Request) -> HTMLResponse:
    return _page("business_plan.html")


@app.get("/production-setup", response_class=HTMLResponse)
async def production_setup_page(request: Request) -> HTMLResponse:
    return _page("production_setup.html")


@app.get("/risk-disclosure", response_class=HTMLResponse)
async def risk_disclosure(request: Request) -> HTMLResponse:
    return _page("risk_disclosure.html")


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request) -> HTMLResponse:
    return _page("privacy.html")


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request) -> HTMLResponse:
    return _page("terms.html")


async def _start_checkout(request: Request, plan: str, user_id: str | None = None):
    normalized = plan.lower().strip()
    if normalized not in PAID_PLANS:
        normalized = "pro"
    price_by_plan = {
        "pro": settings.stripe_price_id_pro,
        "elite": settings.stripe_price_id_elite,
        "all_access": settings.stripe_price_id_all_access,
    }
    missing_by_plan = {
        "pro": "STRIPE_PRICE_ID_PRO",
        "elite": "STRIPE_PRICE_ID_ELITE",
        "all_access": "STRIPE_PRICE_ID_ALL_ACCESS",
    }
    price_id = price_by_plan.get(normalized)
    if not settings.stripe_secret_key or not price_id:
        missing_price = missing_by_plan.get(normalized, "STRIPE_PRICE_ID_PRO")
        return _render_template(
            "checkout_error.html",
            status_code=500,
            error_title="Stripe is not fully configured yet",
            error_message=f"Add STRIPE_SECRET_KEY and {missing_price} in Render environment variables, then redeploy.",
        )

    try:
        import stripe

        stripe.api_key = settings.stripe_secret_key
        base = _base_url(request)
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{base}/billing/success?plan={normalized}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base}/pricing",
            allow_promotion_codes=True,
            client_reference_id=user_id or None,
            metadata={"tradepulse_plan": normalized, "supabase_user_id": user_id or ""},
        )
        return RedirectResponse(str(session.url), status_code=303)
    except Exception as exc:
        return _render_template(
            "checkout_error.html",
            status_code=500,
            error_title="Checkout could not start",
            error_message=str(exc),
        )


@app.get("/billing/checkout")
async def billing_checkout_get(
    request: Request,
    plan: str = Query(default="pro"),
    user_id: str | None = Query(default=None),
):
    return await _start_checkout(request, plan, user_id=user_id)


@app.post("/billing/checkout")
async def billing_checkout_post(
    request: Request,
    plan: str = Query(default="pro"),
    user_id: str | None = Query(default=None),
):
    return await _start_checkout(request, plan, user_id=user_id)


@app.post("/billing/portal")
async def billing_portal(
    request: Request,
    user_id: str | None = Query(default=None),
):
    if not settings.stripe_secret_key:
        return RedirectResponse("/account?billing=portal_demo", status_code=303)
    if not user_id or not store.configured:
        return RedirectResponse("/account?billing=portal_needs_account", status_code=303)

    try:
        subscription = store.user_plan(user_id)
    except Exception:
        subscription = None
    customer_id = subscription.get("stripe_customer_id") if subscription else None
    if not customer_id:
        return RedirectResponse("/account?billing=portal_needs_subscription", status_code=303)

    try:
        import stripe

        stripe.api_key = settings.stripe_secret_key
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{_base_url(request)}/account",
        )
        return RedirectResponse(str(session.url), status_code=303)
    except Exception:
        return RedirectResponse("/account?billing=portal_error", status_code=303)


@app.get("/billing/success", response_class=HTMLResponse)
async def billing_success(request: Request, plan: str = Query(default="pro")) -> HTMLResponse:
    label = PLAN_LABELS.get(plan.lower(), "Pro")
    return _render_template("billing_success.html", purchased_plan=label)


@app.get("/billing/cancel", response_class=HTMLResponse)
async def billing_cancel(request: Request) -> HTMLResponse:
    return RedirectResponse("/pricing", status_code=303)


@app.post("/billing/webhook")
async def billing_webhook(request: Request, stripe_signature: str | None = Header(default=None)) -> dict[str, Any]:
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        return {"ok": True, "mode": "webhook-placeholder", "message": "Stripe webhook secret is not configured yet."}

    try:
        import stripe

        payload = await request.body()
        event = stripe.Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    event_payload = event.to_dict_recursive() if hasattr(event, "to_dict_recursive") else dict(event)
    event_type = event_payload.get("type", "")
    obj = event_payload.get("data", {}).get("object", {})
    if store.configured:
        try:
            store.insert(
                "stripe_webhook_events",
                {"stripe_event_id": event_payload.get("id"), "event_type": event_type, "payload": event_payload},
            )
        except Exception:
            pass
    if event_type == "checkout.session.completed":
        user_id = obj.get("client_reference_id") or obj.get("metadata", {}).get("supabase_user_id")
        plan = obj.get("metadata", {}).get("tradepulse_plan", "pro")
        if user_id and store.configured:
            store.upsert_subscription(
                user_id=user_id,
                plan=plan if plan in PAID_PLANS else "pro",
                status="active",
                stripe_customer_id=obj.get("customer"),
                stripe_subscription_id=obj.get("subscription"),
            )
    return {"ok": True, "received": event_type}


@app.get("/api/access")
async def api_access(
    email: str | None = Query(default=None),
    plan: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    email = email if isinstance(email, str) else None
    plan = plan if isinstance(plan, str) else None
    user_id = user_id if isinstance(user_id, str) else None
    normalized_email = (email or "").strip().lower()
    visible_plan = (plan or "free").strip().lower()
    is_owner = bool(normalized_email and normalized_email in settings.owner_emails)
    token = _bearer_token(authorization)
    subscription: dict[str, Any] | None = None
    if not is_owner:
        try:
            if token and settings.supabase_publishable_key and settings.supabase_url:
                subscription = store.user_plan_with_token(token)
            elif user_id and store.configured:
                subscription = store.user_plan(user_id)
            if subscription and subscription.get("status") in {"active", "trialing"}:
                visible_plan = str(subscription.get("plan") or visible_plan).lower()
        except Exception:
            subscription = None
    if is_owner:
        visible_plan = "all_access"
    if visible_plan not in {"free", *PAID_PLANS}:
        visible_plan = "free"
    return {
        "ok": True,
        "plan": visible_plan,
        "plan_label": PLAN_LABELS.get(visible_plan, "Free"),
        "plan_price": PLAN_PRICES.get(visible_plan, "$0/mo"),
        "is_owner": is_owner,
        "subscription": subscription,
        "features": _plan_features(visible_plan),
        "limits": _plan_limits(visible_plan),
    }


@app.get("/api/plans")
async def api_plans() -> dict[str, Any]:
    return {"ok": True, "plans": _plan_catalog(), "disclaimer": REQUIRED_DISCLAIMER}


@app.get("/api/plan-limits")
async def api_plan_limits() -> dict[str, Any]:
    return {"ok": True, "limits": {plan: _plan_limits(plan) for plan in PLAN_LABELS}, "disclaimer": REQUIRED_DISCLAIMER}


@app.get("/api/usage")
async def api_usage(
    email: str | None = Query(default=None),
    plan: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    email = email if isinstance(email, str) else None
    plan = plan if isinstance(plan, str) else None
    user_id = user_id if isinstance(user_id, str) else None
    normalized_email = (email or "").strip().lower()
    visible_plan = (plan or "free").strip().lower()
    is_owner = bool(normalized_email and normalized_email in settings.owner_emails)
    token = _bearer_token(authorization)
    if not is_owner:
        try:
            subscription = None
            if token and settings.supabase_publishable_key and settings.supabase_url:
                subscription = store.user_plan_with_token(token)
            elif user_id and store.configured:
                subscription = store.user_plan(user_id)
            if subscription and subscription.get("status") in {"active", "trialing"}:
                visible_plan = str(subscription.get("plan") or visible_plan).lower()
        except Exception:
            pass
    if is_owner:
        visible_plan = "all_access"
    if visible_plan not in {"free", *PAID_PLANS}:
        visible_plan = "free"

    mode = "demo-local"
    counts = _demo_usage_counts()
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            counts = _supabase_usage_counts(token)
            mode = "supabase"
        except Exception:
            mode = "demo-fallback"
    return _usage_payload(visible_plan, counts, mode=mode)


@app.get("/api/limit-check")
async def api_limit_check(
    action: str = Query(default="scanner_run"),
    plan: str | None = Query(default=None),
    increment: int = Query(default=1),
) -> dict[str, Any]:
    action = action if isinstance(action, str) else "scanner_run"
    plan = plan if isinstance(plan, str) else "free"
    increment = increment if isinstance(increment, int) else 1
    check = _limit_check(action, plan, increment=increment)
    return {"ok": True, "check": check, "disclaimer": REQUIRED_DISCLAIMER}


@app.get("/api/launch-checklist")
async def api_launch_checklist() -> dict[str, Any]:
    return _launch_checklist_payload()


@app.get("/api/business-plan")
async def api_business_plan() -> dict[str, Any]:
    return _business_plan_payload()


@app.get("/api/production-readiness")
async def api_production_readiness(request: Request) -> dict[str, Any]:
    return _production_setup_payload(request)


@app.get("/api/system/status")
async def api_system_status() -> dict[str, Any]:
    return {
        "ok": True,
        "app_name": settings.app_name,
        "mode": DEMO_MODE_LABEL,
        "configuration": {
            "supabase_public_auth": bool(settings.supabase_url and settings.supabase_publishable_key),
            "supabase_server_persistence": store.configured,
            "stripe_checkout": bool(settings.stripe_secret_key and settings.stripe_price_id_pro),
            "stripe_elite_price": bool(settings.stripe_price_id_elite),
            "stripe_all_access_price": bool(settings.stripe_price_id_all_access),
            "stripe_webhook": bool(settings.stripe_secret_key and settings.stripe_webhook_secret),
            "stripe_customer_portal": bool(settings.stripe_secret_key and store.configured),
            "openai": bool(settings.openai_api_key),
            "openai_model": settings.openai_model,
            "owner_bypass": bool(settings.owner_emails),
            "support_contact": bool(settings.support_email),
            "support_email": settings.support_email or "",
            "security_headers": True,
            "security_header_names": ", ".join(SECURITY_HEADERS.keys()),
            "market_data": bool(settings.finnhub_api_key or settings.alpha_vantage_api_key),
            "real_market_data_enabled": settings.enable_real_market_data,
            "yfinance_research_feed": True,
            "news_data": bool(settings.newsapi_key),
            "broker_orders_disabled": not settings.enable_broker_orders,
        },
        "safe_defaults": [
            "Demo/delayed data is labeled when live market data is unavailable.",
            "AI answers fall back to mock research commentary when OPENAI_API_KEY is missing.",
            "Broker order execution is disabled unless explicitly enabled later.",
            "Protected pages redirect through Supabase auth when Supabase keys are configured.",
        ],
        "disclaimer": REQUIRED_DISCLAIMER,
    }


@app.get("/api/providers/status")
async def api_providers_status() -> dict[str, Any]:
    return {
        "ok": True,
        "ai": {
            "openai_configured": bool(settings.openai_api_key),
            "openai_model": settings.openai_model,
            "fallback": "Safe mock research response",
        },
        "market_data": {
            "real_market_data_enabled": settings.enable_real_market_data,
            "research_feed": "yfinance",
            "default_mode": "demo" if not settings.enable_real_market_data else "real-market-research with demo fallback",
        },
        "news": {
            "yahoo_rss": True,
            "finnhub": bool(settings.finnhub_api_key),
            "alpha_vantage": bool(settings.alpha_vantage_api_key),
            "newsapi": bool(settings.newsapi_key),
        },
        "broker": {
            "orders_enabled": settings.enable_broker_orders,
            "safety": "Broker order execution remains disabled unless ENABLE_BROKER_ORDERS=true.",
        },
        "disclaimer": REQUIRED_DISCLAIMER,
    }


@app.get("/api/demo/dashboard")
async def api_demo_dashboard() -> dict[str, Any]:
    return _dashboard_with_local_state()


@app.get("/api/export/demo-state")
async def api_export_demo_state() -> dict[str, Any]:
    return _demo_export_payload()


@app.get("/api/export/account-data")
async def api_export_account_data(
    email: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    return _account_export_payload(email=email, user_id=user_id, authorization=authorization)


@app.post("/api/account/data-request")
async def api_account_data_request(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    request_type = str(payload.get("request_type") or "export").strip().lower()
    if request_type not in {"export", "delete", "correction"}:
        request_type = "export"
    record = {
        "request_type": request_type,
        "email": str(payload.get("email") or "").strip(),
        "user_id": str(payload.get("user_id") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
    }
    mode = "demo-local"
    warning = None
    token = _bearer_token(authorization)
    if store.configured and record["user_id"]:
        try:
            saved = store.insert(
                "account_data_requests",
                record,
                auth_token=token if token and settings.supabase_url and settings.supabase_publishable_key else None,
            )
            mode = "supabase"
        except Exception as exc:
            saved = add_data_request(record)
            warning = str(exc)
            mode = "demo-fallback"
    else:
        saved = add_data_request(record)
    return {
        "ok": True,
        "mode": mode,
        "request": saved,
        "message": "Request received. Deletion or correction is not automatic; support/admin review is required before any account data is removed or changed.",
        "support_email": settings.support_email or "Add APP_SUPPORT_EMAIL before public launch",
        "warning": warning,
        "disclaimer": REQUIRED_DISCLAIMER,
    }


@app.post("/api/support/ticket")
async def api_support_ticket(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    payload = payload or {}
    email = str(payload.get("email") or "").strip()
    subject = str(payload.get("subject") or "").strip()
    message = str(payload.get("message") or "").strip()
    category = str(payload.get("category") or "general").strip().lower()
    if category not in {"account", "billing", "privacy", "technical", "general"}:
        category = "general"
    if not subject:
        subject = f"{category.title()} support request"
    if not message:
        return {
            "ok": False,
            "mode": "demo-local",
            "message": "Add a short message so support knows what to review.",
            "support_email": settings.support_email or "Add APP_SUPPORT_EMAIL before public launch",
        }
    record = {
        "user_id": str(payload.get("user_id") or "").strip() or None,
        "email": email,
        "subject": subject,
        "message": message,
        "category": category,
    }
    mode = "demo-local"
    warning = None
    if store.configured:
        try:
            saved = store.insert("support_tickets", record)
            mode = "supabase"
        except Exception as exc:
            saved = add_support_ticket(record)
            warning = str(exc)
            mode = "demo-fallback"
    else:
        saved = add_support_ticket(record)
    return {
        "ok": True,
        "mode": mode,
        "ticket": saved,
        "message": "Support request received. Demo mode stores it locally; production can keep it in Supabase and connect email/helpdesk notifications.",
        "support_email": settings.support_email or "Add APP_SUPPORT_EMAIL before public launch",
        "warning": warning,
        "disclaimer": REQUIRED_DISCLAIMER,
    }


@app.get("/api/memory")
async def api_memory() -> dict[str, Any]:
    return _memory_summary()


@app.get("/api/preferences")
async def api_preferences(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            rows = store.select("user_preferences", "select=*&limit=1", auth_token=token)
            if rows:
                return {"ok": True, "mode": "supabase", "preferences": rows[0], "disclaimer": REQUIRED_DISCLAIMER}
        except Exception as exc:
            return {"ok": True, "mode": "demo-fallback", "preferences": get_preferences(), "warning": str(exc), "disclaimer": REQUIRED_DISCLAIMER}
    return {"ok": True, "mode": "demo-local", "preferences": get_preferences(), "disclaimer": REQUIRED_DISCLAIMER}


@app.get("/api/onboarding-checklist")
async def api_onboarding_checklist() -> dict[str, Any]:
    return _onboarding_checklist_payload()


@app.post("/api/preferences")
async def api_preferences_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            allowed = {"user_id", "experience_level", "markets", "platforms", "risk_style", "default_symbols", "learning_goal"}
            saved = store.upsert("user_preferences", _only(payload, allowed), on_conflict="user_id", auth_token=token)
            return {"ok": True, "mode": "supabase", "preferences": saved, "message": "Preferences saved.", "disclaimer": REQUIRED_DISCLAIMER}
        except Exception as exc:
            saved = save_preferences(payload)
            return {"ok": True, "mode": "demo-fallback", "preferences": saved, "warning": str(exc), "disclaimer": REQUIRED_DISCLAIMER}
    return {"ok": True, "mode": "demo-local", "preferences": save_preferences(payload), "message": "Preferences saved in local demo persistence.", "disclaimer": REQUIRED_DISCLAIMER}


@app.get("/api/chart-data")
async def api_chart_data(symbol: str = "SPY", timeframe: str = "5m", live: bool = Query(default=False)) -> dict[str, Any]:
    return chart_data(symbol=symbol, timeframe=timeframe, live=live)


@app.get("/api/alerts")
async def api_alerts(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            rows = store.select("alert_rules", "select=*&order=created_at.desc", auth_token=token)
            evaluated = [_evaluate_alert(row) for row in rows if row.get("enabled", True)]
            return {"ok": True, "mode": "supabase", "items": rows, "evaluated": evaluated, "triggered": [item for item in evaluated if item.get("triggered")], "disclaimer": REQUIRED_DISCLAIMER}
        except Exception as exc:
            fallback = _alert_payload()
            fallback["mode"] = "demo-fallback"
            fallback["warning"] = str(exc)
            return fallback
    return _alert_payload()


@app.post("/api/alerts")
async def api_alerts_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    alert = {
        "user_id": payload.get("user_id"),
        "symbol": str(payload.get("symbol") or "SPY").upper(),
        "alert_type": payload.get("alert_type") or "price",
        "operator": payload.get("operator") or "above",
        "target_value": payload.get("target_value") or "",
        "notes": payload.get("notes") or "",
        "enabled": payload.get("enabled", True),
    }
    limit_check = _limit_check("alert", _payload_plan(payload))
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            allowed = {"user_id", "symbol", "alert_type", "operator", "target_value", "notes", "enabled"}
            saved = store.insert("alert_rules", _only(alert, allowed), auth_token=token)
            return {"ok": True, "mode": "supabase", "item": saved, "evaluated": _evaluate_alert(saved), "limit_check": limit_check, "message": "Alert saved.", "disclaimer": REQUIRED_DISCLAIMER}
        except Exception as exc:
            saved = add_alert(alert)
            return {"ok": True, "mode": "demo-fallback", "item": saved, "evaluated": _evaluate_alert(saved), "limit_check": limit_check, "warning": str(exc), "disclaimer": REQUIRED_DISCLAIMER}
    saved = add_alert(alert)
    return {"ok": True, "mode": "demo-local", "item": saved, "evaluated": _evaluate_alert(saved), "limit_check": limit_check, "message": "Alert saved in local demo persistence.", "disclaimer": REQUIRED_DISCLAIMER}


@app.post("/api/alerts/evaluate")
async def api_alerts_evaluate(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return await api_alerts(authorization=authorization)


@app.get("/api/session-prep")
async def api_session_prep(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            rows = store.select("session_plans", "select=*&order=created_at.desc&limit=50", auth_token=token)
            return _session_prep_payload(rows, mode="supabase")
        except Exception as exc:
            fallback = _session_prep_payload(mode="demo-fallback")
            fallback["warning"] = str(exc)
            return fallback
    return _session_prep_payload()


@app.post("/api/session-prep")
async def api_session_prep_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    suggested = _session_prep_payload().get("suggested_plan") or {}
    saved_payload = {
        "user_id": payload.get("user_id"),
        "session_label": payload.get("session_label") or "Daily session prep",
        "focus_symbols": payload.get("focus_symbols") or suggested.get("focus_symbols") or "SPY,QQQ,NVDA",
        "market_notes": payload.get("market_notes") or suggested.get("market_notes"),
        "risk_notes": payload.get("risk_notes") or suggested.get("risk_notes"),
        "rules_for_today": payload.get("rules_for_today") or "\n".join(suggested.get("rules_for_today") or []),
        "avoid_conditions": payload.get("avoid_conditions") or "\n".join(suggested.get("avoid_conditions") or []),
        "status": payload.get("status") or "planned",
        "plan": payload.get("plan") if isinstance(payload.get("plan"), dict) else suggested,
    }
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            allowed = {
                "user_id",
                "session_label",
                "focus_symbols",
                "market_notes",
                "risk_notes",
                "rules_for_today",
                "avoid_conditions",
                "status",
                "plan",
            }
            saved = store.insert("session_plans", _only(saved_payload, allowed), auth_token=token)
            return {"ok": True, "mode": "supabase", "item": saved, "message": "Session prep saved.", "disclaimer": REQUIRED_DISCLAIMER}
        except Exception as exc:
            saved = add_session_plan(saved_payload)
            return {"ok": True, "mode": "demo-fallback", "item": saved, "warning": str(exc), "disclaimer": REQUIRED_DISCLAIMER}
    saved = add_session_plan(saved_payload)
    return {"ok": True, "mode": "demo-local", "item": saved, "message": "Session prep saved in local demo persistence.", "disclaimer": REQUIRED_DISCLAIMER}


@app.get("/api/review-center")
async def api_review_center() -> dict[str, Any]:
    return _review_center_payload()


@app.get("/api/progress")
async def api_progress() -> dict[str, Any]:
    return _progress_payload()


@app.get("/api/risk-lab")
async def api_risk_lab() -> dict[str, Any]:
    return _risk_lab_payload()


@app.post("/api/risk-lab")
async def api_risk_lab_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    calculation = _risk_lab_calculation(payload)
    scenario = {
        "user_id": payload.get("user_id"),
        "symbol": calculation["symbol"],
        "asset_type": calculation["asset_type"],
        "account_size": calculation["account_size"],
        "entry": calculation["entry"],
        "stop": calculation["stop"],
        "target": calculation["target"],
        "planned_size": calculation["planned_size"],
        "max_risk_dollars": calculation["max_risk_dollars"],
        "planned_risk": calculation["planned_risk"],
        "reward_to_risk": calculation["reward_to_risk"],
        "within_rules": calculation["within_rules"],
        "notes": payload.get("notes") or "",
        "calculation": calculation,
    }
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            allowed = {
                "user_id",
                "symbol",
                "asset_type",
                "account_size",
                "entry",
                "stop",
                "target",
                "planned_size",
                "max_risk_dollars",
                "planned_risk",
                "reward_to_risk",
                "within_rules",
                "notes",
                "calculation",
            }
            saved = store.insert("risk_scenarios", _only(scenario, allowed), auth_token=token)
            return {"ok": True, "mode": "supabase", "item": saved, "calculation": calculation, "message": "Risk scenario saved.", "disclaimer": REQUIRED_DISCLAIMER}
        except Exception as exc:
            saved = add_risk_scenario(scenario)
            return {"ok": True, "mode": "demo-fallback", "item": saved, "calculation": calculation, "warning": str(exc), "disclaimer": REQUIRED_DISCLAIMER}
    saved = add_risk_scenario(scenario)
    return {"ok": True, "mode": "demo-local", "item": saved, "calculation": calculation, "message": "Risk scenario saved in local demo persistence.", "disclaimer": REQUIRED_DISCLAIMER}


@app.post("/api/copilot")
async def api_copilot(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = dict(payload or {})
    limit_check = _limit_check("copilot_prompt", _payload_plan(payload))
    _record_usage("copilot_prompt", {"source": "copilot"}, payload=payload, authorization=authorization)
    payload["memory"] = _memory_summary().get("copilot_context")
    response = openai_research_response(payload)
    response["limit_check"] = limit_check
    if not limit_check["allowed"]:
        response["warning"] = limit_check["message"]
    return response


@app.get("/api/scanner")
async def api_scanner(symbols: str | None = Query(default=None)) -> dict[str, Any]:
    return build_scanner(symbols)


@app.post("/api/scanner/run")
async def api_scanner_run(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    limit_check = _limit_check("scanner_run", _payload_plan(payload))
    _record_usage("scanner_run", {"symbols": payload.get("symbols")}, payload=payload, authorization=authorization)
    response = build_scanner(payload.get("symbols"))
    response["limit_check"] = limit_check
    if not limit_check["allowed"]:
        response["warning"] = limit_check["message"]
    return response


@app.post("/api/trade-checklist")
async def api_trade_checklist(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    return build_trade_checklist(payload)


@app.get("/api/paper-trades")
async def api_paper_trades(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            return {
                "ok": True,
                "mode": "supabase",
                "items": store.select("paper_trades", "select=*&order=created_at.desc&limit=100", auth_token=token),
                "disclaimer": REQUIRED_DISCLAIMER,
            }
        except Exception as exc:
            return {"ok": True, "mode": "demo-fallback", "items": list_paper_trades(), "warning": str(exc), "disclaimer": REQUIRED_DISCLAIMER}
    return {"ok": True, "mode": "demo-local", "items": list_paper_trades(), "disclaimer": REQUIRED_DISCLAIMER}


@app.post("/api/paper-trades")
async def api_paper_trades_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    checklist = build_trade_checklist(payload)
    limit_check = _limit_check("paper_plan", _payload_plan(payload))
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            allowed = {
                "user_id",
                "symbol",
                "asset_type",
                "direction",
                "entry",
                "stop",
                "target",
                "position_size",
                "invalidation",
                "strategy",
                "reason",
                "news",
                "status",
            }
            saved = store.insert("paper_trades", dict(_only(payload, allowed), checklist=checklist), auth_token=token)
            return {
                "ok": True,
                "mode": "supabase",
                "item": saved,
                "checklist": checklist,
                "limit_check": limit_check,
                "message": "Paper trade plan saved. No broker order was placed.",
                "disclaimer": REQUIRED_DISCLAIMER,
            }
        except Exception as exc:
            saved = add_paper_trade(dict(payload, checklist=checklist, status=payload.get("status") or "planned"))
            return {"ok": True, "mode": "demo-fallback", "item": saved, "checklist": checklist, "limit_check": limit_check, "warning": str(exc), "disclaimer": REQUIRED_DISCLAIMER}
    saved = add_paper_trade(dict(payload, checklist=checklist, status=payload.get("status") or "planned"))
    return {
        "ok": True,
        "mode": "demo-local",
        "item": saved,
        "checklist": checklist,
        "limit_check": limit_check,
        "message": "Paper trade plan saved locally. No broker order was placed.",
        "disclaimer": REQUIRED_DISCLAIMER,
    }


@app.post("/api/paper-trades/review")
async def api_paper_trades_review(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    trade_id = str(payload.get("trade_id") or payload.get("id") or "").strip()
    trades = list_paper_trades()
    trade = next((item for item in trades if str(item.get("id")) == trade_id), trades[0] if trades else {})
    if not trade:
        return {"ok": False, "mode": "demo-local", "message": "Save a paper plan before adding a practice review.", "disclaimer": REQUIRED_DISCLAIMER}
    review_payload = _paper_review_payload(trade, payload)
    review = review_payload["review"]
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id") and trade_id:
        try:
            allowed = {"status", "exit_price", "pnl", "result", "review_notes", "lesson_learned", "mistake_tags", "reviewed_at"}
            rows = store.patch("paper_trades", f"id=eq.{trade_id}", _only(review, allowed), auth_token=token)
            saved = rows[0] if rows else dict(trade, **review)
            return {"ok": True, "mode": "supabase", "item": saved, **review_payload, "message": "Practice review saved.", "disclaimer": REQUIRED_DISCLAIMER}
        except Exception as exc:
            saved = update_paper_trade_review(trade_id, review)
            return {"ok": True, "mode": "demo-fallback", "item": saved, **review_payload, "warning": str(exc), "disclaimer": REQUIRED_DISCLAIMER}
    saved = update_paper_trade_review(trade_id, review)
    return {"ok": True, "mode": "demo-local", "item": saved, **review_payload, "message": "Practice review saved in local demo persistence.", "disclaimer": REQUIRED_DISCLAIMER}


@app.post("/api/paper-trades/journalize")
async def api_paper_trades_journalize(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    trade_id = str(payload.get("trade_id") or payload.get("id") or "").strip()
    limit_check = _limit_check("journal_entry", _payload_plan(payload))
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id") and trade_id:
        try:
            rows = store.select("paper_trades", f"select=*&id=eq.{trade_id}&limit=1", auth_token=token)
            trade = rows[0] if rows else {}
            if not trade:
                return {"ok": False, "mode": "supabase", "message": "Could not find that paper plan.", "disclaimer": REQUIRED_DISCLAIMER}
            if trade.get("status") != "reviewed":
                return {"ok": False, "mode": "supabase", "message": "Review the paper plan before sending it to the journal.", "disclaimer": REQUIRED_DISCLAIMER}
            if trade.get("journal_entry_id"):
                return {"ok": True, "mode": "supabase", "item": trade, "message": "This paper review is already linked to a journal entry.", "disclaimer": REQUIRED_DISCLAIMER}
            journal_entry = _journal_entry_from_paper_trade(trade, str(payload.get("user_id")))
            allowed_journal = {
                "user_id",
                "symbol",
                "asset_type",
                "direction",
                "entry_price",
                "exit_price",
                "stop_loss",
                "target_price",
                "position_size",
                "result",
                "pnl",
                "setup_type",
                "entry_reason",
                "exit_reason",
                "mistakes",
                "lesson_learned",
                "screenshot_url",
                "ai_summary",
                "source_type",
                "source_id",
            }
            saved_entry = store.insert("trade_journal", _only(journal_entry, allowed_journal), auth_token=token)
            rows = store.patch(
                "paper_trades",
                f"id=eq.{trade_id}",
                {"journal_entry_id": saved_entry.get("id"), "journalized_at": now_iso()},
                auth_token=token,
            )
            saved_trade = rows[0] if rows else dict(trade, journal_entry_id=saved_entry.get("id"))
            return {
                "ok": True,
                "mode": "supabase",
                "item": saved_trade,
                "journal_entry": saved_entry,
                "limit_check": limit_check,
                "message": "Paper review sent to the journal.",
                "disclaimer": REQUIRED_DISCLAIMER,
            }
        except Exception as exc:
            payload["warning"] = str(exc)
    trades = list_paper_trades()
    trade = next((item for item in trades if str(item.get("id")) == trade_id), trades[0] if trades else {})
    if not trade:
        return {"ok": False, "mode": "demo-local", "message": "Save and review a paper plan before sending it to the journal.", "disclaimer": REQUIRED_DISCLAIMER}
    if trade.get("status") != "reviewed":
        return {"ok": False, "mode": "demo-local", "message": "Review the paper plan before sending it to the journal.", "disclaimer": REQUIRED_DISCLAIMER}
    if trade.get("journal_entry_id"):
        return {
            "ok": True,
            "mode": "demo-local",
            "item": trade,
            "journal_entry_id": trade.get("journal_entry_id"),
            "limit_check": limit_check,
            "message": "This paper review is already linked to a journal entry.",
            "disclaimer": REQUIRED_DISCLAIMER,
        }
    saved_entry = add_journal_entry(_journal_entry_from_paper_trade(trade))
    saved_trade = update_paper_trade_review(
        str(trade.get("id") or trade_id),
        {"journal_entry_id": saved_entry.get("id"), "journalized_at": now_iso()},
    )
    return {
        "ok": True,
        "mode": "demo-local",
        "item": saved_trade,
        "journal_entry": saved_entry,
        "limit_check": limit_check,
        "message": "Paper review saved into the journal in local demo persistence.",
        "warning": payload.get("warning"),
        "disclaimer": REQUIRED_DISCLAIMER,
    }


@app.get("/api/journal")
async def api_journal(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            rows = store.select(
                "trade_journal",
                "select=*&order=created_at.desc&limit=100",
                auth_token=token,
            )
            review = build_weekly_review()
            review["entries"] = rows or review["entries"]
            review["mode"] = "supabase"
            return review
        except Exception as exc:
            fallback = build_weekly_review()
            fallback["mode"] = "demo-fallback"
            fallback["warning"] = str(exc)
            return fallback
    return _weekly_review_from_entries(list_journal_entries())


@app.post("/api/journal")
async def api_journal_create(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    limit_check = _limit_check("journal_entry", _payload_plan(payload))
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            allowed = {
                "user_id",
                "symbol",
                "asset_type",
                "direction",
                "entry_price",
                "exit_price",
                "stop_loss",
                "target_price",
                "position_size",
                "result",
                "pnl",
                "setup_type",
                "entry_reason",
                "exit_reason",
                "mistakes",
                "lesson_learned",
                "screenshot_url",
                "ai_summary",
                "source_type",
                "source_id",
            }
            saved = store.insert("trade_journal", _only(payload, allowed), auth_token=token)
            return {
                "ok": True,
                "mode": "supabase",
                "entry": saved,
                "ai_summary": "Journal entry saved to Supabase. AI summary can be upgraded when OPENAI_API_KEY is connected.",
                "limit_check": limit_check,
                "disclaimer": REQUIRED_DISCLAIMER,
            }
        except Exception as exc:
            demo = _demo_persistence_response("journal", payload)
            demo["warning"] = str(exc)
            demo["limit_check"] = limit_check
            return demo
    saved = add_journal_entry(payload)
    return {
        "ok": True,
        "mode": "demo-local",
        "entry": saved,
        "ai_summary": "Journal entry saved in local demo persistence. Supabase can take over after configuration.",
        "limit_check": limit_check,
        "disclaimer": REQUIRED_DISCLAIMER,
    }


@app.get("/api/journal/weekly-review")
async def api_journal_weekly_review() -> dict[str, Any]:
    return _weekly_review_from_entries(list_journal_entries())


@app.post("/api/strategy-builder")
async def api_strategy_builder(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    return build_strategy(payload)


@app.get("/api/strategies")
async def api_strategies(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            return {
                "ok": True,
                "mode": "supabase",
                "items": store.select("strategy_rules", "select=*&order=created_at.desc", auth_token=token),
            }
        except Exception as exc:
            return {"ok": False, "mode": "demo-fallback", "items": [], "error": str(exc)}
    return {"ok": True, "mode": "demo-local", "items": list_strategies()}


@app.post("/api/strategies")
async def api_strategies_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    limit_check = _limit_check("saved_strategy", _payload_plan(payload))
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            return {"ok": True, "mode": "supabase", "item": store.insert("strategy_rules", payload, auth_token=token), "limit_check": limit_check}
        except Exception as exc:
            demo = _demo_persistence_response("strategy", payload)
            demo["warning"] = str(exc)
            demo["limit_check"] = limit_check
            return demo
    return {"ok": True, "mode": "demo-local", "item": add_strategy(payload), "limit_check": limit_check, "message": "Strategy saved in local demo persistence."}


@app.get("/api/school")
async def api_school(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    dashboard_payload = build_dashboard()
    progress = get_school_progress()
    mode = "demo-local"
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            rows = store.select(
                "school_progress",
                "select=lesson_key,status,quiz_score,updated_at&order=updated_at.desc",
                auth_token=token,
            )
            progress = {row.get("lesson_key"): row for row in rows if row.get("lesson_key")}
            mode = "supabase"
        except Exception:
            mode = "demo-fallback"
    modules = []
    for module in dashboard_payload["school_modules"]:
        lesson_key = _lesson_key(str(module.get("lesson") or "lesson"))
        saved = progress.get(lesson_key) or {}
        modules.append(
            dict(
                module,
                lesson_key=lesson_key,
                status=saved.get("status") or module.get("status"),
                quiz_score=saved.get("quiz_score"),
                quiz=SCHOOL_QUIZZES.get(lesson_key, SCHOOL_QUIZZES["trading_basics"]),
            )
        )
    return {"ok": True, "mode": mode, "modules": modules, "progress": progress, "disclaimer": REQUIRED_DISCLAIMER}


@app.post("/api/school/progress")
async def api_school_progress_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    lesson_key = str(payload.get("lesson_key") or _lesson_key(str(payload.get("lesson") or "lesson")))
    saved_payload = {
        "lesson_key": lesson_key,
        "lesson": payload.get("lesson") or lesson_key.replace("_", " ").title(),
        "status": payload.get("status") or "completed",
        "quiz_score": _number(payload.get("quiz_score")),
    }
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            supabase_payload = dict(saved_payload, user_id=payload.get("user_id"))
            saved = store.upsert("school_progress", supabase_payload, on_conflict="user_id,lesson_key", auth_token=token)
            return {"ok": True, "mode": "supabase", "progress": saved, "message": "Lesson progress saved."}
        except Exception as exc:
            saved = save_school_progress(saved_payload)
            return {"ok": True, "mode": "demo-fallback", "progress": saved, "warning": str(exc)}
    return {"ok": True, "mode": "demo-local", "progress": save_school_progress(saved_payload), "message": "Lesson progress saved in local demo persistence."}


@app.get("/api/risk-rules")
async def api_risk_rules(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            rows = store.select("risk_rules", "select=*&limit=1", auth_token=token)
            if rows:
                return {"ok": True, "mode": "supabase", "rules": rows[0], "disclaimer": REQUIRED_DISCLAIMER}
        except Exception as exc:
            return {"ok": True, "mode": "demo-fallback", "warning": str(exc), "rules": build_dashboard()["risk_rules"], "disclaimer": REQUIRED_DISCLAIMER}
    return {"ok": True, "mode": "demo-local", "rules": get_risk_rules(), "disclaimer": REQUIRED_DISCLAIMER}


@app.post("/api/risk-rules")
async def api_risk_rules_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            saved = store.upsert("risk_rules", payload, on_conflict="user_id", auth_token=token)
            return {"ok": True, "mode": "supabase", "rules": saved, "message": "Risk rules saved."}
        except Exception as exc:
            return {"ok": True, "mode": "demo-fallback", "warning": str(exc), "rules": payload}
    return {"ok": True, "mode": "demo-local", "rules": save_risk_rules(payload), "message": "Risk rules saved in local demo persistence."}


@app.get("/api/dashboard-layout")
async def api_dashboard_layout(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            rows = store.select("dashboard_layouts", "select=layout,updated_at&limit=1", auth_token=token)
            if rows:
                return {"ok": True, "mode": "supabase", "layout": rows[0].get("layout") or {}}
        except Exception as exc:
            return {"ok": True, "mode": "demo-fallback", "layout": {}, "warning": str(exc)}
    return {"ok": True, "mode": "demo-local", "layout": get_dashboard_layout()}


@app.post("/api/dashboard-layout")
async def api_dashboard_layout_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    token = _bearer_token(authorization)
    user_id = payload.get("user_id")
    layout = payload.get("layout") if isinstance(payload.get("layout"), dict) else payload
    if token and settings.supabase_publishable_key and settings.supabase_url and user_id:
        try:
            saved = store.upsert(
                "dashboard_layouts",
                {"user_id": user_id, "layout": layout},
                on_conflict="user_id",
                auth_token=token,
            )
            return {"ok": True, "mode": "supabase", "layout": saved.get("layout") or layout, "message": "Layout saved."}
        except Exception as exc:
            return {"ok": True, "mode": "demo-fallback", "layout": layout, "warning": str(exc)}
    return {"ok": True, "mode": "demo-local", "layout": save_dashboard_layout(layout), "message": "Layout saved in local demo persistence."}


@app.get("/api/watchlists")
async def api_watchlists(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            return {
                "ok": True,
                "mode": "supabase",
                "watchlists": store.select("watchlists", "select=*,watchlist_items(*)&order=created_at.asc", auth_token=token),
            }
        except Exception as exc:
            return {"ok": True, "mode": "demo-fallback", "watchlists": [], "warning": str(exc)}
    return {"ok": True, "mode": "demo-local", "watchlists": list_watchlists()}


@app.post("/api/watchlists")
async def api_watchlists_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            return {"ok": True, "mode": "supabase", "watchlist": store.insert("watchlists", payload, auth_token=token)}
        except Exception as exc:
            demo = _demo_persistence_response("watchlist", payload)
            demo["warning"] = str(exc)
            return demo
    return {"ok": True, "mode": "demo-local", "watchlist": add_watchlist(payload), "message": "Watchlist saved in local demo persistence."}


@app.post("/api/watchlist-items")
async def api_watchlist_items_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    limit_check = _limit_check("watchlist_symbol", _payload_plan(payload))
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            return {"ok": True, "mode": "supabase", "item": store.insert("watchlist_items", payload, auth_token=token), "limit_check": limit_check}
        except Exception as exc:
            demo = _demo_persistence_response("watchlist-item", payload)
            demo["warning"] = str(exc)
            demo["limit_check"] = limit_check
            return demo
    return {"ok": True, "mode": "demo-local", "item": add_watchlist_item(payload), "limit_check": limit_check, "message": "Symbol saved in local demo persistence."}


@app.post("/api/activity")
async def api_activity_save(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            saved = store.upsert("user_activity", payload, on_conflict="user_id", auth_token=token)
            return {"ok": True, "mode": "supabase", "activity": saved}
        except Exception as exc:
            return {"ok": True, "mode": "demo-fallback", "activity": payload, "warning": str(exc)}
    return {"ok": True, "mode": "demo-local", "activity": save_activity(payload), "message": "Activity saved in local demo persistence."}


@app.get("/api/news-impact")
async def api_news_impact() -> dict[str, Any]:
    data = build_dashboard()
    return {"ok": True, "mode": DEMO_MODE_LABEL, "items": data["news_impact"], "disclaimer": REQUIRED_DISCLAIMER}


@app.get("/api/what-changed")
async def api_what_changed() -> dict[str, Any]:
    data = build_dashboard()
    return {"ok": True, "mode": DEMO_MODE_LABEL, "items": data["what_changed"], "disclaimer": REQUIRED_DISCLAIMER}


@app.post("/api/screenshot-analyzer")
async def api_screenshot_analyzer(
    payload: dict[str, Any] | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = payload or {}
    limit_check = _limit_check("screenshot_review", _payload_plan(payload))
    filename = str(payload.get("filename") or "chart screenshot")
    platform = str(payload.get("platform") or "Chart platform")
    symbol = str(payload.get("symbol") or "").upper()
    analysis = _screenshot_demo_analysis(payload, filename, platform, symbol, limit_check)
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url and payload.get("user_id"):
        try:
            saved = store.insert(
                "screenshot_reviews",
                {
                    "user_id": payload.get("user_id"),
                    "filename": filename,
                    "platform": platform,
                    "symbol": symbol,
                    "notes": payload.get("notes") or "",
                    "payload": payload,
                    "analysis": analysis,
                },
                auth_token=token,
            )
            analysis["mode"] = "supabase"
            analysis["review"] = saved
            return analysis
        except Exception as exc:
            analysis["warning"] = str(exc)
            analysis["mode"] = "demo-fallback"
    saved = add_screenshot_review(dict(payload, analysis=analysis))
    analysis["review"] = saved
    return analysis


@app.get("/api/screenshot-reviews")
async def api_screenshot_reviews(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _bearer_token(authorization)
    if token and settings.supabase_publishable_key and settings.supabase_url:
        try:
            return {
                "ok": True,
                "mode": "supabase",
                "items": store.select("screenshot_reviews", "select=*&order=created_at.desc&limit=100", auth_token=token),
                "disclaimer": REQUIRED_DISCLAIMER,
            }
        except Exception as exc:
            return {"ok": True, "mode": "demo-fallback", "items": list_screenshot_reviews(), "warning": str(exc), "disclaimer": REQUIRED_DISCLAIMER}
    return {"ok": True, "mode": "demo-local", "items": list_screenshot_reviews(), "disclaimer": REQUIRED_DISCLAIMER}


@app.get("/api/scan")
async def api_scan(
    symbols: str | None = Query(default=None, description="Comma-separated tickers"),
    period: str = "5d",
    interval: str = "5m",
    save: bool = True,
) -> dict[str, Any]:
    tickers = _parse_symbols(symbols)
    try:
        payload = scan_symbols(tickers, period=period, interval=interval)
        payload["ok"] = True
        payload["disclaimer"] = REQUIRED_DISCLAIMER
        if save:
            payload["snapshot_id"] = save_snapshot("scan", payload)
        return payload
    except Exception as exc:
        return _safe_error_payload("scan", exc, tickers)


@app.get("/api/news")
async def api_news(symbols: str | None = Query(default=None), save: bool = True) -> dict[str, Any]:
    tickers = _parse_symbols(symbols)
    try:
        payload = build_news_brief(tickers)
        payload["ok"] = True
        payload["disclaimer"] = REQUIRED_DISCLAIMER
        if save:
            payload["snapshot_id"] = save_snapshot("news", payload)
        return payload
    except Exception as exc:
        fallback_item = {
            "provider": "Local fallback",
            "symbol": ",".join(tickers),
            "headline": "News engine could not load live headlines yet",
            "summary": str(exc),
            "url": "",
            "published_at": "",
            "categories": ["Company / General Market"],
            "sentiment": {"label": "neutral", "score": 0, "source": "fallback"},
            "urgency": "provider-error",
            "error": True,
        }
        payload = {
            "ok": False,
            "symbols": tickers,
            "items": [fallback_item],
            "by_category": {"Company / General Market": [fallback_item]},
            "by_urgency": {"instant-watch": [], "current": [], "latest": [], "background": [], "provider-error": [fallback_item]},
            "enabled_providers": ["Local fallback"],
            "error": str(exc),
            "disclaimer": REQUIRED_DISCLAIMER,
        }
        if save:
            payload["snapshot_id"] = save_snapshot("news", payload)
        return payload


@app.get("/api/latest")
async def api_latest(symbols: str | None = Query(default=None)) -> dict[str, Any]:
    tickers = _parse_symbols(symbols)
    scans = await api_scan(symbols=",".join(tickers), save=False)
    news = await api_news(symbols=",".join(tickers), save=False)
    payload = {
        "ok": bool(scans.get("ok", False) and news.get("ok", False)),
        "symbols": tickers,
        "scan": scans,
        "news": news,
        "extension_message": _build_extension_message(scans, news),
        "disclaimer": REQUIRED_DISCLAIMER,
    }
    save_snapshot("latest", payload)
    return payload


@app.get("/api/history")
async def api_history(kind: str | None = None, limit: int = 20) -> dict[str, Any]:
    try:
        return {"ok": True, "items": latest_snapshots(kind=kind, limit=limit), "disclaimer": REQUIRED_DISCLAIMER}
    except Exception as exc:
        return _safe_error_payload("history", exc)


def _build_extension_message(scans: dict[str, Any], news: dict[str, Any]) -> str:
    summary = scans.get("summary", "No scan summary.")
    instant = news.get("by_urgency", {}).get("instant-watch", [])
    current = news.get("by_urgency", {}).get("current", [])
    errors = news.get("by_urgency", {}).get("provider-error", [])
    if instant:
        news_line = f"Instant-watch news: {instant[0].get('headline', '')}"
    elif current:
        news_line = f"Current news: {current[0].get('headline', '')}"
    elif errors:
        news_line = "News provider needs setup/check."
    else:
        news_line = "No urgent news bucket hit."
    return f"{summary} | {news_line}"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "message": "TradePulse server is running."}
