from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Any


REQUIRED_DISCLAIMER = (
    "TradePulse is for trading research, education, journaling, and market organization. "
    "It is not financial advice, does not guarantee results, and does not place trades for you. "
    "Always paper trade first and make your own final decisions."
)
DEMO_MODE_LABEL = "Demo/delayed data"

DEMO_WATCHLIST: list[dict[str, Any]] = [
    {"symbol": "SPY", "asset_type": "ETF", "price": 548.42, "change": 0.42, "trend_status": "Constructive above VWAP", "volume_status": "Volume near average", "vwap_status": "Holding above VWAP", "news_risk": "Medium", "volatility_status": "Moderate", "liquidity_status": "High", "setup_note": "Index is balanced; clean entries need confirmation near prior high.", "setup_score": 7.2, "tradepulse_score": 7.5},
    {"symbol": "QQQ", "asset_type": "ETF", "price": 472.18, "change": 0.76, "trend_status": "Stronger than SPY", "volume_status": "Volume slightly elevated", "vwap_status": "Pullback near VWAP", "news_risk": "Medium", "volatility_status": "Elevated", "liquidity_status": "High", "setup_note": "Tech strength is present, but chasing extended candles is the main risk.", "setup_score": 7.8, "tradepulse_score": 7.7},
    {"symbol": "NVDA", "asset_type": "Stock", "price": 128.64, "change": 1.31, "trend_status": "Momentum leader", "volume_status": "High relative volume", "vwap_status": "Extended above VWAP", "news_risk": "High", "volatility_status": "High", "liquidity_status": "High", "setup_note": "Momentum is strong; wait for confirmation instead of chasing the first spike.", "setup_score": 6.9, "tradepulse_score": 7.1},
    {"symbol": "TSLA", "asset_type": "Stock", "price": 187.33, "change": -0.84, "trend_status": "Choppy range", "volume_status": "Volume elevated", "vwap_status": "Testing VWAP from below", "news_risk": "High", "volatility_status": "High", "liquidity_status": "High", "setup_note": "News-driven move; confirmation matters more than direction bias.", "setup_score": 5.8, "tradepulse_score": 6.1},
    {"symbol": "MNQ", "asset_type": "Future", "price": 19842.25, "change": 0.58, "trend_status": "Trend continuation attempt", "volume_status": "Active session volume", "vwap_status": "Near session VWAP", "news_risk": "Medium", "volatility_status": "Elevated", "liquidity_status": "High", "setup_note": "Futures volatility is elevated; size and stop clarity are the key checks.", "setup_score": 6.6, "tradepulse_score": 6.8},
]
MARKET_MOOD: dict[str, Any] = {"mood": "Mixed / risk-on pockets", "spy_trend": "Grinding higher above VWAP", "qqq_trend": "Leadership versus SPY", "vix_status": "Contained but not quiet", "mega_cap_tech": "Firm", "news_risk": "Medium", "best_environment": "Patient pullback entries with defined invalidation", "worst_environment": "Chasing first candles after headlines", "session": "New York open", "volatility_level": "Moderate to elevated", "futures": {"nq_momentum": "Positive but stretched", "es_momentum": "Balanced", "economic_event_nearby": "Demo calendar shows medium-impact data risk", "tick_value_note": "MNQ moves in 0.25 point ticks; each tick is worth $0.50 per contract.", "margin_note": "Margin rules vary by broker and session. Confirm before sizing."}}
NEWS_IMPACT: list[dict[str, Any]] = [
    {"symbol": "NVDA", "impact": "High", "type": "Product launch / analyst commentary", "affected_symbols": ["NVDA", "QQQ", "SMH"], "volatility_risk": "High", "trade_risk": "Fast reversals after headline spikes", "chart_context": "Extended above VWAP; confirmation is more useful than chasing."},
    {"symbol": "TSLA", "impact": "Medium", "type": "Company news", "affected_symbols": ["TSLA", "ARKK"], "volatility_risk": "High", "trade_risk": "Wide candles and spread changes", "chart_context": "Testing VWAP from below inside a choppy range."},
    {"symbol": "SPY", "impact": "Medium", "type": "Macro data", "affected_symbols": ["SPY", "QQQ", "IWM", "ES", "NQ"], "volatility_risk": "Medium", "trade_risk": "Index whipsaw around scheduled events", "chart_context": "Balanced trend; watch prior high and VWAP reaction."},
]
JOURNAL_ENTRIES: list[dict[str, Any]] = [
    {"symbol": "QQQ", "asset_type": "ETF", "direction": "Long", "entry_price": 468.2, "stop_loss": 466.8, "target_price": 472.0, "exit_price": 471.1, "position_size": 50, "result": "Win", "pnl": 145, "setup_type": "VWAP bounce", "entry_reason": "Pulled back to VWAP after trend held.", "exit_reason": "Scaled near prior high.", "mistakes": "Scaled late after the second candle.", "lesson_learned": "Best entry was the first confirmed reclaim, not the extended follow-through.", "ai_summary": "Clean VWAP reclaim, but late scaling increased risk."},
    {"symbol": "TSLA", "asset_type": "Stock", "direction": "Long", "entry_price": 190.8, "stop_loss": 187.8, "target_price": 195.0, "exit_price": 187.6, "position_size": 50, "result": "Loss", "pnl": -160, "setup_type": "News momentum", "entry_reason": "Entered after a large green candle.", "exit_reason": "Stopped after VWAP failed.", "mistakes": "Chased news and did not wait for VWAP confirmation.", "lesson_learned": "Avoid first-candle entries on headline moves.", "ai_summary": "News risk was high and confirmation was weak."},
    {"symbol": "MNQ", "asset_type": "Future", "direction": "Short", "entry_price": 19812.5, "stop_loss": 19828.0, "target_price": 19780.0, "exit_price": 19792.0, "position_size": 1, "result": "Win", "pnl": 82, "setup_type": "Range rejection", "entry_reason": "Rejected prior high with volume fading.", "exit_reason": "Took partial target in elevated volatility.", "mistakes": "Stop was defined but position size was slightly aggressive.", "lesson_learned": "Size down when volatility is elevated.", "ai_summary": "Good structure with room to improve sizing."},
]
SCHOOL_MODULES: list[dict[str, Any]] = [
    {"track": "Basics", "lesson": "Trading basics", "status": "Ready", "score": 0}, {"track": "Charts", "lesson": "Candlesticks", "status": "Ready", "score": 0}, {"track": "Charts", "lesson": "Support and resistance", "status": "Ready", "score": 0}, {"track": "Indicators", "lesson": "VWAP", "status": "Recommended", "score": 0}, {"track": "Indicators", "lesson": "EMA", "status": "Ready", "score": 0}, {"track": "Indicators", "lesson": "RSI and ATR", "status": "Ready", "score": 0}, {"track": "Risk", "lesson": "Risk/reward and stop loss", "status": "Recommended", "score": 0}, {"track": "Options", "lesson": "IV, Greeks, spreads, and open interest", "status": "Ready", "score": 0}, {"track": "Futures", "lesson": "Tick size, tick value, margin, and sessions", "status": "Ready", "score": 0}, {"track": "Review", "lesson": "Journaling and discipline", "status": "Recommended", "score": 0}
]
RISK_RULES: dict[str, Any] = {"max_trades_per_day": 3, "max_losses_per_day": 2, "require_stop_loss": True, "avoid_news_minutes": 15, "max_option_premium": 250, "max_risk_per_trade": 75, "require_checklist": True}
OPTIONS_RESEARCH: dict[str, Any] = {"underlying": "NVDA", "expiration": "Demo weekly", "strike": 130, "type": "Call", "bid": 2.4, "ask": 2.58, "spread": 0.18, "volume": 12800, "open_interest": 21400, "iv": "74%", "delta": 0.42, "gamma": 0.08, "theta": -0.12, "vega": 0.09, "breakeven": 132.58, "explanation": "The spread and IV are the main risk checks in this demo contract."}
FUTURES_RESEARCH: dict[str, Any] = {"contract": "MNQ demo continuous", "session": "New York", "current_price": 19842.25, "daily_range": "19710.50 - 19888.75", "volume": "Active", "tick_size": 0.25, "tick_value": "$0.50 per MNQ tick", "expiration": "Demo continuous", "volatility": "Elevated", "margin_note": "Broker margin changes by product and session. Confirm before sizing.", "event_warning": "Medium-impact macro event in demo calendar."}
WHAT_CHANGED: list[str] = ["QQQ is trending stronger than SPY in this demo snapshot.", "NVDA is extended above VWAP with elevated headline risk.", "TSLA moved into a choppy news-driven range.", "Your demo journal shows chasing after large candles as the most repeated mistake.", "The saved VWAP Bounce strategy has 2 symbols worth reviewing."]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_symbols(symbols: list[str] | str | None) -> list[str]:
    if symbols is None:
        return [item["symbol"] for item in DEMO_WATCHLIST]
    raw = symbols.split(",") if isinstance(symbols, str) else symbols
    cleaned = [str(item).strip().upper().replace("$", "") for item in raw if str(item).strip()]
    return cleaned or [item["symbol"] for item in DEMO_WATCHLIST]


