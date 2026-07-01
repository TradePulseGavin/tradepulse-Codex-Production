from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .data_providers import fetch_all_news

CATEGORY_KEYWORDS = {
    "Breaking / High Impact": [
        "breaking",
        "halt",
        "suspend",
        "crash",
        "plunge",
        "surge",
        "unexpected",
        "emergency",
        "bankruptcy",
        "guidance cut",
        "warning",
    ],
    "Macro / Economy": [
        "fed",
        "federal reserve",
        "powell",
        "cpi",
        "ppi",
        "inflation",
        "jobs report",
        "unemployment",
        "gdp",
        "tariff",
        "rates",
        "yield",
        "treasury",
    ],
    "Earnings / Guidance": [
        "earnings",
        "revenue",
        "eps",
        "guidance",
        "quarter",
        "forecast",
        "profit",
        "sales miss",
        "beats estimates",
    ],
    "Analyst / Ratings": [
        "upgrade",
        "downgrade",
        "price target",
        "analyst",
        "initiates",
        "rating",
        "overweight",
        "underweight",
    ],
    "Legal / Regulatory / SEC": [
        "sec",
        "doj",
        "ftc",
        "lawsuit",
        "probe",
        "investigation",
        "regulator",
        "settlement",
        "fine",
    ],
    "M&A / Deals": [
        "acquisition",
        "merger",
        "buyout",
        "deal",
        "takeover",
        "stake",
        "partnership",
    ],
    "Options / Flow": [
        "options",
        "call options",
        "put options",
        "unusual activity",
        "open interest",
        "implied volatility",
    ],
    "Sector / Industry": [
        "semiconductor",
        "ai chip",
        "ev",
        "energy",
        "banks",
        "retail",
        "software",
        "cloud",
        "oil",
    ],
    "Crypto / Digital Assets": [
        "bitcoin",
        "ethereum",
        "crypto",
        "blockchain",
        "coinbase",
        "solana",
        "etf inflows",
    ],
}

POSITIVE_WORDS = {
    "beat",
    "beats",
    "raise",
    "raises",
    "raised",
    "surge",
    "surges",
    "upgrade",
    "upgraded",
    "record",
    "approval",
    "growth",
    "profit",
    "strong",
    "partnership",
}
NEGATIVE_WORDS = {
    "miss",
    "misses",
    "cut",
    "cuts",
    "downgrade",
    "downgraded",
    "lawsuit",
    "probe",
    "investigation",
    "plunge",
    "falls",
    "warning",
    "bankruptcy",
    "weak",
    "loss",
}


def categorize_item(item: dict[str, Any]) -> list[str]:
    text = f"{item.get('headline', '')} {item.get('summary', '')}".lower()
    matches: list[str] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            matches.append(category)
    if not matches:
        matches.append("Company / General Market")
    return matches


def sentiment(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("overall_sentiment_label"):
        return {
            "label": item.get("overall_sentiment_label"),
            "score": item.get("overall_sentiment_score"),
            "source": "provider",
        }
    words = set(f"{item.get('headline', '')} {item.get('summary', '')}".lower().replace("/", " ").split())
    score = sum(word in POSITIVE_WORDS for word in words) - sum(word in NEGATIVE_WORDS for word in words)
    if score >= 2:
        label = "positive"
    elif score <= -2:
        label = "negative"
    else:
        label = "neutral"
    return {"label": label, "score": score, "source": "keyword"}


def urgency(item: dict[str, Any]) -> str:
    if item.get("error"):
        return "provider-error"
    text = f"{item.get('headline', '')} {item.get('summary', '')}".lower()
    published_raw = item.get("published_at")
    try:
        published = datetime.fromisoformat(str(published_raw).replace("Z", "+00:00"))
        age_minutes = (datetime.now(UTC) - published.astimezone(UTC)).total_seconds() / 60
    except Exception:
        age_minutes = 9999
    high_keywords = CATEGORY_KEYWORDS["Breaking / High Impact"]
    if age_minutes <= 20 or any(k in text for k in high_keywords):
        return "instant-watch"
    if age_minutes <= 180:
        return "current"
    if age_minutes <= 1440:
        return "latest"
    return "background"


def dedupe_news(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        key = (item.get("headline") or "").strip().lower()[:140]
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def build_news_brief(symbols: list[str]) -> dict[str, Any]:
    raw_items = fetch_all_news(symbols)
    items = dedupe_news(raw_items)
    enriched: list[dict[str, Any]] = []
    for item in items:
        enriched.append(
            {
                **item,
                "categories": categorize_item(item),
                "sentiment": sentiment(item),
                "urgency": urgency(item),
            }
        )
    enriched.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    by_category: dict[str, list[dict[str, Any]]] = {}
    by_urgency: dict[str, list[dict[str, Any]]] = {
        "instant-watch": [],
        "current": [],
        "latest": [],
        "background": [],
        "provider-error": [],
    }
    for item in enriched:
        by_urgency.setdefault(item["urgency"], []).append(item)
        for category in item["categories"]:
            by_category.setdefault(category, []).append(item)

    return {
        "symbols": symbols,
        "generated_at": datetime.now(UTC).isoformat(),
        "items": enriched[:80],
        "by_category": {k: v[:15] for k, v in by_category.items()},
        "by_urgency": {k: v[:15] for k, v in by_urgency.items()},
        "enabled_providers": sorted({item.get("provider", "unknown") for item in enriched}),
    }
