# TradePulse MVP Structure Upgrade

This copy contains the stable demo-first TradePulse command center structure. It preserves the existing FastAPI app shape, Stripe checkout route, Supabase client auth, and Render-compatible entrypoint.

## What changed

- copilot/server.py adds the new pages, Pro/Elite/All Access checkout plan routing, safe billing portal routing, owner access endpoint, and safe demo APIs for charts, watchlists, news research, scanner, Copilot, session prep, review center, progress center, risk lab, paper planning/review, paper-to-journal filing, journal, strategy builder, risk rules, demo backup export, news impact, and dashboard layout.
- copilot/config.py adds OWNER_EMAILS, OPENAI_API_KEY, STRIPE_PRICE_ID_ELITE, and STRIPE_PRICE_ID_ALL_ACCESS support.
- copilot/demo_data.py centralizes labeled demo/delayed data and responsible AI response placeholders.
- templates/*.html now includes onboarding, the premium dashboard, watchlists, news research, scanner, session prep, review center, progress center, risk lab, live charts, Copilot, screenshot analyzer, alerts, paper trade planner, journal/replay, school, strategy builder, launch center, account, auth confirmation, pricing, and billing pages.
- static/tradepulse.js runs the demo workspace: onboarding preferences, chart canvas with local annotation marks, panels, watchlist manager, news research, scanner, session prep, review queue, progress summary, risk lab calculations, Copilot, checklist, alerts, metadata-assisted screenshot reviews, paper plans, practice reviews, reviewed-plan journal filing, journal review, demo backup download, school quizzes, strategy builder, and explain popovers.
- static/auth_gate.js redirects logged-out users to login when Supabase is configured, and applies Free/Pro/Elite/All Access lock classes.
- static/auth.js and static/account.js polish auth redirects and account plan display.
- static/style.css replaces the UI layer with a tighter dark trading SaaS style.
- supabase/migrations/001_tradepulse_mvp.sql creates the MVP tables and RLS policies.
- copilot/supabase_store.py adds the Phase 2 Supabase REST helper for RLS-aware persistence.
- copilot/ai_provider.py adds the OpenAI research-response hook with safe mock fallback.
- copilot/market_data.py adds real-market-data chart/quote hooks with demo fallback.
- /billing/webhook adds the Stripe webhook scaffold for subscription sync, and /billing/portal safely falls back to the account page until Stripe customer portal data exists.
- /api/plans, /api/plan-limits, and /api/access expose the Free, Pro, Elite, and All Access feature/limit map for frontend plan gates and account visibility.
- /api/usage compares tracked demo usage against the visible plan limits, including watchlist symbols, scanner runs, Copilot prompts, alerts, journal entries, paper plans, screenshots, and saved strategies.
- /api/limit-check provides soft plan-limit guidance for actions before strict production enforcement is connected.
- /api/onboarding-checklist turns saved demo state into a first-session checklist for profile, watchlist, session prep, risk lab, paper plan, journal, and learning progress.
- Account includes a local demo plan simulator that stores the selected Free/Pro/Elite/All Access preview in browser storage so page gates, usage meters, and soft limit checks can be tested before Stripe/Supabase are live.
- Account also includes safe data controls: `/api/export/account-data` downloads the currently available account/demo data without secrets, and `/api/account/data-request` records reviewed export/delete/correction requests without automatically deleting data.
- Screenshot Analyzer now returns a structured demo review with setup quality, tags, level checks, indicator checks, chasing risk, and journal prompts from user notes while clearly stating that real image AI is not connected yet.
- /launch-center and /api/launch-checklist show the demo-ready vs public-launch checklist for Supabase, Stripe, AI, data, safety, and plan setup.
- /business-plan and /api/business-plan provide an internal operating plan for pricing, launch stages, support posture, safety rules, simple break-even examples, and next actions.
- /production-setup and /api/production-readiness turn the real-connection jump into an in-app setup board for Supabase, Stripe, OpenAI, market data, public URLs, support contact, and broker-safety checks.
- Basic browser safety headers are added to every response: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, and Permissions-Policy.
- /robots.txt and /sitemap.xml expose the public landing, pricing, risk, privacy, and terms pages for the hosted site.
- Unknown website URLs render a TradePulse 404 page, while missing API routes stay machine-readable JSON.
- Public landing/pricing pages include basic description/Open Graph metadata and a TradePulse SVG favicon.
- /forgot-password and /reset-password add the Supabase password recovery flow, with safe demo messaging when Supabase keys are not configured.
- /support gives public account, billing, password reset, privacy, and safety help with configurable support contact text, plus a safe demo support request form backed by `/api/support/ticket`.
- render.yaml, runtime.txt, Procfile, and .env.example prepare the app for Render.
- /risk-disclosure, /privacy, and /terms add launch-ready draft policy pages with configurable support contact text.
- scripts/verify_app.py provides a repeatable pre-deploy smoke check.
- scripts/verify_production_readiness.py prints a safe, no-secret production readiness summary for Supabase, Stripe, OpenAI, market data, public URLs, and safety gates.

## Current demo persistence

Demo mode now saves onboarding preferences, watchlist symbols, dashboard layout, alerts, session prep plans, risk lab scenarios, risk rules, journal entries, school quiz progress, saved strategies, screenshot reviews, account data requests, support tickets, paper trade plans, practice reviews, and paper-to-journal links to `data/demo_state.json`. The Onboarding page reads that state back as a first-session checklist. Supabase tables and API branches are prepared for these workflows when real auth/persistence is configured.

## Render environment variables

Required or existing:

- SUPABASE_URL
- SUPABASE_PUBLISHABLE_KEY or SUPABASE_ANON_KEY
- STRIPE_SECRET_KEY
- STRIPE_PUBLISHABLE_KEY
- STRIPE_PRICE_ID_PRO
- STRIPE_PRICE_ID_ELITE
- STRIPE_PRICE_ID_ALL_ACCESS
- APP_BASE_URL
- APP_SUPPORT_EMAIL

New optional variables:

- OWNER_EMAILS - comma-separated owner/admin emails that should see All Access
- OPENAI_API_KEY - optional for the later real AI upgrade; app uses mock research responses when missing
- OPENAI_MODEL - optional model override for the real AI research response
- OPENAI_BASE_URL - optional OpenAI-compatible API base URL
- ENABLE_REAL_MARKET_DATA - set true only when you want chart routes to request yfinance research candles
- ALPACA_API_KEY, ALPACA_SECRET_KEY, and ALPACA_PAPER_BASE_URL - reserved for a later broker-paper integration; keep ENABLE_BROKER_ORDERS=false
- SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY - needed for server-side Stripe subscription sync
- STRIPE_WEBHOOK_SECRET - needed for verified Stripe webhooks

## Safety posture

All analysis is framed as research, education, journaling, risk review, and setup quality. The app does not place trades, does not promise results, and does not issue trade instructions.

## Verify locally

Run:

`python scripts/verify_app.py`

If a local server is running, also run:

`TRADEPULSE_VERIFY_BASE_URL=http://127.0.0.1:8000 python scripts/verify_app.py`

Workflow smoke tests can run without pytest:

`python -m unittest tests.test_demo_workflows`

Production readiness can be checked without printing secrets:

`python scripts/verify_production_readiness.py`

## Local note

The original OneDrive repo path was readable but not writable from this Codex session. This upgraded copy was created under the writable Codex output folder so the work could continue without damaging the original app.