def symbol_snapshot(symbol: str) -> dict[str, Any]:
    normalized = symbol.strip().upper().replace("$", "") or "SPY"
    for item in DEMO_WATCHLIST:
        if item["symbol"] == normalized:
            return dict(item)
    base = 80 + (sum(ord(char) for char in normalized) % 90)
    return {"symbol": normalized, "asset_type": "Stock", "price": round(base + 0.42, 2), "change": round(((base % 7) - 3) / 10, 2), "trend_status": "Neutral demo trend", "volume_status": "Volume near average", "vwap_status": "Near VWAP", "news_risk": "Medium", "volatility_status": "Moderate", "liquidity_status": "Review spread and volume", "setup_note": "Demo symbol needs confirmation before it becomes a clean setup.", "setup_score": 5.9, "tradepulse_score": 6.0}


def build_demo_candles(symbol: str, timeframe: str = "5m", points: int = 72) -> dict[str, Any]:
    snapshot = symbol_snapshot(symbol)
    seed = sum(ord(char) for char in snapshot["symbol"])
    base = float(snapshot["price"]) - (points * 0.08)
    candles: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    step_minutes = 5
    if timeframe.endswith("m"):
        try:
            step_minutes = max(1, int(timeframe[:-1]))
        except ValueError:
            step_minutes = 5
    elif timeframe.endswith("h"):
        try:
            step_minutes = max(1, int(timeframe[:-1])) * 60
        except ValueError:
            step_minutes = 60
    elif timeframe == "1D":
        step_minutes = 1440
    previous_close = base
    for idx in range(points):
        wave = math.sin((idx + seed % 11) / 4.0) * 0.85
        drift = idx * 0.08 + (seed % 5) * 0.015
        open_price = previous_close
        close = base + drift + wave
        high = max(open_price, close) + 0.28 + (idx % 5) * 0.04
        low = min(open_price, close) - 0.24 - (idx % 3) * 0.03
        previous_close = close
        stamp = now - timedelta(minutes=step_minutes * (points - idx))
        candles.append({"time": stamp.isoformat(), "label": stamp.strftime("%H:%M" if step_minutes < 1440 else "%m/%d"), "open": round(open_price, 2), "high": round(high, 2), "low": round(low, 2), "close": round(close, 2), "volume": int(800000 + (idx * 17000) + (seed % 17) * 23000)})
    return {"ok": True, "mode": DEMO_MODE_LABEL, "symbol": snapshot["symbol"], "asset_type": snapshot["asset_type"], "timeframe": timeframe, "candles": candles, "snapshot": snapshot, "generated_at": utc_now_iso(), "disclaimer": REQUIRED_DISCLAIMER}


