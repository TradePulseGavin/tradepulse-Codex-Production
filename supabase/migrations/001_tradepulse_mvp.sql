-- TradePulse MVP structure with row-level security.
-- Run this in the Supabase SQL editor for the project backing TradePulse.

create extension if not exists pgcrypto;

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  plan text default 'free' check (plan in ('free', 'pro', 'elite', 'all_access')),
  status text default 'active',
  stripe_customer_id text,
  stripe_subscription_id text,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

create table if not exists public.watchlists (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  name text not null,
  created_at timestamp with time zone default now()
);

create table if not exists public.watchlist_items (
  id uuid primary key default gen_random_uuid(),
  watchlist_id uuid references public.watchlists(id) on delete cascade not null,
  user_id uuid references auth.users(id) on delete cascade not null,
  symbol text not null,
  asset_type text default 'stock',
  notes text,
  created_at timestamp with time zone default now()
);

create table if not exists public.trade_journal (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  symbol text not null,
  asset_type text,
  direction text,
  entry_price numeric,
  exit_price numeric,
  stop_loss numeric,
  target_price numeric,
  position_size numeric,
  result text,
  pnl numeric,
  setup_type text,
  entry_reason text,
  exit_reason text,
  mistakes text,
  lesson_learned text,
  screenshot_url text,
  ai_summary text,
  source_type text,
  source_id uuid,
  created_at timestamp with time zone default now()
);

create table if not exists public.paper_trades (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  symbol text not null,
  asset_type text,
  direction text,
  entry numeric,
  stop numeric,
  target numeric,
  position_size numeric,
  invalidation text,
  strategy text,
  reason text,
  news text,
  status text default 'planned',
  checklist jsonb,
  exit_price numeric,
  pnl numeric,
  result text,
  review_notes text,
  lesson_learned text,
  mistake_tags text,
  reviewed_at timestamp with time zone,
  journal_entry_id uuid references public.trade_journal(id) on delete set null,
  journalized_at timestamp with time zone,
  created_at timestamp with time zone default now()
);

create table if not exists public.alert_rules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  symbol text not null,
  alert_type text default 'price',
  operator text default 'above',
  target_value text,
  notes text,
  enabled boolean default true,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

create table if not exists public.session_plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  session_label text,
  focus_symbols text,
  market_notes text,
  risk_notes text,
  rules_for_today text,
  avoid_conditions text,
  status text default 'planned',
  plan jsonb,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

create table if not exists public.risk_scenarios (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  symbol text,
  asset_type text,
  account_size numeric,
  entry numeric,
  stop numeric,
  target numeric,
  planned_size numeric,
  max_risk_dollars numeric,
  planned_risk numeric,
  reward_to_risk numeric,
  within_rules boolean default false,
  notes text,
  calculation jsonb,
  created_at timestamp with time zone default now()
);

create table if not exists public.strategy_rules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  name text not null,
  description text,
  entry_rules jsonb,
  exit_rules jsonb,
  avoid_rules jsonb,
  risk_rules jsonb,
  created_at timestamp with time zone default now()
);

create table if not exists public.screenshot_reviews (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  filename text,
  platform text,
  symbol text,
  notes text,
  payload jsonb,
  analysis jsonb,
  created_at timestamp with time zone default now()
);

create table if not exists public.risk_rules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  max_trades_per_day integer,
  max_losses_per_day integer,
  require_stop_loss boolean default true,
  avoid_news_minutes integer default 15,
  max_option_premium numeric,
  max_risk_per_trade numeric,
  require_checklist boolean default true,
  notes text,
  created_at timestamp with time zone default now()
);

create table if not exists public.dashboard_layouts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  layout jsonb not null,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

create table if not exists public.user_memory (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  memory_type text,
  summary text,
  source text,
  confidence numeric,
  created_at timestamp with time zone default now()
);

create table if not exists public.user_activity (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null unique,
  last_seen_at timestamp with time zone,
  last_dashboard_snapshot jsonb,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

create table if not exists public.usage_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  kind text not null,
  metadata jsonb default '{}'::jsonb,
  created_at timestamp with time zone default now()
);

