from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _csv_env(name: str) -> tuple[str, ...]:
    value = os.getenv(name, "")
    return tuple(item.strip().lower() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    default_symbols: tuple[str, ...]
    finnhub_api_key: str | None
    alpha_vantage_api_key: str | None
    newsapi_key: str | None
    alpaca_api_key: str | None
    alpaca_secret_key: str | None
    alpaca_paper_base_url: str
    enable_broker_orders: bool
    app_name: str
    app_base_url: str | None
    support_email: str | None
    supabase_url: str | None
    supabase_publishable_key: str | None
    supabase_secret_key: str | None
    stripe_publishable_key: str | None
    stripe_secret_key: str | None
    stripe_webhook_secret: str | None
    stripe_price_id_pro: str | None
    stripe_price_id_elite: str | None
    stripe_price_id_all_access: str | None
    owner_emails: tuple[str, ...]
    openai_api_key: str | None
    openai_model: str
    openai_base_url: str
    enable_real_market_data: bool
    max_trades_per_day: int
    max_daily_loss_dollars: int
    max_option_premium_dollars: int
    risk_per_trade_dollars: int


settings = Settings(
    app_name=os.getenv("APP_NAME", "TradePulse"),
    app_base_url=os.getenv("APP_BASE_URL") or None,
    support_email=os.getenv("APP_SUPPORT_EMAIL") or None,
    supabase_url=os.getenv("SUPABASE_URL") or None,
    supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or None,
    supabase_secret_key=os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None,
    stripe_publishable_key=os.getenv("STRIPE_PUBLISHABLE_KEY") or None,
    stripe_secret_key=os.getenv("STRIPE_SECRET_KEY") or None,
    stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET") or None,
    stripe_price_id_pro=os.getenv("STRIPE_PRICE_ID_PRO") or None,
    stripe_price_id_elite=os.getenv("STRIPE_PRICE_ID_ELITE") or None,
    stripe_price_id_all_access=os.getenv("STRIPE_PRICE_ID_ALL_ACCESS") or None,
    owner_emails=_csv_env("OWNER_EMAILS"),
    openai_api_key=os.getenv("OPENAI_API_KEY") or None,
    openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
    enable_real_market_data=_bool_env("ENABLE_REAL_MARKET_DATA", False),
    default_symbols=tuple(
        s.strip().upper()
        for s in os.getenv("DEFAULT_SYMBOLS", "SPY,QQQ,AAPL,NVDA,TSLA").split(",")
        if s.strip()
    ),
    finnhub_api_key=os.getenv("FINNHUB_API_KEY") or None,
    alpha_vantage_api_key=os.getenv("ALPHA_VANTAGE_API_KEY") or None,
    newsapi_key=os.getenv("NEWSAPI_KEY") or None,
    alpaca_api_key=os.getenv("ALPACA_API_KEY") or None,
    alpaca_secret_key=os.getenv("ALPACA_SECRET_KEY") or None,
    alpaca_paper_base_url=os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets"),
    enable_broker_orders=_bool_env("ENABLE_BROKER_ORDERS", False),
    max_trades_per_day=_int_env("MAX_TRADES_PER_DAY", 2),
    max_daily_loss_dollars=_int_env("MAX_DAILY_LOSS_DOLLARS", 100),
    max_option_premium_dollars=_int_env("MAX_OPTION_PREMIUM_DOLLARS", 250),
    risk_per_trade_dollars=_int_env("RISK_PER_TRADE_DOLLARS", 50),
)