def build_scanner(symbols: list[str] | str | None = None) -> dict[str, Any]:
    items = []
    for symbol in normalize_symbols(symbols):
        snapshot = symbol_snapshot(symbol)
        items.append({"symbol": snapshot["symbol"], "asset_type": snapshot["asset_type"], "trend_status": snapshot["trend_status"], "volume_status": snapshot["volume_status"], "vwap_status": snapshot["vwap_status"], "news_risk": snapshot["news_risk"], "volatility_status": snapshot["volatility_status"], "liquidity_status": snapshot["liquidity_status"], "setup_note": snapshot["setup_note"], "setup_score": snapshot["setup_score"], "tradepulse_score": snapshot["tradepulse_score"]})
    return {"ok": True, "mode": DEMO_MODE_LABEL, "title": "Setups worth reviewing", "summary": "Demo scanner found conditions to watch. This is research context, not a trade instruction.", "items": items, "generated_at": utc_now_iso(), "disclaimer": REQUIRED_DISCLAIMER}


def build_dashboard() -> dict[str, Any]:
    wins = sum(1 for item in JOURNAL_ENTRIES if item["result"].lower() == "win")
    losses = sum(1 for item in JOURNAL_ENTRIES if item["result"].lower() == "loss")
    pnl = sum(float(item["pnl"]) for item in JOURNAL_ENTRIES)
    return {"ok": True, "mode": DEMO_MODE_LABEL, "watchlist": DEMO_WATCHLIST, "scanner": build_scanner(), "market_mood": MARKET_MOOD, "news_impact": NEWS_IMPACT, "journal_summary": {"total_trades": len(JOURNAL_ENTRIES), "wins": wins, "losses": losses, "demo_pnl": pnl, "best_setup": "VWAP bounce", "worst_habit": "Chasing large candles after news", "focus": "Wait for confirmation and define invalidation before entry."}, "risk_rules": RISK_RULES, "options": OPTIONS_RESEARCH, "futures": FUTURES_RESEARCH, "what_changed": WHAT_CHANGED, "school_modules": SCHOOL_MODULES, "generated_at": utc_now_iso(), "disclaimer": REQUIRED_DISCLAIMER}


