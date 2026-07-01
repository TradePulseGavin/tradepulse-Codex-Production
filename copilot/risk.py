from __future__ import annotations

from dataclasses import dataclass

from .config import settings


@dataclass
class RiskDecision:
    allowed: bool
    reasons: list[str]
    max_contracts: int
    risk_per_trade_dollars: float
    suggested_stop_pct: float
    suggested_take_profit_pct: float


def evaluate_option_risk(option_ask: float | None, trades_today: int = 0, daily_pnl: float = 0.0) -> RiskDecision:
    reasons: list[str] = []
    allowed = True
    ask = float(option_ask or 0)

    if trades_today >= settings.max_trades_per_day:
        allowed = False
        reasons.append(f"Daily trade limit reached: {trades_today}/{settings.max_trades_per_day}.")
    if daily_pnl <= -abs(settings.max_daily_loss_dollars):
        allowed = False
        reasons.append(f"Daily max loss reached: ${daily_pnl:.2f}.")
    if ask <= 0:
        allowed = False
        reasons.append("No valid option ask price.")
    premium = ask * 100
    if premium > settings.max_option_premium_dollars:
        allowed = False
        reasons.append(
            f"Contract premium ${premium:.2f} is above max ${settings.max_option_premium_dollars:.2f}."
        )

    max_contracts = 0
    if ask > 0:
        max_contracts = max(0, int(settings.risk_per_trade_dollars / (ask * 100 * 0.25)))
        max_contracts = min(max_contracts, 1)  # Beginner guardrail: one contract max.

    if allowed and max_contracts < 1:
        allowed = False
        reasons.append("Risk budget is too small for even one contract at the suggested stop.")

    if allowed:
        reasons.append("Paper-trade risk rules passed. Still confirm manually before acting.")

    return RiskDecision(
        allowed=allowed,
        reasons=reasons,
        max_contracts=max_contracts,
        risk_per_trade_dollars=settings.risk_per_trade_dollars,
        suggested_stop_pct=0.25,
        suggested_take_profit_pct=0.40,
    )
