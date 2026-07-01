from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote_plus

import feedparser
import pandas as pd
import requests
import yfinance as yf

from .config import settings


def clean_symbol(symbol: str) -> str:
    return symbol.strip().upper().replace("$", "")


def fetch_price_history(symbol: str, period: str = "5d", interval: str = "5m") -> pd.DataFrame:
    """Fetch OHLCV candles using yfinance.

    Good for research and prompts. For live execution, always confirm quote/order data with the broker.
    """
    symbol = clean_symbol(symbol)
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=False)
    if df.empty:
        raise ValueError(f"No OHLCV data returned for {symbol}.")
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"]).copy()
    df.index = pd.to_datetime(df.index)
    return df


def fetch_quote(symbol: str) -> dict[str, Any]:
    symbol = clean_symbol(symbol)
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1d", interval="1m", auto_adjust=False)
    if hist.empty:
        return {"symbol": symbol, "price": None, "source": "yfinance"}
    last = hist.dropna().iloc[-1]
    return {
        "symbol": symbol,
        "price": float(last["Close"]),
        "time": hist.dropna().index[-1].isoformat(),
        "source": "yfinance",
    }


def fetch_options_chain(symbol: str, max_expirations: int = 3) -> dict[str, Any]:
    """Fetch a lightweight options chain snapshot.

    Returns calls/puts for the nearest expirations. This is not an execution feed.
    """
    symbol = clean_symbol(symbol)
    ticker = yf.Ticker(symbol)
    expirations = list(ticker.options or [])[:max_expirations]
    chains: list[dict[str, Any]] = []
    for expiration in expirations:
        try:
            chain = ticker.option_chain(expiration)
            calls = chain.calls.copy()
            puts = chain.puts.copy()
            for side_name, df in [("call", calls), ("put", puts)]:
                cols = [
                    col
                    for col in [
                        "contractSymbol",
                        "lastTradeDate",
                        "strike",
                        "lastPrice",
                        "bid",
                        "ask",
                        "change",
                        "percentChange",
                        "volume",
                        "openInterest",
                        "impliedVolatility",
                    ]
                    if col in df.columns
                ]
                records = df[cols].fillna(0).to_dict(orient="records")
                chains.append({"expiration": expiration, "side": side_name, "contracts": records})
        except Exception as exc:  # yfinance can fail on individual expirations.
            chains.append({"expiration": expiration, "error": str(exc), "contracts": []})
    return {"symbol": symbol, "expirations": expirations, "chains": chains, "source": "yfinance"}


def _parse_dt(value: Any) -> str:
    if not value:
        return datetime.now(UTC).isoformat()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, UTC).isoformat()
    if isinstance(value, str):
        try:
            parsed = pd.to_datetime(value, utc=True)
            return parsed.isoformat()
        except Exception:
            return datetime.now(UTC).isoformat()
    return datetime.now(UTC).isoformat()


def fetch_yahoo_rss_news(symbols: list[str], limit_per_symbol: int = 10) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    targets = [clean_symbol(s) for s in symbols if s.strip()]
    if not targets:
        targets = ["SPY", "QQQ"]

    for symbol in targets:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote_plus(symbol)}&region=US&lang=en-US"
        feed = feedparser.parse(url)
        for entry in feed.entries[:limit_per_symbol]:
            published = getattr(entry, "published", None) or getattr(entry, "updated", None)
            items.append(
                {
                    "provider": "Yahoo Finance RSS",
                    "symbol": symbol,
                    "headline": getattr(entry, "title", "").strip(),
                    "summary": getattr(entry, "summary", "").strip(),
                    "url": getattr(entry, "link", ""),
                    "published_at": _parse_dt(published),
                }
            )
    return items