def build_copilot_response(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    message = str(payload.get("message") or "").strip()
    symbol = str(payload.get("symbol") or "SPY").upper()
    asset_type = str(payload.get("asset_type") or symbol_snapshot(symbol)["asset_type"])
    timeframe = str(payload.get("timeframe") or "5m")
    snapshot = symbol_snapshot(symbol)
    lower = message.lower()
    focus = "chart structure"
    if "option" in lower:
        focus = "options risk"
    elif "future" in lower or asset_type.lower() == "future":
        focus = "futures risk"
    elif "beginner" in lower or "new" in lower:
        focus = "beginner explanation"
    elif "changed" in lower:
        focus = "what changed"
    response = f"{symbol} is in {DEMO_MODE_LABEL.lower()} with {snapshot['trend_status'].lower()} and {snapshot['volume_status'].lower()} on the {timeframe} view. For {focus}, the useful research question is whether price confirms near VWAP without forcing an entry after an extended candle. Bullish factors: trend alignment and liquidity. Bearish factors: {snapshot['news_risk'].lower()} news risk and {snapshot['volatility_status'].lower()} volatility. Review stop placement, event risk, and whether this matches your saved strategy before making your own decision."
    if focus == "options risk":
        response += " For the demo option view, compare bid/ask spread, IV, theta decay, open interest, and breakeven before deciding whether the contract is even worth researching."
    if focus == "futures risk":
        response += " For futures, confirm tick value, session volatility, and margin rules before sizing."
    if focus == "beginner explanation":
        response += " In beginner terms: VWAP is a fair-price line many day traders watch; extended moves away from it can be powerful, but they can also snap back quickly."
    return {"ok": True, "mode": "mock-ai", "response": response, "risk_notes": ["This is research commentary only, not a buy or sell call.", f"News risk is {snapshot['news_risk']}; avoid assuming the move is clean.", "Define entry, stop, target, and invalidation before journaling the setup."], "setup_score": snapshot["setup_score"], "confidence": 0.68, "disclaimer": REQUIRED_DISCLAIMER}


def build_trade_checklist(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    score = 4
    violations: list[str] = []
    if payload.get("entry") and payload.get("stop") and payload.get("target"):
        score += 2
    else:
        violations.append("Entry, stop, and target are not all defined.")
    if payload.get("reason"):
        score += 1
    else:
        violations.append("Trade reason is missing.")
    if payload.get("invalidation"):
        score += 1
    else:
        violations.append("Invalidation condition is missing.")
    if str(payload.get("news") or "").lower() in {"high", "yes"}:
        score -= 1
        violations.append("High-impact news risk needs review.")
    if str(payload.get("following_rules") or "").lower() in {"no", "false"}:
        score -= 1
        violations.append("The setup may break saved strategy or personal risk rules.")
    score = max(0, min(10, score))
    return {"ok": True, "setup_quality": score, "risk_clarity": "Good" if score >= 7 else "Fair" if score >= 5 else "Poor", "news_risk": str(payload.get("news") or "Medium").title(), "liquidity": str(payload.get("liquidity") or "Medium").title(), "emotional_risk": "Medium" if score >= 5 else "High", "rule_violations": violations, "suggested_review_notes": ["This setup is cleaner for research when entry, stop, target, and invalidation are specific.", "Review these risks before making your own decision."], "disclaimer": REQUIRED_DISCLAIMER}


def build_strategy(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    prompt = str(payload.get("prompt") or "I like trading VWAP bounces on QQQ and NVDA.")
    symbols = [word.strip(".,").upper() for word in prompt.split() if word.strip(".,").isalpha() and word.strip(".,").isupper()]
    if not symbols:
        symbols = ["QQQ", "NVDA"]
    name = "VWAP Bounce" if "vwap" in prompt.lower() else "Structured Pullback"
    return {"ok": True, "mode": "demo", "strategy": {"name": name, "description": prompt, "entry_rules": ["Price pulls back toward VWAP or a prior support zone.", "A confirmation candle closes back in the intended direction.", "Volume supports the move without a large spread expansion."], "confirmation_rules": ["Trend and VWAP agree.", "Risk/reward is at least 2R before entry.", "No high-impact event is scheduled within the avoid-news window."], "avoid_rules": ["Avoid chasing extended candles.", "Avoid trades without a defined stop.", "Avoid taking the third trade after two losses."], "stop_rules": ["Stop goes beyond the recent swing or invalidation level."], "target_rules": ["Target prior high/low, liquidity area, or a 2R objective."], "risk_rules": RISK_RULES, "best_market_conditions": "Orderly trend with controlled volatility.", "worst_market_conditions": "Headline-driven chop with wide candles.", "watchlist_symbols": symbols, "scanner_logic_summary": "Flag symbols near VWAP with trend alignment, liquidity, and manageable news risk."}, "disclaimer": REQUIRED_DISCLAIMER}


def build_weekly_review() -> dict[str, Any]:
    wins = [item for item in JOURNAL_ENTRIES if item["result"].lower() == "win"]
    losses = [item for item in JOURNAL_ENTRIES if item["result"].lower() == "loss"]
    return {"ok": True, "entries": JOURNAL_ENTRIES, "weekly_review": {"total_trades": len(JOURNAL_ENTRIES), "wins": len(wins), "losses": len(losses), "best_setup": "VWAP bounce", "worst_habit": "Entering after large news candles", "average_win_loss": "Demo sample is too small for a reliable average.", "most_repeated_mistake": "Chasing before confirmation", "focus_next_week": "Wait for confirmation and journal the invalidation level before entry."}, "replay_cards": [{"prompt": "Why did the TSLA demo trade fail?", "choices": ["Entered against trend", "Chased a news candle", "Stop was too wide", "Volume was too low"], "answer": "Chased a news candle", "explanation": "The journal note says the entry came after a large candle without VWAP confirmation."}, {"prompt": "What made the QQQ demo trade cleaner?", "choices": ["VWAP pullback held", "No stop was needed", "Spread was ignored", "News risk was high"], "answer": "VWAP pullback held", "explanation": "The trade had a clear setup, defined structure, and confirmation near VWAP."}], "disclaimer": REQUIRED_DISCLAIMER}
