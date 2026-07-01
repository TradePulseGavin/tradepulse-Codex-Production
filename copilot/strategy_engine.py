from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from .data_providers import clean_symbol, fetch_options_chain, fetch_price_history, fetch_quote
from .indicators import add_core_indicators
from .risk import evaluate_option_risk


def _latest_trading_day(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df.index, pd.DatetimeIndex):
        return df
    last_day = df.index[-1].date()
    return df[df.index.date == last_day].copy()


def _score_setup(row: pd.Series, opening_high: float, opening_low: float) -> dict[str, Any]:
    close = float(row["Close"])
    long_checks = {
        "price_breaks_opening_high": close > opening_high,
        "price_above_vwap": close > float(row["VWAP"]),
        "ema_9_above_ema_21": float(row["EMA_9"]) > float(row["EMA_21"]),
        "volume_above_average": float(row["Volume"]) > float(row["AVG_VOLUME_20"]),
        "rsi_not_extreme": 45 <= float(row["RSI_14"]) <= 75,
    }
    short_checks = {
        "price_breaks_opening_low": close < opening_low,
        "price_below_vwap": close < float(row["VWAP"]),
        "ema_9_below_ema_21": float(row["EMA_9"]) < float(row["EMA_21"]),
        "volume_above_average": float(row["Volume"]) > float(row["AVG_VOLUME_20"]),
        "rsi_not_extreme": 25 <= float(row["RSI_14"]) <= 55,
    }
    long_score = sum(long_checks.values())
    short_score = sum(short_checks.values())
    return {
        "long_score": long_score,
        "short_score": short_score,
        "long_checks": long_checks,
        "short_checks": short_checks,
    }


def _choose_option(symbol: str, side: str, current_price: float) -> dict[str, Any] | None:
    chain = fetch_options_chain(symbol, max_expirations=2)
    wanted_side = "call" if side == "LONG" else "put"
    candidates: list[dict[str, Any]] = []
    for group in chain.get("chains", []):
        if group.get("side") != wanted_side:
            continue
        for contract in group.get("contracts", []):
            bid = float(contract.get("bid") or 0)
            ask = float(contract.get("ask") or 0)
            volume = float(contract.get("volume") or 0)
            oi = float(contract.get("openInterest") or 0)
            strike = float(contract.get("strike") or 0)
            if bid <= 0 or ask <= 0 or ask < bid:
                continue
            spread_pct = (ask - bid) / ask if ask else 99
            if spread_pct > 0.18 or volume < 50 or oi < 100:
                continue
            candidates.append(
                {
                    "expiration": group.get("expiration"),
                    "side": wanted_side,
                    "contractSymbol": contract.get("contractSymbol"),
                    "strike": strike,
                    "bid": bid,
                    "ask": ask,
                    "mid": round((bid + ask) / 2, 2),
                    "spread_pct": round(spread_pct * 100, 2),
                    "volume": int(volume),
                    "openInterest": int(oi),
                    "impliedVolatility": contract.get("impliedVolatility"),
                    "distance_from_price": abs(strike - current_price),
                }
            )
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x["distance_from_price"], x["spread_pct"], -x["volume"]))
    return candidates[0]


def scan_symbol(symbol: str, period: str = "5d", interval: str = "5m") -> dict[str, Any]:
    symbol = clean_symbol(symbol)
    result: dict[str, Any] = {
        "symbol": symbol,
        "generated_at": datetime.now(UTC).isoformat(),
        "data_source": "yfinance",
        "mode": "prompt_only",
    }
    try:
        df = add_core_indicators(fetch_price_history(symbol, period=period, interval=interval))
        today = _latest_trading_day(df)
        if len(today) < 6:
            result.update(
                {
                    "action": "WAIT",
                    "bias": "neutral",
                    "confidence": 0,
                    "reason": "Not enough intraday candles yet.",
                }
            )
            return result

        opening_range = today.iloc[:3]
        latest = today.iloc[-1]
        opening_high = float(opening_range["High"].max())
        opening_low = float(opening_range["Low"].min())
        score = _score_setup(latest, opening_high, opening_low)
        long_score = score["long_score"]
        short_score = score["short_score"]

        if long_score >= 4 and long_score > short_score:
            side = "LONG"
            option_action = "BUY_CALL"
            confidence = min(100, long_score * 18)
            reason = "Bullish opening-range/VWAP/EMA setup."
            checks = score["long_checks"]
        elif short_score >= 4 and short_score > long_score:
            side = "SHORT"
            option_action = "BUY_PUT"
            confidence = min(100, short_score * 18)
            reason = "Bearish opening-range/VWAP/EMA setup."
            checks = score["short_checks"]
        else:
            side = "WAIT"
            option_action = "NO_TRADE"
            confidence = max(long_score, short_score) * 12
            reason = "No clean confluence yet. Better to wait than force a trade."
            checks = {"long": score["long_checks"], "short": score["short_checks"]}

        current_price = float(latest["Close"])
        option = None
        risk = None
        if side in {"LONG", "SHORT"}:
            try:
                option = _choose_option(symbol, side, current_price)
                risk = evaluate_option_risk(option.get("ask") if option else None).__dict__
            except Exception as exc:
                option = None
                risk = {"allowed": False, "reasons": [f"Could not pick option contract: {exc}"]}

        result.update(
            {
                "action": side,
                "option_action": option_action,
                "confidence": confidence,
                "reason": reason,
                "current_price": round(current_price, 4),
                "opening_high": round(opening_high, 4),
                "opening_low": round(opening_low, 4),
                "vwap": round(float(latest["VWAP"]), 4),
                "ema_9": round(float(latest["EMA_9"]), 4),
                "ema_21": round(float(latest["EMA_21"]), 4),
                "rsi_14": round(float(latest["RSI_14"]), 2),
                "atr_14": round(float(latest["ATR_14"]), 4),
                "checks": checks,
                "option_contract": option,
                "risk": risk,
                "warning": "Educational prompt only. Confirm with your broker/chart; do not treat this as financial advice.",
            }
        )
    except Exception as exc:
        result.update(
            {
                "action": "ERROR",
                "bias": "unknown",
                "confidence": 0,
                "reason": str(exc),
                "quote": fetch_quote(symbol),
            }
        )
    return result


def scan_symbols(symbols: list[str], period: str = "5d", interval: str = "5m") -> dict[str, Any]:
    clean = [clean_symbol(s) for s in symbols if s.strip()]
    if not clean:
        clean = ["SPY", "QQQ"]
    scans = [scan_symbol(symbol, period=period, interval=interval) for symbol in clean]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "symbols": clean,
        "scans": scans,
        "summary": summarize_scans(scans),
    }


def summarize_scans(scans: list[dict[str, Any]]) -> str:
    actionable = [s for s in scans if s.get("action") in {"LONG", "SHORT"}]
    if not actionable:
        return "No clean trade prompt yet. Watch for VWAP + opening range confirmation."
    best = sorted(actionable, key=lambda s: s.get("confidence", 0), reverse=True)[0]
    return f"Top prompt: {best['symbol']} {best['action']} / {best.get('option_action')} at {best.get('confidence')}% confidence."
