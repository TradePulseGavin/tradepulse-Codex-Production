# TradePulse Phase 2 Persistence + Billing Scaffold

This phase turns the demo-first command center into a deploy-ready app skeleton with real persistence hooks.

## Added

- Supabase REST helper in `copilot/supabase_store.py`
- RLS-aware journal reads/writes through `/api/journal`
- RLS-aware paper trade plan reads/writes through `/api/paper-trades`
- RLS-aware paper practice reviews through `/api/paper-trades/review`
- RLS-aware reviewed-paper journal filing through `/api/paper-trades/journalize`
- RLS-aware risk rule save/load through `/api/risk-rules`
- RLS-aware dashboard layout save/load through `/api/dashboard-layout`
- RLS-aware alert rules through `/api/alerts`
- RLS-aware watchlist reads/writes through `/api/watchlists` and `/api/watchlist-items`
- RLS-aware session prep plans through `/api/session-prep`
- Computed daily review queue through `/api/review-center`
- Computed demo progress summary through `/api/progress`
- Local demo-state backup export through `/api/export/demo-state`
- RLS-aware risk lab scenarios through `/api/risk-lab`
- RLS-aware onboarding preferences through `/api/preferences`
- Strategy save endpoint through `/api/strategies`
- Watchlist endpoint scaffold through `/api/watchlists`
- School quiz progress endpoint through `/api/school/progress`
- User activity endpoint through `/api/activity`
- Server-backed plan lookup through `/api/access`
- Four-tier plan catalog through `/api/plans`
- Shared plan limits through `/api/plan-limits` and `/api/access`
- Usage and limit visibility through `/api/usage`
- RLS-aware usage event and screenshot review tables in the Supabase migration
- RLS-aware account data request and support ticket tables in the Supabase migration
- Stripe checkout metadata for Supabase `user_id`
- Stripe webhook scaffold at `/billing/webhook`
- Stripe customer portal route at `/billing/portal` with safe account-page fallback until a real customer subscription exists
- Stripe event audit table in the Supabase migration
- Safe OpenAI provider hook through `/api/copilot`
- Real-market-data chart hook through `/api/chart-data?live=true`
- Provider readiness endpoint through `/api/providers/status`
- Launch readiness center through `/launch-center` and `/api/launch-checklist`
- Production setup board through `/production-setup` and `/api/production-readiness`

## New Render env vars

- `SUPABASE_SECRET_KEY` or `SUPABASE_SERVICE_ROLE_KEY`
- `STRIPE_WEBHOOK_SECRET`

Existing vars still matter:

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY` or `SUPABASE_ANON_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_ID_PRO`
- `STRIPE_PRICE_ID_ELITE`
- `STRIPE_PRICE_ID_ALL_ACCESS`
- `OWNER_EMAILS`
- `APP_BASE_URL`
- `APP_SUPPORT_EMAIL`
- `OPENAI_API_KEY` optional for real AI research responses
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `ENABLE_REAL_MARKET_DATA`

## Behavior

When Supabase auth is configured, protected pages send the current user's session token to the backend. Supabase RLS controls what rows the user can read and write.

Plan gates stay server-owned: `/api/access` returns the visible plan, unlocked feature flags, and the matching limits used by the account page. `/api/plans` and `/api/plan-limits` expose the public catalog for pricing and deploy checks.

Usage visibility is now server-shaped too: `/api/usage` compares saved/demo activity against plan limits and the account page renders usage meters. Scanner runs and Copilot prompts are tracked as local demo usage events until real metering is connected.

The Supabase migration includes `usage_events` for real metering, `screenshot_reviews` for future authenticated screenshot review storage, `account_data_requests` for reviewed export/delete/correction workflows, and `support_tickets` for customer support intake. These tables are protected by RLS policies; public support submissions should flow through the backend rather than direct browser writes.

Limit behavior is wired as soft guidance: `/api/limit-check` and action responses return `limit_check` metadata that explains whether an action fits the visible plan and which plan unlocks it. Demo mode still returns results so the app remains testable.

Screenshot Analyzer is demo-useful before real image AI: `/api/screenshot-analyzer` creates a metadata-assisted review from the user's symbol, platform, filename, and notes, then saves it to local demo state or Supabase `screenshot_reviews` when auth is available.

Local plan simulation is available from `/account`: when Supabase is not configured, the selected demo plan is saved in browser storage and used by page gates, usage meters, and demo action payloads.

Launch readiness stays visible in the app: `/api/launch-checklist` combines Supabase, Stripe checkout, Stripe webhook, Stripe customer portal, AI, market data, safety, legal, and plan checks into a score and blocker list.

Production setup is now explicit too: `/api/production-readiness` lists the exact environment variables, hosted URLs, runtime modes, and next actions needed to connect Supabase accounts, Stripe subscriptions, OpenAI research, and market/news providers without exposing secret values.

Reviewed paper trades can be linked to journal entries through `paper_trades.journal_entry_id` and `trade_journal.source_id`, which keeps the review loop traceable without implying broker execution.

When Supabase credentials are missing, the app stays in safe demo mode instead of crashing.

When OpenAI or real market data are missing/off, the app keeps using safe mock AI responses and demo candles. When they are configured, responses are still framed as research, education, and risk review only.

When Stripe webhook secrets are missing, `/billing/webhook` returns a harmless placeholder response. Once configured, it verifies Stripe signatures and can update `subscriptions`. Manage Billing uses `/billing/portal`; without Stripe keys, a logged-in Supabase user, and a saved `stripe_customer_id`, it redirects back to `/account` with a clear status message instead of failing.

## Still manual

- Run `supabase/migrations/001_tradepulse_mvp.sql` in Supabase.
- Add the new Render env vars.
- Configure the Stripe webhook URL to `https://YOUR_DOMAIN/billing/webhook`.
- Deploy from the real GitHub repo once the OneDrive/write issue is resolved.