create table if not exists public.user_preferences (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null unique,
  experience_level text default 'beginner',
  markets jsonb,
  platforms jsonb,
  risk_style text default 'conservative',
  default_symbols text,
  learning_goal text,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

create table if not exists public.account_data_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  request_type text default 'export' check (request_type in ('export', 'delete', 'correction')),
  email text,
  notes text,
  status text default 'received',
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

create table if not exists public.support_tickets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  category text default 'general' check (category in ('account', 'billing', 'privacy', 'technical', 'general')),
  email text,
  subject text,
  message text,
  status text default 'received',
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

create table if not exists public.school_progress (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  lesson_key text not null,
  status text default 'not_started',
  quiz_score numeric,
  updated_at timestamp with time zone default now(),
  unique (user_id, lesson_key)
);

create table if not exists public.stripe_webhook_events (
  id uuid primary key default gen_random_uuid(),
  stripe_event_id text unique,
  event_type text,
  payload jsonb,
  processed_at timestamp with time zone default now()
);

create unique index if not exists risk_rules_one_per_user on public.risk_rules(user_id);
create unique index if not exists dashboard_layouts_one_per_user on public.dashboard_layouts(user_id);
create index if not exists usage_events_user_kind_created_at on public.usage_events(user_id, kind, created_at desc);
create index if not exists screenshot_reviews_user_created_at on public.screenshot_reviews(user_id, created_at desc);
create index if not exists account_data_requests_user_created_at on public.account_data_requests(user_id, created_at desc);
create index if not exists support_tickets_user_created_at on public.support_tickets(user_id, created_at desc);
create index if not exists support_tickets_status_created_at on public.support_tickets(status, created_at desc);

alter table public.subscriptions drop constraint if exists subscriptions_plan_check;
alter table public.subscriptions add constraint subscriptions_plan_check check (plan in ('free', 'pro', 'elite', 'all_access'));

alter table public.paper_trades add column if not exists exit_price numeric;
alter table public.paper_trades add column if not exists pnl numeric;
alter table public.paper_trades add column if not exists result text;
alter table public.paper_trades add column if not exists review_notes text;
alter table public.paper_trades add column if not exists lesson_learned text;
alter table public.paper_trades add column if not exists mistake_tags text;
alter table public.paper_trades add column if not exists reviewed_at timestamp with time zone;
alter table public.paper_trades add column if not exists journal_entry_id uuid references public.trade_journal(id) on delete set null;
alter table public.paper_trades add column if not exists journalized_at timestamp with time zone;
alter table public.trade_journal add column if not exists source_type text;
alter table public.trade_journal add column if not exists source_id uuid;

alter table public.subscriptions enable row level security;
alter table public.watchlists enable row level security;
alter table public.watchlist_items enable row level security;
alter table public.trade_journal enable row level security;
alter table public.paper_trades enable row level security;
alter table public.alert_rules enable row level security;
alter table public.session_plans enable row level security;
alter table public.risk_scenarios enable row level security;
alter table public.strategy_rules enable row level security;
alter table public.screenshot_reviews enable row level security;
alter table public.risk_rules enable row level security;
alter table public.dashboard_layouts enable row level security;
alter table public.user_memory enable row level security;
alter table public.user_activity enable row level security;
alter table public.usage_events enable row level security;
alter table public.user_preferences enable row level security;
alter table public.account_data_requests enable row level security;
alter table public.support_tickets enable row level security;
alter table public.school_progress enable row level security;
alter table public.stripe_webhook_events enable row level security;

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists subscriptions_set_updated_at on public.subscriptions;
create trigger subscriptions_set_updated_at before update on public.subscriptions for each row execute function public.set_updated_at();

drop trigger if exists dashboard_layouts_set_updated_at on public.dashboard_layouts;
create trigger dashboard_layouts_set_updated_at before update on public.dashboard_layouts for each row execute function public.set_updated_at();

drop trigger if exists user_activity_set_updated_at on public.user_activity;
create trigger user_activity_set_updated_at before update on public.user_activity for each row execute function public.set_updated_at();

drop trigger if exists user_preferences_set_updated_at on public.user_preferences;
create trigger user_preferences_set_updated_at before update on public.user_preferences for each row execute function public.set_updated_at();

drop trigger if exists account_data_requests_set_updated_at on public.account_data_requests;
create trigger account_data_requests_set_updated_at before update on public.account_data_requests for each row execute function public.set_updated_at();

drop trigger if exists support_tickets_set_updated_at on public.support_tickets;
create trigger support_tickets_set_updated_at before update on public.support_tickets for each row execute function public.set_updated_at();

drop trigger if exists alert_rules_set_updated_at on public.alert_rules;
create trigger alert_rules_set_updated_at before update on public.alert_rules for each row execute function public.set_updated_at();

drop trigger if exists session_plans_set_updated_at on public.session_plans;
create trigger session_plans_set_updated_at before update on public.session_plans for each row execute function public.set_updated_at();

-- Policies are dropped first so this file can be re-run safely during development.
drop policy if exists subscriptions_own_select on public.subscriptions;
drop policy if exists subscriptions_own_insert on public.subscriptions;
drop policy if exists subscriptions_own_update on public.subscriptions;
drop policy if exists subscriptions_own_delete on public.subscriptions;
create policy subscriptions_own_select on public.subscriptions for select using (auth.uid() = user_id);
create policy subscriptions_own_insert on public.subscriptions for insert with check (auth.uid() = user_id);
create policy subscriptions_own_update on public.subscriptions for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy subscriptions_own_delete on public.subscriptions for delete using (auth.uid() = user_id);

drop policy if exists watchlists_own_select on public.watchlists;
drop policy if exists watchlists_own_insert on public.watchlists;
drop policy if exists watchlists_own_update on public.watchlists;
drop policy if exists watchlists_own_delete on public.watchlists;
create policy watchlists_own_select on public.watchlists for select using (auth.uid() = user_id);
create policy watchlists_own_insert on public.watchlists for insert with check (auth.uid() = user_id);
create policy watchlists_own_update on public.watchlists for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy watchlists_own_delete on public.watchlists for delete using (auth.uid() = user_id);

drop policy if exists watchlist_items_own_select on public.watchlist_items;
drop policy if exists watchlist_items_own_insert on public.watchlist_items;
drop policy if exists watchlist_items_own_update on public.watchlist_items;
drop policy if exists watchlist_items_own_delete on public.watchlist_items;
create policy watchlist_items_own_select on public.watchlist_items for select using (auth.uid() = user_id);
create policy watchlist_items_own_insert on public.watchlist_items for insert with check (auth.uid() = user_id);
create policy watchlist_items_own_update on public.watchlist_items for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy watchlist_items_own_delete on public.watchlist_items for delete using (auth.uid() = user_id);

drop policy if exists trade_journal_own_select on public.trade_journal;
drop policy if exists trade_journal_own_insert on public.trade_journal;
drop policy if exists trade_journal_own_update on public.trade_journal;
drop policy if exists trade_journal_own_delete on public.trade_journal;
create policy trade_journal_own_select on public.trade_journal for select using (auth.uid() = user_id);
create policy trade_journal_own_insert on public.trade_journal for insert with check (auth.uid() = user_id);
create policy trade_journal_own_update on public.trade_journal for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy trade_journal_own_delete on public.trade_journal for delete using (auth.uid() = user_id);

drop policy if exists paper_trades_own_select on public.paper_trades;
drop policy if exists paper_trades_own_insert on public.paper_trades;
drop policy if exists paper_trades_own_update on public.paper_trades;
drop policy if exists paper_trades_own_delete on public.paper_trades;
create policy paper_trades_own_select on public.paper_trades for select using (auth.uid() = user_id);
create policy paper_trades_own_insert on public.paper_trades for insert with check (auth.uid() = user_id);
create policy paper_trades_own_update on public.paper_trades for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy paper_trades_own_delete on public.paper_trades for delete using (auth.uid() = user_id);

drop policy if exists alert_rules_own_select on public.alert_rules;
drop policy if exists alert_rules_own_insert on public.alert_rules;
drop policy if exists alert_rules_own_update on public.alert_rules;
drop policy if exists alert_rules_own_delete on public.alert_rules;
create policy alert_rules_own_select on public.alert_rules for select using (auth.uid() = user_id);
create policy alert_rules_own_insert on public.alert_rules for insert with check (auth.uid() = user_id);
create policy alert_rules_own_update on public.alert_rules for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy alert_rules_own_delete on public.alert_rules for delete using (auth.uid() = user_id);

drop policy if exists session_plans_own_select on public.session_plans;
drop policy if exists session_plans_own_insert on public.session_plans;
drop policy if exists session_plans_own_update on public.session_plans;
drop policy if exists session_plans_own_delete on public.session_plans;
create policy session_plans_own_select on public.session_plans for select using (auth.uid() = user_id);
create policy session_plans_own_insert on public.session_plans for insert with check (auth.uid() = user_id);
create policy session_plans_own_update on public.session_plans for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy session_plans_own_delete on public.session_plans for delete using (auth.uid() = user_id);

drop policy if exists risk_scenarios_own_select on public.risk_scenarios;
drop policy if exists risk_scenarios_own_insert on public.risk_scenarios;
drop policy if exists risk_scenarios_own_update on public.risk_scenarios;
drop policy if exists risk_scenarios_own_delete on public.risk_scenarios;
create policy risk_scenarios_own_select on public.risk_scenarios for select using (auth.uid() = user_id);
create policy risk_scenarios_own_insert on public.risk_scenarios for insert with check (auth.uid() = user_id);
create policy risk_scenarios_own_update on public.risk_scenarios for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy risk_scenarios_own_delete on public.risk_scenarios for delete using (auth.uid() = user_id);

drop policy if exists strategy_rules_own_select on public.strategy_rules;
drop policy if exists strategy_rules_own_insert on public.strategy_rules;
drop policy if exists strategy_rules_own_update on public.strategy_rules;
drop policy if exists strategy_rules_own_delete on public.strategy_rules;
create policy strategy_rules_own_select on public.strategy_rules for select using (auth.uid() = user_id);
create policy strategy_rules_own_insert on public.strategy_rules for insert with check (auth.uid() = user_id);
create policy strategy_rules_own_update on public.strategy_rules for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy strategy_rules_own_delete on public.strategy_rules for delete using (auth.uid() = user_id);

drop policy if exists screenshot_reviews_own_select on public.screenshot_reviews;
drop policy if exists screenshot_reviews_own_insert on public.screenshot_reviews;
drop policy if exists screenshot_reviews_own_update on public.screenshot_reviews;
drop policy if exists screenshot_reviews_own_delete on public.screenshot_reviews;
create policy screenshot_reviews_own_select on public.screenshot_reviews for select using (auth.uid() = user_id);
create policy screenshot_reviews_own_insert on public.screenshot_reviews for insert with check (auth.uid() = user_id);
create policy screenshot_reviews_own_update on public.screenshot_reviews for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy screenshot_reviews_own_delete on public.screenshot_reviews for delete using (auth.uid() = user_id);

drop policy if exists risk_rules_own_select on public.risk_rules;
drop policy if exists risk_rules_own_insert on public.risk_rules;
drop policy if exists risk_rules_own_update on public.risk_rules;
drop policy if exists risk_rules_own_delete on public.risk_rules;
create policy risk_rules_own_select on public.risk_rules for select using (auth.uid() = user_id);
create policy risk_rules_own_insert on public.risk_rules for insert with check (auth.uid() = user_id);
create policy risk_rules_own_update on public.risk_rules for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy risk_rules_own_delete on public.risk_rules for delete using (auth.uid() = user_id);

drop policy if exists dashboard_layouts_own_select on public.dashboard_layouts;
drop policy if exists dashboard_layouts_own_insert on public.dashboard_layouts;
drop policy if exists dashboard_layouts_own_update on public.dashboard_layouts;
drop policy if exists dashboard_layouts_own_delete on public.dashboard_layouts;
create policy dashboard_layouts_own_select on public.dashboard_layouts for select using (auth.uid() = user_id);
create policy dashboard_layouts_own_insert on public.dashboard_layouts for insert with check (auth.uid() = user_id);
create policy dashboard_layouts_own_update on public.dashboard_layouts for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy dashboard_layouts_own_delete on public.dashboard_layouts for delete using (auth.uid() = user_id);

drop policy if exists user_memory_own_select on public.user_memory;
drop policy if exists user_memory_own_insert on public.user_memory;
drop policy if exists user_memory_own_update on public.user_memory;
drop policy if exists user_memory_own_delete on public.user_memory;
create policy user_memory_own_select on public.user_memory for select using (auth.uid() = user_id);
create policy user_memory_own_insert on public.user_memory for insert with check (auth.uid() = user_id);
create policy user_memory_own_update on public.user_memory for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy user_memory_own_delete on public.user_memory for delete using (auth.uid() = user_id);

drop policy if exists user_activity_own_select on public.user_activity;
drop policy if exists user_activity_own_insert on public.user_activity;
drop policy if exists user_activity_own_update on public.user_activity;
drop policy if exists user_activity_own_delete on public.user_activity;
create policy user_activity_own_select on public.user_activity for select using (auth.uid() = user_id);
create policy user_activity_own_insert on public.user_activity for insert with check (auth.uid() = user_id);
create policy user_activity_own_update on public.user_activity for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy user_activity_own_delete on public.user_activity for delete using (auth.uid() = user_id);

drop policy if exists usage_events_own_select on public.usage_events;
drop policy if exists usage_events_own_insert on public.usage_events;
drop policy if exists usage_events_own_update on public.usage_events;
drop policy if exists usage_events_own_delete on public.usage_events;
create policy usage_events_own_select on public.usage_events for select using (auth.uid() = user_id);
create policy usage_events_own_insert on public.usage_events for insert with check (auth.uid() = user_id);
create policy usage_events_own_update on public.usage_events for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy usage_events_own_delete on public.usage_events for delete using (auth.uid() = user_id);

drop policy if exists user_preferences_own_select on public.user_preferences;
drop policy if exists user_preferences_own_insert on public.user_preferences;
drop policy if exists user_preferences_own_update on public.user_preferences;
drop policy if exists user_preferences_own_delete on public.user_preferences;
create policy user_preferences_own_select on public.user_preferences for select using (auth.uid() = user_id);
create policy user_preferences_own_insert on public.user_preferences for insert with check (auth.uid() = user_id);
create policy user_preferences_own_update on public.user_preferences for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy user_preferences_own_delete on public.user_preferences for delete using (auth.uid() = user_id);

drop policy if exists school_progress_own_select on public.school_progress;
drop policy if exists school_progress_own_insert on public.school_progress;
drop policy if exists school_progress_own_update on public.school_progress;
drop policy if exists school_progress_own_delete on public.school_progress;
create policy school_progress_own_select on public.school_progress for select using (auth.uid() = user_id);
create policy school_progress_own_insert on public.school_progress for insert with check (auth.uid() = user_id);
create policy school_progress_own_update on public.school_progress for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy school_progress_own_delete on public.school_progress for delete using (auth.uid() = user_id);

drop policy if exists account_data_requests_own_select on public.account_data_requests;
drop policy if exists account_data_requests_own_insert on public.account_data_requests;
drop policy if exists account_data_requests_own_update on public.account_data_requests;
drop policy if exists account_data_requests_own_delete on public.account_data_requests;
create policy account_data_requests_own_select on public.account_data_requests for select using (auth.uid() = user_id);
create policy account_data_requests_own_insert on public.account_data_requests for insert with check (auth.uid() = user_id);
create policy account_data_requests_own_update on public.account_data_requests for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy account_data_requests_own_delete on public.account_data_requests for delete using (auth.uid() = user_id);

drop policy if exists support_tickets_own_select on public.support_tickets;
drop policy if exists support_tickets_own_insert on public.support_tickets;
drop policy if exists support_tickets_own_update on public.support_tickets;
drop policy if exists support_tickets_own_delete on public.support_tickets;
create policy support_tickets_own_select on public.support_tickets for select using (auth.uid() = user_id);
create policy support_tickets_own_insert on public.support_tickets for insert with check (auth.uid() = user_id);
create policy support_tickets_own_update on public.support_tickets for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy support_tickets_own_delete on public.support_tickets for delete using (auth.uid() = user_id);
