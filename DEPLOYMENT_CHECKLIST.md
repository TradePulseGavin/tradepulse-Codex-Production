# TradePulse Deployment Checklist

Use this when moving the saved MVP into the real GitHub repo and Render service.

## Before Deploying

- Move the contents of this MVP copy into the real TradePulse repo.
- Confirm `main.py` still imports `copilot.server:app`.
- Confirm `requirements.txt`, `runtime.txt`, `render.yaml`, and `Procfile` are present.
- Copy `.env.example` into Render env vars manually; never commit real `.env` secrets.
- Keep `ENABLE_BROKER_ORDERS=false`.
- Run the Supabase migration: `supabase/migrations/001_tradepulse_mvp.sql`.
- Run `python scripts/verify_app.py` before pushing/deploying.
- Run `python scripts/verify_production_readiness.py` before turning on paid beta.

## Render Environment

Required for public auth:

- `APP_BASE_URL`
- `APP_SUPPORT_EMAIL`
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`

Required for subscriptions:

- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_ID_PRO`
- `STRIPE_PRICE_ID_ELITE`
- `STRIPE_PRICE_ID_ALL_ACCESS`
- `STRIPE_WEBHOOK_SECRET`
- `SUPABASE_SECRET_KEY`

Useful owner/admin setting:

- `OWNER_EMAILS`

Optional later:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `ENABLE_REAL_MARKET_DATA`
- `FINNHUB_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `NEWSAPI_KEY`

## Stripe

- Create Pro product/price at `$15/mo`.
- Create Elite product/price at `$25/mo`.
- Create All Access product/price at `$50/mo`.
- Add the Render webhook endpoint: `https://YOUR_DOMAIN/billing/webhook`.
- Subscribe to `checkout.session.completed`.
- Put the webhook signing secret in `STRIPE_WEBHOOK_SECRET`.
- Enable the Stripe customer portal so the Account page's Manage Billing button can open `/billing/portal` for real subscribers.

## Supabase

- Run the migration SQL.
- Confirm RLS is enabled on user data tables.
- Confirm `usage_events` and `screenshot_reviews` exist after running the migration.
- Confirm `account_data_requests` and `support_tickets` exist after running the migration.
- Confirm user signup/login works.
- Confirm `OWNER_EMAILS` gives All Access on `/account`.
- Confirm `/pricing`, `/api/plans`, `/api/plan-limits`, and `/account` show the same Free, Pro, Elite, and All Access limits.
- Confirm `/api/usage` and `/account` show expected usage meters for the active plan.
- Confirm `/api/limit-check` returns the expected upgrade guidance before turning on strict enforcement.
- Confirm `/onboarding` and `/api/onboarding-checklist` guide a new demo user through the first-session workflow.
- Confirm the `/account` demo plan selector changes local gates and usage meters while Supabase is not configured.
- Confirm `/account` can download account data and record a reviewed deletion request without deleting data automatically.
- Confirm `/support` can record a demo support request, then connect it to email/helpdesk before larger paid traffic.
- Confirm `/launch-center` and `/api/launch-checklist` show only expected production blockers.
- Confirm `/business-plan` reflects the current Free, Pro, Elite, and All Access pricing and launch blockers.
- Confirm `/production-setup` and `/api/production-readiness` show only expected missing production variables.
- Confirm journal/risk/layout/session prep/risk lab saves are in demo mode until Supabase keys are configured.
- Confirm Screenshot Analyzer returns a structured demo review and stores it in review history without claiming real image AI is connected.
- Confirm responses include the browser safety headers shown in Settings.
- Confirm `/robots.txt` points to `/sitemap.xml`, and `/sitemap.xml` uses the production `APP_BASE_URL`.
- Confirm `/forgot-password` sends Supabase reset emails and reset links return to `/reset-password`.
- Confirm paper trades, practice reviews, paper-to-journal links, and school progress save in demo mode, then in Supabase after migration/env setup.

## Smoke Test

After deploy, check:

- `/health`
- `/`
- `/onboarding`
- `/dashboard`
- `/watchlists`
- `/news`
- `/scanner`
- `/session-prep`
- `/review-center`
- `/progress`
- `/risk-lab`
- `/live-charts`
- `/copilot`
- `/screenshot-analyzer`
- `/alerts`
- `/paper-trade`
- `/journal`
- `/school`
- `/strategy-builder`
- `/settings`
- `/launch-center`
- `/business-plan`
- `/production-setup`
- `/api/demo/dashboard`
- `/api/export/demo-state`
- `/api/export/account-data`
- `/api/news-impact`
- `/api/what-changed`
- `/api/scanner`
- `/api/system/status`
- `/api/providers/status`
- `/api/plans`
- `/api/plan-limits`
- `/api/usage`
- `/api/limit-check`
- `/api/launch-checklist`
- `/api/business-plan`
- `/api/production-readiness`
- `/api/onboarding-checklist`
- `/api/account/data-request`
- `/api/support/ticket`
- `/api/preferences`
- `/api/watchlists`
- `/api/session-prep`
- `/api/review-center`
- `/api/progress`
- `/api/risk-lab`
- `/api/alerts`
- `/api/paper-trades/review`
- `/api/paper-trades/journalize`
- `/api/screenshot-reviews`
- `/risk-disclosure`
- `/privacy`
- `/terms`

TradePulse must stay framed as research, education, journaling, and risk review. It must not place trades or promise results.
