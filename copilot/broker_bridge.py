from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from .config import settings
from .storage import save_snapshot


class BrokerSafetyError(RuntimeError):
    pass


def paper_order_preview(symbol: str, side: str, qty: int, limit_price: float, asset_class: str = "option") -> dict[str, Any]:
    """Create a saved preview. This never sends an order."""
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "mode": "preview_only",
        "asset_class": asset_class,
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "type": "limit",
        "limit_price": limit_price,
        "time_in_force": "day",
        "status": "not_sent",
    }
    payload["snapshot_id"] = save_snapshot("order_preview", payload)
    return payload


def submit_alpaca_paper_option_order(contract_symbol: str, side: str, qty: int, limit_price: float) -> dict[str, Any]:
    """Optional Alpaca PAPER order bridge.

    This refuses to run unless ENABLE_BROKER_ORDERS=true and a paper base URL is configured.
    It is intentionally paper-first. Do not change this to live without understanding the risk.
    """
    if not settings.enable_broker_orders:
        raise BrokerSafetyError("Broker orders are disabled. Set ENABLE_BROKER_ORDERS=true only for paper testing.")
    if "paper" not in settings.alpaca_paper_base_url.lower():
        raise BrokerSafetyError("Refusing to send orders to a non-paper Alpaca URL.")
    if not settings.alpaca_api_key or not settings.alpaca_secret_key:
        raise BrokerSafetyError("Missing Alpaca paper API keys.")
    if side.lower() not in {"buy", "sell"}:
        raise BrokerSafetyError("Side must be buy or sell.")
    if qty < 1:
        raise BrokerSafetyError("Quantity must be at least 1.")

    url = settings.alpaca_paper_base_url.rstrip("/") + "/v2/orders"
    headers = {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
        "Content-Type": "application/json",
    }
    order = {
        "symbol": contract_symbol,
        "qty": str(qty),
        "side": side.lower(),
        "type": "limit",
        "limit_price": str(limit_price),
        "time_in_force": "day",
    }
    response = requests.post(url, headers=headers, json=order, timeout=10)
    payload = {"request": order, "status_code": response.status_code, "response": response.json() if response.text else {}}
    save_snapshot("alpaca_paper_order", payload)
    response.raise_for_status()
    return payload
