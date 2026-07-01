from __future__ import annotations

import json
import os
import py_compile
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PYTHON_FILES = [
    ROOT / "main.py",
    ROOT / "copilot" / "ai_provider.py",
    ROOT / "copilot" / "server.py",
    ROOT / "copilot" / "config.py",
    ROOT / "copilot" / "demo_data.py",
    ROOT / "copilot" / "local_store.py",
    ROOT / "copilot" / "market_data.py",
    ROOT / "copilot" / "memory_engine.py",
    ROOT / "copilot" / "supabase_store.py",
    ROOT / "copilot" / "strategy_engine.py",
    ROOT / "scripts" / "verify_production_readiness.py",
]

REQUIRED_ROUTES = {
    "/",
    "/favicon.ico",
    "/robots.txt",
    "/sitemap.xml",
    "/support",
    "/forgot-password",
    "/reset-password",
    "/onboarding",
    "/dashboard",
    "/watchlists",
    "/news",
    "/scanner",
    "/session-prep",
    "/review-center",
    "/progress",
    "/risk-lab",
    "/live-charts",
    "/copilot",
    "/screenshot-analyzer",
    "/alerts",
    "/paper-trade",
    "/journal",
    "/school",
    "/strategy-builder",
    "/settings",
    "/launch-center",
    "/business-plan",
    "/production-setup",
    "/risk-disclosure",
    "/privacy",
    "/terms",
    "/billing/portal",
    "/billing/webhook",
    "/api/system/status",
    "/api/providers/status",
    "/api/plans",
    "/api/plan-limits",
    "/api/usage",
    "/api/limit-check",
    "/api/launch-checklist",
    "/api/business-plan",
    "/api/production-readiness",
    "/api/onboarding-checklist",
    "/api/preferences",
    "/api/session-prep",
    "/api/review-center",
    "/api/progress",
    "/api/risk-lab",
    "/api/demo/dashboard",
    "/api/export/demo-state",
    "/api/export/account-data",
    "/api/account/data-request",
    "/api/support/ticket",
    "/api/news-impact",
    "/api/what-changed",
    "/api/chart-data",
    "/api/scanner",
    "/api/scanner/run",
    "/api/memory",
    "/api/alerts",
    "/api/alerts/evaluate",
    "/api/screenshot-analyzer",
    "/api/screenshot-reviews",
    "/api/paper-trades",
    "/api/paper-trades/review",
    "/api/paper-trades/journalize",
    "/api/journal",
    "/api/risk-rules",
    "/api/dashboard-layout",
    "/api/watchlists",
    "/api/watchlist-items",
    "/api/activity",
    "/api/school/progress",
}

REQUIRED_TEMPLATES = [
    "landing.html",
    "onboarding.html",
    "dashboard.html",
    "watchlists.html",
    "news.html",
    "scanner.html",
    "session_prep.html",
    "review_center.html",
    "progress.html",
    "risk_lab.html",
    "live_charts.html",
    "copilot.html",
    "screenshot_analyzer.html",
    "alerts.html",
    "paper_trade.html",
    "journal.html",
    "school.html",
    "strategy_builder.html",
    "settings.html",
    "launch_center.html",
    "business_plan.html",
    "production_setup.html",
    "risk_disclosure.html",
    "privacy.html",
    "terms.html",
    "support.html",
    "forgot_password.html",
    "reset_password.html",
    "not_found.html",
]

SMOKE_PATHS = [
    "/health",
    "/",
    "/favicon.ico",
    "/robots.txt",
    "/sitemap.xml",
    "/support",
    "/forgot-password",
    "/reset-password",
    "/onboarding",
    "/dashboard",
    "/watchlists",
    "/news",
    "/scanner",
    "/session-prep",
    "/review-center",
    "/progress",
    "/risk-lab",
    "/screenshot-analyzer",
    "/alerts",
    "/paper-trade",
    "/settings",
    "/launch-center",
    "/business-plan",
    "/production-setup",
    "/risk-disclosure",
    "/api/system/status",
    "/api/providers/status",
    "/api/plans",
    "/api/plan-limits",
    "/api/usage",
    "/api/limit-check",
    "/api/launch-checklist",
    "/api/business-plan",
    "/api/production-readiness",
    "/api/onboarding-checklist",
    "/api/demo/dashboard",
    "/api/export/demo-state",
    "/api/export/account-data",
    "/api/news-impact",
    "/api/what-changed",
    "/api/memory",
]


def ok(message: str) -> None:
    print(f"OK  {message}")


def fail(message: str) -> None:
    print(f"ERR {message}")
    raise SystemExit(1)


def compile_python() -> None:
    for file in PYTHON_FILES:
        if not file.exists():
            fail(f"missing {file.relative_to(ROOT)}")
        py_compile.compile(str(file), doraise=True)
    ok("Python files compile")


def check_templates() -> None:
    missing = [name for name in REQUIRED_TEMPLATES if not (ROOT / "templates" / name).exists()]
    if missing:
        fail(f"missing templates: {', '.join(missing)}")
    ok("Required templates exist")


def check_routes() -> None:
    sys.path.insert(0, str(ROOT))
    from main import app

    routes = {getattr(route, "path", "") for route in app.routes}
    missing = sorted(REQUIRED_ROUTES - routes)
    if missing:
        fail(f"missing routes: {', '.join(missing)}")
    ok(f"Route registry contains {len(app.routes)} routes")


def smoke_live_server(base_url: str) -> None:
    base = base_url.rstrip("/")
    for path in SMOKE_PATHS:
        with urllib.request.urlopen(base + path, timeout=10) as response:
            if response.status >= 400:
                fail(f"{path} returned {response.status}")
            if path.endswith("/api/system/status"):
                payload = json.loads(response.read().decode("utf-8"))
                if not payload.get("ok"):
                    fail("/api/system/status returned ok=false")
    ok(f"Live smoke check passed for {base}")


def main() -> None:
    compile_python()
    check_templates()
    check_routes()
    base_url = os.getenv("TRADEPULSE_VERIFY_BASE_URL")
    if base_url:
        smoke_live_server(base_url)
    else:
        ok("Skipped live HTTP checks; set TRADEPULSE_VERIFY_BASE_URL to enable them")


if __name__ == "__main__":
    main()
