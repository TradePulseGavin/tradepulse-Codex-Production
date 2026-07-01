from pathlib import Path
import asyncio
import json
import subprocess
import sys
import tempfile
import unittest

from starlette.requests import Request

import copilot.local_store as local_store
from copilot import server


def run(coro):
    return asyncio.run(coro)


def request_for(path="/", method="POST"):
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 123),
        }
    )


class DemoWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = local_store.DATA_DIR
        self.old_state_path = local_store.STATE_PATH
        local_store.DATA_DIR = Path(self.tmp.name)
        local_store.STATE_PATH = Path(self.tmp.name) / "demo_state.json"

    def tearDown(self):
        local_store.DATA_DIR = self.old_data_dir
        local_store.STATE_PATH = self.old_state_path
        self.tmp.cleanup()

    def test_paper_review_can_be_sent_to_journal(self):
        plan = run(
            server.api_paper_trades_save(
                payload={
                    "symbol": "IWM",
                    "asset_type": "ETF",
                    "direction": "Long",
                    "entry": "202.50",
                    "stop": "201.40",
                    "target": "205.20",
                    "position_size": "4",
                    "strategy": "Opening range demo",
                    "reason": "Practice review loop test",
                    "news": "Low",
                },
                authorization=None,
            )
        )
        trade_id = plan["item"]["id"]

        reviewed = run(
            server.api_paper_trades_review(
                payload={
                    "trade_id": trade_id,
                    "exit_price": "205.00",
                    "review_notes": "Followed the plan and waited for confirmation.",
                    "lesson_learned": "Keep the invalidation written before entry.",
                    "status": "reviewed",
                },
                authorization=None,
            )
        )
        journalized = run(server.api_paper_trades_journalize(payload={"trade_id": trade_id}, authorization=None))
        progress = run(server.api_progress())

        self.assertTrue(reviewed["ok"])
        self.assertTrue(journalized["ok"])
        self.assertEqual(journalized["journal_entry"]["source_id"], trade_id)
        self.assertEqual(progress["latest"]["paper_trade"]["journal_entry_id"], journalized["journal_entry"]["id"])

    def test_watchlist_manager_routes_save_symbols(self):
        page = run(server.watchlists_page(None))
        created = run(server.api_watchlists_save(payload={"name": "Swing research"}, authorization=None))
        watchlist_id = created["watchlist"]["id"]
        saved = run(
            server.api_watchlist_items_save(
                payload={"watchlist_id": watchlist_id, "symbol": "MSFT", "asset_type": "stock", "notes": "Demo test"},
                authorization=None,
            )
        )
        watchlists = run(server.api_watchlists(authorization=None))["watchlists"]

        self.assertEqual(page.status_code, 200)
        self.assertEqual(saved["item"]["symbol"], "MSFT")
        self.assertTrue(
            any(
                item.get("symbol") == "MSFT"
                for watchlist in watchlists
                for item in (watchlist.get("items") or watchlist.get("watchlist_items") or [])
            )
        )

    def test_onboarding_checklist_guides_first_session(self):
        page = run(server.onboarding(None)).body.decode("utf-8")
        checklist = run(server.api_onboarding_checklist())
        by_key = {item["key"]: item for item in checklist["items"]}

        self.assertIn("onboarding-checklist", page)
        self.assertTrue(checklist["ok"])
        self.assertEqual(checklist["total"], 7)
        self.assertTrue(by_key["profile"]["ready"])
        self.assertTrue(by_key["watchlist"]["ready"])
        self.assertEqual(checklist["next_item"]["key"], "session_prep")
        self.assertGreaterEqual(checklist["score"], 0)
        self.assertLessEqual(checklist["score"], 100)

    def test_demo_export_includes_counts_without_secrets(self):
        exported = run(server.api_export_demo_state())

        self.assertTrue(exported["ok"])
        self.assertEqual(exported["counts"]["watchlists"], 1)
        self.assertIn("state", exported)
        self.assertIn("data_requests", exported["counts"])
        self.assertTrue(all(not key.lower().endswith("key") for key in exported["state"].keys()))

    def test_account_data_export_and_delete_request_are_safe(self):
        request = run(
            server.api_account_data_request(
                payload={"request_type": "delete", "email": "demo@example.com", "notes": "test request"},
                authorization=None,
            )
        )
        run(
            server.api_account_data_request(
                payload={"request_type": "export", "email": "other@example.com", "notes": "not this account"},
                authorization=None,
            )
        )
        run(
            server.api_support_ticket(
                payload={
                    "email": "demo@example.com",
                    "category": "account",
                    "subject": "Export",
                    "message": "Include this ticket.",
                }
            )
        )
        run(
            server.api_support_ticket(
                payload={
                    "email": "other@example.com",
                    "category": "technical",
                    "subject": "Other",
                    "message": "Do not include this ticket.",
                }
            )
        )
        exported = run(server.api_export_account_data(email="demo@example.com", user_id="demo-user", authorization=None))

        self.assertTrue(request["ok"])
        self.assertEqual(request["request"]["request_type"], "delete")
        self.assertEqual(request["request"]["status"], "received")
        self.assertIn("not automatic", request["message"])
        self.assertTrue(exported["ok"])
        self.assertFalse(exported["secrets_included"])
        self.assertEqual(exported["account"]["email"], "demo@example.com")
        self.assertEqual(exported["counts"]["data_requests"], 1)
        self.assertEqual(exported["counts"]["support_tickets"], 1)
        self.assertTrue(exported["data_requests"])
        self.assertTrue(exported["support_tickets"])
        self.assertNotIn("other@example.com", json.dumps(exported))

    def test_all_access_is_only_full_access_plan(self):
        pro = server._plan_features("pro")
        elite = server._plan_features("elite")
        all_access = server._plan_features("all_access")
        catalog = run(server.api_plans())["plans"]
        plan_limits = run(server.api_plan_limits())["limits"]

        self.assertTrue(pro["scanner"])
        self.assertFalse(pro["live_charts"])
        self.assertTrue(elite["live_charts"])
        self.assertFalse(elite["strategy_builder"])
        self.assertFalse(elite["screenshot_analyzer"])
        self.assertTrue(all_access["strategy_builder"])
        self.assertTrue(all_access["screenshot_analyzer"])
        self.assertTrue(all_access["full_ai_data"])
        self.assertEqual([plan["id"] for plan in catalog], ["free", "pro", "elite", "all_access"])
        self.assertEqual(catalog[-1]["price"], "$50/mo")
        self.assertEqual(catalog[1]["limits"]["watchlist_symbols"], 50)
        self.assertEqual(plan_limits["elite"]["scanner_runs_per_day"], 250)
        self.assertEqual(plan_limits["all_access"]["watchlist_symbols"], "Unlimited")
        self.assertEqual(catalog[-1]["limits"]["screenshot_reviews"], "Included")

    def test_premium_pages_have_required_feature_markers(self):
        screenshot = run(server.screenshot_analyzer(None)).body.decode("utf-8")
        strategy = run(server.strategy_builder(None)).body.decode("utf-8")
        live = run(server.live_charts(None)).body.decode("utf-8")

        self.assertIn('data-required-feature="screenshot_analyzer"', screenshot)
        self.assertIn('data-required-feature="strategy_builder"', strategy)
        self.assertIn('data-required-feature="live_charts"', live)
        self.assertIn('data-tool="clear"', live)
        self.assertNotIn("Trendline placeholder", live)

    def test_screenshot_analyzer_returns_structured_demo_review(self):
        analysis = run(
            server.api_screenshot_analyzer(
                payload={
                    "filename": "spy-vwap.png",
                    "symbol": "SPY",
                    "platform": "TradingView",
                    "notes": "Breakout above VWAP near resistance with strong volume.",
                },
                authorization=None,
            )
        )
        reviews = run(server.api_screenshot_reviews(authorization=None))["items"]

        self.assertTrue(analysis["ok"])
        self.assertEqual(analysis["ai_provider"], "Safe demo screenshot reviewer")
        self.assertFalse(analysis["image_ai_connected"])
        self.assertGreaterEqual(analysis["setup_quality"], 1)
        self.assertIn("Bullish context", analysis["review_tags"])
        self.assertIn("Save the screenshot", analysis["journal_prompt"])
        self.assertTrue(reviews)

    def test_launch_checklist_tracks_required_blockers(self):
        payload = run(server.api_launch_checklist())
        titles = [item["title"] for item in payload["items"]]
        blocker_titles = [item["title"] for item in payload["blockers"]]

        self.assertTrue(payload["ok"])
        self.assertIn(payload["mode"], {"demo-ready", "launch-ready"})
        self.assertIn("Supabase login keys", titles)
        self.assertIn("Stripe checkout core", titles)
        self.assertIn("Stripe customer portal", titles)
        self.assertIn("Account data controls", titles)
        self.assertIn("Support contact", titles)
        self.assertIn("Security headers", titles)
        self.assertIn("Broker execution disabled", titles)
        self.assertTrue(all(title in titles for title in blocker_titles))
        self.assertTrue(all(item["required_for_public_launch"] for item in payload["blockers"]))
        self.assertGreaterEqual(payload["score"], 0)
        self.assertLessEqual(payload["score"], 100)

    def test_business_plan_page_tracks_pricing_and_launch_model(self):
        page = run(server.business_plan_page(None)).body.decode("utf-8")
        payload = run(server.api_business_plan())

        self.assertIn("Business Plan", page)
        self.assertIn("/api/business-plan", Path(__file__).resolve().parents[1].joinpath("static", "tradepulse.js").read_text(encoding="utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["offer"]["full_access_plan"], "all_access")
        self.assertEqual([plan["price"] for plan in payload["offer"]["plans"]], ["$0/mo", "$15/mo", "$25/mo", "$50/mo"])
        self.assertIn("broker execution", " ".join(payload["risk_controls"]).lower())
        self.assertTrue(payload["unit_economics"]["break_even_examples"])

    def test_production_setup_tracks_real_connection_requirements(self):
        page = run(server.production_setup_page(None)).body.decode("utf-8")
        payload = run(server.api_production_readiness(request_for("/api/production-readiness", method="GET")))
        keys = [item["key"] for item in payload["items"]]

        self.assertIn("Production Setup", page)
        self.assertIn("/api/production-readiness", Path(__file__).resolve().parents[1].joinpath("static", "tradepulse.js").read_text(encoding="utf-8"))
        self.assertTrue(payload["ok"])
        self.assertIn("SUPABASE_URL", keys)
        self.assertIn("STRIPE_WEBHOOK_SECRET", keys)
        self.assertIn("OPENAI_API_KEY", keys)
        self.assertIn("ENABLE_REAL_MARKET_DATA", keys)
        self.assertIn("ENABLE_BROKER_ORDERS", keys)
        self.assertIn("/billing/webhook", payload["urls"]["stripe_webhook_url"])
        self.assertEqual(payload["runtime_modes"]["ai"], "safe-mock")
        self.assertTrue(any("secret keys" in note for note in payload["safe_notes"]))

    def test_production_readiness_script_prints_safe_summary(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / "scripts" / "verify_production_readiness.py")],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("TradePulse production readiness", result.stdout)
        self.assertIn("Runtime modes", result.stdout)
        self.assertNotIn("sk_", result.stdout)
        self.assertNotIn("whsec_", result.stdout)

    def test_usage_tracks_demo_runs_against_plan_limits(self):
        run(server.api_scanner_run(payload={"symbols": "SPY,QQQ"}))
        run(server.api_copilot(payload={"prompt": "Review my demo watchlist."}))
        usage = run(server.api_usage(plan="pro", authorization=None))
        by_key = {item["key"]: item for item in usage["items"]}

        self.assertTrue(usage["ok"])
        self.assertEqual(usage["plan"], "pro")
        self.assertEqual(by_key["scanner_runs_per_day"]["used"], 1)
        self.assertEqual(by_key["scanner_runs_per_day"]["limit"], 75)
        self.assertEqual(by_key["copilot_prompts_per_day"]["used"], 1)
        self.assertEqual(by_key["watchlist_symbols"]["used"], 5)
        self.assertEqual(usage["summary"], "All tracked usage is inside this plan.")

    def test_limit_checks_explain_upgrade_path_without_blocking_demo(self):
        free_alert = run(server.api_limit_check(action="alert", plan="free"))
        scanner = run(server.api_scanner_run(payload={"symbols": "SPY", "plan": "free"}))
        strategy = run(server.api_strategies_save(payload={"name": "Demo strategy", "plan": "elite"}, authorization=None))

        self.assertFalse(free_alert["check"]["allowed"])
        self.assertEqual(free_alert["check"]["upgrade_plan"], "pro")
        self.assertIn("limit_check", scanner)
        self.assertTrue(scanner["limit_check"]["allowed"])
        self.assertIn("limit_check", strategy)
        self.assertFalse(strategy["limit_check"]["allowed"])
        self.assertEqual(strategy["limit_check"]["upgrade_plan"], "all_access")

    def test_account_page_exposes_demo_plan_simulator(self):
        page = run(server.account(None)).body.decode("utf-8")

        self.assertIn('id="demo-plan-select"', page)
        self.assertIn('id="download-account-data"', page)
        self.assertIn('id="request-account-delete"', page)
        self.assertIn('value="free"', page)
        self.assertIn('value="all_access"', page)
        self.assertIn('action="/billing/portal"', page)
        self.assertIn('/business-plan', page)

    def test_policy_pages_use_configurable_support_contact(self):
        privacy = run(server.privacy(None)).body.decode("utf-8")
        terms = run(server.terms(None)).body.decode("utf-8")

        self.assertIn("Add APP_SUPPORT_EMAIL before public launch", privacy)
        self.assertIn("Add APP_SUPPORT_EMAIL before public launch", terms)
        self.assertNotIn("Add your support email here", privacy)

    def test_security_headers_are_registered(self):
        self.assertEqual(server.SECURITY_HEADERS["X-Content-Type-Options"], "nosniff")
        self.assertIn("Permissions-Policy", server.SECURITY_HEADERS)

    def test_public_discovery_files_render(self):
        robots = run(server.robots_txt(request_for("/robots.txt", method="GET"))).body.decode("utf-8")
        sitemap = run(server.sitemap_xml(request_for("/sitemap.xml", method="GET"))).body.decode("utf-8")

        self.assertIn("User-agent: *", robots)
        self.assertIn("/sitemap.xml", robots)
        self.assertIn("<urlset", sitemap)
        self.assertIn("/pricing", sitemap)
        self.assertIn("/support", sitemap)
        self.assertIn("/privacy", sitemap)

    def test_not_found_template_is_user_friendly(self):
        page = server._render_template("not_found.html", status_code=404)
        body = page.body.decode("utf-8")

        self.assertEqual(page.status_code, 404)
        self.assertIn("Page not found", body)
        self.assertIn("/dashboard", body)

    def test_public_pages_include_share_metadata_and_favicon(self):
        landing = run(server.landing(None)).body.decode("utf-8")
        pricing = run(server.pricing(None)).body.decode("utf-8")
        favicon = Path(__file__).resolve().parents[1] / "static" / "favicon.svg"

        self.assertTrue(favicon.exists())
        self.assertIn('meta name="description"', landing)
        self.assertIn('property="og:title"', landing)
        self.assertIn('/static/favicon.svg', pricing)

    def test_password_reset_pages_are_available(self):
        login = run(server.login(None)).body.decode("utf-8")
        forgot = run(server.forgot_password(None)).body.decode("utf-8")
        reset = run(server.reset_password(None)).body.decode("utf-8")

        self.assertIn("/forgot-password", login)
        self.assertIn("password-reset-request-form", forgot)
        self.assertIn("password-update-form", reset)
        self.assertIn("password_reset.js", forgot)

    def test_support_page_is_public_and_linked(self):
        support = run(server.support(None)).body.decode("utf-8")
        landing = run(server.landing(None)).body.decode("utf-8")

        self.assertIn("Get help with TradePulse", support)
        self.assertIn("/forgot-password", support)
        self.assertIn("support-ticket-form", support)
        self.assertIn("support.js", support)
        self.assertIn("/support", landing)

    def test_support_ticket_endpoint_records_demo_request(self):
        missing = run(server.api_support_ticket(payload={"message": ""}))
        ticket = run(
            server.api_support_ticket(
                payload={
                    "email": "demo@example.com",
                    "category": "billing",
                    "subject": "Plan question",
                    "message": "Can you check my demo plan?",
                }
            )
        )
        exported = run(server.api_export_demo_state())

        self.assertFalse(missing["ok"])
        self.assertTrue(ticket["ok"])
        self.assertEqual(ticket["ticket"]["category"], "billing")
        self.assertEqual(ticket["ticket"]["status"], "received")
        self.assertEqual(exported["counts"]["support_tickets"], 1)

    def test_billing_portal_is_safe_without_stripe(self):
        old_secret = server.settings.stripe_secret_key
        object.__setattr__(server.settings, "stripe_secret_key", "")
        try:
            response = run(server.billing_portal(request_for("/billing/portal"), user_id=None))
        finally:
            object.__setattr__(server.settings, "stripe_secret_key", old_secret)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/account?billing=portal_demo")

    def test_supabase_migration_includes_usage_metering_tables(self):
        migration = (Path(__file__).resolve().parents[1] / "supabase" / "migrations" / "001_tradepulse_mvp.sql").read_text(encoding="utf-8")

        self.assertIn("create table if not exists public.usage_events", migration)
        self.assertIn("create table if not exists public.screenshot_reviews", migration)
        self.assertIn("create table if not exists public.account_data_requests", migration)
        self.assertIn("create table if not exists public.support_tickets", migration)
        self.assertIn("usage_events_own_select", migration)
        self.assertIn("screenshot_reviews_own_select", migration)
        self.assertIn("account_data_requests_own_select", migration)
        self.assertIn("support_tickets_own_select", migration)


if __name__ == "__main__":
    unittest.main()
