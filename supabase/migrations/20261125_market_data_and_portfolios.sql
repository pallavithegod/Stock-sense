-- Apply once in the Supabase SQL Editor before enabling collection or portfolio APIs.

create table if not exists public.market_daily_bars (
    symbol text not null,
    trading_date date not null,
    open double precision not null check (open > 0),
    high double precision not null check (high > 0),
    low double precision not null check (low > 0),
    close double precision not null check (close > 0),
    volume bigint not null check (volume >= 0),
    provider text not null,
    fetched_at timestamptz not null,
    primary key (symbol, trading_date),
    check (high >= greatest(open, low, close)),
    check (low <= least(open, high, close))
);

alter table public.market_daily_bars enable row level security;
revoke all on public.market_daily_bars from anon, authenticated;
grant all on public.market_daily_bars to service_role;

create table if not exists public.portfolio_positions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    symbol text not null,
    quantity numeric(18, 6) not null check (quantity > 0),
    avg_price numeric(18, 6) not null check (avg_price > 0),
    added_date timestamptz not null default now(),
    unique (user_id, symbol)
);

alter table public.portfolio_positions enable row level security;
grant select, insert, update, delete on public.portfolio_positions to authenticated;

drop policy if exists "portfolio_positions_select_own" on public.portfolio_positions;
create policy "portfolio_positions_select_own"
    on public.portfolio_positions for select to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists "portfolio_positions_insert_own" on public.portfolio_positions;
create policy "portfolio_positions_insert_own"
    on public.portfolio_positions for insert to authenticated
    with check ((select auth.uid()) = user_id);

drop policy if exists "portfolio_positions_update_own" on public.portfolio_positions;
create policy "portfolio_positions_update_own"
    on public.portfolio_positions for update to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

drop policy if exists "portfolio_positions_delete_own" on public.portfolio_positions;
create policy "portfolio_positions_delete_own"
    on public.portfolio_positions for delete to authenticated
    using ((select auth.uid()) = user_id);
