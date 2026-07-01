# TradePulse Phase 1 Product Update

This update turns the basic hosted scanner into the first product version of TradePulse.

## Added

- Landing page at `/`
- Pricing page at `/pricing`
- Dashboard moved to `/dashboard`
- Login/signup pages using Supabase client-side auth
- Account page placeholder
- Stripe Checkout route at `/billing/checkout`
- Payment success page at `/billing/success`
- Free/Pro plan copy
- Updated `.env.example`
- Added `stripe` to requirements

## Important

This is Phase 1. Stripe Checkout can open, but subscription status is not fully written back to Supabase yet. Phase 2 should add Stripe webhooks and Pro feature gating.

## Render environment variables needed

- SUPABASE_URL
- SUPABASE_PUBLISHABLE_KEY
- SUPABASE_SECRET_KEY
- STRIPE_PRICE_ID_PRO
- STRIPE_SECRET_KEY
- STRIPE_PUBLISHABLE_KEY
- PYTHON_VERSION=3.12.8

Optional but recommended:

- APP_BASE_URL=https://your-render-url.onrender.com