def fetch_finnhub_news(symbols: list[str], days_back: int = 3) -> list[dict[str, Any]]:
    if not settings.finnhub_api_key:
        return []
    items: list[dict[str, Any]] = []
    today = datetime.now(UTC).date()
    frm = (today - timedelta(days=days_back)).isoformat()
    to = today.isoformat()
    for symbol in [clean_symbol(s) for s in symbols if s.strip()]:
        url = "https://finnhub.io/api/v1/company-news"
        params = {"symbol": symbol, "from": frm, "to": to, "token": settings.finnhub_api_key}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            for row in response.json()[:30]:
                items.append(
                    {
                        "provider": "Finnhub",
                        "symbol": symbol,
                        "headline": row.get("headline", ""),
                        "summary": row.get("summary", ""),
                        "url": row.get("url", ""),
                        "published_at": _parse_dt(row.get("datetime")),
                        "source": row.get("source", ""),
                    }
                )
        except Exception as exc:
            items.append(
                {
                    "provider": "Finnhub",
                    "symbol": symbol,
                    "headline": f"Finnhub error for {symbol}",
                    "summary": str(exc),
                    "url": "",
                    "published_at": datetime.now(UTC).isoformat(),
                    "error": True,
                }
            )
    return items


def fetch_alpha_vantage_news(symbols: list[str], limit: int = 50) -> list[dict[str, Any]]:
    if not settings.alpha_vantage_api_key:
        return []
    tickers = ",".join(clean_symbol(s) for s in symbols if s.strip()) or "SPY,QQQ"
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": tickers,
        "apikey": settings.alpha_vantage_api_key,
        "limit": str(limit),
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        feed = payload.get("feed", [])
    except Exception as exc:
        return [
            {
                "provider": "Alpha Vantage",
                "symbol": tickers,
                "headline": "Alpha Vantage error",
                "summary": str(exc),
                "url": "",
                "published_at": datetime.now(UTC).isoformat(),
                "error": True,
            }
        ]

    items: list[dict[str, Any]] = []
    for row in feed[:limit]:
        ticker_sentiment = row.get("ticker_sentiment") or []
        related = ",".join(ts.get("ticker", "") for ts in ticker_sentiment if ts.get("ticker"))
        items.append(
            {
                "provider": "Alpha Vantage",
                "symbol": related or tickers,
                "headline": row.get("title", ""),
                "summary": row.get("summary", ""),
                "url": row.get("url", ""),
                "published_at": _parse_dt(row.get("time_published")),
                "overall_sentiment_score": row.get("overall_sentiment_score"),
                "overall_sentiment_label": row.get("overall_sentiment_label"),
            }
        )
    return items


def fetch_newsapi_news(symbols: list[str], limit: int = 20) -> list[dict[str, Any]]:
    if not settings.newsapi_key:
        return []
    query = " OR ".join(clean_symbol(s) for s in symbols if s.strip()) or "SPY OR QQQ"
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": str(min(limit, 100)),
        "apiKey": settings.newsapi_key,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        articles = response.json().get("articles", [])
    except Exception as exc:
        return [
            {
                "provider": "NewsAPI",
                "symbol": query,
                "headline": "NewsAPI error",
                "summary": str(exc),
                "url": "",
                "published_at": datetime.now(UTC).isoformat(),
                "error": True,
            }
        ]
    return [
        {
            "provider": "NewsAPI",
            "symbol": query,
            "headline": row.get("title", ""),
            "summary": row.get("description", "") or row.get("content", ""),
            "url": row.get("url", ""),
            "published_at": _parse_dt(row.get("publishedAt")),
            "source": (row.get("source") or {}).get("name", ""),
        }
        for row in articles
    ]


def fetch_all_news(symbols: list[str]) -> list[dict[str, Any]]:
    yahoo = fetch_yahoo_rss_news(symbols)
    finnhub = fetch_finnhub_news(symbols)
    alpha = fetch_alpha_vantage_news(symbols)
    newsapi = fetch_newsapi_news(symbols)
    return yahoo + finnhub + alpha + newsapi
