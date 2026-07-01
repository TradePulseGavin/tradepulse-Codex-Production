from __future__ import annotations

from typing import Any

import pandas as pd

from .config import settings
from .data_providers import clean_symbol, fetch_price_history, fetch_quote
from .demo_data import DEMO_MODE_LABEL, REQUIRED_DISCLAIMER, build_demo_candles, symbol_snapshot, utc_now_iso


TIMEFRAME_INTERVALS = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "60m",
    "4h": "60m",
    "1D": "1d",
}


TIMEFRAME_PERIODS = {
    "1m": "1d",
    "5m": "5d",
    "15m": "5d",
    "30m": "1mo",
    "1h": "1mo",
    "4h": "3mo",
    "1D": "6mo",
}


def _row_value(row: pd.Series, name: str) -> float:
    try:
        return round(float(row[name]), 4)
    except Exception:
        return 0.0


def _candles_from_history(symbol: str, timeframe: str, df: pd.DataFrame, limit: int = 96) -> dict[str, Any]:
    history = df.tail(limit).copy()
    candles: list[dict[str, Any]] = []
    for stamp, row in history.iterrows():
        label = stamp.strftime("%H:%M" if timeframe != "1D" else "%m/%d") if hasattr(stamp, "strftime") else str(stamp)
        candles.append(
            {
                "time": stamp.isoformat() if hasattr(stamp, "isoformat") else str(stamp),
                "label": label,
                "open": _row_value(row, "Open"),
                "high": _row_value(row, "High"),
                "low": _row_value(row, "Low"),
                "close": _row_value(row, "Close"),
                "volume": int(float(row.get("Volume") or 0)),
            }
        )
    latest = candles[-1] if candles else {}
    snapshot = symbol_snapshot(symbol)
    if latest:
        previous = candles[-2]["close"] if len(candles) > 1 else latest["close"]
        change = latest["close"] - previous
        snapshot.update(
            {
                "price": round(latest["close"], 2),
                "change": round(change, 2),
                "trend_status": "Real data loaded; review chart structure",
                "volume_status": "Volume from yfinance research feed",
                "vwap_status": "Use chart indicators for VWAP confirmation",
                "setup_note": "Real research candles are loaded. Confirm with broker/chart data before decisions.",
            }
        )
    return {
        "ok": True,
        "mode": "real-market-research",
        "symbol": clean_symbol(symbol),
        "asset_type": snapshot.get("asset_type", "Stock"),
        "timeframe": timeframe,
        "candles": candles,
        "snapshot": snapshot,
        "data_source": "yfinance",
        "generated_at": utc_now_iso(),
        "disclaimer": REQUIRED_DISCLAIMER,
    }


def chart_data(symbol: str, timeframe: str = "5m", live: bool = False) -> dict[str, Any]:
    normalized = clean_symbol(symbol or "SPY")
    if not live or not settings.enable_real_market_data:
        payload = build_demo_candles(symbol=normalized, timeframe=timeframe)
        payload["data_source"] = "demo"
        payload["real_market_data_enabled"] = settings.enable_real_market_data
        return payload
    try:
        interval = TIMEFRAME_INTERVALS.get(timeframe, "5m")
        period = TIMEFRAME_PERIODS.get(timeframe, "5d")
        df = fetch_price_history(normalized, period=period, interval=interval)
        return _candles_from_history(normalized, timeframe, df)
    except Exception as exc:
        payload = build_demo_candles(symbol=normalized, timeframe=timeframe)
        payload["data_source"] = "demo-fallback"
        payload["mode"] = DEMO_MODE_LABEL
        payload["warning"] = f"Real market data fallback used: {exc}"
        payload["real_market_data_enabled"] = settings.enable_real_market_data
        return payload


def quote_snapshot(symbol: str, live: bool = False) -> dict[str, Any]:
    normalized = clean_symbol(symbol or "SPY")
    snapshot = symbol_snapshot(normalized)
    if not live or not settings.enable_real_market_data:
        snapshot["data_source"] = "demo"
        return snapshot
    try:
        quote = fetch_quote(normalized)
        if quote.get("price") is not None:
            snapshot["price"] = round(float(quote["price"]), 2)
            snapshot["data_source"] = quote.get("source") or "yfinance"
            snapshot["quote_time"] = quote.get("time")
            snapshot["setup_note"] = "Real quote loaded for research. Confirm with your broker/chart feed before decisions."
        return snapshot
    except Exception as exc:
        snapshot["data_source"] = "demo-fallback"
        snapshot["warning"] = str(exc)
        return snapshot
