-- Enforce FIFO for recorded sells (LIFO/HIFO stay simulation-only in the API).
-- Replaces public.record_portfolio_sell with an identical body plus a FIFO guard.
-- Safe to re-run: CREATE OR REPLACE keeps the signature, so grants are preserved;
-- they are re-applied below for clarity. Historical LIFO/HIFO transactions are
-- left untouched. Apply after 20261127_portfolio_trade_ledger.sql.

create or replace function public.record_portfolio_sell(
    p_symbol text,
    p_quantity numeric,
    p_price numeric,
    p_trade_date date default current_date,
    p_fees numeric default 0,
    p_method text default 'FIFO',
    p_notes text default null,
    p_idempotency_key text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_user_id uuid := auth.uid();
    v_symbol text := upper(trim(p_symbol));
    v_method text := upper(coalesce(p_method, 'FIFO'));
    v_source_key text;
    v_txn_id uuid;
    v_existing_tx public.portfolio_transactions%rowtype;
    v_lot record;
    v_take numeric;
    v_buy_fee numeric;
    v_sell_fee numeric;
    v_gain numeric;
    v_remaining numeric;
    v_total_gain numeric := 0;
    v_matched jsonb := '[]'::jsonb;
    v_open_quantity numeric;
    v_avg_price numeric;
    v_added_date date;
begin
    if v_user_id is null then
        raise exception 'Authentication is required.';
    end if;
    if v_symbol = '' or p_quantity is null or p_quantity <= 0
       or p_price is null or p_price <= 0 or coalesce(p_fees, 0) < 0
       or v_method not in ('FIFO', 'LIFO', 'HIFO') then
        raise exception 'Invalid sell trade.';
    end if;
    -- Product decision: recorded sells consume lots FIFO only.
    -- LIFO/HIFO remain available for read-only simulation in the API.
    if v_method <> 'FIFO' then
        raise exception 'Recorded sells must use FIFO; LIFO/HIFO are simulation-only.';
    end if;

    v_source_key := case
        when p_idempotency_key is null then null
        else 'api:' || p_idempotency_key
    end;
    if v_source_key is not null then
        select tx.* into v_existing_tx
        from public.portfolio_transactions as tx
        where tx.user_id = v_user_id and tx.source_key = v_source_key;
        if found then
            if v_existing_tx.side <> 'SELL' or v_existing_tx.symbol <> v_symbol
               or v_existing_tx.quantity <> p_quantity or v_existing_tx.price <> p_price
               or v_existing_tx.trade_date <> coalesce(p_trade_date, current_date)
               or v_existing_tx.fees <> coalesce(p_fees, 0)
               or v_existing_tx.lot_method <> v_method then
                raise exception 'Idempotency key was already used for a different trade.';
            end if;
            return jsonb_build_object('status', 'ok', 'transaction_id', v_existing_tx.id, 'already_recorded', true);
        end if;
    end if;

    perform 1 from public.portfolio_positions
    where user_id = v_user_id and symbol = v_symbol
    for update;

    perform l.id
    from public.portfolio_lots as l
    where l.user_id = v_user_id and l.symbol = v_symbol and l.remaining_quantity > 0
    for update;
    select coalesce(sum(l.remaining_quantity), 0) into v_open_quantity
    from public.portfolio_lots as l
    where l.user_id = v_user_id and l.symbol = v_symbol and l.remaining_quantity > 0;
    if p_quantity > v_open_quantity then
        raise exception 'Sell quantity exceeds the available open-lot quantity.';
    end if;

    insert into public.portfolio_transactions (
        user_id, symbol, side, quantity, price, trade_date, fees, notes, source_key, lot_method
    ) values (
        v_user_id, v_symbol, 'SELL', p_quantity, p_price,
        coalesce(p_trade_date, current_date), coalesce(p_fees, 0), p_notes, v_source_key, v_method
    )
    on conflict (user_id, source_key) do nothing
    returning id into v_txn_id;
    if v_txn_id is null then
        select tx.* into v_existing_tx
        from public.portfolio_transactions as tx
        where tx.user_id = v_user_id and tx.source_key = v_source_key;
        if not found or v_existing_tx.side <> 'SELL' or v_existing_tx.symbol <> v_symbol
           or v_existing_tx.quantity <> p_quantity or v_existing_tx.price <> p_price
           or v_existing_tx.trade_date <> coalesce(p_trade_date, current_date)
           or v_existing_tx.fees <> coalesce(p_fees, 0)
           or v_existing_tx.lot_method <> v_method then
            raise exception 'Idempotency key was already used for a different trade.';
        end if;
        v_txn_id := v_existing_tx.id;
        return jsonb_build_object('status', 'ok', 'transaction_id', v_txn_id, 'already_recorded', true);
    end if;

    v_remaining := p_quantity;
    for v_lot in
        select l.*
        from public.portfolio_lots as l
        where l.user_id = v_user_id and l.symbol = v_symbol and l.remaining_quantity > 0
        order by
            case when v_method = 'HIFO' then l.buy_price end desc,
            case when v_method = 'FIFO' then l.buy_date end asc,
            case when v_method = 'LIFO' then l.buy_date end desc,
            l.id asc
        for update
    loop
        exit when v_remaining <= 0;
        if coalesce(p_trade_date, current_date) < v_lot.buy_date then
            raise exception 'Sell date cannot be earlier than the lot purchase date.';
        end if;
        v_take := least(v_remaining, v_lot.remaining_quantity);
        v_buy_fee := v_lot.remaining_fees * v_take / v_lot.remaining_quantity;
        v_sell_fee := coalesce(p_fees, 0) * v_take / p_quantity;
        v_gain := (p_price - v_lot.buy_price) * v_take - v_buy_fee - v_sell_fee;

        update public.portfolio_lots
        set remaining_quantity = remaining_quantity - v_take,
            remaining_fees = remaining_fees - v_buy_fee
        where id = v_lot.id;

        insert into public.portfolio_realized_gains (
            user_id, symbol, sell_txn_id, lot_id, quantity, buy_price, sell_price,
            buy_fees, sell_fees, gain, gain_percent, holding_days, gain_type, realized_at
        ) values (
            v_user_id, v_symbol, v_txn_id, v_lot.id, v_take, v_lot.buy_price, p_price,
            v_buy_fee, v_sell_fee, v_gain,
            case when v_lot.buy_price * v_take + v_buy_fee = 0 then null
                 else v_gain / (v_lot.buy_price * v_take + v_buy_fee) * 100 end,
            coalesce(p_trade_date, current_date) - v_lot.buy_date,
            case when coalesce(p_trade_date, current_date) >= (v_lot.buy_date + interval '12 months')::date
                 then 'LTCG' else 'STCG' end,
            coalesce(p_trade_date, current_date)
        );
        v_remaining := v_remaining - v_take;
        v_total_gain := v_total_gain + v_gain;
        v_matched := v_matched || jsonb_build_array(jsonb_build_object(
            'lot_id', v_lot.id,
            'quantity', v_take,
            'buy_price', v_lot.buy_price,
            'realized_gain', v_gain
        ));
    end loop;

    select coalesce(sum(l.remaining_quantity), 0),
           case when sum(l.remaining_quantity) > 0
                then sum(l.remaining_quantity * l.buy_price) / sum(l.remaining_quantity)
                else null end,
           min(l.buy_date)
    into v_open_quantity, v_avg_price, v_added_date
    from public.portfolio_lots as l
    where l.user_id = v_user_id and l.symbol = v_symbol;

    if v_open_quantity = 0 then
        delete from public.portfolio_positions
        where user_id = v_user_id and symbol = v_symbol;
    else
        update public.portfolio_positions
        set quantity = v_open_quantity, avg_price = v_avg_price,
            added_date = v_added_date::timestamp at time zone 'UTC'
        where user_id = v_user_id and symbol = v_symbol;
    end if;

    return jsonb_build_object(
        'status', 'ok',
        'transaction_id', v_txn_id,
        'already_recorded', false,
        'symbol', v_symbol,
        'quantity', p_quantity,
        'sell_price', p_price,
        'method', v_method,
        'realized_gain', v_total_gain,
        'matched_lots', v_matched
    );
end;
$$;

revoke all on function public.record_portfolio_sell(text, numeric, numeric, date, numeric, text, text, text)
    from public, anon;
grant execute on function public.record_portfolio_sell(text, numeric, numeric, date, numeric, text, text, text)
    to authenticated;
