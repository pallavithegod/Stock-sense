// -*- coding: utf-8 -*-
// ============================================================================
// NEXUS QUANTUM AI - COMPLETE PRODUCTION app.js
// ============================================================================
// ensure terminal output uses UTF-8 when running under Node
if (typeof process !== 'undefined' && process.stdout && process.stdout.setEncoding) {
    try { process.stdout.setEncoding('utf8'); } catch (e) {}
}
window.__NEXUS_APPJS_ACTIVE = true;
// Socket Configuration (Consolidated Arch Phase 4)
window.NEXUS_SOCKET = io(window.location.origin, {
    transports: ["polling", "websocket"],
    upgrade: true,
    rememberUpgrade: false,
    timeout: 20000,
    reconnection: true,
    reconnectionAttempts: 20,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000
});

const socket = window.NEXUS_SOCKET; // Alias for backward compatibility
window.__PORTFOLIO_LOCK = false;
window.__PF_INLINE_EDIT_SYMBOL = null;
window.__PENDING_PORTFOLIO_ADD = null;
window.__PORTFOLIO_SORT = { column: 'symbol', direction: 'asc' };
window.__PF_ALERT_STYLES_READY = false;
window.__NEXUS_METRIC_TOOLTIP_READY = false;
window.__PF_EXPANDED_SYMBOL = null;
window.__PF_NEWS_CACHE = {};
window.__PF_LEGEND_READY = false;
window.__PF_EXPANDED_PINNED = false;
window.__PF_SYMBOL_META_CACHE = {};
window.__PF_DEEP_CACHE = {};
window.__PF_LOT_INSIGHTS_CACHE = {};
window.__PF_SELL_SIM_CACHE = {};
window.__PF_SELL_SIM_LOADING = {};
window.__PF_TAX_SUMMARY_CACHE = null;
window.__PF_METRIC_HISTORY = {};
window.__PF_REALIZED_JOURNAL_CACHE = {};
window.__PF_REALIZED_LOADING = {};
window.__PF_LOTS_LOADING = {};
window.__PF_LEDGER_SYNC_LOCK = {};
window.__PF_UI_SELL_SIM_LOADING = {};
window.__PF_INTEL_SUITE_CACHE = null;
window.__PF_INTEL_SUITE_LOADING = false;
window.__PF_ROW_WINDOW_START = 0;
window.__PF_ROW_WINDOW_SIZE = 18;
window.__PF_EXPANDER_NEWS_CACHE = {};
window.__PF_EXPANDER_CACHE_TTL_MS = 120000;
window.__PF_VSCROLL_BOUND = false;
window.__PF_VSCROLL_TICK = 0;
window.__COG_LAST_ACTION_AT = 0;
window.__COG_LAST_ACTION = '';
window.__WS_FALLBACK_TS = 0;
window.__PF_TAX_LAST_REQ_AT = 0;
window.__PF_RENDER_TIMER = null;
window.__PF_RENDER_PAYLOAD = null;
window.__PF_LAST_RENDER_AT = 0;
window.__PF_RENDER_MIN_MS = 1200;
window.__PF_LAST_SIGNATURE = '';
window.__PF_PANELS_LAST_SIG = '';
window.__PF_PANELS_LAST_AT = 0;
window.__PF_RENDERING = false;
window.__PF_RENDER_PENDING = null;
window.__PF_WS_LAST_APPLY = 0;
window.__PF_LAST_WINDOW_KEY = '';
window.__PF_STATE_INFLIGHT = false;
window.__STOCK_SORT = window.__STOCK_SORT || { key: 'symbol', direction: 'asc' };
window.__WS_FALLBACK_INFLIGHT = false;
window.__PRED_INFLIGHT = false;
window.__DASH_INFLIGHT = false;

function isTabActive(tabId) {
    const el = document.getElementById(tabId);
    return !!(el && el.classList.contains('active'));
}

function schedulePortfolioRender(positions = null, accountMetrics = null, force = false) {
    if (!force && !isTabActive('portfolio')) return;
    if (!force && (document.getElementById('lotEditorModal') || document.getElementById('sellWorkflowModal'))) return;
    if (!force && window.__PF_EXPANDED_SYMBOL) return;
    window.__PF_RENDER_PAYLOAD = { positions, accountMetrics, force };
    if (window.__PF_RENDER_TIMER) return;
    const now = Date.now();
    const wait = Math.max(0, Number(window.__PF_RENDER_MIN_MS || 650) - (now - Number(window.__PF_LAST_RENDER_AT || 0)));
    window.__PF_RENDER_TIMER = setTimeout(() => {
        window.__PF_RENDER_TIMER = null;
        const payload = window.__PF_RENDER_PAYLOAD || {};
        window.__PF_RENDER_PAYLOAD = null;
        if (!payload.force && !isTabActive('portfolio')) return;
        const sigPositions = Array.isArray(payload.positions) ? payload.positions : (window.NEURAL_STATE?.portfolio_intelligence?.positions || []);
        const sig = sigPositions.map((p) => {
            const s = String(p?.symbol || '');
            const cp = Number(p?.current_price || 0).toFixed(2);
            const q = Number(p?.open_qty ?? p?.quantity ?? 0).toFixed(4);
            const a = String(p?.action || 'HOLD');
            const c = Number(p?.confidence || 0).toFixed(1);
            return `${s}|${cp}|${q}|${a}|${c}`;
        }).join(';') + `|w:${Number(window.__PF_ROW_WINDOW_START || 0)}|x:${String(window.__PF_EXPANDED_SYMBOL || '')}`;
        if (!payload.force && sig && sig === window.__PF_LAST_SIGNATURE) return;
        window.__PF_LAST_RENDER_AT = Date.now();
        window.__PF_LAST_SIGNATURE = sig;
        if (window.__PF_RENDERING) {
            if (window.__PF_EXPANDED_SYMBOL && !payload.force) return;
            window.__PF_RENDER_PENDING = { positions: payload.positions || null, accountMetrics: payload.accountMetrics || null };
            return;
        }
        renderPortfolio(payload.positions || null, payload.accountMetrics || null);
    }, wait);
}

function ensurePortfolioAlertStyles() {
    if (window.__PF_ALERT_STYLES_READY) return;
    const style = document.createElement('style');
    style.id = 'pf-alert-strip-style';
    style.textContent = `
        @keyframes pfAlertFlow {
            0% { background-position: -200% 50%; opacity: 0.42; }
            50% { opacity: 0.92; }
            100% { background-position: 0% 50%; opacity: 0.42; }
        }
        .pf-alert-strip {
            height: 2px;
            border-radius: 999px;
            margin-top: 3px;
            background-size: 200% 100%;
            animation: pfAlertFlow 1.7s linear infinite;
            box-shadow: 0 0 5px currentColor;
        }
        .pf-alert-strip-bottom {
            margin-top: 5px;
        }
        #portfolio .table-container {
            border-radius: 10px;
            overflow: hidden;
        }
        #portfolio #portfolioTable thead th:first-child {
            border-top-left-radius: 10px;
        }
        #portfolio #portfolioTable thead th:last-child {
            border-top-right-radius: 10px;
        }
        #pf_date {
            color-scheme: dark;
        }
        #pf_date::-webkit-calendar-picker-indicator {
            cursor: pointer;
            filter: invert(77%) sepia(40%) saturate(3052%) hue-rotate(145deg) brightness(102%) contrast(103%);
            opacity: 1;
        }
        #nexusMetricTooltip {
            position: fixed;
            z-index: 99999;
            pointer-events: none;
            min-width: 190px;
            max-width: 260px;
            background: rgba(5,10,20,0.98);
            border: 1px solid rgba(0,243,255,0.35);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.45);
            padding: 8px 10px;
            color: #eaf7ff;
            font-size: 11px;
            line-height: 1.35;
            display: none;
        }
        #nexusMetricTooltip .mt-title {
            font-weight: 700;
            color: var(--electric-yellow);
            margin-bottom: 4px;
            font-size: 11px;
        }
        #nexusMetricTooltip .mt-desc {
            color: var(--text-muted);
            margin-bottom: 6px;
        }
        #nexusMetricTooltip .mt-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
            color: #cdefff;
        }
        #nexusMetricTooltip .mt-bar {
            height: 5px;
            border-radius: 999px;
            background: rgba(255,255,255,0.08);
            overflow: hidden;
        }
        #nexusMetricTooltip .mt-fill {
            height: 100%;
            border-radius: 999px;
            background-size: 200% 100%;
            animation: pfAlertFlow 2.1s linear infinite;
        }
    `;
    document.head.appendChild(style);
    window.__PF_ALERT_STYLES_READY = true;
}

function ensureMetricTooltipEl() {
    let tip = document.getElementById('nexusMetricTooltip');
    if (tip) return tip;
    tip = document.createElement('div');
    tip.id = 'nexusMetricTooltip';
    document.body.appendChild(tip);
    return tip;
}

function clamp10(v) {
    const n = Number(v);
    if (!Number.isFinite(n)) return 0;
    return Math.max(0, Math.min(10, n));
}

function clamp01(v) {
    const n = Number(v);
    if (!Number.isFinite(n)) return 0;
    return Math.max(0, Math.min(1, n));
}

function sparklineFromSeries(series) {
    const ticks = "▁▂▃▄▅▆▇█";
    if (!Array.isArray(series) || !series.length) return "—";
    const nums = series.map(Number).filter(Number.isFinite);
    if (!nums.length) return "—";
    const min = Math.min(...nums);
    const max = Math.max(...nums);
    const span = Math.max(1e-9, max - min);
    return nums.map((n) => {
        const idx = Math.max(0, Math.min(ticks.length - 1, Math.floor(((n - min) / span) * (ticks.length - 1))));
        return ticks[idx];
    }).join("");
}

function trendSummaryFromSeries(series, currentValue, digits = 2) {
    const nums = (series || []).map(Number).filter(Number.isFinite);
    const curr = Number(currentValue);
    if (nums.length < 2) {
        if (Number.isFinite(curr)) return `Seed ${curr.toFixed(digits)}`;
        return 'Seed n/a';
    }
    const first = nums[0];
    const last = nums[nums.length - 1];
    const delta = last - first;
    const arrow = delta > 0 ? '↗' : delta < 0 ? '↘' : '→';
    const prefix = delta > 0 ? '+' : '';
    return `${arrow} ${prefix}${delta.toFixed(digits)}`;
}

function buildLotLedgerHtmlForSymbol(symbol, limit = 12) {
    const lotInsights = (window.__PF_LOT_INSIGHTS_CACHE[symbol] || {}).data || {};
    const openLots = Array.isArray(lotInsights.open_lots) ? lotInsights.open_lots : [];
    const allLots = Array.isArray(lotInsights.all_lots) && lotInsights.all_lots.length ? lotInsights.all_lots : openLots;
    if (!allLots.length) return '<div class="pf-expander-muted">No lot history available</div>';
    return allLots
        .slice()
        .sort((a, b) => String(a.buy_date || '').localeCompare(String(b.buy_date || '')))
        .slice(0, limit)
        .map((lot) => {
            const d = formatPortfolioDate(lot.buy_date || '');
            const orig = Number(lot.original_quantity || 0);
            const open = Number(lot.remaining_quantity || 0);
            const sold = Math.max(0, orig - open);
            const px = Number(lot.buy_price || 0).toFixed(2);
            const state = open <= 0 ? 'CLOSED' : (sold > 0 ? 'PARTIAL' : 'OPEN');
            const stateColor = open <= 0 ? 'var(--text-muted)' : (sold > 0 ? 'var(--electric-yellow)' : 'var(--electric-green)');
            return `<div class="pf-journal-card">
                <div class="pf-journal-head">
                    <span>${d} · Lot ${Number(lot.id || lot.lot_id || 0)}</span>
                    <span style="color:${stateColor};">${state}</span>
                </div>
                <div class="pf-journal-meta">
                    <span>Open ${open.toFixed(2)}/${orig.toFixed(2)}</span>
                    <span>Buy @ \u20b9${px}</span>
                    <span>Sold ${sold.toFixed(2)}</span>
                </div>
            </div>`;
        }).join('');
}

function buildRealizedJournalHtmlForSymbol(symbol, limit = 8) {
    const journalCache = window.__PF_REALIZED_JOURNAL_CACHE[symbol] || {};
    const realizedRows = journalCache.data || [];
    const grouped = Object.values(
        (realizedRows || []).reduce((acc, row) => {
            const key = String(row.sell_txn_id || row.id || `${row.realized_at || ''}-${row.lot_id || ''}`);
            if (!acc[key]) {
                acc[key] = { sell_txn_id: row.sell_txn_id || row.id || key, realized_at: row.realized_at || '', lots: 0, qty: 0, stcg: 0, ltcg: 0, total: 0, lot_ids: [] };
            }
            const gain = Number(row.gain || 0);
            const qty = Number(row.quantity || 0);
            const gt = String(row.gain_type || 'STCG').toUpperCase();
            acc[key].lots += 1;
            acc[key].qty += qty;
            acc[key].total += gain;
            if (gt === 'LTCG') acc[key].ltcg += gain; else acc[key].stcg += gain;
            if (row.lot_id != null) acc[key].lot_ids.push(Number(row.lot_id));
            return acc;
        }, {})
    ).sort((a, b) => String(b.realized_at || '').localeCompare(String(a.realized_at || ''))).slice(0, limit);
    if (!grouped.length) return '<div class="pf-expander-muted">No realized sell journal yet</div>';
    const body = grouped.map((j) => {
        const dateStr = j.realized_at ? formatPortfolioDate(j.realized_at) : '—';
        return `<div class="pf-journal-card">
            <div class="pf-journal-head">
                <span>${dateStr} · Txn ${j.sell_txn_id}</span><span>Lots ${j.lots} · Qty ${j.qty.toFixed(2)}</span>
            </div>
            <div class="pf-journal-meta">
                <span>STCG <span style="color:${j.stcg >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'}">${formatInr(j.stcg)}</span></span>
                <span>LTCG <span style="color:${j.ltcg >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'}">${formatInr(j.ltcg)}</span></span>
                <span>Total <span style="color:${j.total >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'}">${formatInr(j.total)}</span></span>
            </div>
            <div class="pf-expander-muted">Matched lots: ${j.lot_ids.length ? j.lot_ids.join(', ') : '—'}</div>
        </div>`;
    }).join('');
    const loadMoreBtn = journalCache.next_cursor
        ? `<div style="margin-top:6px; text-align:right;">
                <button onclick="loadMoreRealizedJournal('${symbol}','${String(journalCache.next_cursor)}')" style="padding:3px 8px;border-radius:4px;border:1px solid rgba(0,243,255,0.35);background:rgba(0,243,255,0.10);color:var(--electric-cyan);font-size:10px;cursor:pointer;">Load more</button>
           </div>`
        : '';
    return `${body}${loadMoreBtn}`;
}

async function hydrateLedgerLazy(kind, symbol, targetId) {
    const el = document.getElementById(targetId);
    if (!el || el.dataset.loaded === '1') return;
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base) return;
    if (kind === 'lots') {
        const cachedLots = window.__PF_LOT_INSIGHTS_CACHE?.[base]?.data;
        const hasLots = Array.isArray(cachedLots?.all_lots);
        if (!hasLots) {
            if (!window.__PF_LOTS_LOADING[base]) {
                el.dataset.loaded = 'loading';
                el.innerHTML = '<div class="pf-expander-muted">Loading purchase ledger...</div>';
                window.__PF_LOTS_LOADING[base] = loadPortfolioLotInsights(base)
                    .catch(() => null)
                    .finally(() => { delete window.__PF_LOTS_LOADING[base]; });
            }
            await window.__PF_LOTS_LOADING[base];
        }
        el.innerHTML = buildLotLedgerHtmlForSymbol(base, 12);
    } else {
        const cachedJournal = window.__PF_REALIZED_JOURNAL_CACHE?.[base]?.data;
        const hasJournal = Array.isArray(cachedJournal);
        if (!hasJournal) {
            if (!window.__PF_REALIZED_LOADING[base]) {
                el.dataset.loaded = 'loading';
                el.innerHTML = '<div class="pf-expander-muted">Loading realized journal...</div>';
                window.__PF_REALIZED_LOADING[base] = loadPortfolioRealizedJournal(base)
                    .catch(() => [])
                    .finally(() => { delete window.__PF_REALIZED_LOADING[base]; });
            }
            await window.__PF_REALIZED_LOADING[base];
        }
        el.innerHTML = buildRealizedJournalHtmlForSymbol(base, 8);
    }
    el.dataset.loaded = '1';
}
window.hydrateLedgerLazy = hydrateLedgerLazy;

async function syncPortfolioLedgerPanels(symbol) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base) return;
    if (window.__PF_LEDGER_SYNC_LOCK[base]) return;

    const lotsCard = document.getElementById(`pf-lots-card-${base}`);
    const journalCard = document.getElementById(`pf-journal-card-${base}`);
    if (!lotsCard || !journalCard) return;

    // If either panel is opened, force a unified view with both datasets loaded.
    if (!(lotsCard.open || journalCard.open)) return;

    window.__PF_LEDGER_SYNC_LOCK[base] = true;
    try {
        lotsCard.open = true;
        journalCard.open = true;
        await Promise.allSettled([
            hydrateLedgerLazy('lots', base, `pf-lots-${base}`),
            hydrateLedgerLazy('journal', base, `pf-journal-${base}`)
        ]);
    } finally {
        delete window.__PF_LEDGER_SYNC_LOCK[base];
    }
}
window.syncPortfolioLedgerPanels = syncPortfolioLedgerPanels;


async function loadMoreRealizedJournal(symbol, cursor) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base) return;
    const current = window.__PF_REALIZED_JOURNAL_CACHE[base] || { data: [] };
    try {
        const r = await fetch(`/api/portfolio/realized-gains?symbol=${encodeURIComponent(base)}&limit=120&cursor=${encodeURIComponent(String(cursor || '0'))}`);
        if (!r.ok) throw new Error(`realized journal page http ${r.status}`);
        const payload = await r.json();
        const rows = Array.isArray(payload?.data) ? payload.data : [];
        const merged = (current.data || []).concat(rows);
        window.__PF_REALIZED_JOURNAL_CACHE[base] = {
            ts: Date.now(),
            data: merged,
            cursor: payload?.cursor || String(cursor || '0'),
            next_cursor: payload?.next_cursor || null,
            total: Number(payload?.total || merged.length)
        };
        const target = document.getElementById(`pf-journal-${base}`);
        if (target) target.innerHTML = buildRealizedJournalHtmlForSymbol(base, 16);
    } catch (e) {
        showToast('Failed to load more journal rows', 'error');
    }
}
window.loadMoreRealizedJournal = loadMoreRealizedJournal;

function buildExpanderNewsHtml(symbol, news, maxItems = 10) {
    const list = Array.isArray(news) ? news : [];
    const key = `${symbol}|${list.length}|${list.slice(0, maxItems).map((n) => `${n?.title || ''}|${n?.published || n?.timestamp || ''}`).join('||')}`;
    const now = Date.now();
    const hit = window.__PF_EXPANDER_NEWS_CACHE[key];
    if (hit && (now - Number(hit.ts || 0)) < Number(window.__PF_EXPANDER_CACHE_TTL_MS || 120000)) return hit.html;
    Object.keys(window.__PF_EXPANDER_NEWS_CACHE).forEach((k) => {
        const v = window.__PF_EXPANDER_NEWS_CACHE[k];
        if (!v || (now - Number(v.ts || 0)) > Number(window.__PF_EXPANDER_CACHE_TTL_MS || 120000)) {
            delete window.__PF_EXPANDER_NEWS_CACHE[k];
        }
    });
    const html = list.length
        ? list.slice(0, maxItems).map((n) => {
            const title = escapeHtml(n.title || n.headline || 'Market update');
            const url = n.link || n.url || n.source_url || '';
            const source = escapeHtml(n.source || 'Source');
            const age = formatNewsAge(n.published || n.normalized_time || n.timestamp);
            const reliability = Number(n.source_reliability ?? n.confidence ?? 0);
            const relPct = Math.max(0, Math.min(100, reliability > 1 ? reliability : reliability * 100));
            const relType = String(n.relevance_type || 'primary').toLowerCase();
            const relLabel = relType === 'strict' ? 'Ticker' : (relType === 'sector' ? 'Sector' : 'Primary');
            const relColor = relType === 'strict' ? 'var(--electric-green)' : (relType === 'sector' ? 'var(--electric-yellow)' : 'var(--electric-cyan)');
            const chips = `<span style="display:inline-block; margin-left:6px; color:var(--text-muted); font-size:9px;">${source} · ${age} · R${relPct.toFixed(0)}% · <span style="color:${relColor};">${relLabel}</span></span>`;
            if (url) {
                return `<div style="margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">• <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" style="color:var(--electric-cyan); text-decoration:none;">${title}</a>${chips}</div>`;
            }
            return `<div style="margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">• ${title}${chips}</div>`;
        }).join('')
        : '<div style="margin-top:4px; color:var(--text-muted);">• No fresh news found</div>';
    window.__PF_EXPANDER_NEWS_CACHE[key] = { html, ts: now };
    return html;
}

function bindPortfolioVirtualScroll(totalRows, windowSize) {
    const panel = document.querySelector('#portfolio .table-container');
    if (!panel) return;
    if (!panel.style.maxHeight) panel.style.maxHeight = '62vh';
    panel.style.overflowY = 'auto';
    if (!window.__PF_VSCROLL_BOUND) {
        panel.addEventListener('scroll', () => {
            if (window.__PF_VSCROLL_TICK) cancelAnimationFrame(window.__PF_VSCROLL_TICK);
            window.__PF_VSCROLL_TICK = requestAnimationFrame(() => {
                window.__PF_VSCROLL_TICK = 0;
                if (!isTabActive('portfolio')) return;
                if (window.__PF_EXPANDED_SYMBOL) return; // keep stable while expanded
                const rowH = 58;
                const nextStart = Math.max(0, Math.min(totalRows - windowSize, Math.floor(panel.scrollTop / rowH)));
                if (nextStart !== window.__PF_ROW_WINDOW_START) {
                    window.__PF_ROW_WINDOW_START = nextStart;
                    renderPortfolio();
                }
            });
        }, { passive: true });
        window.__PF_VSCROLL_BOUND = true;
    }
}

function updatePositionMetricHistory(positions) {
    const now = Date.now();
    const seen = new Set();
    (positions || []).forEach((p) => {
        const sym = String(p?.symbol || '').toUpperCase().replace(/\.NS$|\.BO$/i, '');
        if (!sym) return;
        seen.add(sym);
        const arr = window.__PF_METRIC_HISTORY[sym] || [];
        arr.push({
            ts: now,
            risk: Number(p.risk || 0),
            confidence: Number(p.confidence || 0),
            price: Number(p.current_price || 0),
            drift: Number(p.change_percent || 0)
        });
        window.__PF_METRIC_HISTORY[sym] = arr.slice(-10);
    });
    Object.keys(window.__PF_METRIC_HISTORY).forEach((k) => {
        if (!seen.has(k)) delete window.__PF_METRIC_HISTORY[k];
    });
}

function mergePortfolioWithLiveStocks(positions) {
    const rows = Array.isArray(positions) ? positions : [];
    if (!rows.length || !Array.isArray(dashState?.stocks) || !dashState.stocks.length) return rows;
    const bySym = new Map();
    dashState.stocks.forEach((s) => {
        const k = String(s?.symbol || '').toUpperCase().replace(/\.NS$|\.BO$/i, '');
        if (k) bySym.set(k, s);
    });
    return rows.map((p) => {
        const k = String(p?.symbol || '').toUpperCase().replace(/\.NS$|\.BO$/i, '');
        const live = bySym.get(k);
        if (!live) return p;
        const merged = { ...p };
        if (Number.isFinite(Number(live.current_price))) merged.current_price = Number(live.current_price);
        if (Number.isFinite(Number(live.change_percent))) merged.change_percent = Number(live.change_percent);
        if (Number.isFinite(Number(live.day_high))) merged.day_high = Number(live.day_high);
        if (Number.isFinite(Number(live.day_low))) merged.day_low = Number(live.day_low);
        if (Number.isFinite(Number(live.volume))) merged.volume = Number(live.volume);
        return merged;
    });
}

function renderMetricTooltip(metric) {
    const tip = ensureMetricTooltipEl();
    const score = clamp10(metric.score);
    const pct = (score / 10) * 100;
    const fillColor = score >= 7 ? 'var(--electric-green)' : score >= 4 ? 'var(--electric-yellow)' : 'var(--electric-red)';
    tip.innerHTML = `
        <div class="mt-title">${metric.title}</div>
        <div class="mt-desc">${metric.desc}</div>
        <div class="mt-desc" style="margin-top:-2px; color:#bfe9ff;">${metric.better || ''}</div>
        <div class="mt-row">
            <span>Scale</span>
            <span><b>${score.toFixed(1)}</b> / 10</span>
        </div>
        <div class="mt-bar">
            <div class="mt-fill" style="width:${pct}%; background-image:linear-gradient(90deg, rgba(255,255,255,0.05), ${fillColor}, rgba(255,255,255,0.05));"></div>
        </div>
    `;
    tip.style.display = 'block';
}

function hideMetricTooltip() {
    const tip = document.getElementById('nexusMetricTooltip');
    if (tip) tip.style.display = 'none';
}

function metricDefsFromState() {
    const pi = window.NEURAL_STATE?.portfolio_intelligence || {};
    const metrics = pi.account_metrics || {};
    const positions = pi.positions || [];
    const avg = (fn) => positions.length ? (positions.reduce((s, p) => s + fn(p), 0) / positions.length) : 0;

    const avgConf = avg(p => Number(p.confidence || 0));
    const avgEdge = avg(p => Number(p.edge || 0));
    const avgEntropy = avg(p => Number(p.entropy || 0));
    const avgKelly = avg((p) => {
        const kp = Number(p.kelly_percent);
        if (Number.isFinite(kp) && kp > 0) return kp;
        const kf = Number(p.kelly_fraction || 0);
        return kf > 0 ? (kf * 100) : 0;
    });
    const avgRisk = avg(p => Number(p.risk || 0));

    return {
        portfolio_edge: {
            title: 'Portfolio Edge',
            desc: 'Is portfolio statistically profitable?',
            better: 'Higher is better.',
            score: clamp10((Number(metrics.edge || 0)) * 20)
        },
        portfolio_risk: {
            title: 'Portfolio Risk',
            desc: 'Can one move damage your capital?',
            better: 'Lower is better.',
            score: clamp10((1 - Math.min(1, Number(metrics.total_risk || 0))) * 10)
        },
        regime_fit: {
            title: 'Regime Alignment',
            desc: 'Are positions aligned with current market structure?',
            better: 'Higher is better.',
            score: clamp10(Number(metrics.regimeFit || 0) * 10)
        },
        confidence: {
            title: 'Confidence',
            desc: 'How sure AI is about direction.',
            better: 'Higher is better.',
            score: clamp10(avgConf / 10)
        },
        edge: {
            title: 'Edge',
            desc: 'Expected return advantage vs neutral hold.',
            better: 'Higher is better.',
            score: clamp10(avgEdge * 30)
        },
        entropy: {
            title: 'Entropy',
            desc: 'Model disagreement / market noise.',
            better: 'Lower is better.',
            score: clamp10((1 - Math.min(1, avgEntropy)) * 10)
        },
        kelly: {
            title: 'Kelly %',
            desc: 'How much capital AI suggests for this setup.',
            better: 'Higher means AI allows a bigger size. Near 0% means keep size small.',
            score: clamp10(avgKelly / 2)
        },
        risk: {
            title: 'Risk',
            desc: 'Downside threat level.',
            better: 'Lower is better.',
            score: clamp10((1 - Math.min(1, avgRisk)) * 10)
        }
    };
}

function ensurePortfolioLegend() {
    if (window.__PF_LEGEND_READY) return;
    const h2 = document.querySelector('#portfolio h2');
    if (!h2 || !h2.parentElement) return;
    const wrap = document.createElement('div');
    wrap.style.display = 'flex';
    wrap.style.alignItems = 'center';
    wrap.style.justifyContent = 'space-between';
    wrap.style.gap = '10px';
    wrap.style.width = '100%';
    wrap.style.marginBottom = '6px';
    h2.parentElement.insertBefore(wrap, h2);
    const leftWrap = document.createElement('div');
    leftWrap.style.display = 'inline-flex';
    leftWrap.style.alignItems = 'center';
    leftWrap.style.gap = '10px';
    leftWrap.appendChild(h2);
    wrap.appendChild(leftWrap);

    const legendBtn = document.createElement('button');
    legendBtn.id = 'pfLegendBtn';
    legendBtn.type = 'button';
    legendBtn.innerHTML = '<i class="fas fa-info-circle"></i>';
    legendBtn.style.cssText = 'width:24px;height:24px;border-radius:50%;border:1px solid rgba(255,255,255,0.18);background:rgba(255,255,255,0.04);color:var(--electric-yellow);cursor:pointer;';
    leftWrap.appendChild(legendBtn);


    const panel = document.createElement('div');
    panel.id = 'pfLegendPanel';
    panel.style.cssText = 'display:none;position:fixed;z-index:5000;background:rgba(5,10,20,0.98);border:1px solid rgba(0,243,255,0.35);border-radius:8px;padding:10px 12px;min-width:240px;box-shadow:0 8px 24px rgba(0,0,0,0.45);';
    panel.innerHTML = `
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;">Signal Colors</div>
        <div style="display:flex;align-items:center;gap:8px;font-size:11px;color:#d9f7e9;"><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--electric-green);"></span>Green: Take profit zone</div>
        <div style="display:flex;align-items:center;gap:8px;font-size:11px;color:#ffeec0;margin-top:5px;"><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--electric-yellow);"></span>Yellow: Rolled target active</div>
        <div style="display:flex;align-items:center;gap:8px;font-size:11px;color:#ffd6de;margin-top:5px;"><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--electric-red);"></span>Red: Stop risk near</div>
    `;
    document.body.appendChild(panel);
    legendBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (panel.style.display === 'none') {
            const r = legendBtn.getBoundingClientRect();
            panel.style.left = `${Math.max(10, Math.min(window.innerWidth - 270, r.left - 230 + r.width))}px`;
            panel.style.top = `${Math.max(10, r.bottom + 8)}px`;
            panel.style.display = 'block';
        } else {
            panel.style.display = 'none';
        }
    });
    document.addEventListener('click', () => { panel.style.display = 'none'; });

    const exportWrap = document.createElement('div');
    exportWrap.style.display = 'inline-flex';
    exportWrap.style.gap = '6px';
    exportWrap.style.marginLeft = 'auto';
    const xlsBtn = document.createElement('button');
    xlsBtn.textContent = 'Export Excel';
    xlsBtn.style.cssText = 'padding:4px 9px;font-size:11px;border-radius:6px;border:1px solid rgba(255,255,255,0.2);background:rgba(57,255,20,0.08);color:var(--electric-green);cursor:pointer;';
    xlsBtn.onclick = exportPortfolioExcel;
    const pdfBtn = document.createElement('button');
    pdfBtn.textContent = 'Export PDF';
    pdfBtn.style.cssText = 'padding:4px 9px;font-size:11px;border-radius:6px;border:1px solid rgba(255,255,255,0.2);background:rgba(0,243,255,0.08);color:var(--electric-cyan);cursor:pointer;';
    pdfBtn.onclick = exportPortfolioPDF;
    exportWrap.appendChild(xlsBtn);
    exportWrap.appendChild(pdfBtn);
    wrap.appendChild(exportWrap);
    window.__PF_LEGEND_READY = true;
}


function worldStateCard(label, value, sub, color, heat = null) {
    const heatClamped = heat == null || Number.isNaN(Number(heat)) ? null : Math.max(0, Math.min(100, Number(heat)));
    const heatBar = heatClamped == null ? '' : `
        <div style="margin-top:6px;">
            <div style="height:4px; border-radius:999px; background:rgba(255,255,255,0.10); overflow:hidden;">
                <div style="width:${heatClamped.toFixed(1)}%; height:100%; background:linear-gradient(90deg, var(--electric-red), var(--electric-yellow), var(--electric-green)); box-shadow:0 0 8px rgba(57,255,20,0.25);"></div>
            </div>
            <div style="color:var(--text-muted); font-size:9px; margin-top:2px;">Heat ${heatClamped.toFixed(0)}%</div>
        </div>
    `;
    return `
        <div style="border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:7px; background:rgba(255,255,255,0.02);">
            <div style="color:${color}; font-size:10px; font-weight:700; margin-bottom:3px;">${label}</div>
            <div style="color:#e8f2ff; font-size:12px; font-weight:700;">${value}</div>
            <div style="color:var(--text-muted); font-size:10px; margin-top:2px;">${sub}</div>
            ${heatBar}
        </div>
    `;
}

function ensurePredictionsWorldStateMount() {
    let section = document.getElementById('predictionsWorldState');
    if (section) {
        const title = section.querySelector('h3');
        if (title) title.textContent = 'Future Intelligence Layers';
        return section;
    }

    const predictionsTab = document.getElementById('predictions');
    if (!predictionsTab) return null;

    section = document.createElement('section');
    section.id = 'predictionsWorldState';
    section.style.cssText = 'margin-bottom:16px; border:1px solid rgba(0,255,255,0.2); border-radius:10px; background:linear-gradient(145deg, rgba(8,14,24,0.85), rgba(12,20,30,0.85)); padding:10px;';
    section.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:8px;">
            <h3 style="margin:0; color:var(--electric-cyan); font-size:13px; letter-spacing:0.4px;">Future Intelligence Layers</h3>
            <span id="worldStateUpdatedAt" style="font-size:10px; color:var(--text-muted);">Updating...</span>
        </div>
        <div id="worldStateGrid" style="display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; font-size:11px;"></div>
        <div id="worldStateCompass" style="margin-top:10px; border:1px solid rgba(255,255,255,0.10); border-radius:8px; padding:8px; background:rgba(255,255,255,0.02);"></div>
    `;

    const cognitivePanel = document.getElementById('aiCognitivePanel')?.closest('section');
    if (cognitivePanel && cognitivePanel.parentElement === predictionsTab) {
        predictionsTab.insertBefore(section, cognitivePanel);
    } else {
        predictionsTab.prepend(section);
    }
    return section;
}

function renderPredictionsWorldState(force = false) {
    if (!force && !isTabActive('predictions')) return;
    ensurePredictionsWorldStateMount();
    const grid = document.getElementById('worldStateGrid');
    const compass = document.getElementById('worldStateCompass');
    if (!grid) return;
    const updatedAt = document.getElementById('worldStateUpdatedAt');
    const data = dashState.data || {};
    const market = data.market_status || {};
    const indices = Array.isArray(data.live_indices) ? data.live_indices : [];
    const perf = data.ai_performance || {};
    const sentiment = dashState.marketSentiment || {};
    const newsIntel = dashState.newsIntelligence || {};
    const predictionRows = Array.isArray(window.__INTEL_PRED_ROWS) && window.__INTEL_PRED_ROWS.length
        ? window.__INTEL_PRED_ROWS
        : (Array.isArray(dashState.predictions) ? dashState.predictions : []);
    const regime = document.getElementById('marketRegimeValue')?.textContent?.trim()
        || predictionRows[0]?.market_regime
        || perf.regime
        || 'UNKNOWN';
    const riskFromPortfolio = (() => {
        const ps = window.NEURAL_STATE?.portfolio_intelligence?.positions || [];
        if (!ps.length) return null;
        return ps.reduce((s, p) => s + Number(p.risk || 0), 0) / ps.length;
    })();

    const idxAvgMove = (() => {
        if (!indices.length) return 0;
        return indices.reduce((s, i) => s + Math.abs(Number(i.change_percent || i.change || 0)), 0) / indices.length;
    })();

    const sentimentScore = Number(sentiment.overall_score ?? sentiment.sentiment_score ?? 0);
    const sentimentLabel = String(sentiment.label || 'NEUTRAL').toUpperCase();
    const marketStatus = String(market.status || 'UNKNOWN').toUpperCase();
    const activeModels = (() => {
        const raw = perf.active_models ?? perf.models_active ?? [];
        if (Array.isArray(raw)) return raw.length;
        const count = Number(raw);
        return Number.isFinite(count) ? count : 0;
    })();
    const nextOpen = market.next_open || '--';
    const percentileBand = (value, series, labels) => {
        const clean = (series || []).map(Number).filter(Number.isFinite).sort((a, b) => a - b);
        if (!clean.length) return { label: labels[1], pct: 50 };
        const pct = (clean.filter(v => v <= value).length / clean.length) * 100;
        if (pct >= 66.67) return { label: labels[2], pct };
        if (pct <= 33.33) return { label: labels[0], pct };
        return { label: labels[1], pct };
    };

    const predictionMetrics = predictionRows.reduce((acc, row) => {
        const confidence = Number(row?.confidence ?? row?.confidences15d ?? row?.prediction?.confidence ?? 0);
        const reliability = Number(row?.reliability_score ?? 0);
        const edge = Number(row?.predicted_return ?? row?.prediction?.predicted_return ?? 0);
        const entropy = Number(row?.entropy ?? row?.prediction?.entropy ?? 0);
        const sector = String(row?.sector || '').trim();
        if (Number.isFinite(confidence)) acc.confidences.push(confidence);
        if (Number.isFinite(reliability)) acc.reliabilities.push(reliability);
        if (Number.isFinite(edge)) acc.edges.push(edge);
        if (Number.isFinite(entropy)) acc.entropies.push(entropy);
        if (sector) {
            acc.sectors[sector] = (acc.sectors[sector] || 0) + Math.max(1, reliability || 0);
        }
        return acc;
    }, { confidences: [], reliabilities: [], edges: [], entropies: [], sectors: {} });

    const macroBand = percentileBand(idxAvgMove, indices.map((item) => Math.abs(Number(item?.change_percent || item?.change || 0))), ['Calm', 'Balanced', 'High']);
    const reliabilityMean = predictionMetrics.reliabilities.length
        ? predictionMetrics.reliabilities.reduce((sum, val) => sum + val, 0) / predictionMetrics.reliabilities.length
        : 0;
    const confidenceMean = predictionMetrics.confidences.length
        ? predictionMetrics.confidences.reduce((sum, val) => sum + val, 0) / predictionMetrics.confidences.length
        : 0;
    const entropyMean = predictionMetrics.entropies.length
        ? predictionMetrics.entropies.reduce((sum, val) => sum + val, 0) / predictionMetrics.entropies.length
        : 0;
    const edgeMean = predictionMetrics.edges.length
        ? predictionMetrics.edges.reduce((sum, val) => sum + val, 0) / predictionMetrics.edges.length
        : 0;
    const stability = riskFromPortfolio == null
        ? (reliabilityMean >= 60 ? 'Stable' : reliabilityMean >= 35 ? 'Watch' : 'Fragile')
        : (riskFromPortfolio <= 0.25 ? 'Stable' : riskFromPortfolio <= 0.5 ? 'Watch' : 'Fragile');
    const allocationStance = (() => {
        const regimeText = String(regime || '').toUpperCase();
        const postureScore = ((confidenceMean * 0.35) + (reliabilityMean * 0.35) + ((100 - entropyMean) * 0.15) + (Math.max(edgeMean, 0) * 5));
        if (/CRISIS|BEAR|RISK|PANIC/.test(regimeText) || postureScore < 40) return 'Defensive';
        if (/TREND|BULL|MOMENTUM/.test(regimeText) && postureScore >= 60) return 'Pro-Growth';
        return 'Balanced';
    })();

    const topSectors = (() => {
        const sectorwise = dashState?.newsSectorwise || {};
        const entries = Object.entries(sectorwise || {}).map(([key, rows]) => {
            const list = Array.isArray(rows) ? rows : [];
            const score = list.length
                ? list.reduce((sum, item) => sum + Number(item?.impact_score ?? item?.impact_strength ?? 0), 0) / list.length
                : 0;
            return [key, Number.isFinite(score) ? score * 100 : 0];
        });
        const fallbackEntries = Object.entries(predictionMetrics.sectors || {}).map(([key, value]) => [key, Number(value)]);
        const source = entries.length ? entries : fallbackEntries;
        if (!source.length) return 'Building sector map';
        return source
            .filter(([, value]) => Number.isFinite(value))
            .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
            .slice(0, 2)
            .map(([key, value]) => `${String(key).toUpperCase()}: ${Number(value).toFixed(1)}`)
            .join(' | ');
    })();

    const mpi = Number(newsIntel.market_pressure_index);
    const mpiAbs = Number.isFinite(mpi) ? Math.abs(mpi) * 100 : null;
    const geoMacroPressure = Number.isFinite(mpiAbs)
        ? Math.max(0, Math.min(100, ((100 - reliabilityMean) * 0.35) + (macroBand.pct * 0.25) + ((100 - sentimentScore) * 0.15) + (mpiAbs * 0.25)))
        : Math.max(0, Math.min(100, ((100 - reliabilityMean) * 0.45) + (macroBand.pct * 0.35) + ((100 - sentimentScore) * 0.20)));
    const geoMacroLabel = percentileBand(geoMacroPressure, [0, geoMacroPressure, 100], ['Contained', 'Moderate', 'Elevated']).label;
    const positions = window.NEURAL_STATE?.portfolio_intelligence?.positions || [];
    const avgConfidence = positions.length ? positions.reduce((s, p) => s + Number(p.confidence || 0), 0) / positions.length : confidenceMean;
    const avgEdge = positions.length ? positions.reduce((s, p) => s + Number(p.edge || 0), 0) / positions.length : edgeMean;
    const avgEntropy = positions.length ? positions.reduce((s, p) => s + Number(p.entropy || 0), 0) / positions.length : entropyMean;
    const avgRisk = positions.length ? positions.reduce((s, p) => s + Number(p.risk || 0), 0) / positions.length : Math.max(0, 1 - (reliabilityMean / 100));

    const sessionHeat = marketStatus === 'OPEN' ? 85 : reliabilityMean || 45;
    const regimeHeat = reliabilityMean || confidenceMean || 50;
    const macroHeat = macroBand.pct;
    const riskHeat = Math.max(0, Math.min(100, (1 - Number(avgRisk || 0)) * 100));
    const allocHeat = allocationStance === 'Pro-Growth' ? Math.max(confidenceMean, reliabilityMean) : allocationStance === 'Balanced' ? 55 : Math.max(20, 100 - reliabilityMean);
    const sectorHeat = (() => {
        const values = Object.values(predictionMetrics.sectors).map(Number).filter(Number.isFinite);
        if (!values.length) return 30;
        return Math.max(0, Math.min(100, values.reduce((a, b) => a + b, 0) / values.length));
    })();

    // 8-card comprehensive layer with heat bars
    grid.innerHTML = [
        worldStateCard('Market Hours', marketStatus, `Next open: ${nextOpen}`, marketStatus === 'OPEN' ? 'var(--electric-green)' : 'var(--electric-yellow)', sessionHeat),
        worldStateCard('AI Reading', regime, `${activeModels} models active`, 'var(--electric-purple)', regimeHeat),
        worldStateCard('Market Move', `${macroBand.label} (${idxAvgMove.toFixed(2)}%)`, 'How much the indexes are moving', 'var(--electric-cyan)', macroHeat),
        worldStateCard('News Mood', `${sentimentLabel} ${sentimentScore.toFixed(1)}%`, 'What live news is saying', sentimentScore >= 60 ? 'var(--electric-green)' : sentimentScore <= 40 ? 'var(--electric-red)' : 'var(--electric-yellow)', sentimentScore),
        worldStateCard('Risk Level', stability, riskFromPortfolio == null ? 'Waiting for live portfolio risk' : `Average risk ${(riskFromPortfolio).toFixed(3)}`, 'var(--electric-red)', riskHeat),
        worldStateCard('Sizing Mood', allocationStance, 'How aggressive sizing should be', allocationStance === 'Defensive' ? 'var(--electric-red)' : allocationStance === 'Pro-Growth' ? 'var(--electric-green)' : 'var(--electric-yellow)', allocHeat),
        worldStateCard('Global Pressure', `${geoMacroLabel} ${geoMacroPressure.toFixed(0)}%`, Number.isFinite(mpi) ? `MPI ${mpi > 0 ? '+' : ''}${mpi.toFixed(2)} · ${humanizeToken(newsIntel.market_pressure_bias || 'Neutral')}` : 'Global markets, news and risk blend', geoMacroPressure >= 65 ? 'var(--electric-red)' : geoMacroPressure >= 45 ? 'var(--electric-yellow)' : 'var(--electric-green)', 100 - geoMacroPressure),
        worldStateCard('Leading Sectors', topSectors, 'Sectors carrying the strongest live pulse', 'var(--electric-pink)', sectorHeat)
    ].join('');

    if (compass) {
        const clamp01 = (v) => Math.max(0, Math.min(1, Number(v || 0)));
        const conf01 = clamp01(avgConfidence > 1 ? avgConfidence / 100 : avgConfidence);
        const edge01 = clamp01(avgEdge);
        const risk01 = clamp01(avgRisk);
        const entropy01 = clamp01(avgEntropy);
        const sentiment01 = clamp01(sentimentScore / 100);
        const macro01 = clamp01(idxAvgMove / 2);
        const geo01 = clamp01(geoMacroPressure / 100);

        const shortScore = Math.max(0, Math.min(100, (conf01 * 35 + edge01 * 20 + sentiment01 * 15 + (1 - entropy01) * 15 + (1 - risk01) * 15) * 100));
        const mediumScore = Math.max(0, Math.min(100, (conf01 * 30 + edge01 * 25 + (1 - risk01) * 20 + (1 - geo01) * 15 + (1 - macro01) * 10) * 100));
        const longScore = Math.max(0, Math.min(100, ((1 - geo01) * 30 + (1 - risk01) * 25 + edge01 * 20 + conf01 * 15 + sentiment01 * 10) * 100));

        const posture = shortScore >= 65 && mediumScore >= 60 ? 'GO' : (shortScore < 45 || mediumScore < 45 ? 'REDUCE' : 'BALANCED');
        const postureColor = posture === 'GO' ? 'var(--electric-green)' : posture === 'REDUCE' ? 'var(--electric-red)' : 'var(--electric-yellow)';

        const horizonBar = (label, score) => {
            const color = score >= 65 ? 'var(--electric-green)' : score >= 45 ? 'var(--electric-yellow)' : 'var(--electric-red)';
            return `
                <div style="display:grid; grid-template-columns:110px 1fr 56px; gap:8px; align-items:center; margin-top:6px;">
                    <div style="font-size:10px; color:#d7f5ff;">${label}</div>
                    <div style="height:7px; border-radius:999px; background:rgba(255,255,255,0.10); overflow:hidden;">
                        <div style="width:${score.toFixed(1)}%; height:100%; background:linear-gradient(90deg, rgba(255,7,58,0.8), rgba(255,241,0,0.85), rgba(57,255,20,0.85)); box-shadow:0 0 8px rgba(57,255,20,0.18);"></div>
                    </div>
                    <div style="font-size:10px; color:${color}; text-align:right; font-weight:700;">${score.toFixed(0)}%</div>
                </div>`;
        };

        const chip = (name, val, goodHigh = true) => {
            const score = Math.max(0, Math.min(100, Number(val || 0)));
            const good = goodHigh ? score >= 60 : score <= 40;
            const color = good ? 'var(--electric-green)' : score >= 45 && score <= 60 ? 'var(--electric-yellow)' : 'var(--electric-red)';
            return `<span style="display:inline-flex; align-items:center; gap:6px; padding:2px 8px; border:1px solid rgba(255,255,255,0.14); border-radius:999px; font-size:10px; color:${color};">${name} ${score.toFixed(0)}%</span>`;
        };

        compass.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
                <div style="color:var(--electric-cyan); font-weight:700; font-size:11px;">Futures Compass</div>
                <div style="font-size:11px; color:${postureColor}; font-weight:800;">AI Posture: ${posture}</div>
            </div>
            ${horizonBar('Near-Term Conviction', shortScore)}
            ${horizonBar('Medium-Term Conviction', mediumScore)}
            ${horizonBar('Structural Conviction', longScore)}
            <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:8px;">
                ${chip('Sentiment', sentimentScore, true)}
                ${chip('Risk', (riskFromPortfolio == null ? 50 : riskFromPortfolio * 100), false)}
                ${chip('Entropy', avgEntropy * 100, false)}
                ${chip('Geo', geoMacroPressure, false)}
            </div>
        `;
    }

    if (updatedAt) updatedAt.textContent = `Updated ${new Date().toLocaleTimeString()}`;
}

function escapeHtml(s) {
    return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

async function loadPortfolioTickerNews(symbol) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base) return [];
    const cached = window.__PF_NEWS_CACHE[base];
    if (cached && (Date.now() - cached.ts) < 30000) return cached.articles;
    try {
        const res = await fetch(`/api/news/symbol/${encodeURIComponent(base)}`);
        if (!res.ok) throw new Error(`news http ${res.status}`);
        const data = await res.json();
        const payload = Array.isArray(data) ? { articles: data } : (data || {});
        const articles = Array.isArray(payload.articles)
            ? payload.articles
            : (payload.news || payload.results || []);
        const companyName = String(payload.company_name || base);
        const sectorName = String(payload.sector || '').toLowerCase();
        const tokenStop = new Set(['limited', 'ltd', 'inc', 'company', 'industries', 'services', 'the', 'and', 'of']);
        const strictTokens = new Set([base.toLowerCase()]);
        companyName.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).forEach((t) => {
            if (t && t.length >= 4 && !tokenStop.has(t)) strictTokens.add(t);
        });
        const normalized = articles.map((a) => {
            const rawRel = Number(a.source_reliability ?? a.confidence ?? 0);
            const relPct = rawRel > 1 ? rawRel : rawRel * 100;
            const txt = `${a.title || ''} ${a.description || ''}`.toLowerCase();
            const strictHits = Array.from(strictTokens).reduce((acc, t) => acc + (txt.includes(t) ? 1 : 0), 0);
            const sectorHit = sectorName ? (txt.includes(sectorName) ? 1 : 0) : 0;
            const relType = String(a.relevance_type || '').toLowerCase();
            const strictBoost = relType === 'strict' ? 0.8 : 0;
            const primaryBoost = relType === 'primary' ? 0.5 : 0;
            const sectorPenalty = relType === 'sector' && strictHits === 0 ? 0.35 : 0;
            const ageBias = (() => {
                const ts = new Date(a.published || a.normalized_time || a.timestamp || 0).getTime();
                if (!ts) return 0;
                const ageH = Math.max(0, (Date.now() - ts) / 3600000);
                return Math.max(0, 0.35 - (ageH / 240)); // fades over ~10 days
            })();
            const score = (strictHits * 1.25) + (sectorHit * 0.20) + (relPct / 200) + strictBoost + primaryBoost + ageBias - sectorPenalty;
            return {
                ...a,
                source_reliability: Math.max(0, Math.min(100, relPct)),
                _score: score,
                _strict_hits: strictHits
            };
        });
        normalized.sort((x, y) => Number(y._score || 0) - Number(x._score || 0));
        const strictFirst = normalized.filter((a) => {
            const relType = String(a.relevance_type || '').toLowerCase();
            const strictHits = Number(a._strict_hits || 0);
            return strictHits > 0 || relType === 'strict';
        });
        const sectorOnly = normalized.filter((a) => !strictFirst.includes(a));
        const strictPool = strictFirst.slice(0, 5);
        const selected = strictPool.length
            ? [...strictPool, ...sectorOnly.slice(0, Math.max(0, 5 - strictPool.length))]
            : sectorOnly.slice(0, 5);

        // De-dupe near-identical headlines from mixed feeds
        const seenTitles = new Set();
        const uniqueSelected = selected.filter((a) => {
            const key = String(a.title || a.headline || '').trim().toLowerCase();
            if (!key) return false;
            if (seenTitles.has(key)) return false;
            seenTitles.add(key);
            return true;
        }).slice(0, 5);

        const ranked = uniqueSelected.map((a) => {
            const cleaned = { ...a };
            delete cleaned._score;
            delete cleaned._strict_hits;
            return cleaned;
        });
        window.__PF_NEWS_CACHE[base] = { ts: Date.now(), articles: ranked };
        return window.__PF_NEWS_CACHE[base].articles;
    } catch {
        window.__PF_NEWS_CACHE[base] = { ts: Date.now(), articles: [] };
        return window.__PF_NEWS_CACHE[base].articles;
    }
}

function formatNewsAge(ts) {
    const d = new Date(ts || '');
    if (isNaN(d.getTime())) return 'Now';
    const sec = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
    if (sec < 60) return `${sec}s ago`;
    if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
    return `${Math.floor(sec / 86400)}d ago`;
}

async function loadSymbolMeta(symbol) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base) return { name: base, sector: '' };
    if (window.__PF_SYMBOL_META_CACHE[base]) return window.__PF_SYMBOL_META_CACHE[base];
    try {
        const r = await fetch(`/api/search?q=${encodeURIComponent(base)}&limit=1`);
        if (!r.ok) throw new Error(`meta http ${r.status}`);
        const data = await r.json();
        const rows = Array.isArray(data) ? data : (data.results || []);
        const one = rows[0] || {};
        let sector = one.sector || '';
        let name = one.name || base;
        if (!sector || /unknown/i.test(sector)) {
            try {
                const sr = await fetch('/api/stocks');
                if (sr.ok) {
                    const sd = await sr.json();
                    const list = Array.isArray(sd) ? sd : (sd.stocks || sd.results || []);
                    const hit = list.find(x => String(x.symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '') === base);
                    if (hit && hit.sector) sector = hit.sector;
                    if (!one.name && hit && hit.name) name = hit.name;
                }
            } catch { }
        }
        if (!sector || /unknown/i.test(sector) || !name || name === base) {
            try {
                const ar = await fetch(`/api/stock/analysis/${encodeURIComponent(base)}`);
                if (ar.ok) {
                    const ad = await ar.json();
                    const info = ad?.data || {};
                    if (info.company_name) name = info.company_name;
                    if (info.sector) sector = info.sector;
                }
            } catch { }
        }
        window.__PF_SYMBOL_META_CACHE[base] = {
            name: name || base,
            sector: sector || 'Unknown Industry'
        };
        return window.__PF_SYMBOL_META_CACHE[base];
    } catch {
        window.__PF_SYMBOL_META_CACHE[base] = { name: base, sector: 'Unknown Industry' };
        return window.__PF_SYMBOL_META_CACHE[base];
    }
}

async function loadPortfolioDeepData(symbol) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base) return null;
    const cached = window.__PF_DEEP_CACHE[base];
    if (cached && (Date.now() - cached.ts) < 120000) return cached.data;
    try {
        const r = await fetch(`/api/stock/analysis/${encodeURIComponent(base)}`);
        if (!r.ok) throw new Error(`deep http ${r.status}`);
        const data = await r.json();
        const deep = data?.data || {};
        window.__PF_DEEP_CACHE[base] = { ts: Date.now(), data: deep };
        if (deep.company_name || deep.sector) {
            const old = window.__PF_SYMBOL_META_CACHE[base] || {};
            window.__PF_SYMBOL_META_CACHE[base] = {
                name: deep.company_name || old.name || base,
                sector: deep.sector || old.sector || 'Unknown Industry'
            };
        }
        return deep;
    } catch {
        window.__PF_DEEP_CACHE[base] = { ts: Date.now(), data: {} };
        return window.__PF_DEEP_CACHE[base].data;
    }
}

async function loadPortfolioLotInsights(symbol) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base) return null;
    const cached = window.__PF_LOT_INSIGHTS_CACHE[base];
    if (cached && (Date.now() - cached.ts) < 60000) return cached.data;
    try {
        const r = await fetch(`/api/portfolio/lot-insights?symbol=${encodeURIComponent(base)}&days=60`);
        if (!r.ok) throw new Error(`lot insights http ${r.status}`);
        const payload = await r.json();
        const data = payload?.data || {};
        window.__PF_LOT_INSIGHTS_CACHE[base] = { ts: Date.now(), data };
        if (data?.fy_summary) {
            window.__PF_TAX_SUMMARY_CACHE = { ts: Date.now(), data: data.fy_summary };
        }
        return data;
    } catch {
        window.__PF_LOT_INSIGHTS_CACHE[base] = { ts: Date.now(), data: { open_lots: [], all_lots: [], near_ltcg: [], fy_summary: null } };
        return window.__PF_LOT_INSIGHTS_CACHE[base].data;
    }
}

async function loadPortfolioTaxSummary(force = false) {
    const cached = window.__PF_TAX_SUMMARY_CACHE;
    if (!force && cached && (Date.now() - cached.ts) < 120000) return cached.data;
    try {
        const r = await fetch('/api/portfolio/tax-summary');
        if (!r.ok) throw new Error(`tax summary http ${r.status}`);
        const payload = await r.json();
        const data = payload?.data || null;
        window.__PF_TAX_SUMMARY_CACHE = { ts: Date.now(), data };
        return data;
    } catch {
        return cached?.data || null;
    }
}

async function loadPortfolioSellSimulation(symbol, quantity, sellPrice) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    const qty = Number(quantity || 0);
    const px = Number(sellPrice || 0);
    if (!base || qty <= 0 || px <= 0) return null;
    const key = `${base}|${Math.round(qty * 1000) / 1000}|${Math.round(px * 100) / 100}`;
    const cached = window.__PF_SELL_SIM_CACHE[key];
    if (cached && (Date.now() - cached.ts) < 60000) return cached.data;
    if (window.__PF_SELL_SIM_LOADING[key]) return window.__PF_SELL_SIM_LOADING[key];
    window.__PF_SELL_SIM_LOADING[key] = (async () => {
        try {
            const ctl = new AbortController();
            const t = setTimeout(() => ctl.abort(), 10000);
            const r = await fetch('/api/portfolio/sell/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: base,
                    qty: qty,
                    sell_price: px,
                    methods: ['FIFO', 'LIFO', 'HIFO']
                }),
                signal: ctl.signal
            });
            clearTimeout(t);
            if (!r.ok) throw new Error(`sell sim http ${r.status}`);
            const payload = await r.json();
            const data = payload?.data || null;
            window.__PF_SELL_SIM_CACHE[key] = { ts: Date.now(), data };
            return data;
        } catch {
            window.__PF_SELL_SIM_CACHE[key] = { ts: Date.now(), data: null };
            return null;
        } finally {
            delete window.__PF_SELL_SIM_LOADING[key];
        }
    })();
    return window.__PF_SELL_SIM_LOADING[key];
}

async function loadPortfolioRealizedJournal(symbol, force = false) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base) return [];
    const cached = window.__PF_REALIZED_JOURNAL_CACHE[base];
    if (!force && cached && (Date.now() - cached.ts) < 60000) return cached.data || [];
    try {
        const r = await fetch(`/api/portfolio/realized-gains?symbol=${encodeURIComponent(base)}&limit=150`);
        if (!r.ok) throw new Error(`realized journal http ${r.status}`);
        const payload = await r.json();
        const rows = Array.isArray(payload?.data) ? payload.data : [];
        window.__PF_REALIZED_JOURNAL_CACHE[base] = { ts: Date.now(), data: rows, cursor: payload?.cursor || '0', next_cursor: payload?.next_cursor || null, total: Number(payload?.total || rows.length) };
        return rows;
    } catch {
        return cached?.data || [];
    }
}

async function loadPortfolioIntelligenceSuite(force = false) {
    const cached = window.__PF_INTEL_SUITE_CACHE;
    if (!force && cached && cached.data && (Date.now() - cached.ts) < 60000) return cached.data;
    if (!force && cached && !cached.data && (Date.now() - cached.ts) < 10000) return null;
    if (window.__PF_INTEL_SUITE_LOADING) return cached?.data || null;
    window.__PF_INTEL_SUITE_LOADING = true;
    try {
        const r = await fetch('/api/portfolio/intelligence-suite');
        if (!r.ok) throw new Error(`intelligence suite http ${r.status}`);
        const payload = await r.json();
        const data = payload?.data || null;
        window.__PF_INTEL_SUITE_CACHE = { ts: Date.now(), data };
        return data;
    } catch {
        window.__PF_INTEL_SUITE_CACHE = { ts: Date.now(), data: null };
        return cached?.data || null;
    } finally {
        window.__PF_INTEL_SUITE_LOADING = false;
    }
}

async function togglePortfolioExpand(symbol) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base) return;
    if (window.__PF_EXPANDED_PINNED && window.__PF_EXPANDED_SYMBOL && window.__PF_EXPANDED_SYMBOL !== base) {
        return;
    }
    if (window.__PF_EXPANDED_SYMBOL === base) {
        if (!window.__PF_EXPANDED_PINNED) window.__PF_EXPANDED_SYMBOL = null;
    } else {
        window.__PF_EXPANDED_SYMBOL = base;
    }
    renderPortfolio();
    if (window.__PF_EXPANDED_SYMBOL) {
        Promise.allSettled([
            loadPortfolioTickerNews(base),
            loadSymbolMeta(base),
            loadPortfolioDeepData(base),
            loadPortfolioLotInsights(base),
            loadPortfolioRealizedJournal(base)
        ]).then(() => {
            if (window.__PF_EXPANDED_SYMBOL === base) renderPortfolio();
        });
    }
}

function togglePortfolioPin(symbol) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base || window.__PF_EXPANDED_SYMBOL !== base) return;
    window.__PF_EXPANDED_PINNED = !window.__PF_EXPANDED_PINNED;
    renderPortfolio();
}

function attachMetricTooltip(el, defKey) {
    if (!el || el.dataset.tipBound === '1') return;
    el.dataset.tipBound = '1';
    el.style.cursor = 'help';
    el.addEventListener('mouseenter', (e) => {
        const defs = metricDefsFromState();
        const metric = defs[defKey];
        if (!metric) return;
        renderMetricTooltip(metric);
        const tip = ensureMetricTooltipEl();
        tip.style.left = `${Math.min(window.innerWidth - 280, e.clientX + 14)}px`;
        tip.style.top = `${Math.min(window.innerHeight - 130, e.clientY + 14)}px`;
    });
    el.addEventListener('mousemove', (e) => {
        const tip = ensureMetricTooltipEl();
        if (tip.style.display === 'block') {
            tip.style.left = `${Math.min(window.innerWidth - 280, e.clientX + 14)}px`;
            tip.style.top = `${Math.min(window.innerHeight - 130, e.clientY + 14)}px`;
        }
    });
    el.addEventListener('mouseleave', hideMetricTooltip);
}

function ensureMetricTooltips() {
    if (window.__NEXUS_METRIC_TOOLTIP_READY) return;
    ensurePortfolioAlertStyles();
    ensureMetricTooltipEl();

    const ths = Array.from(document.querySelectorAll('th'));
    ths.forEach((th) => {
        const txt = (th.textContent || '').toUpperCase().trim();
        if (txt.includes('CONFIDENCE')) attachMetricTooltip(th, 'confidence');
        else if (txt === 'EDGE' || txt.startsWith('EDGE')) attachMetricTooltip(th, 'edge');
        else if (txt.includes('ENTROPY')) attachMetricTooltip(th, 'entropy');
        else if (txt.includes('KELLY')) attachMetricTooltip(th, 'kelly');
        else if (txt === 'RISK' || txt.startsWith('RISK')) attachMetricTooltip(th, 'risk');
    });
    window.__NEXUS_METRIC_TOOLTIP_READY = true;
}

function scoreColor(score) {
    if (score >= 7) return 'var(--electric-green)';
    if (score >= 4) return 'var(--electric-yellow)';
    return 'var(--electric-red)';
}

function ensurePortfolioCardAssist() {
    const defs = metricDefsFromState();
    const map = [
        { id: 'portfolioEdgeValue', key: 'portfolio_edge' },
        { id: 'portfolioRiskValue', key: 'portfolio_risk' },
        { id: 'regimeFitValue', key: 'regime_fit' }
    ];
    map.forEach(({ id, key }) => {
        const v = document.getElementById(id);
        if (!v || !v.parentElement) return;
        const card = v.parentElement;
        card.style.minHeight = '120px';
        card.style.display = 'flex';
        card.style.flexDirection = 'column';
        card.style.justifyContent = 'space-between';
        const label = card.querySelector('.label');
        if (label) {
            label.style.fontWeight = '700';
            label.style.color = 'var(--electric-yellow)';
            label.style.letterSpacing = '0.3px';
        }

        let explain = card.querySelector('.pf-card-explain');
        if (!explain) {
            explain = document.createElement('div');
            explain.className = 'pf-card-explain';
            explain.style.marginTop = '8px';
            explain.style.fontSize = '10px';
            explain.style.color = 'var(--text-muted)';
            card.appendChild(explain);
        }
        const m = defs[key];
        const sc = clamp10(m?.score || 0);
        const col = scoreColor(sc);
        v.style.color = col;
        explain.innerHTML = `
            <div style="color:${col}; font-size:10px; margin-bottom:3px;">${m?.desc || ''} <span style="color:#bfe9ff;">${m?.better || ''}</span></div>
            <div style="height:4px; border-radius:999px; background:rgba(255,255,255,0.08); overflow:hidden;">
                <div style="height:100%; width:${(sc / 10) * 100}%; background:${col}; box-shadow:0 0 8px ${col};"></div>
            </div>
            <div style="margin-top:3px; color:var(--text-muted);">${sc >= 7 ? 'Strong' : sc >= 4 ? 'Balanced' : 'Weak'} reading</div>
        `;
    });
}

function calcHoldingDays(addedDate) {
    const d = new Date(addedDate || '');
    if (isNaN(d.getTime())) return 0;
    return Math.max(0, Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24)));
}

function formatInr(v) {
    return `₹${Number(v || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function humanizeToken(v) {
    const t = String(v || '').replace(/_/g, ' ').trim();
    if (!t) return '';
    return t.split(' ').map(x => x.charAt(0).toUpperCase() + x.slice(1).toLowerCase()).join(' ');
}

function setElementText(id, value, color = null) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = value;
    if (color) el.style.color = color;
}

function getDashboardPortfolioEmptyMetrics() {
    const positions = Array.isArray(window.NEURAL_STATE?.portfolio_intelligence?.positions)
        ? window.NEURAL_STATE.portfolio_intelligence.positions
        : [];
    const stocks = Array.isArray(dashState.stocks) ? dashState.stocks : [];
    const baselineRisk = positions.length || stocks.length ? 'Low' : 'Awaiting';
    return {
        portfolioValue: formatInr(0),
        dayPnl: `${formatInr(0)}`,
        risk: baselineRisk
    };
}

function setDashboardPortfolioEmptyState() {
    const metrics = getDashboardPortfolioEmptyMetrics();
    setElementText('portfolioValue', metrics.portfolioValue, 'var(--electric-cyan)');
    setElementText('portfolioChange', '--', 'var(--text-secondary)');
    setElementText('dayPnl', metrics.dayPnl, 'var(--text-secondary)');
    setElementText('riskLevel', metrics.risk, metrics.risk === 'Low' ? 'var(--electric-green)' : 'var(--text-secondary)');
}

function deriveSidebarAIPerformance(aiPerformance = {}, state = null) {
    const rows = Array.isArray(window.__INTEL_PRED_ROWS) && window.__INTEL_PRED_ROWS.length
        ? window.__INTEL_PRED_ROWS
        : (Array.isArray(dashState.predictions) ? dashState.predictions : []);
    const aiEngine = state?.cognitive_state || state?.ai_engine || window.NEURAL_STATE?.cognitive_state || window.NEURAL_STATE?.ai_engine || {};
    const accuracyRaw =
        aiPerformance?.accuracy ??
        aiPerformance?.prediction_accuracy ??
        state?.ai_performance?.accuracy ??
        state?.ai_engine?.accuracy ??
        aiEngine?.accuracy ??
        aiEngine?.market_state?.system_confidence;
    let accuracy = Number(accuracyRaw);
    if (Number.isFinite(accuracy) && accuracy <= 1) accuracy *= 100;

    let modelsActive = Number(aiPerformance?.models_active ?? state?.ai_performance?.models_active);
    if (!Number.isFinite(modelsActive) || modelsActive <= 0) {
        const engineModels = Array.isArray(aiEngine?.active_models) ? aiEngine.active_models : [];
        modelsActive = Number(aiEngine?.models_active ?? (Array.isArray(engineModels) ? engineModels.length : 0));
    }
    if (!Number.isFinite(modelsActive) || modelsActive <= 0) {
        const modelPool = rows.flatMap((row) => Array.isArray(row?.models_used) ? row.models_used : []);
        modelsActive = new Set(modelPool.filter(Boolean)).size;
    }

    let dataPoints = Number(aiPerformance?.data_points ?? aiPerformance?.total_data_points ?? aiPerformance?.data_points_min);
    if (!Number.isFinite(dataPoints) || dataPoints <= 0) {
        dataPoints = rows.length || Number(aiEngine?.data_points || aiEngine?.predictions_today || aiEngine?.total_predictions || 0) || 0;
    }

    return {
        accuracy: Number.isFinite(accuracy) && accuracy > 0 ? `${accuracy.toFixed(1)}%` : '--',
        modelsActive: Number.isFinite(modelsActive) && modelsActive > 0 ? String(Math.round(modelsActive)) : '--',
        dataPoints: Number.isFinite(dataPoints) && dataPoints > 0 ? Math.round(dataPoints).toLocaleString('en-IN') : '--'
    };
}

function updateSidebarAIPerformance(aiPerformance = {}, state = null) {
    const derived = deriveSidebarAIPerformance(aiPerformance, state);
    setElementText('predictionAccuracy', derived.accuracy, derived.accuracy === '--' ? 'var(--text-secondary)' : 'var(--electric-green)');
    setElementText('modelsActive', derived.modelsActive, derived.modelsActive === '--' ? 'var(--text-secondary)' : 'var(--electric-cyan)');
    setElementText('dataPoints', derived.dataPoints, derived.dataPoints === '--' ? 'var(--text-secondary)' : 'var(--electric-cyan)');
}

function updateDashboardPortfolioCardsFromPI(pi) {
    const positions = Array.isArray(pi?.positions) ? pi.positions : [];
    if (!positions.length) {
        setDashboardPortfolioEmptyState();
        updateDashboardMarketIntelligenceCard();
        updateDashboardPortfolioSnapshotCard(pi);
        updateDashboardMarketPulseCard();
        return false;
    }

    updateDashboardPortfolioSnapshotCard(pi);
    updateDashboardMarketIntelligenceCard();
    updateDashboardMarketPulseCard();
    
    updateDashboardAllocationChartFromPositions(positions);
    syncV7DashboardIframe(dashState.data || {});

    return true;
}

// 🕐 Helper function to calculate and display relative time (e.g., "1 min ago")
function getRelativeTime(timestamp) {
    if (!timestamp) return 'just now';
    const now = Date.now();
    const diff = now - timestamp;
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (seconds < 60) return 'just now';
    if (minutes < 60) return `${minutes} min${minutes > 1 ? 's' : ''} ago`;
    if (hours < 24) return `${hours}h ${minutes % 60}m ago`;
    return `${days}d ago`;
}

// 🔄 Update card timestamp display
function updateCardTimestamp(elementId, timestamp) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = getRelativeTime(timestamp);
    }
}

function parseNumericValue(value) {
    if (value === null || value === undefined || value === '') return 0;
    if (typeof value === 'number') return Number(value);
    const normalized = String(value).trim().replace(/,/g, '').replace('%', '');
    return Number.isFinite(Number(normalized)) ? Number(normalized) : 0;
}

function format12HourTime(timeStr) {
    if (!timeStr) return '--';
    const trimmed = String(timeStr).trim();
    const match = trimmed.match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
    if (match) {
        let hour = Number(match[1]);
        const minute = String(match[2]).padStart(2, '0');
        const ampm = hour >= 12 ? 'PM' : 'AM';
        hour = hour % 12 || 12;
        return `${hour}:${minute} ${ampm}`;
    }
    return trimmed;
}

function computeCloseMessage(status, closeTime) {
    if (!closeTime || status !== 'OPEN') return '--';
    try {
        const now = new Date();
        const [hour, minute] = String(closeTime).split(':').map(Number);
        const target = new Date(now);
        target.setHours(hour, minute, 0, 0);
        if (target <= now) target.setDate(target.getDate() + 1);
        const diff = target - now;
        const hours = Math.floor(diff / 3600000);
        const mins = Math.floor((diff % 3600000) / 60000);
        return `Closes in ${hours}h ${mins}m`;
    } catch (e) {
        return String(closeTime);
    }
}

function normalizeAndExtractDashboardData(rawData = {}) {
    const data = rawData || {};
    const marketStatusRaw = data.market_status || {};
    const session = String(marketStatusRaw.session || marketStatusRaw.current_time || '').trim();
    const marketOpen = String(marketStatusRaw.market_open_time || marketStatusRaw.open_time || '').trim();
    const marketClose = String(marketStatusRaw.market_close_time || marketStatusRaw.close_time || '').trim();
    const nextOpenRaw = String(marketStatusRaw.next_open || data.next_open || '').trim();
    const statusRaw = String(marketStatusRaw.status || marketStatusRaw.market_state || '').trim().toUpperCase();
    let status = statusRaw;
    if (!status) {
        const now = new Date();
        if (marketOpen && marketClose) {
            const [openH, openM] = marketOpen.split(':').map(Number);
            const [closeH, closeM] = marketClose.split(':').map(Number);
            const openMoment = new Date(now);
            openMoment.setHours(openH, openM, 0, 0);
            const closeMoment = new Date(now);
            closeMoment.setHours(closeH, closeM, 0, 0);
            status = (now >= openMoment && now < closeMoment) ? 'OPEN' : 'CLOSED';
        } else {
            status = 'CLOSED';
        }
    }
    const displayTime = session || new Date().toLocaleTimeString('en-IN', { hour12: false });
    const closingTimeText = computeCloseMessage(status, marketClose);
    const nextOpen = nextOpenRaw ? `${nextOpenRaw}${marketOpen ? ` | ${format12HourTime(marketOpen)}` : ''}` : '--';

    const normalized = {
        market_status: {
            status,
            market: marketStatusRaw.market || marketStatusRaw.exchange || 'NSE',
            session: displayTime,
            next_open: nextOpen,
            closing_time: closingTimeText === '--' ? '--' : closingTimeText,
            open_time: marketOpen,
            close_time: marketClose
        },
        news_intelligence: {
            market_regime: String(data.news_intelligence?.market_regime || data.market_intelligence?.regime || data.regime || 'SYNCHRONIZING').toUpperCase(),
            regime_confidence: parseNumericValue(data.news_intelligence?.regime_confidence || data.market_intelligence?.confidence || data.confidence || 0),
            market_pressure_index: parseNumericValue(data.news_intelligence?.market_pressure_index || data.market_intelligence?.mpi || data.mpi || 0)
        },
        market_sentiment: {
            vix: parseNumericValue(data.market_sentiment?.vix || data.sentiment?.volatility_index || data.vix || 0),
            vix_change: parseNumericValue(data.market_sentiment?.vix_change || data.sentiment?.vix_change || data.vix_change || 0),
            label: String(data.market_sentiment?.label || data.sentiment?.label || data.sentiment_label || 'NEUTRAL').toUpperCase()
        },
        macro: {
            global_sync: Array.isArray(data.macro?.global_sync) ? data.macro.global_sync
                : Array.isArray(data.market_data?.indices) ? data.market_data.indices
                : Array.isArray(data.global_sync) ? data.global_sync
                : Array.isArray(data.indices) ? data.indices
                : [],
            live_indices: Array.isArray(data.live_indices) ? data.live_indices
                : Array.isArray(data.market_data?.indices) ? data.market_data.indices
                : Array.isArray(data.indices) ? data.indices
                : Array.isArray(data.global_sync) ? data.global_sync
                : [],
            commodities: Array.isArray(data.macro?.commodities) ? data.macro.commodities
                : Array.isArray(data.market_data?.commodities) ? data.market_data.commodities
                : Array.isArray(data.commodities) ? data.commodities
                : [],
            forex: Array.isArray(data.macro?.forex) ? data.macro.forex
                : Array.isArray(data.market_data?.forex) ? data.market_data.forex
                : Array.isArray(data.forex) ? data.forex
                : Array.isArray(data.fx) ? data.fx
                : Array.isArray(data.fx_rates) ? data.fx_rates
                : [],
            crypto: Array.isArray(data.macro?.crypto) ? data.macro.crypto
                : Array.isArray(data.market_data?.crypto) ? data.market_data.crypto
                : Array.isArray(data.crypto) ? data.crypto
                : Array.isArray(data.cryptocurrencies) ? data.cryptocurrencies
                : [],
            interest_rates: Array.isArray(data.macro?.interest_rates) ? data.macro.interest_rates
                : Array.isArray(data.market_data?.interest_rates) ? data.market_data.interest_rates
                : Array.isArray(data.interest_rates) ? data.interest_rates
                : Array.isArray(data.rates) ? data.rates
                : Array.isArray(data.rate_cards) ? data.rate_cards
                : [],
            macro_watch: Array.isArray(data.macro?.macro_watch) ? data.macro.macro_watch
                : Array.isArray(data.macro_watch) ? data.macro_watch
                : [],
            details: {
                gdp: data.macro?.gdp || data.macro?.gdp_growth || data.gdp || data.gdp_growth || data.economy?.gdp || null,
                inflation: data.macro?.inflation || data.macro?.inflation_rate || data.inflation || data.inflation_rate || data.economy?.inflation || null
            }
        }
    };

    console.log('🔍 normalizeAndExtractDashboardData OUTPUT:', {
        market_status: normalized.market_status,
        news_intelligence: normalized.news_intelligence,
        market_sentiment: normalized.market_sentiment,
        macro: {
            commodities: normalized.macro.commodities.length,
            forex: normalized.macro.forex.length,
            crypto: normalized.macro.crypto.length,
            interest_rates: normalized.macro.interest_rates.length
        }
    });

    return normalized;
}

function updateDashboardMarketIntelligenceCard(passedData = null) {
    // 🛡️ FRONTEND GUARD: Prevent UI clearing if partial data is passed
    const rawData = passedData || dashState?.data || window.dashState?.data || {};
    
    // If incoming data is empty/null but we have existing data in dashState, use the existing one
    const hasNewData = rawData && (rawData.live_indices?.length > 0 || rawData.macro?.commodities?.length > 0);
    const useData = (hasNewData) ? rawData : (dashState.data || rawData);

    const normalized = normalizeAndExtractDashboardData(useData);
    
    const marketStatus = normalized.market_status;
    const newsIntel = normalized.news_intelligence;
    const sentiment = normalized.market_sentiment;
    const macro = normalized.macro;
    
    console.log('🔍 Extracted values for display:', {
        status: marketStatus.status,
        session: marketStatus.session,
        regime: newsIntel.market_regime,
        confidence: newsIntel.regime_confidence,
        sentiment_label: sentiment.label,
        vix: sentiment.vix,
        mpi: newsIntel.market_pressure_index,
        commodities_array: macro.commodities,
        forex_array: macro.forex,
        crypto_array: macro.crypto
    });

    const statusVal = document.getElementById('marketStatusVal');
    const nextEventVal = document.getElementById('nextEventVal');
    const regimeVal = document.getElementById('marketRegimeVal');
    const sentimentVal = document.getElementById('globalSentimentVal');
    const mpiVal = document.getElementById('mpiVal');
    const globalSyncVal = document.getElementById('globalSyncVal');

    // Market Status with time info
    const status = String(marketStatus.status || 'CLOSED').toUpperCase();
    const statusPieces = [`${status} (${marketStatus.market || 'NSE'})`];
    if (marketStatus.session) statusPieces.push(marketStatus.session);
    if (status === 'OPEN' && marketStatus.closing_time && marketStatus.closing_time !== '--') {
        statusPieces.push(marketStatus.closing_time);
    }
    if (statusVal) {
        statusVal.innerHTML = statusPieces.join(' | ');
        statusVal.className = `market-status-hero val ${status === 'OPEN' ? 'green' : 'red'}`;
        console.log('✅ Set statusVal to:', statusVal.innerHTML);
    }

    // Next Event
    if (nextEventVal) {
        nextEventVal.textContent = String(marketStatus.next_open || '--');
        console.log('✅ Set nextEventVal to:', nextEventVal.textContent);
    }

    // Market Regime
    const regime = (newsIntel.market_regime && newsIntel.market_regime !== 'SYNCHRONIZING') ? newsIntel.market_regime : (window.NEURAL_STATE?.ai_engine?.regime || 'SYNCHRONIZING');
    const regimeUpper = String(regime || '').toUpperCase();
    const regimeBias = /BUY|UP|BULL|TREND|STRENGTH|MOMENTUM/.test(regimeUpper)
        ? 1
        : (/SELL|DOWN|BEAR|CRISIS|WEAK|RISK/.test(regimeUpper) ? -1 : 0);
    const rawConfidence = Number(newsIntel.regime_confidence || 0);
    const confidence = rawConfidence <= 1 ? rawConfidence * 100 : rawConfidence;
    if (regimeVal) {
        const confText = confidence > 0 ? ` (${Math.round(confidence)}% conf)` : '';
        regimeVal.textContent = `${regime}${confText}`;
        regimeVal.className = `metric-value val ${regimeBias > 0 ? 'green' : regimeBias < 0 ? 'red' : 'yellow'}`;
        console.log('✅ Set regimeVal to:', regimeVal.textContent);
    }

    // Global Sentiment
    const vix = Number(sentiment.vix || 0).toFixed(2);
    const vixChange = Number(sentiment.vix_change || 0);
    const vixChangeStr = vixChange !== 0 ? ` ${vixChange >= 0 ? '↑' : '↓'} ${Math.abs(vixChange).toFixed(2)}%` : '';
    const sentLabel = String(sentiment.label || 'NEUTRAL').toUpperCase();
    const sentimentBias = /BULL|EARLY|RISK-ON|POSITIVE|OPTIMISTIC/.test(sentLabel)
        ? 1
        : (/BEAR|RISK-OFF|NEGATIVE|FEAR|CAUTION/.test(sentLabel) ? -1 : 0);
    if (sentimentVal) {
        const sentColor = sentimentBias > 0 ? 'green' : (sentimentBias < 0 ? 'red' : 'yellow');
        sentimentVal.innerHTML = `<span class="${sentColor}">${sentLabel}</span> (VIX: ${vix}${vixChangeStr})`;
        console.log('✅ Set sentimentVal to:', sentimentVal.innerHTML);
    }

    // MPI
    const mpi = Number(newsIntel.market_pressure_index || 0);
    const mpiBias = String(
        useData?.news_intelligence?.market_pressure_bias ||
        useData?.market_intelligence?.market_pressure_bias ||
        useData?.market_pressure_bias ||
        useData?.mpi_label ||
        ''
    ).trim();
    const mpiLabel = mpiBias ? humanizeToken(mpiBias) : '';
    const mpiBiasVote = /BULL|BUY|UP|POSITIVE|RISK-ON/.test(String(mpiLabel || '').toUpperCase())
        ? 1
        : (/BEAR|SELL|DOWN|NEGATIVE|RISK-OFF/.test(String(mpiLabel || '').toUpperCase()) ? -1 : (mpi > 0 ? 1 : mpi < 0 ? -1 : 0));
    if (mpiVal) {
        mpiVal.innerHTML = `${mpi.toFixed(2)}${mpiLabel ? ` (${escapeHtml(mpiLabel)})` : ''}`;
        const biasText = String(mpiLabel || '').toUpperCase();
        mpiVal.className = `val ${/BULL|BUY|UP|POSITIVE|RISK-ON/.test(biasText) ? 'green' : (/BEAR|SELL|DOWN|NEGATIVE|RISK-OFF/.test(biasText) ? 'red' : 'cyan')}`;
        console.log('✅ Set mpiVal to:', mpiVal.innerHTML);
    }

    const mpiPressureFill = document.getElementById('mpiPressureFill');
    if (mpiPressureFill) {
        const mpiPct = Number.isFinite(mpi) ? Math.max(0, Math.min(100, Math.abs(mpi) <= 1 ? mpi * 100 : mpi)) : 0;
        mpiPressureFill.style.width = `${mpiPct}%`;
        mpiPressureFill.style.background = mpiVal?.classList?.contains('red')
            ? 'linear-gradient(90deg, rgba(255,7,58,0.25), var(--electric-red))'
            : mpiVal?.classList?.contains('green')
                ? 'linear-gradient(90deg, rgba(57,255,20,0.25), var(--electric-green))'
                : 'linear-gradient(90deg, rgba(0,255,255,0.18), var(--electric-cyan))';
    }

    const marketCoverageVal = document.getElementById('marketCoverageVal');
    if (marketCoverageVal) {
        const modelCountRaw = useData?.ai_performance?.models_active ?? useData?.ai_engine?.models_active ?? [];
        const modelCount = Array.isArray(modelCountRaw) ? modelCountRaw.length : Number(modelCountRaw);
        const indexCount = Array.isArray(macro.live_indices) ? macro.live_indices.length : 0;
        const newsCount = Array.isArray(dashState.news) ? dashState.news.length : 0;
        const pieces = [
            Number.isFinite(modelCount) && modelCount > 0 ? `${Math.round(modelCount)} models` : null,
            indexCount > 0 ? `${indexCount} indices` : null,
            newsCount > 0 ? `${newsCount} news signals` : null
        ].filter(Boolean);
        marketCoverageVal.textContent = pieces.length ? pieces.join(' | ') : 'Live context is warming up';
    }

    const marketQualityVal = document.getElementById('marketQualityVal');
    if (marketQualityVal) {
        const coveragePieces = [
            Array.isArray(macro.live_indices) && macro.live_indices.length ? `${macro.live_indices.length} index feeds` : null,
            Array.isArray(macro.commodities) && macro.commodities.length ? `${macro.commodities.length} commodity feeds` : null,
            Array.isArray(macro.forex) && macro.forex.length ? `${macro.forex.length} FX feeds` : null,
            Array.isArray(macro.crypto) && macro.crypto.length ? `${macro.crypto.length} crypto feeds` : null,
            Array.isArray(dashState.news) && dashState.news.length ? `${dashState.news.length} news events` : null
        ].filter(Boolean);
        marketQualityVal.textContent = coveragePieces.length ? coveragePieces.join(' | ') : 'Live source coverage is warming up';
    }

    const portfolioImpactVal = document.getElementById('portfolioImpactVal');
    if (portfolioImpactVal) {
        const alerts = Array.isArray(dashState.portfolioNewsAlerts) ? dashState.portfolioNewsAlerts : [];
        const symbols = [...new Set(alerts.flatMap(a => Array.isArray(a.symbols) ? a.symbols : [a.symbol]).filter(Boolean))];
        portfolioImpactVal.textContent = symbols.length
            ? `Portfolio-sensitive: ${symbols.slice(0, 4).join(', ')}${symbols.length > 4 ? ` +${symbols.length - 4}` : ''}`
            : 'No portfolio-specific news pressure detected';
    }

    const marketDecisionVal = document.getElementById('marketDecisionVal');
    if (marketDecisionVal) {
        const votes = [
            { name: 'Regime', value: regimeBias },
            { name: 'Sentiment', value: sentimentBias },
            { name: 'MPI', value: mpiBiasVote }
        ].filter(vote => vote.value !== 0);
        const netVote = votes.reduce((sum, vote) => sum + vote.value, 0);
        const stance = netVote > 0 ? 'Risk-on alignment' : netVote < 0 ? 'Risk-off pressure' : 'Mixed tape';
        const evidence = votes.map(vote => `${vote.name}:${vote.value > 0 ? 'up' : 'down'}`).join(' | ');
        const heldCount = Array.isArray(window.NEURAL_STATE?.portfolio_intelligence?.positions)
            ? window.NEURAL_STATE.portfolio_intelligence.positions.length
            : 0;
        marketDecisionVal.textContent = `${stance}${evidence ? ` from ${evidence}` : ''}${heldCount ? ` | ${heldCount} holdings cross-checked` : ' | Portfolio map waiting for holdings'}`;
        marketDecisionVal.className = `metric-subline strong ${netVote > 0 ? 'green' : netVote < 0 ? 'red' : 'yellow'}`;
    }

    const toNumeric = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
    const formatPrice = (value, currency = '₹') => `${currency}${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
    const formatPercent = (value) => {
        const num = toNumeric(value);
        const sign = num >= 0 ? '+' : '↓';
        return `${sign}${Math.abs(num).toFixed(2)}%`;
    };
    const formatIndex = (item) => {
        if (!item) return null;
        const name = String(item.name || item.symbol || item.ticker || '').trim();
        const value = toNumeric(item.value ?? item.level ?? item.last ?? item.price ?? 0);
        const change = toNumeric(item.change_percent ?? item.change ?? item.change_pct ?? item.delta ?? 0);
        const arrow = change >= 0 ? '+' : '↓';
        const valueText = value ? Number(value).toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '--';
        return `${name} ${valueText} (${arrow}${Math.abs(change).toFixed(2)}%)`;
    };

    // Global Sync (market indices)
    if (globalSyncVal) {
        const sources = [...(macro.global_sync || []), ...(macro.live_indices || [])];
        const findIndex = (...matches) => sources.find(item => {
            const name = String(item.name || item.symbol || '').toUpperCase();
            return matches.some(match => name.includes(match));
        });
        const order = [
            ['S&P', 'S&P 500'],
            ['NASDAQ'],
            ['DOW', 'DOW JONES', 'DJIA'],
            ['NSE', 'NIFTY', 'NIFTY 50']
        ];
        let syncItems = order.map(names => findIndex(...names)).filter(Boolean);
        if (!syncItems.length) syncItems = sources.slice(0, 4);
        const uniqueItems = [];
        syncItems.forEach(item => {
            const key = String(item.name || item.symbol || '').toUpperCase();
            if (key && !uniqueItems.some(existing => String(existing.name || existing.symbol || '').toUpperCase() === key)) {
                uniqueItems.push(item);
            }
        });
        const syncHtml = uniqueItems.map(formatIndex).filter(Boolean).join(' | ');
        globalSyncVal.innerHTML = syncHtml || '--';
        globalSyncVal.className = `metric-subline strong val ${uniqueItems.some(item => toNumeric(item.change_percent ?? item.change ?? item.change_pct ?? 0) < 0) ? 'red' : 'green'}`;
        console.log('✅ Set globalSyncVal to:', globalSyncVal.innerHTML);
    }

    // Macro commodities display
    const commoditiesVal = document.getElementById('commoditiesVal');
    const commoditiesEnergyVal = document.getElementById('commoditiesEnergyVal');
    const commodities = Array.isArray(macro.commodities) ? macro.commodities : [];
    const gold = commodities.find(c => String(c.symbol || '').toUpperCase() === 'GOLD' || String(c.name || '').toUpperCase().includes('GOLD'));
    const silver = commodities.find(c => String(c.symbol || '').toUpperCase() === 'SILVER' || String(c.name || '').toUpperCase().includes('SILVER'));
    const crude = commodities.find(c => String(c.symbol || '').toUpperCase() === 'CRUDE' || String(c.name || '').toUpperCase().includes('CRUDE'));
    const naturalGas = commodities.find(c => String(c.name || '').toUpperCase().includes('GAS'));
    const coal = commodities.find(c => String(c.name || '').toUpperCase().includes('COAL'));

    if (commoditiesVal) {
        const lines = [];
        if (gold) lines.push(`Gold ${formatPrice(gold.value, '₹')} ${formatPercent(gold.change_percent ?? gold.change ?? 0)}`);
        if (silver) lines.push(`Silver ${formatPrice(silver.value, '₹')} ${formatPercent(silver.change_percent ?? silver.change ?? 0)}`);
        commoditiesVal.innerHTML = lines.length ? lines.join(' | ') : '--';
        commoditiesVal.className = `val ${lines.some(line => line.includes('↓')) ? 'red' : lines.length ? 'green' : ''}`;
        console.log('✅ Set commoditiesVal to:', commoditiesVal.innerHTML);
    }
    if (commoditiesEnergyVal) {
        const energyItems = commodities.filter(i => {
            const n = (i.name || i.symbol || '').toUpperCase();
            return n.includes('CRUDE') || n.includes('GAS') || n.includes('COAL') || n.includes('OIL');
        });
        
        // Format exactly as requested: Crude | Natural Gas | Coal
        const crude = energyItems.find(i => (i.name || '').toUpperCase().includes('CRUDE'));
        const gas = energyItems.find(i => (i.name || '').toUpperCase().includes('GAS'));
        const coal = energyItems.find(i => (i.name || '').toUpperCase().includes('COAL'));
        
        const lines = [];
        if (crude) lines.push(`Crude ${formatPrice(crude.value, '$')} ${formatPercent(crude.change_percent ?? 0)}`);
        if (gas) lines.push(`Natural Gas ${formatPrice(gas.value, '$')} ${formatPercent(gas.change_percent ?? 0)}`);
        if (coal) lines.push(`Coal ${formatPrice(coal.value, '$')} ${formatPercent(coal.change_percent ?? 0)}`);
        
        commoditiesEnergyVal.innerHTML = lines.length ? lines.join(' | ') : '--';
        commoditiesEnergyVal.className = `val ${lines.some(l => l.includes('↓')) ? 'red' : 'green'}`;
        console.log('✅ Set Energy to:', commoditiesEnergyVal.innerHTML);
    }

    // Macro forex display
    const forexVal = document.getElementById('forexVal');
    if (forexVal) {
        const forex = Array.isArray(macro.forex) ? macro.forex : [];
        const usd = forex.find(f => /USDINR|USD\/?INR|USD/.test(String(f.symbol || f.name || '').toUpperCase()));
        const gbp = forex.find(f => /GBP|POUND/.test(String(f.symbol || f.name || '').toUpperCase()));
        const eur = forex.find(f => /EUR|EURO/.test(String(f.symbol || f.name || '').toUpperCase()));
        const pairs = [
            usd ? `USD/INR ${toNumeric(usd.value).toFixed(2)} ${formatPercent(usd.change_percent ?? usd.change ?? usd.change_pct ?? 0)}` : null,
            gbp ? `GBP/INR ${toNumeric(gbp.value).toFixed(2)} ${formatPercent(gbp.change_percent ?? gbp.change ?? gbp.change_pct ?? 0)}` : null,
            eur ? `EUR/INR ${toNumeric(eur.value).toFixed(2)} ${formatPercent(eur.change_percent ?? eur.change ?? eur.change_pct ?? 0)}` : null
        ].filter(Boolean);
        forexVal.innerHTML = pairs.length ? pairs.join(' | ') : '--';
        forexVal.className = `val ${pairs.some(pair => pair.includes('↓')) ? 'red' : pairs.length ? 'green' : ''}`;
        console.log('✅ Set forexVal to:', forexVal.innerHTML);
    }

    const dashboardMacroVal = document.getElementById('dashboardMacroVal');
    if (dashboardMacroVal) {
        const forex = Array.isArray(macro.forex) ? macro.forex : [];
        const commoditiesList = Array.isArray(macro.commodities) ? macro.commodities : [];
        const rates = Array.isArray(macro.interest_rates) ? macro.interest_rates : [];
        const usd = forex.find(f => /USD|DXY|DOLLAR/.test(String(f.symbol || f.name || '').toUpperCase()));
        const crudeDriver = commoditiesList.find(c => /CRUDE|OIL/.test(String(c.symbol || c.name || '').toUpperCase()));
        const leadRate = rates.find(r => /RBI|REPO|INDIA/.test(String(r.symbol || r.name || '').toUpperCase())) || rates[0];
        const macroPieces = [
            usd ? `${escapeHtml(usd.symbol || usd.name || 'USD')} ${toNumeric(usd.value ?? usd.rate ?? 0).toFixed(2)} ${formatPercent(usd.change_percent ?? usd.change ?? usd.change_pct ?? 0)}` : null,
            crudeDriver ? `${escapeHtml(crudeDriver.symbol || crudeDriver.name || 'Crude')} ${formatPrice(crudeDriver.value ?? crudeDriver.price ?? 0, '$')} ${formatPercent(crudeDriver.change_percent ?? crudeDriver.change ?? 0)}` : null,
            leadRate ? `${escapeHtml(leadRate.symbol || leadRate.name || 'Rate')} ${toNumeric(leadRate.value ?? leadRate.rate ?? 0).toFixed(2)} ${formatPercent(leadRate.change_percent ?? leadRate.change ?? 0)}` : null
        ].filter(Boolean);
        dashboardMacroVal.innerHTML = macroPieces.length ? macroPieces.join(' | ') : 'Live macro feed syncing';
        dashboardMacroVal.className = `val ${macroPieces.some(piece => piece.includes('â†“')) ? 'red' : macroPieces.length ? 'green' : 'yellow'}`;
    }

    // Macro crypto display
    const cryptoVal = document.getElementById('cryptoVal');
    if (cryptoVal) {
        const crypto = Array.isArray(macro.crypto) ? macro.crypto : [];
        const btc = crypto.find(c => String(c.symbol || '').toUpperCase() === 'BTC' || String(c.name || '').toUpperCase().includes('BITCOIN'));
        const eth = crypto.find(c => String(c.symbol || '').toUpperCase() === 'ETH' || String(c.name || '').toUpperCase().includes('ETHEREUM'));
        const cryptoLines = [btc, eth].filter(Boolean).map(item => {
            const change = toNumeric(item.change_percent ?? item.change ?? 0);
            const delta = toNumeric(item.value ?? 0) * (change / 100);
            const sign = change >= 0 ? '+' : '↓';
            const cls = change >= 0 ? 'green' : 'red';
            return `<span class="${cls}">${item.symbol || item.name} ${formatPrice(item.value, '$')} ${sign}${Math.abs(change).toFixed(1)}% (${delta >= 0 ? '+' : '↓'}${formatPrice(Math.abs(delta), '$')})</span>`;
        });
        cryptoVal.innerHTML = cryptoLines.length ? cryptoLines.join(' | ') : '--';
        cryptoVal.className = `val ${cryptoLines.some(line => line.includes('↓')) ? 'red' : cryptoLines.length ? 'green' : ''}`;
        console.log('✅ Set cryptoVal to:', cryptoVal.innerHTML);
    }

    // Macro interest rates and GDP/Inflation
    const interestRatesVal = document.getElementById('interestRatesVal');
    if (interestRatesVal) {
        const rates = Array.isArray(macro.interest_rates) ? macro.interest_rates : [];
        const sortedRates = [...rates].sort((a, b) => {
            const score = (item) => {
                const label = String(item.name || item.symbol || '').toUpperCase();
                if (label.includes('INDIA') || label.includes('RBI') || label.includes('REPO')) return 0;
                if (label.includes('UK') || label.includes('GILT')) return 1;
                if (label.includes('US 10Y')) return 2;
                if (label.includes('US 5Y') || label.includes('FED')) return 3;
                return 4;
            };
            return score(a) - score(b);
        }).slice(0, 3);
        const rateRows = sortedRates.map(item => {
            const change = toNumeric(item.change_percent ?? item.change ?? 0);
            const sign = change >= 0 ? '+' : '↓';
            const cls = change >= 0 ? 'green' : 'red';
            const name = item.name || item.symbol || 'Rate';
            const value = toNumeric(item.value ?? item.rate ?? 0).toFixed(2);
            return `<span class="${cls}">${name} ${value} ${sign}${Math.abs(change).toFixed(2)}%</span>`;
        });
        interestRatesVal.innerHTML = rateRows.length ? rateRows.join(' | ') : '--';
        interestRatesVal.className = `val ${rateRows.some(row => row.includes('↓')) ? 'red' : rateRows.length ? 'green' : ''}`;
        console.log('✅ Set interestRatesVal to:', interestRatesVal.innerHTML);
    }

    const macroDetailsVal = document.getElementById('macroDetailsVal');
    if (macroDetailsVal) {
        const drivers = macro.macro_watch || [];
        if (drivers.length) {
            macroDetailsVal.innerHTML = drivers.join(' | ');
            // "Inflation ↑ Sticky | Growth Weak | Liquidity Tight"
            const isNegative = drivers.some(d => d.toLowerCase().includes('sticky') || 
                                               d.toLowerCase().includes('contraction') || 
                                               d.toLowerCase().includes('tight') ||
                                               d.toLowerCase().includes('weak'));
            macroDetailsVal.className = `val ${isNegative ? 'red' : 'green'}`;
        } else {
            // Fallback to legacy derivation if new drivers missing
            const perf = dashState?.data?.ai_performance || {};
            const mpiNum = Number(perf.market_pressure_index);
            macroDetailsVal.innerHTML = Number.isFinite(mpiNum)
                ? `MPI Pressure ${mpiNum.toFixed(2)} | Synchronising Drivers...`
                : 'Synchronising live macro drivers...';
            macroDetailsVal.className = 'val yellow';
        }
        console.log('✅ Set macroDetailsVal to:', macroDetailsVal.innerHTML);
    }

    // Update timestamps
    updateCardTimestamp('marketIntelligenceTimestamp', dashState?.lastUpdate?.dashboard);
}

function renderDashboardPortfolioCommand(pi, positions, metrics, totalValue, totalInvested) {
    const valueEl = document.getElementById('pfTotalValueVal');
    const positionsEl = document.getElementById('pfPositionsVal');
    const breadthBar = document.getElementById('pfBreadthBar');
    const gainerEl = document.getElementById('pfTopGainerVal');
    const loserEl = document.getElementById('pfTopLoserVal');
    const exposureEl = document.getElementById('pfExposureVal');
    const riskEl = document.getElementById('pfRiskVal');
    const alertEl = document.getElementById('pfTopAlertVal');
    const computedDayPnl = totalValue - totalInvested;
    const dayPnlValue = Number(metrics?.day_pnl ?? metrics?.daily_pnl ?? metrics?.today_pnl ?? metrics?.pnl_today ?? computedDayPnl);
    const dayPnlPct = Number(metrics?.day_pnl_percent ?? metrics?.daily_pnl_percent ?? metrics?.today_pnl_percent ?? metrics?.pnl_today_percent ?? (totalInvested > 0 ? (computedDayPnl / totalInvested * 100) : 0));
    const dailyClass = dayPnlValue >= 0 ? 'green' : 'red';

    if (valueEl) {
        valueEl.innerHTML = `${formatInr(totalValue)} <span class="${dailyClass}">${dayPnlValue >= 0 ? '+' : ''}${Number.isFinite(dayPnlPct) ? dayPnlPct.toFixed(2) : '--'}% today</span>`;
    }

    const breadth = positions.reduce((acc, p) => {
        const change = Number(p.change_percent || p.day_change_percent || 0);
        if (change > 0) acc.green += 1;
        else if (change < 0) acc.red += 1;
        else acc.flat += 1;
        return acc;
    }, { green: 0, red: 0, flat: 0 });
    if (positionsEl) {
        positionsEl.textContent = positions.length
            ? `${positions.length} stocks | ${breadth.green} green | ${breadth.red} red | ${breadth.flat} flat`
            : 'No active positions';
    }
    if (breadthBar) {
        const total = Math.max(positions.length, 1);
        breadthBar.innerHTML = `
            <span class="breadth-green" style="width:${(breadth.green / total) * 100}%"></span>
            <span class="breadth-flat" style="width:${(breadth.flat / total) * 100}%"></span>
            <span class="breadth-red" style="width:${(breadth.red / total) * 100}%"></span>
        `;
    }

    if (gainerEl) {
        const top = positions.length ? [...positions].sort((a, b) => Number(b.change_percent || 0) - Number(a.change_percent || 0))[0] : null;
        if (top) {
            const symbol = String(top.symbol || '').replace('.NS', '').replace('.BO', '');
            const change = Number(top.change_percent || 0);
            const price = Number(top.current_price || top.price || 0);
            gainerEl.innerHTML = `<span class="${change >= 0 ? 'green' : 'red'}">${escapeHtml(symbol)} ${change >= 0 ? '+' : ''}${change.toFixed(2)}%</span>${price > 0 ? ` at ${formatInr(price)}` : ''} <span class="terminal-inline-link" onclick="event.stopPropagation(); window.dashboard?.showStockDetails?.('${escapeHtml(symbol)}')">View</span>`;
        } else {
            gainerEl.textContent = '--';
        }
    }

    if (loserEl) {
        const bottom = positions.length ? [...positions].sort((a, b) => Number(a.change_percent || 0) - Number(b.change_percent || 0))[0] : null;
        if (bottom) {
            const symbol = String(bottom.symbol || '').replace('.NS', '').replace('.BO', '');
            const change = Number(bottom.change_percent || 0);
            const price = Number(bottom.current_price || bottom.price || 0);
            loserEl.innerHTML = `<span class="${change >= 0 ? 'green' : 'red'}">${escapeHtml(symbol)} ${change >= 0 ? '+' : ''}${change.toFixed(2)}%</span>${price > 0 ? ` at ${formatInr(price)}` : ''} <span class="terminal-inline-link" onclick="event.stopPropagation(); window.dashboard?.showStockDetails?.('${escapeHtml(symbol)}')">View</span>`;
        } else {
            loserEl.textContent = '--';
        }
    }

    if (exposureEl) {
        const exposure = positions
            .map(p => {
                const value = Number(p.market_value ?? p.current_value ?? ((p.current_price || p.price || p.avg_price || 0) * (p.quantity || 0)));
                return { symbol: String(p.symbol || '').replace('.NS', '').replace('.BO', ''), value: Number.isFinite(value) ? value : 0 };
            })
            .filter(item => item.symbol && item.value > 0)
            .sort((a, b) => b.value - a.value);
        const topExposure = exposure[0];
        exposureEl.textContent = topExposure && totalValue > 0
            ? `${topExposure.symbol} ${(topExposure.value / totalValue * 100).toFixed(1)}% of live value`
            : 'Exposure map builds after live prices arrive';
    }

    if (riskEl) {
        const risks = positions.map(p => Number(p.risk ?? p.risk_score)).filter(Number.isFinite);
        const edges = positions.map(p => Number(p.edge ?? p.predicted_return ?? p.expected_return)).filter(Number.isFinite);
        const confidences = positions.map(p => Number(p.confidence ?? p.confidence_score)).filter(Number.isFinite);
        const avg = (items) => items.length ? items.reduce((sum, value) => sum + value, 0) / items.length : null;
        const avgRisk = avg(risks);
        const avgEdge = avg(edges);
        const avgConfidence = avg(confidences);
        const riskText = avgRisk == null ? (metrics?.risk_level || metrics?.risk || 'Risk model syncing') : `Risk ${avgRisk.toFixed(3)}`;
        const edgeText = avgEdge == null ? null : `Edge ${avgEdge >= 0 ? '+' : ''}${avgEdge.toFixed(2)}`;
        const confText = avgConfidence == null ? null : `Conf ${avgConfidence.toFixed(avgConfidence > 1 ? 0 : 2)}${avgConfidence > 1 ? '%' : ''}`;
        riskEl.textContent = [riskText, edgeText, confText].filter(Boolean).join(' | ');
    }

    if (alertEl) {
        const portfolioAlerts = Array.isArray(dashState.portfolioNewsAlerts) ? dashState.portfolioNewsAlerts : [];
        const alert = portfolioAlerts[0] || pi?.top_alert || null;
        if (alert && typeof alert === 'object') {
            const symbols = Array.isArray(alert.symbols) ? alert.symbols.join(', ') : (alert.symbol || '');
            alertEl.innerHTML = `<span class="yellow">${escapeHtml(symbols || 'Portfolio')}</span> ${escapeHtml(alert.title || alert.headline || 'Live alert')} <span class="terminal-inline-link" onclick="event.stopPropagation(); document.querySelector('[data-tab=\\'news\\']')?.click()">Details</span>`;
        } else {
            alertEl.textContent = alert || 'No critical portfolio alerts detected.';
        }
    }
}

function updateDashboardPortfolioSnapshotCard(pi = {}) {
    // 🛡️ FRONTEND GUARD: Don't clear if incoming data is empty
    let positions = Array.isArray(pi?.positions) ? pi.positions : [];
    if (!positions.length && window.NEURAL_STATE?.portfolio_intelligence?.positions?.length) {
        pi = window.NEURAL_STATE.portfolio_intelligence;
        positions = pi.positions;
    }
    
    const valueEl = document.getElementById('pfTotalValueVal');
    const positionsEl = document.getElementById('pfPositionsVal');
    const investedEl = null;
    const gainerEl = document.getElementById('pfTopGainerVal');
    const alertEl = document.getElementById('pfTopAlertVal');

    const metrics = pi?.account_metrics || {};
    
    let totalInvested = 0;
    let totalValue = 0;
    
    positions.forEach(pos => {
        const costBasis = (pos.avg_price || pos.buy_price || 0) * (pos.quantity || 0);
        const currentValue = (pos.current_price || pos.price || 0) * (pos.quantity || 0);
        totalInvested += costBasis;
        totalValue += currentValue;
    });

    const totalPnL = totalValue - totalInvested;
    const pnlPercent = totalInvested > 0 ? (totalPnL / totalInvested * 100) : 0;
    const computedDayPnl = totalValue - totalInvested;
    const dayPnlValue = metrics.day_pnl ?? metrics.daily_pnl ?? metrics.today_pnl ?? metrics.pnl_today ?? computedDayPnl;
    const dayPnlPct = metrics.day_pnl_percent ?? metrics.daily_pnl_percent ?? metrics.today_pnl_percent ?? metrics.pnl_today_percent ?? (totalInvested > 0 ? (computedDayPnl / totalInvested * 100) : 0);
    renderDashboardPortfolioCommand(pi, positions, metrics, totalValue, totalInvested);
    updateCardTimestamp('portfolioSnapshotTimestamp', dashState?.lastUpdate?.portfolio);
    return;

    if (investedEl) investedEl.textContent = `₹${Math.round(totalInvested).toLocaleString('en-IN')}`;
    if (valueEl) valueEl.textContent = `₹${Math.round(totalValue).toLocaleString('en-IN')}`;
    if (valueEl) {
        const cls = dayPnlValue >= 0 ? 'green' : 'red';
        valueEl.innerHTML = `${formatInr(totalValue)} <span class="${cls}">(${dayPnlValue >= 0 ? '+' : ''}${Number(dayPnlPct || 0).toFixed(2)}% today)</span>`;
    }
    if (positionsEl) {
        const green = positions.filter(p => Number(p.change_percent || p.day_change_percent || 0) > 0).length;
        const red = positions.filter(p => Number(p.change_percent || p.day_change_percent || 0) < 0).length;
        const flat = Math.max(0, positions.length - green - red);
        positionsEl.textContent = positions.length
            ? `${positions.length} stocks (${green} green, ${red} red, ${flat} flat)`
            : 'No active positions';
    }
    if (false && dailyPnlEl) {
        const cls = dayPnlValue >= 0 ? 'green' : 'red';
        const arrow = dayPnlValue >= 0 ? '↑' : '↓';
        dailyPnlEl.innerHTML = `<span class="${cls}" style="font-weight:700;">${arrow} ₹${Math.round(Math.abs(dayPnlValue)).toLocaleString('en-IN')} (${dayPnlValue >= 0 ? '+' : ''}${dayPnlPct.toFixed(2)}%)</span>`;
    }
    if (false && pnlEl) {
        const cls = totalPnL >= 0 ? 'green' : 'red';
        const arrow = totalPnL >= 0 ? '↑' : '↓';
        pnlEl.innerHTML = `<span class="${cls}" style="font-weight:700;">${arrow} ₹${Math.round(Math.abs(totalPnL)).toLocaleString('en-IN')} (${totalPnL >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%)</span>`;
    }

    if (gainerEl) {
        if (positions.length > 0) {
            const top = [...positions].sort((a,b) => (b.change_percent || 0) - (a.change_percent || 0))[0];
            const cls = (top.change_percent || 0) >= 0 ? 'green' : 'red';
            const arrow = (top.change_percent || 0) >= 0 ? '↑' : '↓';
            gainerEl.innerHTML = `<span class="muted">${(top.symbol || '').replace('.NS', '').replace('.BO', '')}</span> <span class="${cls}">${arrow}${(top.change_percent || 0) >= 0 ? '+' : ''}${(top.change_percent || 0).toFixed(2)}%</span>`;
        } else {
            gainerEl.textContent = '--';
        }
    }

    if (gainerEl && positions.length > 0) {
        const top = [...positions].sort((a, b) => Number(b.change_percent || 0) - Number(a.change_percent || 0))[0];
        const cls = Number(top.change_percent || 0) >= 0 ? 'green' : 'red';
        const symbol = String(top.symbol || '').replace('.NS', '').replace('.BO', '');
        const price = Number(top.current_price || top.price || 0);
        gainerEl.innerHTML = `<span class="muted">${escapeHtml(symbol)}</span> <span class="${cls}">${Number(top.change_percent || 0) >= 0 ? '+' : ''}${Number(top.change_percent || 0).toFixed(2)}%</span>${price > 0 ? ` (${formatInr(price)})` : ''} <span class="terminal-inline-link" onclick="event.stopPropagation(); window.dashboard?.showStockDetails?.('${escapeHtml(symbol)}')">View</span>`;
    }

    if (alertEl) {
        const portfolioAlerts = Array.isArray(dashState.portfolioNewsAlerts) ? dashState.portfolioNewsAlerts : [];
        const alert = portfolioAlerts[0] || pi?.top_alert || null;
        if (alert && typeof alert === 'object') {
            const symbols = Array.isArray(alert.symbols) ? alert.symbols.join(', ') : (alert.symbol || '');
            alertEl.innerHTML = `<span class="yellow">${escapeHtml(symbols || 'Portfolio')}</span> ${escapeHtml(alert.title || alert.headline || 'Live alert')} <span class="terminal-inline-link" onclick="event.stopPropagation(); document.querySelector('[data-tab=\\'news\\']')?.click()">Details</span>`;
        } else {
            alertEl.textContent = alert || 'No critical portfolio alerts detected.';
        }
    }
    
    // Update timestamp for Portfolio Snapshot card
    updateCardTimestamp('portfolioSnapshotTimestamp', dashState?.lastUpdate?.portfolio);
}

async function updateDashboardMarketPulseCard() {
    const newsListEl = document.getElementById('dashboardNewsList');
    const summaryEl = document.getElementById('newsSummaryVal');
    if (!newsListEl) return;

    let articles = Array.isArray(dashState.news) ? dashState.news.slice() : [];
    const lastNewsTs = Number(dashState.lastUpdate?.news || 0);
    const newsAge = Number.isFinite(lastNewsTs) && lastNewsTs > 0 ? Date.now() - lastNewsTs : Infinity;
    if (!articles.length && newsAge > 0) {
        try {
            const response = await api.fetch('/news/market', { cache: false, timeout: 10000 });
            if (response && (response.articles || response.news || response.items)) {
                articles = response.articles || response.news || response.items || [];
                dashState.news = articles;
                dashState.lastUpdate.news = Date.now();
            }
        } catch (e) {
            console.warn("Market Pulse Update Error:", e?.message);
        }
    }

    const impactValues = (Array.isArray(articles) ? articles : [])
        .map(a => Number(a.impact_score ?? a.importance ?? a.impact_strength))
        .filter(Number.isFinite)
        .sort((a, b) => a - b);
    const rankImpact = (score) => {
        if (!impactValues.length || !Number.isFinite(score)) return { label: 'LIVE', color: 'var(--electric-cyan)' };
        const belowOrEqual = impactValues.filter(v => v <= score).length;
        const percentile = belowOrEqual / impactValues.length;
        if (percentile >= (impactValues.length - 1) / Math.max(impactValues.length, 1)) return { label: 'HIGH IMPACT', color: 'var(--electric-pink)' };
        if (percentile <= 1 / Math.max(impactValues.length, 1)) return { label: 'LOW IMPACT', color: 'var(--text-secondary)' };
        return { label: 'MARKET IMPACT', color: 'var(--electric-yellow)' };
    };
    const pulse = articles && Array.isArray(articles)
        ? articles.slice().sort((a, b) => Number(b.impact_score ?? b.importance ?? b.impact_strength ?? 0) - Number(a.impact_score ?? a.importance ?? a.impact_strength ?? 0)).slice(0, 3)
        : [];
    if (pulse.length === 0) {
        if (summaryEl) summaryEl.textContent = 'Live pulse map is waiting for verified market news.';
        newsListEl.innerHTML = `
            <div class="news-pulse-item" style="padding:1.25rem 1rem; text-align:center; color:var(--text-secondary);">
                <div style="font-size:10px; font-weight:800; margin-bottom:6px;">SYNCHRONISING PULSE...</div>
                <div style="font-weight:700;">Fetching live high-impact market intelligence...</div>
            </div>
        `;
        return;
    }

    const heldSymbols = new Set((window.NEURAL_STATE?.portfolio_intelligence?.positions || [])
        .map(p => String(p.symbol || '').toUpperCase().replace('.NS', '').replace('.BO', ''))
        .filter(Boolean));
    if (summaryEl) {
        const sectorScores = {};
        const portfolioHits = new Set();
        articles.forEach(article => {
            const score = Number(article.impact_score ?? article.importance ?? article.impact_strength ?? 0);
            const sectors = Array.isArray(article.affected_sectors) ? article.affected_sectors : (article.sector ? [article.sector] : []);
            sectors.filter(Boolean).forEach(sector => {
                const key = String(sector).trim();
                if (key) sectorScores[key] = (sectorScores[key] || 0) + (Number.isFinite(score) ? score : 0);
            });
            [
                ...(Array.isArray(article?.entities?.symbols) ? article.entities.symbols : []),
                ...(Array.isArray(article?.symbols) ? article.symbols : []),
                article.related_symbol || article.symbol || ''
            ].map(s => String(s || '').toUpperCase().replace('.NS', '').replace('.BO', '')).filter(Boolean)
                .forEach(symbol => { if (heldSymbols.has(symbol)) portfolioHits.add(symbol); });
        });
        const leadSectors = Object.entries(sectorScores)
            .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
            .slice(0, 3)
            .map(([sector]) => sector);
        const strongest = impactValues.length ? impactValues[impactValues.length - 1] : null;
        summaryEl.textContent = [
            `${articles.length} live news events`,
            strongest == null ? null : `top impact ${Number(strongest).toFixed(2)}`,
            leadSectors.length ? `sectors: ${leadSectors.join(' | ')}` : null,
            portfolioHits.size ? `portfolio: ${[...portfolioHits].slice(0, 4).join(', ')}` : 'no portfolio hit'
        ].filter(Boolean).join(' | ');
    }
    newsListEl.innerHTML = pulse.map(a => {
        const impactScore = Number(a.impact_score ?? a.importance ?? a.impact_strength);
        const impact = rankImpact(impactScore);
        const rawTime = a.time || a.timestamp || a.published_at || a.published || a.normalized_time || Date.now();
        const time = typeof rawTime === 'number' ? getRelativeTime(rawTime) : (formatNewsAge(rawTime) || String(rawTime));
        const url = (a.url || a.link || '#').replace(/'/g, "\\'");
        const title = (a.title || a.headline || 'Live market update').substring(0, 120);
        const symbols = [
            ...(Array.isArray(a?.entities?.symbols) ? a.entities.symbols : []),
            ...(Array.isArray(a?.symbols) ? a.symbols : []),
            a.related_symbol || a.symbol || ''
        ].map(s => String(s || '').toUpperCase().replace('.NS', '').replace('.BO', '')).filter(Boolean);
        const portfolioHits = [...new Set(symbols.filter(s => heldSymbols.has(s)))];
        const sectors = Array.isArray(a.affected_sectors) ? a.affected_sectors : (a.sector ? [a.sector] : []);
        const sentimentText = humanizeToken(a.sentiment || a.sentiment_label || 'Neutral');
        
        return `
            <div class="news-pulse-item" onclick="window.open('${url}', '_blank')">
                <div class="news-pulse-meta" style="color:${impact.color};">${impact.label} | ${escapeHtml(time)}</div>
                <div class="news-pulse-title">${escapeHtml(title)}</div>
                <div class="news-pulse-impact">Impact: ${escapeHtml(sectors.slice(0, 3).join(' | ') || 'Market')} | Sentiment: ${escapeHtml(sentimentText)}${portfolioHits.length ? ` | Portfolio: ${escapeHtml(portfolioHits.join(', '))}` : ''}</div>
            </div>
        `;
    }).join('');
    
    // Update timestamp for Market Pulse card
    updateCardTimestamp('marketPulseTimestamp', dashState?.lastUpdate?.news);
}

function updateDashboardAllocationChartFromPositions(positions) {
    try {
        if (!chart || !chart.data || !Array.isArray(chart.data.datasets) || !chart.data.datasets[0]) return false;

        const sectorTotals = {};
        positions.forEach((p) => {
            const sym = String(p.symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
            const meta = window.__PF_SYMBOL_META_CACHE?.[sym] || {};
            const rawSector = String(p.sector || meta.sector || 'Others').trim();
            const sector = rawSector || 'Others';
            const qty = Number(p.quantity || 0);
            const cp = Number(p.current_price || 0);
            const ap = Number(p.avg_price || 0);
            const value = Math.max(0, qty * (cp > 0 ? cp : ap));
            if (value <= 0) return;
            sectorTotals[sector] = (sectorTotals[sector] || 0) + value;
        });

        const entries = Object.entries(sectorTotals).sort((a, b) => b[1] - a[1]);
        if (!entries.length) return false;
        const top = entries.slice(0, 4);
        const others = entries.slice(4).reduce((s, [, v]) => s + v, 0);
        const finalEntries = others > 0 ? [...top, ['Others', others]] : top;

        const palette = ['#39FF14', '#00FFFF', '#FFFF00', '#FF1493', '#BF00FF', '#00E5FF'];
        chart.data.labels = finalEntries.map(([name]) => name);
        chart.data.datasets[0].data = finalEntries.map(([, val]) => Number(val.toFixed(2)));
        chart.data.datasets[0].backgroundColor = finalEntries.map((_, i) => palette[i % palette.length]);
        chart.update('none');
        return true;
    } catch (e) {
        console.warn('Allocation chart update skipped:', e?.message || e);
        return false;
    }
}

function updateDashboardAIPredictionCard(aiPerformance, state = null) {
    const aiPredEl = document.getElementById('aiPredictions');
    const accEl = document.getElementById('accuracyRate');
    const modelsEl = document.getElementById('totalModels');
    if (!aiPredEl && !accEl && !modelsEl) return;
    const aiEngine = state?.cognitive_state || state?.ai_engine || window.NEURAL_STATE?.cognitive_state || window.NEURAL_STATE?.ai_engine || {};

    const totalPred =
        Number(aiPerformance?.total_predictions) ||
        Number(aiPerformance?.predictions_today) ||
        Number(aiEngine?.predictions_today) ||
        Number(aiEngine?.data_points) ||
        (Array.isArray(window.__INTEL_PRED_ROWS) ? window.__INTEL_PRED_ROWS.length : 0) ||
        0;

    const accRaw =
        aiPerformance?.accuracy_percent ??
        aiPerformance?.accuracy ??
        aiPerformance?.prediction_accuracy?.percentage ??
        aiEngine?.accuracy ??
        aiEngine?.market_state?.system_confidence;
    let acc = Number(accRaw);
    if (Number.isFinite(acc) && acc <= 1) acc *= 100;
    if ((!Number.isFinite(acc) || acc <= 0) && Array.isArray(window.__INTEL_PRED_ROWS) && window.__INTEL_PRED_ROWS.length) {
        const confidences = window.__INTEL_PRED_ROWS
            .map((row) => Number(row?.confidence ?? row?.prediction?.confidence ?? 0))
            .filter((value) => Number.isFinite(value) && value > 0);
        if (confidences.length) {
            acc = confidences.reduce((sum, value) => sum + value, 0) / confidences.length;
        }
    }

    let modelCount = Number(aiPerformance?.models_active);
    if (!Number.isFinite(modelCount) || modelCount <= 0) {
        const models = aiEngine?.models_active || aiEngine?.active_models || aiPerformance?.active_models || [];
        modelCount = Array.isArray(models) ? models.length : Number(models || 0);
        if ((!Number.isFinite(modelCount) || modelCount <= 0) && Array.isArray(window.__INTEL_PRED_ROWS)) {
            modelCount = new Set(window.__INTEL_PRED_ROWS.flatMap((row) => Array.isArray(row?.prediction?.models_used) ? row.prediction.models_used : (Array.isArray(row?.models_used) ? row.models_used : []))).size;
        }
    }

    if (aiPredEl) aiPredEl.textContent = Number.isFinite(totalPred) && totalPred > 0 ? String(Math.round(totalPred)) : '--';
    if (accEl) {
        accEl.textContent = Number.isFinite(acc) && acc >= 0 ? `${acc.toFixed(1)}% Accuracy` : '--';
        accEl.style.color = Number.isFinite(acc) ? (acc >= 65 ? 'var(--electric-green)' : acc >= 45 ? 'var(--electric-yellow)' : 'var(--electric-red)') : 'var(--text-muted)';
    }
    if (modelsEl) modelsEl.textContent = Number.isFinite(modelCount) && modelCount > 0 ? String(Math.round(modelCount)) : '--';
    updateSidebarAIPerformance(aiPerformance, state);
}

function renderPortfolioAdvancedPanel(positions, accountMetrics = null) {
    const tab = document.getElementById('portfolio');
    if (!tab) return;
    const tableCard = tab.querySelector('.table-card.dense-table');
    if (!tableCard) return;

    let panel = document.getElementById('portfolioAdvancedPanel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'portfolioAdvancedPanel';
        panel.style.cssText = 'margin:4px 0 8px; display:grid; grid-template-columns:1fr 1fr; gap:8px;';
        tableCard.parentElement.insertBefore(panel, tableCard);
    }

    const rows = Array.isArray(positions) ? positions : [];
    if (!rows.length) {
        panel.innerHTML = '';
        return;
    }

    const flow = { increase: 0, hold: 0, reduce: 0 };
    const conviction = { high: 0, medium: 0, low: 0 };
    const bySector = {};
    const spreads = [];
    const vols = [];
    const entropyVals = [];
    const riskVals = [];

    rows.forEach((p) => {
        const action = String(p.action || 'HOLD').toUpperCase();
        const conf = Number(p.confidence || 0);
        const sector = String((window.__PF_SYMBOL_META_CACHE[p.symbol] || {}).sector || 'Unknown');
        const dayHigh = Number(p.day_high || 0);
        const dayLow = Number(p.day_low || 0);
        const price = Number(p.current_price || 0);
        const vol = Number(p.volume || 0);

        if (action === 'ADD' || action === 'BUY') flow.increase += 1;
        else if (action === 'REDUCE' || action === 'SELL') flow.reduce += 1;
        else flow.hold += 1;

        if (conf >= 60) conviction.high += 1;
        else if (conf >= 45) conviction.medium += 1;
        else conviction.low += 1;

        if (!bySector[sector]) bySector[sector] = { increase: 0, hold: 0, reduce: 0 };
        if (action === 'ADD' || action === 'BUY') bySector[sector].increase += 1;
        else if (action === 'REDUCE' || action === 'SELL') bySector[sector].reduce += 1;
        else bySector[sector].hold += 1;

        if (dayHigh > 0 && dayLow > 0 && price > 0) spreads.push((dayHigh - dayLow) / price);
        if (vol > 0) vols.push(vol);
        entropyVals.push(Number(p.entropy || 0));
        riskVals.push(Number(p.risk || 0));
    });

    const count = rows.length;
    const barW = (n) => `${Math.max(3, Math.round((n / Math.max(1, count)) * 100))}%`;
    const topSectors = Object.entries(bySector)
        .map(([name, v]) => ({ name, net: v.increase - v.reduce, total: v.increase + v.hold + v.reduce, v }))
        .sort((a, b) => Math.abs(b.net) - Math.abs(a.net))
        .slice(0, 4);
    const unknownNet = (bySector.Unknown?.increase || 0) - (bySector.Unknown?.reduce || 0);

    const median = (arr) => {
        const a = arr.filter(Number.isFinite).sort((x, y) => x - y);
        if (!a.length) return 0;
        const m = Math.floor(a.length / 2);
        return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
    };
    const spreadMed = median(spreads);
    const volMed = median(vols);
    const riskAvg = riskVals.reduce((s, v) => s + v, 0) / Math.max(1, riskVals.length);
    const entropyAvg = entropyVals.reduce((s, v) => s + v, 0) / Math.max(1, entropyVals.length);
    const windowScore = clamp01((1 - Math.min(1, spreadMed * 20)) * 0.45 + (1 - Math.min(1, riskAvg)) * 0.30 + (1 - Math.min(1, entropyAvg)) * 0.25);
    const windowLabel = windowScore >= 0.66 ? 'Favorable execution window' : windowScore >= 0.45 ? 'Selective execution window' : 'Defensive execution window';
    const windowColor = windowScore >= 0.66 ? '#39ff8a' : windowScore >= 0.45 ? '#ff66e0' : '#ff3b6b';

    panel.innerHTML = `
        <div class="metric-card pf-adv-card pf-adv-card-rotation" title="Shows where AI is rotating capital right now. More Reduce means de-risk; more Increase means accumulation.">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
                <div class="pf-adv-card-title pf-adv-rotation-title">Capital Rotation Graph</div>
                <div class="pf-adv-card-subtitle pf-adv-rotation-title">Where AI is shifting capital now</div>
            </div>
            <div class="pf-adv-legend">
                <span class="pf-adv-legend-chip pf-legend-up">Increase ${flow.increase}</span>
                <span class="pf-adv-legend-chip pf-legend-hold">Hold ${flow.hold}</span>
                <span class="pf-adv-legend-chip pf-legend-down">Reduce ${flow.reduce}</span>
                <span class="pf-adv-legend-chip pf-legend-unknown">Unknown ${unknownNet > 0 ? '+' : ''}${unknownNet}</span>
            </div>
            <div class="pf-adv-meter">
                <div class="pf-adv-fill pf-adv-flow-up" style="width:${barW(flow.increase)};"></div>
                <div class="pf-adv-fill pf-adv-flow-hold" style="width:${barW(flow.hold)};"></div>
                <div class="pf-adv-fill pf-adv-flow-down" style="width:${barW(flow.reduce)};"></div>
            </div>
            <div style="font-size:10px; color:#ffc5eb;" title="Decision hint">If <b>Reduce</b> dominates, trim risk concentration. If <b>Increase</b> dominates, accumulation bias is active.</div>
            <div style="font-size:10px; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                ${topSectors.map((s) => `${escapeHtml(s.name)} ${s.net > 0 ? '+' : ''}${s.net}`).join(' · ') || 'No sector tilt yet'}
            </div>
        </div>
        <div class="metric-card pf-adv-card pf-adv-card-exec" title="Entry/exit smoothness gauge from spread, liquidity, entropy, and risk. Higher is better for cleaner execution.">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
                <div class="pf-adv-card-title pf-adv-exec-title">Execution Window Advisor</div>
                <div class="pf-adv-card-subtitle pf-adv-exec-title">${windowLabel}</div>
            </div>
            <div class="pf-adv-legend">
                <span class="pf-adv-legend-chip pf-legend-window-good">Smooth</span>
                <span class="pf-adv-legend-chip pf-legend-window-mid">Selective</span>
                <span class="pf-adv-legend-chip pf-legend-window-risk">Defensive</span>
            </div>
            <div class="pf-adv-meter">
                <div class="pf-adv-fill pf-adv-window" style="width:${Math.round(windowScore * 100)}%; --pf-window-color:${windowColor};"></div>
            </div>
            <div style="font-size:10px; color:#ffd3f5;" title="Decision hint">High score: phase entries normally. Mid score: stagger entries. Low score: reduce size and avoid forced execution.</div>
            <div style="font-size:10px; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                Lower spread + better liquidity = cleaner execution. Spread ${(spreadMed * 100).toFixed(2)}% · Vol ${volMed > 0 ? Number(volMed).toLocaleString('en-IN') : '—'} · Risk ${riskAvg.toFixed(3)} · Entropy ${entropyAvg.toFixed(3)}${accountMetrics?.regimeFit != null ? ` · Regime ${(Number(accountMetrics.regimeFit) * 100).toFixed(1)}%` : ''}
            </div>
        </div>
    `;
}

function renderPortfolioIntelligencePanel(positions, accountMetrics = null) {
    const tab = document.getElementById('portfolio');
    if (!tab) return;
    const tableCard = tab.querySelector('.table-card.dense-table');
    if (!tableCard) return;

    let panel = document.getElementById('portfolioIntelligencePanel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'portfolioIntelligencePanel';
        panel.style.cssText = 'margin:2px 0 8px; display:grid; grid-template-columns:1fr 1fr; gap:8px;';
        tableCard.parentElement.insertBefore(panel, tableCard);
    }

    const rows = Array.isArray(positions) ? positions : [];
    if (!rows.length) {
        panel.innerHTML = '';
        return;
    }

    const suite = window.__PF_INTEL_SUITE_CACHE?.data || null;
    if (!suite) {
        panel.innerHTML = `
            <div class="metric-card pf-intel-card" style="grid-column:1 / -1;">
                <div class="pf-intel-title">Capital Intelligence</div>
                <div class="ai-thinking ai-dots" style="font-size:11px; color:var(--text-muted);">Building forecast + survival diagnostics</div>
            </div>
        `;
        if (!window.__PF_INTEL_SUITE_LOADING) {
            loadPortfolioIntelligenceSuite().then(() => {
                if (document.getElementById('portfolioIntelligencePanel')) {
                    renderPortfolioIntelligencePanel(positions, accountMetrics);
                }
            });
        }
        return;
    }

    const forecast = suite.forecast || {};
    const survival = suite.survival || {};
    const backtest = suite.backtesting || {};
    const drift = suite.drift || {};
    const governance = suite.governance || {};
    const explainability = suite.explainability || {};
    const scorecard = Array.isArray(suite.scorecard) ? suite.scorecard : [];

    const h30 = forecast.horizons?.['30d'] || {};
    const h90 = forecast.horizons?.['90d'] || {};
    const h1y = forecast.horizons?.['1y'] || {};
    const currentValue = Number(forecast.current_value || 0);
    const expected90 = Number(h90.expected_value || 0);
    const expectedMove90 = currentValue > 0 ? ((expected90 - currentValue) / currentValue) * 100 : 0;
    const ddProb = Number(h90.drawdown_prob_10 || 0) * 100;
    const survivalProb = Number(h90.survival_prob_25 || 0) * 100;

    const survivalScore = Number(survival.score || 0);
    const depletionProb = Number(survival.capital_depletion_prob || 0) * 100;
    const scenarios = Array.isArray(survival.scenarios) ? survival.scenarios : [];
    const worstScenario = scenarios.length
        ? [...scenarios].sort((a, b) => Number(b.drawdown_pct || 0) - Number(a.drawdown_pct || 0))[0]
        : null;

    const calScore = Number(backtest.forecast_calibration_score);
    const sugVsAct = Number(backtest.suggested_vs_actual_score);
    const predDD = Number(backtest.predicted_drawdown_proxy || 0) * 100;
    const realDD = Number(backtest.realized_drawdown_proxy || 0) * 100;

    const driftDims = drift.dimensions || {};
    const highDrift = Object.values(driftDims).filter((d) => d?.level === 'HIGH').length;
    const modDrift = Object.values(driftDims).filter((d) => d?.level === 'MODERATE').length;
    const driftStatus = String(drift.status || 'WARMING');

    const govAlerts = Array.isArray(governance.alerts) ? governance.alerts : [];
    const govStatus = String(governance.status || 'WATCH');
    const stance = String(explainability.recommended_stance || 'SELECTIVE');
    const why = Array.isArray(explainability.why) ? explainability.why.slice(0, 3) : [];

    const generatedLabel = suite.generated_at || suite.generated_on || formatPortfolioDateTime(new Date().toISOString());
    const scorecardHtml = scorecard.length
        ? scorecard.map((s) => `
            <div class="pf-intel-score-row">
                <span>${escapeHtml(String(s.module || 'Module'))}</span>
                <span>${escapeHtml(String(s.calibration ?? '--'))}</span>
                <span>${escapeHtml(String(s.drift || '--'))}</span>
                <span>${escapeHtml(String(s.status || '--'))}</span>
            </div>
          `).join('')
        : '<div class="pf-intel-muted">Scorecard warming up</div>';

    panel.innerHTML = `
        <div class="metric-card pf-intel-card" title="Probabilistic forward distribution from live portfolio state.">
            <div class="pf-intel-header">
                <div class="pf-intel-title">Portfolio Forecast</div>
                <div class="pf-intel-chip">${generatedLabel}</div>
            </div>
            <div class="pf-intel-main ${expectedMove90 >= 0 ? 'pf-intel-positive' : 'pf-intel-negative'}">
                90D Expected ${expectedMove90 >= 0 ? '+' : ''}${expectedMove90.toFixed(2)}%
            </div>
            <div class="pf-intel-muted">
                30D P05/P95: ${formatInr(Number(h30.p05_value || 0))} → ${formatInr(Number(h30.p95_value || 0))}
            </div>
            <div class="pf-intel-muted">
                1Y P05/P95: ${formatInr(Number(h1y.p05_value || 0))} → ${formatInr(Number(h1y.p95_value || 0))}
            </div>
            <div class="pf-intel-bar"><div class="pf-intel-fill pf-intel-fill-cyan" style="width:${Math.max(1, Math.min(100, survivalProb))}%;"></div></div>
            <div class="pf-intel-muted">Survival probability (90D): ${survivalProb.toFixed(1)}% · Drawdown risk: ${ddProb.toFixed(1)}%</div>
        </div>

        <div class="metric-card pf-intel-card" title="Stress engine + governance constraints + drift monitor.">
            <div class="pf-intel-header">
                <div class="pf-intel-title">Survival + Governance</div>
                <div class="pf-intel-chip">${govStatus}</div>
            </div>
            <div class="pf-intel-main ${survivalScore >= 60 ? 'pf-intel-positive' : survivalScore >= 40 ? 'pf-intel-warn' : 'pf-intel-negative'}">
                Survival Score ${survivalScore.toFixed(1)} / 100
            </div>
            <div class="pf-intel-muted">Capital depletion probability: ${depletionProb.toFixed(1)}% · Drift: ${driftStatus}</div>
            <div class="pf-intel-muted">Drift dimensions: High ${highDrift} · Moderate ${modDrift}</div>
            <div class="pf-intel-bar"><div class="pf-intel-fill pf-intel-fill-magenta" style="width:${Math.max(1, Math.min(100, survivalScore))}%;"></div></div>
            <div class="pf-intel-muted">
                ${worstScenario ? `Worst stress: ${escapeHtml(String(worstScenario.name || 'Scenario'))} (${Number(worstScenario.drawdown_pct || 0).toFixed(1)}% DD)` : 'Worst stress: collecting'}
            </div>
        </div>

        <div class="metric-card pf-intel-card" title="Continuous validation: forecast calibration, drawdown alignment, decision quality.">
            <div class="pf-intel-header">
                <div class="pf-intel-title">Backtesting + Scorecard</div>
                <div class="pf-intel-chip">${Number.isFinite(calScore) ? `${calScore.toFixed(1)}%` : '--'}</div>
            </div>
            <div class="pf-intel-muted">Calibration score: ${Number.isFinite(calScore) ? `${calScore.toFixed(1)}%` : 'n/a'} · Suggested vs Actual: ${Number.isFinite(sugVsAct) ? `${sugVsAct.toFixed(1)}%` : 'n/a'}</div>
            <div class="pf-intel-muted">Predicted DD proxy: ${predDD.toFixed(2)}% · Realized DD proxy: ${realDD.toFixed(2)}%</div>
            <div class="pf-intel-score-head">
                <span>Module</span><span>Cal</span><span>Drift</span><span>Status</span>
            </div>
            ${scorecardHtml}
        </div>

        <div class="metric-card pf-intel-card" title="Plain-language reasons for current recommendation stance.">
            <div class="pf-intel-header">
                <div class="pf-intel-title">Explainability</div>
                <div class="pf-intel-chip">${stance}</div>
            </div>
            ${why.length ? why.map((r) => `<div class="pf-intel-why">• ${escapeHtml(String(r))}</div>`).join('') : '<div class="pf-intel-muted">No explainability reasons available yet.</div>'}
            <div class="pf-intel-muted" style="margin-top:6px;">
                Governance alerts: ${govAlerts.length ? govAlerts.slice(0, 2).map((a) => escapeHtml(String(a.type || 'ALERT'))).join(' · ') : 'None'}
            </div>
        </div>
    `;
}

function portfolioExportRows() {
    const pi = window.NEURAL_STATE?.portfolio_intelligence || {};
    const positions = pi.positions || [];
    return positions.map((p) => {
        const qty = Number(p.open_qty ?? p.quantity ?? 0);
        const cp = Number(p.current_price || 0);
        const ap = Number(p.avg_price || 0);
        const invested = Number.isFinite(Number(p.open_cost)) ? Number(p.open_cost) : (ap * qty);
        const currentValue = Number.isFinite(Number(p.current_value)) ? Number(p.current_value) : (cp * qty);
        const pnl = currentValue - invested;
        const days = calcHoldingDays(p.added_date);
        const stUnreal = Number(p.stcg_unrealized);
        const ltUnreal = Number(p.ltcg_unrealized);
        const stRealized = Number(p.stcg_realized || 0);
        const ltRealized = Number(p.ltcg_realized || 0);
        const st = Number.isFinite(stUnreal) ? (stUnreal + stRealized) : (days <= 365 ? pnl : 0);
        const lt = Number.isFinite(ltUnreal) ? (ltUnreal + ltRealized) : (days > 365 ? pnl : 0);
        const kellyPct = Number(p.kelly_percent);
        const kellyFrac = Number(p.kelly_fraction || 0);
        const kellyEffective = Number.isFinite(kellyPct) && kellyPct > 0
            ? kellyPct
            : (kellyFrac > 0 ? kellyFrac * 100 : 0);
        return {
            symbol: p.symbol || '',
            qty, ap, cp, invested, currentValue, pnl,
            action: p.action || 'HOLD',
            confidence: Number(p.confidence || 0),
            edge: Number(p.edge || 0),
            entropy: Number(p.entropy || 0),
            kelly: kellyEffective,
            risk: Number(p.risk || 0),
            tp: Number(p.tp || 0),
            sl: Number(p.sl || 0),
            stcg: st,
            ltcg: lt,
            stcg_unrealized: Number.isFinite(stUnreal) ? stUnreal : (days <= 365 ? pnl : 0),
            ltcg_unrealized: Number.isFinite(ltUnreal) ? ltUnreal : (days > 365 ? pnl : 0),
            stcg_realized: stRealized,
            ltcg_realized: ltRealized,
            intent: p.intent_state || 'BALANCE',
            urgency: Number(p.urgency_score || 0)
        };
    });
}

function portfolioExportTotals(rows) {
    const sum = (fn) => rows.reduce((a, r) => a + fn(r), 0);
    const invested = sum(r => Number(r.invested || 0));
    const currentValue = sum(r => Number(r.currentValue || 0));
    const pnl = currentValue - invested;
    const stcg = sum(r => Number(r.stcg || 0));
    const ltcg = sum(r => Number(r.ltcg || 0));
    const avg = (fn) => rows.length ? sum(fn) / rows.length : 0;
    return {
        count: rows.length,
        invested,
        currentValue,
        pnl,
        pnlPct: invested > 0 ? (pnl / invested * 100) : 0,
        stcg,
        ltcg,
        avgConfidence: avg(r => Number(r.confidence || 0)),
        avgEdge: avg(r => Number(r.edge || 0)),
        avgEntropy: avg(r => Number(r.entropy || 0)),
        avgKelly: avg(r => Number(r.kelly || 0)),
        avgRisk: avg(r => Number(r.risk || 0))
    };
}

async function fetchPortfolioLotsForExport(onlyOpen = false) {
    try {
        const r = await fetch(`/api/portfolio/lots?only_open=${onlyOpen ? 1 : 0}`);
        if (!r.ok) return [];
        const payload = await r.json();
        return Array.isArray(payload?.data) ? payload.data : [];
    } catch {
        return [];
    }
}

function getFinancialYearBounds(fyLabel = null) {
    let startYear = null;
    if (typeof fyLabel === 'string') {
        const m = fyLabel.match(/^(\d{4})-/);
        if (m) startYear = Number(m[1]);
    }
    if (!Number.isFinite(startYear)) {
        const now = new Date();
        startYear = now.getMonth() >= 3 ? now.getFullYear() : (now.getFullYear() - 1);
    }
    const from = new Date(startYear, 3, 1, 0, 0, 0, 0);
    const to = new Date(startYear + 1, 3, 1, 0, 0, 0, 0);
    return { from: from.toISOString(), to: to.toISOString(), fy: `${startYear}-${String(startYear + 1).slice(-2)}` };
}

async function fetchRealizedGainsForFY(fyLabel = null) {
    const bounds = getFinancialYearBounds(fyLabel);
    try {
        const url = `/api/portfolio/realized-gains?from=${encodeURIComponent(bounds.from)}&to=${encodeURIComponent(bounds.to)}`;
        const r = await fetch(url);
        if (!r.ok) return { rows: [], bounds };
        const payload = await r.json();
        const rows = Array.isArray(payload?.data) ? payload.data : [];
        return { rows, bounds };
    } catch {
        return { rows: [], bounds };
    }
}

async function exportPortfolioExcel() {
    const rows = portfolioExportRows();
    const t = portfolioExportTotals(rows);
    const generatedAt = formatPortfolioDateTime(new Date().toISOString());
    const lots = await fetchPortfolioLotsForExport(false);
    const fy = window.__PF_TAX_SUMMARY_CACHE?.data || null;
    const fyLine = fy
        ? `FY ${fy.fy} Realized STCG: <b style="color:${Number(fy.stcg_realized || 0) >= 0 ? '#0a0' : '#c00'}">${formatInr(fy.stcg_realized || 0)}</b> | LTCG: <b style="color:${Number(fy.ltcg_realized || 0) >= 0 ? '#0a0' : '#c00'}">${formatInr(fy.ltcg_realized || 0)}</b>`
        : `FY realized summary: <b>Syncing...</b>`;
    const lotsBySymbol = lots.reduce((acc, lot) => {
        const s = String(lot.symbol || '').toUpperCase();
        if (!acc[s]) acc[s] = [];
        acc[s].push(lot);
        return acc;
    }, {});
    const lotSection = Object.keys(lotsBySymbol).length
        ? `<h3 style="margin:12px 0 6px;color:#0f172a;">Purchase Lot Ledger (Open + Closed)</h3>
            <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;font-family:Segoe UI;font-size:12px;">
                <tr style="background:#111827;color:#facc15;font-weight:700;"><th>Symbol</th><th>Lot ID</th><th>Buy Date</th><th>Original Qty</th><th>Open Qty</th><th>Sold Qty</th><th>Buy Price</th><th>Status</th></tr>
                ${Object.entries(lotsBySymbol).map(([sym, arr]) => arr.map((lot) => `
                    <tr>
                        <td>${sym}</td>
                        <td>${Number(lot.id || lot.lot_id || 0)}</td>
                        <td>${formatPortfolioDate(lot.buy_date)}</td>
                        <td>${Number(lot.original_quantity || 0).toFixed(4)}</td>
                        <td>${Number(lot.remaining_quantity || 0).toFixed(4)}</td>
                        <td>${Math.max(0, Number(lot.original_quantity || 0) - Number(lot.remaining_quantity || 0)).toFixed(4)}</td>
                        <td>${Number(lot.buy_price || 0).toFixed(2)}</td>
                        <td>${Number(lot.remaining_quantity || 0) <= 0 ? 'CLOSED' : (Math.max(0, Number(lot.original_quantity || 0) - Number(lot.remaining_quantity || 0)) > 0 ? 'PARTIAL' : 'OPEN')}</td>
                    </tr>
                `).join('')).join('')}
            </table>`
        : `<div style="margin-top:10px;color:#475569;">Purchase lot ledger: not available</div>`;
    const html = `
    <html><head><meta charset="utf-8"></head><body>
    <div style="font-family:Segoe UI;font-size:12px;margin-bottom:8px;">
        <h2 style="margin:0 0 8px;color:#0f172a;">NEXUS Portfolio Executive Summary</h2>
        <div>Positions: <b>${t.count}</b> | Invested: <b>${formatInr(t.invested)}</b> | Current: <b>${formatInr(t.currentValue)}</b> | P&L: <b style="color:${t.pnl >= 0 ? '#0a0' : '#c00'}">${formatInr(t.pnl)} (${t.pnlPct.toFixed(2)}%)</b></div>
        <div style="margin-top:4px;">Avg Conf: <b>${t.avgConfidence.toFixed(1)}%</b> | Avg Edge: <b>${t.avgEdge.toFixed(3)}</b> | Avg Entropy: <b>${t.avgEntropy.toFixed(3)}</b> | Avg Kelly: <b>${t.avgKelly.toFixed(2)}%</b> | Avg Risk: <b>${t.avgRisk.toFixed(3)}</b></div>
        <div style="margin-top:4px;">${fyLine}</div>
    </div>
    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;font-family:Segoe UI;font-size:12px;">
        <tr style="background:#111827;color:#facc15;font-weight:700;">
            <th>Symbol</th><th>Qty</th><th>Avg</th><th>Price</th><th>Invested</th><th>Current</th><th>P&L</th><th>Action</th><th>Conf%</th><th>Edge</th><th>Entropy</th><th>Kelly%</th><th>Risk</th><th>TP</th><th>SL</th><th>STCG/L</th><th>LTCG/L</th><th>Intent</th><th>Urgency</th>
        </tr>
        ${rows.map(r => `<tr>
            <td>${r.symbol}</td><td>${r.qty}</td><td>${r.ap.toFixed(2)}</td><td>${r.cp.toFixed(2)}</td><td>${r.invested.toFixed(2)}</td><td>${r.currentValue.toFixed(2)}</td><td style="color:${r.pnl >= 0 ? '#0a0' : '#c00'}">${r.pnl.toFixed(2)}</td><td>${r.action}</td>
            <td>${r.confidence.toFixed(1)}</td><td>${r.edge.toFixed(3)}</td><td>${r.entropy.toFixed(3)}</td><td>${r.kelly.toFixed(2)}</td><td>${r.risk.toFixed(3)}</td>
            <td>${r.tp.toFixed(2)}</td><td>${r.sl.toFixed(2)}</td>
            <td style="color:${r.stcg >= 0 ? '#0a0' : '#c00'}">${r.stcg.toFixed(2)}</td>
            <td style="color:${r.ltcg >= 0 ? '#0a0' : '#c00'}">${r.ltcg.toFixed(2)}</td>
            <td>${r.intent}</td><td>${r.urgency.toFixed(1)}</td>
        </tr>`).join('')}
        <tr style="background:#f8fafc;font-weight:700;">
            <td>TOTAL</td><td>${t.count}</td><td></td><td></td><td>${t.invested.toFixed(2)}</td><td>${t.currentValue.toFixed(2)}</td><td style="color:${t.pnl >= 0 ? '#0a0' : '#c00'}">${t.pnl.toFixed(2)}</td><td></td><td>${t.avgConfidence.toFixed(1)}</td><td>${t.avgEdge.toFixed(3)}</td><td>${t.avgEntropy.toFixed(3)}</td><td>${t.avgKelly.toFixed(2)}</td><td>${t.avgRisk.toFixed(3)}</td><td></td><td></td><td style="color:${t.stcg >= 0 ? '#0a0' : '#c00'}">${t.stcg.toFixed(2)}</td><td style="color:${t.ltcg >= 0 ? '#0a0' : '#c00'}">${t.ltcg.toFixed(2)}</td><td></td><td></td>
        </tr>
    </table>
    ${lotSection}
    <div style="font-family:Segoe UI;font-size:11px;color:#475569;margin-top:10px;border-top:1px solid #cbd5e1;padding-top:6px;">
        Generated: <b>${generatedAt}</b> | Source: <b>NEXUS AI QUANTUM</b> | Developed by <b>Avinash Jain</b> | For educational purpose only.
    </div></body></html>`;
    const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    const stamp = formatPortfolioDate(new Date().toISOString()).replace(/\s+/g, '_').toUpperCase();
    a.download = `portfolio_report_${stamp}.xls`;
    a.click();
}

async function exportPortfolioPDF() {
    const rows = portfolioExportRows();
    const t = portfolioExportTotals(rows);
    const generatedAt = formatPortfolioDateTime(new Date().toISOString());
    const lots = await fetchPortfolioLotsForExport(false);
    const fy = window.__PF_TAX_SUMMARY_CACHE?.data || null;
    const realizedFY = await fetchRealizedGainsForFY(fy?.fy || null);
    const maxPnl = Math.max(1, ...rows.map(r => Math.abs(r.pnl || 0)));
    const pnlBars = rows.slice(0, 8).map((r) => {
        const w = Math.max(3, Math.round((Math.abs(r.pnl || 0) / maxPnl) * 100));
        const c = r.pnl >= 0 ? '#39FF14' : '#FF073A';
        return `<div style="display:flex;align-items:center;gap:6px;margin:2px 0;"><div style="width:64px;color:#9fb3c8;font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(r.symbol)}</div><div style="flex:1;height:8px;background:#182332;border-radius:999px;overflow:hidden;"><div style="width:${w}%;height:100%;background:${c};"></div></div><div style="width:72px;text-align:right;font-size:9px;color:${c};">${formatInr(r.pnl)}</div></div>`;
    }).join('');
    const actionBuckets = rows.reduce((acc, r) => {
        const k = String(r.action || 'HOLD').toUpperCase();
        acc[k] = (acc[k] || 0) + 1;
        return acc;
    }, {});
    const maxAction = Math.max(1, ...Object.values(actionBuckets));
    const actionBars = Object.entries(actionBuckets).map(([k, v]) => {
        const w = Math.max(8, Math.round((v / maxAction) * 100));
        const c = (k === 'ADD' || k === 'BUY') ? '#39FF14' : (k === 'REDUCE' || k === 'SELL') ? '#FF073A' : '#FFD500';
        return `<div style="display:flex;align-items:center;gap:6px;margin:2px 0;"><div style="width:72px;font-size:9px;color:#9fb3c8;">${k}</div><div style="flex:1;height:8px;background:#182332;border-radius:999px;overflow:hidden;"><div style="width:${w}%;height:100%;background:${c};"></div></div><div style="width:20px;text-align:right;font-size:9px;color:${c};">${v}</div></div>`;
    }).join('');
    const riskLow = rows.filter(r => r.risk < 0.25).length;
    const riskMed = rows.filter(r => r.risk >= 0.25 && r.risk < 0.5).length;
    const riskHigh = rows.filter(r => r.risk >= 0.5).length;
    const riskTotal = Math.max(1, rows.length);
    const riskBars = [
        { label: 'Low', value: riskLow, color: '#39FF14' },
        { label: 'Medium', value: riskMed, color: '#FFD500' },
        { label: 'High', value: riskHigh, color: '#FF073A' }
    ].map((r) => {
        const w = Math.max(6, Math.round((r.value / riskTotal) * 100));
        return `<div style="display:flex;align-items:center;gap:6px;margin:2px 0;"><div style="width:58px;font-size:9px;color:#9fb3c8;">${r.label}</div><div style="flex:1;height:8px;background:#182332;border-radius:999px;overflow:hidden;"><div style="width:${w}%;height:100%;background:${r.color};"></div></div><div style="width:20px;text-align:right;font-size:9px;color:${r.color};">${r.value}</div></div>`;
    }).join('');
    const confSorted = [...rows].sort((a, b) => b.confidence - a.confidence).slice(0, 8);
    const confBars = confSorted.map((r) => {
        const w = Math.max(4, Math.round(Math.max(0, Math.min(100, r.confidence))));
        return `<div style="display:flex;align-items:center;gap:6px;margin:2px 0;"><div style="width:64px;color:#9fb3c8;font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(r.symbol)}</div><div style="flex:1;height:8px;background:#182332;border-radius:999px;overflow:hidden;"><div style="width:${w}%;height:100%;background:#00F3FF;"></div></div><div style="width:36px;text-align:right;font-size:9px;color:#00F3FF;">${r.confidence.toFixed(0)}%</div></div>`;
    }).join('');
    const w = window.open('', '_blank');
    if (!w) return;
    const lotsBySymbol = lots.reduce((acc, lot) => {
        const s = String(lot.symbol || '').toUpperCase();
        if (!acc[s]) acc[s] = [];
        acc[s].push(lot);
        return acc;
    }, {});
    const lotRows = Object.entries(lotsBySymbol).map(([sym, arr]) => arr.map((lot) => {
        const originalQty = Number(lot.original_quantity || 0);
        const openQty = Number(lot.remaining_quantity || 0);
        const soldQty = Math.max(0, originalQty - openQty);
        const status = openQty <= 0 ? 'CLOSED' : (soldQty > 0 ? 'PARTIAL' : 'OPEN');
        const statusColor = openQty <= 0 ? '#9fb3c8' : (soldQty > 0 ? '#FFD500' : '#39FF14');
        return `<tr>
            <td style="padding:5px;border:1px solid #243243;">${sym}</td>
            <td style="padding:5px;border:1px solid #243243;">${Number(lot.id || lot.lot_id || 0)}</td>
            <td style="padding:5px;border:1px solid #243243;">${formatPortfolioDate(lot.buy_date)}</td>
            <td style="padding:5px;border:1px solid #243243;text-align:right;">${originalQty.toFixed(4)}</td>
            <td style="padding:5px;border:1px solid #243243;text-align:right;">${openQty.toFixed(4)}</td>
            <td style="padding:5px;border:1px solid #243243;text-align:right;">${soldQty.toFixed(4)}</td>
            <td style="padding:5px;border:1px solid #243243;text-align:right;">₹${Number(lot.buy_price || 0).toFixed(2)}</td>
            <td style="padding:5px;border:1px solid #243243;color:${statusColor};">${status}</td>
        </tr>`;
    }).join('')).join('');
    const lotSectionPdf = lotRows
        ? `<div style="margin-top:8px;">
            <div style="font-size:11px;color:#facc15;font-weight:700;margin:2px 0 4px;">Purchase Lot Ledger (Open + Closed)</div>
            <table style="width:100%;border-collapse:collapse;font-size:9px;">
                <tr style="background:#121826;color:#facc15;">
                    <th style="padding:5px;border:1px solid #243243;">Symbol</th>
                    <th style="padding:5px;border:1px solid #243243;">Lot</th>
                    <th style="padding:5px;border:1px solid #243243;">Buy Date</th>
                    <th style="padding:5px;border:1px solid #243243;">Orig Qty</th>
                    <th style="padding:5px;border:1px solid #243243;">Open Qty</th>
                    <th style="padding:5px;border:1px solid #243243;">Sold Qty</th>
                    <th style="padding:5px;border:1px solid #243243;">Buy Px</th>
                    <th style="padding:5px;border:1px solid #243243;">Status</th>
                </tr>
                ${lotRows}
            </table>
          </div>`
        : '';
    const realizedBySymbolMonth = (realizedFY.rows || []).reduce((acc, row) => {
        const sym = String(row.symbol || '').toUpperCase();
        const month = String(row.realized_at || '').slice(0, 7) || 'Unknown';
        const key = `${sym}|${month}`;
        if (!acc[key]) {
            acc[key] = { symbol: sym, month, stcg: 0, ltcg: 0, total: 0, trades: 0 };
        }
        const gain = Number(row.gain || 0);
        const gt = String(row.gain_type || 'STCG').toUpperCase();
        if (gt === 'LTCG') acc[key].ltcg += gain;
        else acc[key].stcg += gain;
        acc[key].total += gain;
        acc[key].trades += 1;
        return acc;
    }, {});
    const realizedRows = Object.values(realizedBySymbolMonth)
        .sort((a, b) => {
            const sm = String(a.symbol).localeCompare(String(b.symbol));
            if (sm !== 0) return sm;
            return String(a.month).localeCompare(String(b.month));
        });
    const realizedFySection = realizedRows.length
        ? `<div style="margin-top:8px;">
            <div style="font-size:11px;color:#facc15;font-weight:700;margin:2px 0 4px;">FY MIS (Realized Gains by Symbol + Month: ${realizedFY.bounds.fy})</div>
            <table style="width:100%;border-collapse:collapse;font-size:9px;">
                <tr style="background:#121826;color:#facc15;">
                    <th style="padding:5px;border:1px solid #243243;">Symbol</th>
                    <th style="padding:5px;border:1px solid #243243;">Month</th>
                    <th style="padding:5px;border:1px solid #243243;">Trades</th>
                    <th style="padding:5px;border:1px solid #243243;">STCG</th>
                    <th style="padding:5px;border:1px solid #243243;">LTCG</th>
                    <th style="padding:5px;border:1px solid #243243;">Total</th>
                </tr>
                ${realizedRows.map((r) => `
                    <tr>
                        <td style="padding:5px;border:1px solid #243243;">${r.symbol}</td>
                        <td style="padding:5px;border:1px solid #243243;">${r.month}</td>
                        <td style="padding:5px;border:1px solid #243243;text-align:right;">${r.trades}</td>
                        <td style="padding:5px;border:1px solid #243243;text-align:right;color:${r.stcg >= 0 ? '#3cff70' : '#ff4b5e'};">${formatInr(r.stcg)}</td>
                        <td style="padding:5px;border:1px solid #243243;text-align:right;color:${r.ltcg >= 0 ? '#3cff70' : '#ff4b5e'};">${formatInr(r.ltcg)}</td>
                        <td style="padding:5px;border:1px solid #243243;text-align:right;color:${r.total >= 0 ? '#3cff70' : '#ff4b5e'};">${formatInr(r.total)}</td>
                    </tr>
                `).join('')}
            </table>
          </div>`
        : '';

    w.document.write(`
    <html><head><title>Portfolio Report</title>
    <style>
      @page { size: A4 portrait; margin: 7mm; }
      html, body { zoom: 0.95; }
      * { box-sizing: border-box; }
    </style>
    </head>
    <body style="font-family:Segoe UI;background:#0b1016;color:#fff;padding:12px;">
      <h2 style="color:#facc15;margin:0 0 8px;">NEXUS Portfolio Report</h2>
      <div style="display:grid;grid-template-columns:1.2fr 1fr;gap:8px;margin-bottom:8px;">
        <div style="border:1px solid #243243;border-radius:8px;padding:8px;background:#111827;">
          <div style="font-size:12px;color:#facc15;font-weight:700;margin-bottom:4px;">Executive Summary</div>
          <div style="font-size:10px;color:#dbeafe;">Positions: <b>${t.count}</b></div>
          <div style="font-size:10px;color:#dbeafe;">Invested Value: <b>${formatInr(t.invested)}</b></div>
          <div style="font-size:10px;color:#dbeafe;">Current Value: <b>${formatInr(t.currentValue)}</b></div>
          <div style="font-size:10px;color:${t.pnl >= 0 ? '#39FF14' : '#FF073A'};">Net P&L: <b>${formatInr(t.pnl)} (${t.pnlPct.toFixed(2)}%)</b></div>
          <div style="font-size:10px;color:#9fb3c8;margin-top:5px;">Avg Conf ${t.avgConfidence.toFixed(1)}% | Edge ${t.avgEdge.toFixed(3)} | Entropy ${t.avgEntropy.toFixed(3)} | Kelly ${t.avgKelly.toFixed(2)}% | Risk ${t.avgRisk.toFixed(3)}</div>
          <div style="font-size:10px;color:#9fb3c8;margin-top:4px;">STCG/L ${formatInr(t.stcg)} | LTCG/L ${formatInr(t.ltcg)}</div>
          <div style="font-size:10px;color:#9fb3c8;margin-top:4px;">${fy ? `FY ${fy.fy} Realized STCG ${formatInr(fy.stcg_realized || 0)} | LTCG ${formatInr(fy.ltcg_realized || 0)}` : 'FY realized summary syncing...'}</div>
        </div>
        <div style="border:1px solid #243243;border-radius:8px;padding:8px;background:#111827;">
          <div style="font-size:12px;color:#facc15;font-weight:700;margin-bottom:4px;">P&L Breakup (Top 8)</div>
          ${pnlBars || '<div style="font-size:10px;color:#9fb3c8;">No rows</div>'}
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:8px;">
        <div style="border:1px solid #243243;border-radius:8px;padding:8px;background:#111827;">
          <div style="font-size:11px;color:#facc15;font-weight:700;margin-bottom:4px;">Action Mix</div>
          ${actionBars || '<div style="font-size:10px;color:#9fb3c8;">No actions</div>'}
        </div>
        <div style="border:1px solid #243243;border-radius:8px;padding:8px;background:#111827;">
          <div style="font-size:11px;color:#facc15;font-weight:700;margin-bottom:4px;">Risk Buckets</div>
          ${riskBars}
        </div>
        <div style="border:1px solid #243243;border-radius:8px;padding:8px;background:#111827;">
          <div style="font-size:11px;color:#facc15;font-weight:700;margin-bottom:4px;">Confidence Leaders</div>
          ${confBars || '<div style="font-size:10px;color:#9fb3c8;">No rows</div>'}
        </div>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:11px;">
        <tr style="background:#121826;color:#facc15;">
          <th style="padding:6px;border:1px solid #243243;">Sym</th><th style="padding:6px;border:1px solid #243243;">Qty</th><th style="padding:6px;border:1px solid #243243;">Invested</th><th style="padding:6px;border:1px solid #243243;">Current</th><th style="padding:6px;border:1px solid #243243;">P&L</th><th style="padding:6px;border:1px solid #243243;">Action</th><th style="padding:6px;border:1px solid #243243;">Conf</th><th style="padding:6px;border:1px solid #243243;">Edge</th><th style="padding:6px;border:1px solid #243243;">Entropy</th><th style="padding:6px;border:1px solid #243243;">Kelly%</th><th style="padding:6px;border:1px solid #243243;">Risk</th><th style="padding:6px;border:1px solid #243243;">TP</th><th style="padding:6px;border:1px solid #243243;">SL</th><th style="padding:6px;border:1px solid #243243;">STCG/L</th><th style="padding:6px;border:1px solid #243243;">LTCG/L</th>
        </tr>
        ${rows.map(r => `<tr>
          <td style="padding:6px;border:1px solid #243243;">${r.symbol}</td>
          <td style="padding:6px;border:1px solid #243243;">${r.qty}</td>
          <td style="padding:6px;border:1px solid #243243;">${formatInr(r.invested)}</td>
          <td style="padding:6px;border:1px solid #243243;">${formatInr(r.currentValue)}</td>
          <td style="padding:6px;border:1px solid #243243;color:${r.pnl >= 0 ? '#3cff70' : '#ff4b5e'};">${formatInr(r.pnl)}</td>
          <td style="padding:6px;border:1px solid #243243;">${r.action}</td>
          <td style="padding:6px;border:1px solid #243243;">${r.confidence.toFixed(1)}%</td>
          <td style="padding:6px;border:1px solid #243243;">${r.edge.toFixed(3)}</td>
          <td style="padding:6px;border:1px solid #243243;">${r.entropy.toFixed(3)}</td>
          <td style="padding:6px;border:1px solid #243243;">${r.kelly.toFixed(2)}%</td>
          <td style="padding:6px;border:1px solid #243243;">${r.risk.toFixed(3)}</td>
          <td style="padding:6px;border:1px solid #243243;">${formatInr(r.tp)}</td>
          <td style="padding:6px;border:1px solid #243243;">${formatInr(r.sl)}</td>
          <td style="padding:6px;border:1px solid #243243;color:${r.stcg >= 0 ? '#3cff70' : '#ff4b5e'};">${formatInr(r.stcg)}</td>
          <td style="padding:6px;border:1px solid #243243;color:${r.ltcg >= 0 ? '#3cff70' : '#ff4b5e'};">${formatInr(r.ltcg)}</td>
        </tr>`).join('')}
        <tr style="background:#111827;font-weight:700;">
          <td style="padding:6px;border:1px solid #243243;">TOTAL</td>
          <td style="padding:6px;border:1px solid #243243;">${t.count}</td>
          <td style="padding:6px;border:1px solid #243243;">${formatInr(t.invested)}</td>
          <td style="padding:6px;border:1px solid #243243;">${formatInr(t.currentValue)}</td>
          <td style="padding:6px;border:1px solid #243243;color:${t.pnl >= 0 ? '#3cff70' : '#ff4b5e'};">${formatInr(t.pnl)}</td>
          <td style="padding:6px;border:1px solid #243243;"></td>
          <td style="padding:6px;border:1px solid #243243;">${t.avgConfidence.toFixed(1)}%</td>
          <td style="padding:6px;border:1px solid #243243;">${t.avgEdge.toFixed(3)}</td>
          <td style="padding:6px;border:1px solid #243243;">${t.avgEntropy.toFixed(3)}</td>
          <td style="padding:6px;border:1px solid #243243;">${t.avgKelly.toFixed(2)}%</td>
          <td style="padding:6px;border:1px solid #243243;">${t.avgRisk.toFixed(3)}</td>
          <td style="padding:6px;border:1px solid #243243;"></td>
          <td style="padding:6px;border:1px solid #243243;"></td>
          <td style="padding:6px;border:1px solid #243243;color:${t.stcg >= 0 ? '#3cff70' : '#ff4b5e'};">${formatInr(t.stcg)}</td>
          <td style="padding:6px;border:1px solid #243243;color:${t.ltcg >= 0 ? '#3cff70' : '#ff4b5e'};">${formatInr(t.ltcg)}</td>
        </tr>
      </table>
      ${lotSectionPdf}
      ${realizedFySection}
      <div style="margin-top:8px;padding-top:6px;border-top:1px solid #243243;font-size:9px;color:#9fb3c8;text-align:center;">
        Generated: <b>${generatedAt}</b> | Source: <b>NEXUS AI QUANTUM</b> | Developed by <b>Avinash Jain</b> | For educational purpose only.
      </div>
    </body></html>`);
    w.document.close();
    w.focus();
    setTimeout(() => w.print(), 250);
}

function getExpandedSymbolExportPayload(symbol) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    const pi = window.NEURAL_STATE?.portfolio_intelligence || {};
    const positions = Array.isArray(pi.positions) ? pi.positions : [];
    const pos = positions.find((p) => String(p?.symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '') === base);
    if (!pos) return null;
    const lots = (window.__PF_LOT_INSIGHTS_CACHE?.[base]?.data?.all_lots || []);
    const journal = (window.__PF_REALIZED_JOURNAL_CACHE?.[base]?.data || []);
    const news = (window.__PF_NEWS_CACHE?.[base]?.data || []).slice(0, 35);
    const deep = (window.__PF_DEEP_CACHE?.[base]?.data || {});
    return { base, pos, lots, journal, news, deep, generatedAt: formatPortfolioDateTime(new Date().toISOString()) };
}

function exportExpandedSymbolExcel(symbol) {
    const payload = getExpandedSymbolExportPayload(symbol);
    if (!payload) {
        showToast('No expanded symbol data to export', 'error');
        return;
    }
    const { base, pos, lots, journal, deep, generatedAt } = payload;
    const html = `
    <html><head><meta charset="utf-8"></head><body>
    <h2>${escapeHtml(base)} · Detailed Position Report</h2>
    <div>Generated: <b>${generatedAt}</b></div>
    <h3>Summary</h3>
    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;">
      <tr><td>Action</td><td>${escapeHtml(String(pos.action || 'HOLD'))}</td></tr>
      <tr><td>Quantity</td><td>${Number(pos.open_qty || pos.quantity || 0).toFixed(4)}</td></tr>
      <tr><td>Current Price</td><td>${Number(pos.current_price || 0).toFixed(2)}</td></tr>
      <tr><td>Avg Price</td><td>${Number(pos.avg_price || 0).toFixed(2)}</td></tr>
      <tr><td>Confidence</td><td>${Number(pos.confidence || 0).toFixed(1)}%</td></tr>
      <tr><td>Edge</td><td>${Number(pos.edge || 0).toFixed(3)}</td></tr>
      <tr><td>Entropy</td><td>${Number(pos.entropy || 0).toFixed(3)}</td></tr>
      <tr><td>Kelly %</td><td>${Number(pos.kelly_percent || 0).toFixed(2)}%</td></tr>
      <tr><td>Risk</td><td>${Number(pos.risk || 0).toFixed(3)}</td></tr>
      <tr><td>TP / SL</td><td>${Number(pos.tp || 0).toFixed(2)} / ${Number(pos.sl || 0).toFixed(2)}</td></tr>
      <tr><td>PE / PB</td><td>${deep.pe_ratio ?? deep.pe ?? '—'} / ${deep.pb_ratio ?? deep.price_to_book ?? '—'}</td></tr>
      <tr><td>Dividend / Yield</td><td>${deep.dividend_rate ?? deep.dividendRate ?? '—'} / ${deep.dividend_yield ?? deep.dividendYield ?? '—'}</td></tr>
    </table>
    <h3>Purchase Ledger</h3>
    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;">
      <tr><th>Lot ID</th><th>Buy Date</th><th>Original Qty</th><th>Open Qty</th><th>Buy Price</th></tr>
      ${lots.map(l => `<tr><td>${Number(l.id || l.lot_id || 0)}</td><td>${formatPortfolioDate(l.buy_date)}</td><td>${Number(l.original_quantity || 0).toFixed(4)}</td><td>${Number(l.remaining_quantity || 0).toFixed(4)}</td><td>${Number(l.buy_price || 0).toFixed(2)}</td></tr>`).join('')}
    </table>
    <h3>Realized Sell Journal</h3>
    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;">
      <tr><th>Txn</th><th>Date</th><th>Lot ID</th><th>Qty</th><th>Gain</th><th>Type</th></tr>
      ${journal.map(j => `<tr><td>${escapeHtml(String(j.sell_txn_id || j.id || '—'))}</td><td>${formatPortfolioDate(j.realized_at)}</td><td>${escapeHtml(String(j.lot_id || '—'))}</td><td>${Number(j.quantity || 0).toFixed(4)}</td><td>${Number(j.gain || 0).toFixed(2)}</td><td>${escapeHtml(String(j.gain_type || 'STCG'))}</td></tr>`).join('')}
    </table>
    <h3>Latest News (Top ${news.length})</h3>
    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;">
      <tr><th>Published</th><th>Source</th><th>Title</th><th>URL</th></tr>
      ${news.map(n => `<tr><td>${escapeHtml(formatPortfolioDateTime(n.published || n.normalized_time || n.timestamp || ''))}</td><td>${escapeHtml(String(n.source || 'Source'))}</td><td>${escapeHtml(String(n.title || n.headline || 'News'))}</td><td>${escapeHtml(String(n.link || n.url || ''))}</td></tr>`).join('')}
    </table>
    <div style="margin-top:10px;font-size:11px;">Source: <b>NEXUS AI QUANTUM</b> | Developed by <b>Avinash Jain</b> | For educational purpose only.</div>
    </body></html>`;
    const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${base}_detailed_report.xls`;
    a.click();
}

function exportExpandedSymbolPDF(symbol) {
    const payload = getExpandedSymbolExportPayload(symbol);
    if (!payload) {
        showToast('No expanded symbol data to export', 'error');
        return;
    }
    const { base, pos, lots, journal, news, deep, generatedAt } = payload;
    const w = window.open('', '_blank');
    if (!w) return;
    w.document.write(`
    <html><head><meta charset="utf-8"><title>${base} Report</title></head>
    <body style="font-family:Segoe UI,Arial,sans-serif;padding:12px;">
      <h2 style="margin:0 0 6px;">${escapeHtml(base)} · Detailed Position Report</h2>
      <div style="font-size:12px;color:#334155;">Generated: ${generatedAt}</div>
      <div style="margin-top:8px;font-size:13px;">Action: <b>${escapeHtml(String(pos.action || 'HOLD'))}</b> · Qty: <b>${Number(pos.open_qty || pos.quantity || 0).toFixed(2)}</b> · Price: <b>₹${Number(pos.current_price || 0).toFixed(2)}</b></div>
      <h3 style="margin:10px 0 6px;">Summary</h3>
      <table style="width:100%;border-collapse:collapse;font-size:11px;">
        <tr><th style="border:1px solid #cbd5e1;padding:5px;">Metric</th><th style="border:1px solid #cbd5e1;padding:5px;">Value</th></tr>
        <tr><td style="border:1px solid #cbd5e1;padding:5px;">Intent</td><td style="border:1px solid #cbd5e1;padding:5px;">${escapeHtml(String(pos.intent_state || 'BALANCE'))}</td></tr>
        <tr><td style="border:1px solid #cbd5e1;padding:5px;">Confidence</td><td style="border:1px solid #cbd5e1;padding:5px;">${Number(pos.confidence || 0).toFixed(1)}%</td></tr>
        <tr><td style="border:1px solid #cbd5e1;padding:5px;">Edge</td><td style="border:1px solid #cbd5e1;padding:5px;">${Number(pos.edge || 0).toFixed(3)}</td></tr>
        <tr><td style="border:1px solid #cbd5e1;padding:5px;">Entropy</td><td style="border:1px solid #cbd5e1;padding:5px;">${Number(pos.entropy || 0).toFixed(3)}</td></tr>
        <tr><td style="border:1px solid #cbd5e1;padding:5px;">Kelly %</td><td style="border:1px solid #cbd5e1;padding:5px;">${Number(pos.kelly_percent || 0).toFixed(2)}%</td></tr>
        <tr><td style="border:1px solid #cbd5e1;padding:5px;">Risk</td><td style="border:1px solid #cbd5e1;padding:5px;">${Number(pos.risk || 0).toFixed(3)}</td></tr>
        <tr><td style="border:1px solid #cbd5e1;padding:5px;">TP / SL</td><td style="border:1px solid #cbd5e1;padding:5px;">₹${Number(pos.tp || 0).toFixed(2)} / ₹${Number(pos.sl || 0).toFixed(2)}</td></tr>
      </table>
      <h3 style="margin:10px 0 6px;">Fundamental</h3>
      <table style="width:100%;border-collapse:collapse;font-size:11px;">
        <tr><th style="border:1px solid #cbd5e1;padding:5px;">Metric</th><th style="border:1px solid #cbd5e1;padding:5px;">Value</th></tr>
        <tr><td style="border:1px solid #cbd5e1;padding:5px;">PE / PB</td><td style="border:1px solid #cbd5e1;padding:5px;">${deep.pe_ratio ?? deep.pe ?? '—'} / ${deep.pb_ratio ?? deep.price_to_book ?? '—'}</td></tr>
        <tr><td style="border:1px solid #cbd5e1;padding:5px;">Dividend / Yield</td><td style="border:1px solid #cbd5e1;padding:5px;">${deep.dividend_rate ?? deep.dividendRate ?? '—'} / ${deep.dividend_yield ?? deep.dividendYield ?? '—'}</td></tr>
        <tr><td style="border:1px solid #cbd5e1;padding:5px;">Face Value</td><td style="border:1px solid #cbd5e1;padding:5px;">${deep.face_value ?? deep.faceValue ?? '—'}</td></tr>
        <tr><td style="border:1px solid #cbd5e1;padding:5px;">MCap / Volume</td><td style="border:1px solid #cbd5e1;padding:5px;">${deep.market_cap ?? deep.marketCap ?? '—'} / ${deep.volume ?? '—'}</td></tr>
      </table>
      <h3 style="margin:10px 0 6px;">Purchase Ledger</h3>
      <table style="width:100%;border-collapse:collapse;font-size:11px;">
        <tr><th style="border:1px solid #cbd5e1;padding:5px;">Lot</th><th style="border:1px solid #cbd5e1;padding:5px;">Buy Date</th><th style="border:1px solid #cbd5e1;padding:5px;">Orig Qty</th><th style="border:1px solid #cbd5e1;padding:5px;">Open Qty</th><th style="border:1px solid #cbd5e1;padding:5px;">Price</th></tr>
        ${lots.map(l => `<tr><td style="border:1px solid #cbd5e1;padding:5px;">${Number(l.id || l.lot_id || 0)}</td><td style="border:1px solid #cbd5e1;padding:5px;">${formatPortfolioDate(l.buy_date)}</td><td style="border:1px solid #cbd5e1;padding:5px;text-align:right;">${Number(l.original_quantity || 0).toFixed(2)}</td><td style="border:1px solid #cbd5e1;padding:5px;text-align:right;">${Number(l.remaining_quantity || 0).toFixed(2)}</td><td style="border:1px solid #cbd5e1;padding:5px;text-align:right;">₹${Number(l.buy_price || 0).toFixed(2)}</td></tr>`).join('')}
      </table>
      <h3 style="margin:10px 0 6px;">Realized Sell Journal</h3>
      <table style="width:100%;border-collapse:collapse;font-size:11px;">
        <tr><th style="border:1px solid #cbd5e1;padding:5px;">Txn</th><th style="border:1px solid #cbd5e1;padding:5px;">Date</th><th style="border:1px solid #cbd5e1;padding:5px;">Lot</th><th style="border:1px solid #cbd5e1;padding:5px;">Qty</th><th style="border:1px solid #cbd5e1;padding:5px;">Gain</th><th style="border:1px solid #cbd5e1;padding:5px;">Type</th></tr>
        ${journal.map(j => `<tr><td style="border:1px solid #cbd5e1;padding:5px;">${escapeHtml(String(j.sell_txn_id || j.id || '—'))}</td><td style="border:1px solid #cbd5e1;padding:5px;">${formatPortfolioDate(j.realized_at)}</td><td style="border:1px solid #cbd5e1;padding:5px;">${escapeHtml(String(j.lot_id || '—'))}</td><td style="border:1px solid #cbd5e1;padding:5px;text-align:right;">${Number(j.quantity || 0).toFixed(2)}</td><td style="border:1px solid #cbd5e1;padding:5px;text-align:right;">₹${Number(j.gain || 0).toFixed(2)}</td><td style="border:1px solid #cbd5e1;padding:5px;">${escapeHtml(String(j.gain_type || 'STCG'))}</td></tr>`).join('')}
      </table>
      <div style="margin-top:10px;font-size:10px;color:#475569;">Source: NEXUS AI QUANTUM | Developed by Avinash Jain | For educational purpose only.</div>
    </body></html>`);
    w.document.close();
    w.focus();
    setTimeout(() => w.print(), 200);
}

window.exportExpandedSymbolExcel = exportExpandedSymbolExcel;
window.exportExpandedSymbolPDF = exportExpandedSymbolPDF;

async function safeFetchJSON(url, options = {}) {
    try {
        const r = await fetch(url, options);
        if (!r.ok) throw new Error(`HTTP error! status: ${r.status}`);
        const text = await r.text();
        const cleaned = text
            .replace(/\bNaN\b/g, "null")
            .replace(/\binfinity\b/gi, "null")
            .replace(/\b-Infinity\b/gi, "null");
        return JSON.parse(cleaned);
    } catch (e) {
        console.error("Invalid JSON or Fetch error from", url, e);
        return { success: false, predictions: [], data: [] };
    }
}

async function hydrateOnWsDegrade(reason = 'ws') {
    try {
        const now = Date.now();
        if (window.__WS_FALLBACK_INFLIGHT) return;
        if (now - Number(window.__WS_FALLBACK_TS || 0) < 90000) return;
        const dashboardActive = isTabActive('dashboard');
        const portfolioActive = isTabActive('portfolio');
        const predictionsActive = isTabActive('predictions');
        if (reason === 'connect_error' && portfolioActive && !dashboardActive) return;
        window.__WS_FALLBACK_TS = now;
        window.__WS_FALLBACK_INFLIGHT = true;
        console.warn(`⚠️ WS degraded (${reason}) -> hydrating from HTTP state`);
        const jobs = [];
        if (dashboardActive) jobs.push(safeInit(loadDashboard));
        const portfolioBusy = !!(window.__PF_EXPANDED_SYMBOL || document.getElementById('lotEditorModal') || document.getElementById('sellWorkflowModal'));
        const pfLast = Number(dashState?.lastUpdate?.portfolio || 0);
        if (portfolioActive && !portfolioBusy && (now - pfLast) > 45000) jobs.push(safeInit(() => loadPortfolioState(true)));
        if (predictionsActive) jobs.push(safeInit(() => (typeof loadIntelligencePredictions === 'function' ? loadIntelligencePredictions() : loadPredictions())));
        if (!jobs.length) return;
        await Promise.allSettled(jobs);
    } catch (e) {
        console.warn('WS degrade hydration failed:', e?.message || e);
    } finally {
        window.__WS_FALLBACK_INFLIGHT = false;
    }
}

socket.on("connect", () => console.log("🧠 Neural Link Active (WS)"));
socket.on("connect_error", (err) => {
    console.warn("⚠️ Neural link connect error:", err?.message || err);
    hydrateOnWsDegrade('connect_error');
});
socket.on("disconnect", (reason) => {
    console.warn("⚠️ Neural link disconnected:", reason || 'unknown');
    hydrateOnWsDegrade('disconnect');
});
socket.on("reconnect_attempt", (n) => {
    console.log(`🔄 Neural reconnect attempt ${n}`);
});
socket.on("sentiment_pulse", (p) => {
    dashState.marketSentiment = {
        ...(dashState.marketSentiment || {}),
        ...(p || {})
    };
    // ✅ SYNC WITH BACKEND CONTRACT (overall_score, label, total_articles)
    const valEl = document.getElementById("marketSentimentValue");
    const labelEl = document.getElementById("marketSentimentLabel");
    const artsEl = document.getElementById("marketSentimentArticles");

    if (valEl && p.overall_score != null) {
        valEl.innerText = `${p.overall_score.toFixed(1)}%`;
        valEl.style.color = p.overall_score > 60 ? "var(--electric-green)" : p.overall_score < 40 ? "var(--electric-red)" : "var(--electric-yellow)";
    }
    if (labelEl && p.label) {
        labelEl.innerText = p.label;
        labelEl.style.color = p.label === 'POSITIVE' ? 'var(--electric-green)' : p.label === 'NEGATIVE' ? 'var(--electric-red)' : 'var(--electric-yellow)';
    }
    if (artsEl && p.total_articles != null) {
        artsEl.innerText = p.total_articles;
    }
    if (isTabActive('news')) {
        safeInit(loadNews);
    }
    updateDashboardMarketIntelligenceCard();
});

// 🧠 AI STATE UPDATE (Consolidated & Real-time)
window.NEXUS_SOCKET.on("ai_state", handleAIState);
window.NEXUS_SOCKET.on("prediction_update", () => {
    if (isTabActive('predictions') && typeof loadIntelligencePredictions === 'function') {
        loadIntelligencePredictions();
    }
    if (isTabActive('news')) {
        safeInit(loadNews);
    }
});


function handleAIState(state) {
    if (!state) return;
    window.NEURAL_STATE = state; // Set Global State
    ensurePortfolioLegend();
    ensureMetricTooltips();
    ensurePortfolioCardAssist();
    const nowTs = Date.now();
    if (isTabActive('predictions') || (nowTs - Number(window.__LAST_WORLD_STATE_AT || 0)) > 60000) {
        window.__LAST_WORLD_STATE_AT = nowTs;
        renderPredictionsWorldState(false);
    }
    if (isTabActive('predictions') && typeof loadIntelligencePredictions === 'function') {
        loadIntelligencePredictions();
    }
    const livePredictionRows = getLivePredictionRowsFromState();
    if (livePredictionRows.length) {
        dashState.predictions = livePredictionRows;
        if (isTabActive('predictions')) {
            displayLivePredictions(livePredictionRows);
        }
        updatePredictionCards({
            stocks: livePredictionRows,
            predictions: livePredictionRows
        });
    }
    const regimeLabel = document.querySelector('#regimeFitValue')?.parentElement?.querySelector('.label');
    if (regimeLabel) regimeLabel.textContent = 'Regime Alignment';

    // Bridge for Cognitive State
    const cognitiveEl = document.getElementById("aiCognitivePanel");
    if (cognitiveEl) {
        renderCognitivePanel(buildCognitiveFallbackState(state));
    }

    // Bridge for Market Regime
    const regimeEl = document.getElementById("marketRegimeValue");
    if (regimeEl) {
        regimeEl.textContent = state.ai_engine?.regime || state.ai_engine?.current_regime || state.cognitive_state?.current_regime || "NEUTRAL";
        regimeEl.style.color = "var(--electric-purple)";
    }

    // 🚀 PORTFOLIO — PERMANENT STATE (No gate required)
    // Bind controls once on first ai_state arrival
    if (!window.PORTFOLIO_BOUND) {
        window.NEURAL_READY = true;
        bindPortfolioControls();
        window.PORTFOLIO_BOUND = true;
    }

    // WebSocket is authoritative for intelligence VALUES, not for position existence.
    const wsPositionsRaw = state?.portfolio_intelligence?.positions || [];
    const portfolioTickMs = window.__PF_EXPANDED_SYMBOL ? 3500 : 1200;
    const nowPortfolioTick = Date.now();
    const shouldApplyPortfolioTick = (nowPortfolioTick - Number(window.__PF_WS_LAST_APPLY || 0)) >= portfolioTickMs;
    let wsPositions = null;
    if (shouldApplyPortfolioTick) {
        wsPositions = mergePortfolioWithLiveStocks(wsPositionsRaw);
        updatePositionMetricHistory(wsPositions);
        updateDashboardPortfolioCardsFromPI(state?.portfolio_intelligence || {});
        dashState.lastUpdate.portfolio = nowPortfolioTick;
        window.__PF_WS_LAST_APPLY = nowPortfolioTick;
    }
    updateDashboardAIPredictionCard(state?.ai_performance || {}, state);

    if (window.__PENDING_PORTFOLIO_ADD) {
        const pending = window.__PENDING_PORTFOLIO_ADD;
        const found = (wsPositions || wsPositionsRaw || []).some(p => (p.symbol || "").toUpperCase().replace(".NS", "").replace(".BO", "") === pending.symbol);
        if (found) {
            clearTimeout(pending.timeoutId);
            window.__PENDING_PORTFOLIO_ADD = null;
            const btn = document.getElementById("pf_add_btn");
            if (btn) {
                btn.disabled = false;
                btn.textContent = "ADD";
            }
            showToast("Sent to AI engine", "success");
        }
    }

    // Render expensive portfolio table only when portfolio tab is active.
    if (isTabActive('portfolio') && wsPositions) {
        window.__PORTFOLIO_LOCK = true;
        schedulePortfolioRender(wsPositions, state?.portfolio_intelligence?.account_metrics || null, false);
    }
}




// Version: 14.0 FINAL - 100% Dynamic, Zero Hardcoding  

// November 19, 2025, 10:55 PM IST

// Pure API Integration | CSS Classes | No Inline Styles

// ============================================================================



'use strict';



// ============================================================================

// CONFIGURATION

// ============================================================================

const CONFIG = {

    API_BASE: '/api',

    REFRESH_INTERVALS: {

        dashboard: 30000,  // 30 seconds

        stocks: 30000,

        predictions: 60000,

        portfolio: 60000,

        analytics: 120000,

        news: 300000

    },

    CACHE_DURATION: 30000,

    TIMEOUT: 60000,

    MAX_RETRIES: 3,

    DEBUG_MODE: false

};

// Sync Ledger on Boot (Neural Ready Gate handles this now)



// ============================================================================

// GLOBAL STATE

// ============================================================================

let dashState = {

    data: null,

    stocks: [],

    predictions: [],

    portfolio: [],

    analytics: null,

    news: [],
    newsSectorwise: {},

    userTickers: [],

    hiddenTickers: [],

    charts: {},

    lastUpdate: {},

    performance: {

        api_calls: 0,

        cache_hits: 0,

        cache_misses: 0,

        success_rate: 100

    }

};



// ============================================================================

// ADVANCED API CLIENT

// ============================================================================

class APIClient {

    constructor(baseURL) {

        this.baseURL = baseURL;

        this.cache = new Map();

    }



    async fetch(endpoint, options = {}) {

        const { cache = true, timeout = CONFIG.TIMEOUT, retries = 1 } = options;

        const cacheKey = endpoint;

        const now = Date.now();



        // Check cache

        if (cache && this.cache.has(cacheKey)) {

            const cached = this.cache.get(cacheKey);

            if (now - cached.timestamp < CONFIG.CACHE_DURATION) {

                dashState.performance.cache_hits++;

                if (CONFIG.DEBUG_MODE) console.log(`[Cache HIT] ${endpoint}`);

                return cached.data;

            }

        }



        dashState.performance.cache_misses++;



        // Execute request

        let timeoutId = null;
        let attempt = 0;
        while (attempt <= retries) {
        try {

            const controller = new AbortController();

            timeoutId = setTimeout(() => controller.abort(), timeout);



            const response = await fetch(`${this.baseURL}${endpoint}`, {

                signal: controller.signal,

                headers: {

                    'Content-Type': 'application/json',

                    'X-Requested-With': 'XMLHttpRequest'

                }

            });



            if (!response.ok) {

                throw new Error(`HTTP ${response.status}`);

            }



            const data = await response.json();



            // Cache successful response
            if (cache && data) {
                this.cache.set(cacheKey, { data, timestamp: now });
            }



            dashState.performance.api_calls++;

            return data;



        } catch (error) {
            if (error && error.name === 'AbortError') {
                console.warn(`[API TIMEOUT] ${endpoint} exceeded ${timeout}ms`);
                if (attempt < retries) {
                    attempt++;
                    continue;
                }
                if (this.cache.has(cacheKey)) {
                    const stale = this.cache.get(cacheKey);
                    if (stale && stale.data) {
                        console.warn(`[STALE CACHE] Using last known response for ${endpoint}`);
                        return stale.data;
                    }
                }
                return null;
            }
            console.error(`[API ERROR] ${endpoint}:`, error);
            if (this.cache.has(cacheKey)) {
                const stale = this.cache.get(cacheKey);
                if (stale && stale.data) {
                    console.warn(`[STALE CACHE] API error fallback for ${endpoint}`);
                    return stale.data;
                }
            }
            return null;
        } finally {
            // Ensure timer is always released even when fetch throws.
            try { clearTimeout(timeoutId); } catch { }
        }
        }
        return null;

    }



    async post(endpoint, body) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(body)
            });
            return await response.json();
        } catch (error) {
            console.error(`[API POST ERROR] ${endpoint}:`, error);
            return { success: false, error: error.message };
        }
    }

    async delete(endpoint) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            return await response.json();
        } catch (error) {
            console.error(`[API DELETE ERROR] ${endpoint}:`, error);
            return { success: false, error: error.message };
        }
    }

    clearCache() {
        this.cache.clear();
        console.log('[Cache] Cleared');
    }
}



// ----------------------------------------------------------------------------

// DATA SAFETY UTILITIES (Aligns with Backend Contract)

// ----------------------------------------------------------------------------

function safePrediction(p) {

    return {

        symbol: p?.symbol || "-",

        signal: p?.signal || "HOLD",

        confidence: Number(p?.confidence ?? 50.0).toFixed(1),

        target_price: Number(p?.target_price ?? 0).toFixed(2),

        current_price: Number(p?.current_price ?? 0).toFixed(2),

        predicted_return: Number(p?.predicted_return ?? 0).toFixed(2),

        risk_level: p?.risk_level || "MEDIUM",

        models_used: Array.isArray(p?.models_used) ? p.models_used : [],

        timestamp: p?.timestamp || new Date().toISOString()

    };

}



const api = new APIClient(CONFIG.API_BASE);



// ============================================================================

// DATA LOADING FUNCTIONS

// ============================================================================

function ensureDashboardFallbackState() {
    if (dashState.data && typeof dashState.data === 'object' && Object.keys(dashState.data).length) {
        return dashState.data;
    }
    const neural = window.NEURAL_STATE || {};
    const cognitive = isNonEmptyObject(neural.cognitive_state) ? neural.cognitive_state : (isNonEmptyObject(neural.ai_engine) ? neural.ai_engine : {});
    const portfolio = neural.portfolio_intelligence || {};
    const positions = Array.isArray(portfolio.positions) ? portfolio.positions : [];
    dashState.data = {
        live_indices: Array.isArray(dashState.data?.live_indices) ? dashState.data.live_indices : [],
        market_status: dashState.data?.market_status || {},
        macro: {
            commodities: Array.isArray(dashState.data?.macro?.commodities) ? dashState.data.macro.commodities : [],
            forex: Array.isArray(dashState.data?.macro?.forex) ? dashState.data.macro.forex : [],
            crypto: Array.isArray(dashState.data?.macro?.crypto) ? dashState.data.macro.crypto : [],
            interest_rates: Array.isArray(dashState.data?.macro?.interest_rates) ? dashState.data.macro.interest_rates : [],
            global_sync: Array.isArray(dashState.data?.macro?.global_sync) ? dashState.data.macro.global_sync : [] ,
            details: {
                gdp: dashState.data?.macro?.details?.gdp || null,
                inflation: dashState.data?.macro?.details?.inflation || null
            }
        },
        ai_performance: {
            accuracy: neural?.accuracy || cognitive?.accuracy || cognitive?.market_state?.system_confidence || 0,
            models_active: Array.isArray(neural?.active_models) ? neural.active_models.length : Number(neural?.models_active || cognitive?.models_active || 0),
            prediction_accuracy: neural?.market_state?.system_confidence || cognitive?.market_state?.system_confidence || 0,
            total_predictions: Number(cognitive?.data_points || neural?.data_points || (Array.isArray(dashState.predictions) ? dashState.predictions.length : 0)),
            data_points_per_minute: Number(cognitive?.data_points_per_minute || neural?.data_points || 0)
        },
        portfolio_summary: {
            total_value: positions.reduce((sum, p) => sum + Number(p.current_value || 0), 0),
            positions_count: positions.length
        }
    };
    return dashState.data;
}

function isNonEmptyObject(value) {
    return !!value && typeof value === 'object' && Object.keys(value).length > 0;
}

function publishNexusDashboardState() {
    const data = dashState.data || {};
    const cognitiveState =
        (isNonEmptyObject(data.cognitive_state) && data.cognitive_state)
        || (isNonEmptyObject(data.ai_engine) && data.ai_engine)
        || (isNonEmptyObject(window.NEURAL_STATE?.cognitive_state) && window.NEURAL_STATE.cognitive_state)
        || (isNonEmptyObject(window.NEURAL_STATE?.ai_engine) && window.NEURAL_STATE.ai_engine)
        || {};
    window.__NEXUS_DASHBOARD_STATE = {
        data,
        live_indices: Array.isArray(data.live_indices) ? data.live_indices : [],
        marketSentiment: dashState.marketSentiment || data.market_sentiment || {},
        predictions: Array.isArray(dashState.predictions) ? dashState.predictions : [],
        stocks: Array.isArray(dashState.stocks) ? dashState.stocks : [],
        news: Array.isArray(dashState.news) ? dashState.news : [],
        alerts: Array.isArray(dashState.portfolioNewsAlerts) ? dashState.portfolioNewsAlerts : [],
        topStocks: Array.isArray(data.top_stocks) ? data.top_stocks : [],
        portfolioMetrics: dashState.portfolioMetrics || data.PORTFOLIO_STATE?.account_metrics || {},
        PORTFOLIO_STATE: data.PORTFOLIO_STATE || {},
        portfolio_intelligence: window.NEURAL_STATE?.portfolio_intelligence || data.PORTFOLIO_STATE?.portfolio_intelligence || {},
        ai_performance: data.ai_performance || {},
        ai_engine: cognitiveState,
        cognitive_state: cognitiveState,
        newsIntelligence: dashState.newsIntelligence || data.news_intelligence || {},
        newsSectorwise: dashState.newsSectorwise || data.sectorwise || {},
        newsNarratives: dashState.newsNarratives || data.narratives || [],
        newsNarrativeMomentum: dashState.newsNarrativeMomentum || data.narrative_momentum || [],
        newsShockPropagation: dashState.newsShockPropagation || data.shock_propagation || [],
        newsPredictionContext: dashState.newsPredictionContext || data.prediction_context || [],
        infoAdvantage: dashState.infoAdvantage || data.information_advantage || {},
        lastUpdate: { ...(dashState.lastUpdate || {}) }
    };
    return window.__NEXUS_DASHBOARD_STATE;
}

function renderStocksEmptyState(message = 'Live stock feed is syncing...') {
    const tbody = document.getElementById('stocksTableBody') || document.getElementById('recommendationsTableBody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:2rem; color: var(--text-secondary);">${message}</td></tr>`;
}

function renderAnalyticsFallback(message = 'Analytics is syncing from the AI engine...') {
    const content = document.getElementById('analyticsContent');
    if (!content) return;
    content.innerHTML = `<div class="text-center" style="padding:2rem; color: var(--text-secondary);">${message}</div>`;
}

function renderNewsFallback(message = 'News intelligence is syncing from live feeds...') {
    const container = document.getElementById('newsContent');
    if (!container) return;
    container.innerHTML = `<div style="text-align:center; padding:2rem; color: var(--text-secondary);">${message}</div>`;
}

async function loadPortfolioState(force = false) {
    if (window.__PF_STATE_INFLIGHT) return false;
    window.__PF_STATE_INFLIGHT = true;
    try {
        const data = await api.fetch('/portfolio/state', {
            cache: !force,
            timeout: Math.max(1, Math.floor(CONFIG.TIMEOUT * 0.5))
        });

        if (!data || data.success === false) {
            setDashboardPortfolioEmptyState();
            updateDashboardMarketIntelligenceCard();
            return false;
        }

        const positions = Array.isArray(data.positions) ? data.positions : [];
        const accountMetrics = (data.account_metrics && typeof data.account_metrics === 'object')
            ? data.account_metrics
            : {};

        if (!window.NEURAL_STATE || typeof window.NEURAL_STATE !== 'object') {
            window.NEURAL_STATE = {};
        }
        window.NEURAL_STATE.portfolio_intelligence = {
            ...(window.NEURAL_STATE.portfolio_intelligence || {}),
            positions,
            account_metrics: accountMetrics
        };

        const merged = mergePortfolioWithLiveStocks(positions);
        updatePositionMetricHistory(merged);
        updateDashboardPortfolioCardsFromPI({
            positions: merged,
            account_metrics: accountMetrics
        });
        if (isTabActive('portfolio')) {
            schedulePortfolioRender(merged, accountMetrics, false);
        }
        dashState.lastUpdate.portfolio = Date.now();
        publishNexusDashboardState();
        syncV7DashboardIframe(dashState.data || {});
        return true;
    } catch (error) {
        console.error('Portfolio state load error:', error);
        setDashboardPortfolioEmptyState();
        // Don't call updateDashboardMarketIntelligenceCard here - let loadDashboard() handle it with full data
        return false;
    } finally {
        window.__PF_STATE_INFLIGHT = false;
    }
}

function syncV7DashboardIframe(data = {}) {
    const iframe = document.querySelector('#dashboard iframe');
    if (!iframe || !iframe.contentWindow || !iframe.contentWindow.NexusAPI || typeof iframe.contentWindow.NexusAPI.refresh !== 'function') {
        if (iframe && !iframe.dataset.v7SyncBound) {
            iframe.dataset.v7SyncBound = '1';
            iframe.addEventListener('load', () => {
                syncV7DashboardIframe(dashState.data || {});
            }, { once: true });
        }
        return false;
    }

    const resolveIndexArray = (input) => {
        if (Array.isArray(input)) return input;
        if (input && typeof input === 'object') {
            return Object.entries(input).map(([name, value]) => {
                if (typeof value === 'object' && value !== null) {
                    return {
                        name,
                        value: value.value ?? value.last ?? value.price ?? value.close ?? value_level ?? 0,
                        change: value.change ?? value.change_percent ?? value.delta ?? 0
                    };
                }
                return { name, value, change: 0 };
            });
        }
        return [];
    };

    const liveIndexList = resolveIndexArray(data.live_indices || data.indices || data.market_indices || data.global_sync);
    console.log('📊 [IFRAME SYNC] Live indices from API:', liveIndexList);
    const indexMap = {};
    const changePercentMap = {};
    liveIndexList.forEach((index) => {
        const name = String(index?.name || '').toUpperCase();
        const symbol = String(index?.symbol || '').toUpperCase();
        let key = null;
        if (name.includes('NIFTY 50') || name === 'NIFTY' || symbol.includes('NSEI')) {
            key = 'nifty50';
        } else if (name.includes('BANK NIFTY') || name.includes('BANK') || symbol.includes('NSEBANK')) {
            key = 'bankNifty';
        } else if (name.includes('SENSEX') || symbol.includes('BSESN')) {
            key = 'sensex';
        } else if (name.includes('S&P') || symbol.includes('GSPC')) {
            key = 'sp500';
        } else if (name.includes('DOW') || symbol.includes('DJI')) {
            key = 'dowJones';
        } else if (name.includes('NASDAQ') || symbol.includes('IXIC')) {
            key = 'nasdaq';
        }

        if (!key) {
            console.log(`   ⚠️  Unmatched index: name='${name}' symbol='${symbol}'`);
            return;
        }
        const value = Number(index?.value ?? index?.last ?? index?.price ?? index?.close);
        const changePct = Number(index?.change_percent ?? index?.change ?? 0);
        if (Number.isFinite(value)) {
            indexMap[key] = value;
            changePercentMap[key] = changePct;
            console.log(`   ✓ ${key} = ${value} (${changePct >= 0 ? '+' : ''}${changePct}%)`);
        }
    });
    console.log('📊 [IFRAME SYNC] Final indexMap:', indexMap);
    console.log('📊 [IFRAME SYNC] Final changePercentMap:', changePercentMap);

    const ai = data.ai_performance || {};
    const aiEngine =
        (isNonEmptyObject(data.ai_engine) && data.ai_engine)
        || (isNonEmptyObject(data.cognitive_state) && data.cognitive_state)
        || (isNonEmptyObject(window.NEURAL_STATE?.cognitive_state) && window.NEURAL_STATE.cognitive_state)
        || (isNonEmptyObject(window.NEURAL_STATE?.ai_engine) && window.NEURAL_STATE.ai_engine)
        || {};
    const predictionRows = Array.isArray(dashState.predictions) && dashState.predictions.length
        ? dashState.predictions.slice(0, 7)
        : Array.isArray(window.NEURAL_STATE?.predictions) && window.NEURAL_STATE.predictions.length
            ? window.NEURAL_STATE.predictions.slice(0, 7)
            : Array.isArray(window.NEURAL_STATE?.opportunities) && window.NEURAL_STATE.opportunities.length
                ? window.NEURAL_STATE.opportunities.slice(0, 7)
                : [];
    const predLabels = predictionRows.length
        ? predictionRows.map((row, idx) => String(row?.symbol || row?.name || `S${idx + 1}`).replace(/\.NS|\.BO/g, ''))
        : undefined;
    const predValues = predictionRows.length
        ? predictionRows.map((row) => Number(row?.confidence ?? row?.prediction?.confidence))
        : undefined;
    const realityValues = predictionRows.length
        ? predictionRows.map((row) => {
            const actual = row?.actual ?? row?.actual_value ?? row?.realized_return ?? row?.realized_value ?? row?.prediction?.actual;
            const value = Number(actual);
            return Number.isFinite(value) ? value : null;
        })
        : undefined;

    const sentiment = dashState.marketSentiment || data.market_sentiment || window.NEURAL_STATE?.market_sentiment || {};
    const marketStatus = data.market_status || dashState.data?.market_status || window.NEURAL_STATE?.market_status || {};
    const liveIndices = Array.isArray(dashState.data?.live_indices)
        ? dashState.data.live_indices
        : Array.isArray(data.live_indices)
            ? data.live_indices
            : Array.isArray(window.NEURAL_STATE?.live_indices)
                ? window.NEURAL_STATE.live_indices
                : [];
    const portfolioState = dashState.data?.PORTFOLIO_STATE
        || data.PORTFOLIO_STATE
        || window.NEURAL_STATE?.PORTFOLIO_STATE
        || data.portfolio
        || data.portfolio_state
        || window.NEURAL_STATE?.portfolio
        || {};
    const portfolioMetrics = portfolioState.account_metrics
        || portfolioState.metrics
        || portfolioState
        || dashState.portfolioMetrics
        || window.NEURAL_STATE?.portfolio_intelligence?.account_metrics
        || window.NEURAL_STATE?.portfolio_intelligence
        || {};
    const sentimentCounts = [
        Number(sentiment.bullish_count || 0),
        Number(sentiment.neutral_count || 0),
        Number(sentiment.bearish_count || 0)
    ];
    const sentimentTotal = sentimentCounts.reduce((sum, value) => sum + (Number.isFinite(value) && value > 0 ? value : 0), 0);
    const bull = sentimentTotal > 0 ? Math.round((Math.max(0, sentimentCounts[0]) / sentimentTotal) * 100) : undefined;
    const neutral = sentimentTotal > 0 ? Math.round((Math.max(0, sentimentCounts[1]) / sentimentTotal) * 100) : undefined;
    const bear = sentimentTotal > 0 ? Math.max(0, 100 - bull - neutral) : undefined;

    const portfolioValue = Number(
        ai.portfolio_value
        ?? ai.total_portfolio_value
        ?? data.PORTFOLIO_STATE?.total_value
        ?? data.PORTFOLIO_STATE?.value
        ?? data.portfolio?.total_value
        ?? data.portfolio?.value
        ?? data.portfolio_state?.total_value
        ?? data.portfolio_state?.value
        ?? window.NEURAL_STATE?.portfolio_intelligence?.account_metrics?.total_value
        ?? window.NEURAL_STATE?.portfolio_intelligence?.total_value
        ?? window.NEURAL_STATE?.portfolio_intelligence?.value
        ?? dashState.data?.portfolio_value
        ?? dashState.data?.total_portfolio_value
        ?? 0
    ) || undefined;

    const totalReturn = Number(portfolioMetrics?.total_return ?? portfolioMetrics?.returns ?? portfolioMetrics?.portfolio_return ?? 0) || undefined;
    const totalReturnPct = Number(portfolioMetrics?.total_return_pct ?? portfolioMetrics?.returns_pct ?? portfolioMetrics?.portfolio_return_pct ?? portfolioMetrics?.return_percent ?? 0) || undefined;
    const activePositions = Array.isArray(portfolioState?.positions)
        ? portfolioState.positions.length
        : (Array.isArray(window.NEURAL_STATE?.portfolio_intelligence?.positions) ? window.NEURAL_STATE.portfolio_intelligence.positions.length : undefined);
    const portfolioVar = Number(
        portfolioMetrics?.var95
        ?? portfolioMetrics?.var_95
        ?? portfolioMetrics?.value_at_risk
        ?? portfolioMetrics?.var
        ?? portfolioMetrics?.portfolio_var
        ?? NaN
    );
    const aiIndex = Number(ai.index_score ?? ai.ai_index ?? ai.model_index ?? ai.index ?? NaN);
    const aiIndexChange = Number(ai.index_change ?? ai.index_delta ?? ai.market_state?.index_change ?? NaN);
    const newsItems = Array.isArray(data.news_items)
        ? data.news_items.slice(0, 6)
        : Array.isArray(dashState.news)
            ? dashState.news.slice(0, 6)
            : Array.isArray(window.NEURAL_STATE?.news)
                ? window.NEURAL_STATE.news.slice(0, 6)
                : undefined;
    const alerts = Array.isArray(data.alerts)
        ? data.alerts.slice(0, 6)
        : Array.isArray(dashState.portfolioNewsAlerts)
            ? dashState.portfolioNewsAlerts.slice(0, 6)
            : Array.isArray(window.NEURAL_STATE?.portfolio_alerts)
                ? window.NEURAL_STATE.portfolio_alerts.slice(0, 6)
                : undefined;
    const topStocks = Array.isArray(data.top_stocks)
        ? data.top_stocks.slice(0, 10)
        : Array.isArray(window.NEURAL_STATE?.top_stocks)
            ? window.NEURAL_STATE.top_stocks.slice(0, 10)
            : Array.isArray(window.NEURAL_STATE?.opportunities)
                ? window.NEURAL_STATE.opportunities.slice(0, 10)
                : undefined;

    const payload = {
        portfolioValue,
        totalReturn: Number.isFinite(totalReturn) ? totalReturn : undefined,
        totalReturnPct: Number.isFinite(totalReturnPct) ? totalReturnPct : undefined,
        activePositions: Number.isFinite(activePositions) ? activePositions : undefined,
        portfolioVar: Number.isFinite(portfolioVar) ? portfolioVar : undefined,
        portfolioVarChange: portfolioMetrics?.var_change ?? portfolioMetrics?.var_delta ?? undefined,
        modelAccuracy: Number(ai.prediction_accuracy ?? ai.accuracy ?? ai.accuracy_percent ?? ai.market_state?.system_confidence ?? NaN) || undefined,
        totalPredictions: Number(ai.total_predictions ?? ai.predictions_today ?? ai.data_points ?? predictionRows.length) || undefined,
        aiIndex: Number.isFinite(aiIndex) ? aiIndex : undefined,
        aiIndexChange: Number.isFinite(aiIndexChange) ? aiIndexChange : undefined,
        aiIndexPrice: Number(ai.index_price ?? ai.price ?? ai.value ?? NaN) || undefined,
        aiIndexPeriod: data.market_status?.session || undefined,
        aiIndexTrend: data.news_intelligence?.market_regime || data.market_sentiment?.label || undefined,
        ai_engine: aiEngine,
        cognitive_state: aiEngine,
        indices: indexMap,
        indicesChangePercent: changePercentMap,
        marketStatus,
        marketSentiment: sentiment,
        stocks: topStocks,
        topStocks,
        newsItems,
        alerts,
        newsIntelligence: dashState.newsIntelligence || data.news_intelligence || window.NEURAL_STATE?.news_intelligence || undefined,
        macro: data.macro || {},
        live_indices: liveIndices,
        PORTFOLIO_STATE: portfolioState,
        portfolioMetrics,
        portfolio_intelligence: window.NEURAL_STATE?.portfolio_intelligence || portfolioState.portfolio_intelligence || undefined,
        ticker: {
            price: portfolioValue,
            change: Number(data.market_sentiment?.vix_change ?? data.market_sentiment?.vix_change ?? 0) || undefined
        }
    };

    if (sentimentTotal > 0) {
        payload.bull = bull;
        payload.neutral = neutral;
        payload.bear = bear;
    }

    if (
        predLabels
        && predValues
        && realityValues
        && predValues.every((value) => Number.isFinite(value))
        && realityValues.every((value) => value !== null && Number.isFinite(value))
    ) {
        payload.predLabels = predLabels;
        payload.predictions = predValues;
        payload.reality = realityValues;
    }
    if (Array.isArray(predValues) && predValues.length) {
        const cleanPreds = predValues.filter(Number.isFinite);
        if (cleanPreds.length) {
            const avgPred = cleanPreds.reduce((sum, value) => sum + value, 0) / cleanPreds.length;
            const normalizedAvg = avgPred > 0 && avgPred <= 1 ? avgPred * 100 : avgPred;
            payload.predictionViewLabel = `${Math.round(normalizedAvg)}% ▾`;
        }
    }

    try {
        iframe.contentWindow.NexusAPI.refresh(payload);
        return true;
    } catch (error) {
        console.warn('V7 dashboard iframe sync failed:', error);
        return false;
    }
}

async function loadDashboard() {
    if (window.__DASH_INFLIGHT) return false;
    window.__DASH_INFLIGHT = true;

    try {

        if (CONFIG.DEBUG_MODE) console.log('📊 Loading dashboard data...');

        let data = await api.fetch('/dashboard-data/live', {
            timeout: Math.max(1, Math.floor(CONFIG.TIMEOUT * 0.5))
        });
        if (!data || !data.success) {
            data = await api.fetch('/dashboard-data', {
                timeout: Math.max(1, Math.floor(CONFIG.TIMEOUT * 0.5))
            });
        }

        // 🔍 DEEP DEBUG: Log raw API response
        console.log('🔍 RAW API Response from /dashboard-data:', data);
        console.log('   ├─ data.success:', data?.success);
        console.log('   ├─ data.data:', data?.data);
        console.log('   ├─ Keys in data.data:', Object.keys(data?.data || {}));
        console.log('   └─ Full response structure:', JSON.stringify(data, null, 2).substring(0, 500));

        if (!data || !data.success) {
            console.error('Dashboard API failed', data);
            dashState.data = ensureDashboardFallbackState();
            updateDashboardMarketIntelligenceCard(dashState.data);
            updateDashboardUI();
            updateDashboardMarketPulseCard();
            renderPredictionsWorldState();
            return false;
        }

        const dashboardPayload = (data && typeof data.data === 'object' && data.data && Object.keys(data.data).length)
            ? data.data
            : (data && typeof data === 'object' && !Array.isArray(data))
                ? Object.fromEntries(Object.entries(data).filter(([key]) => !['success', 'message', 'error'].includes(key)))
                : {};
        dashState.data = dashboardPayload;
        if (isNonEmptyObject(dashState.data.ai_engine) || isNonEmptyObject(dashState.data.cognitive_state)) {
            if (!window.NEURAL_STATE || typeof window.NEURAL_STATE !== 'object') {
                window.NEURAL_STATE = {};
            }
            window.NEURAL_STATE.cognitive_state = isNonEmptyObject(dashState.data.cognitive_state)
                ? dashState.data.cognitive_state
                : dashState.data.ai_engine;
            window.NEURAL_STATE.ai_engine = isNonEmptyObject(dashState.data.ai_engine)
                ? dashState.data.ai_engine
                : dashState.data.cognitive_state;
            if (dashState.data.PORTFOLIO_STATE?.portfolio_intelligence) {
                window.NEURAL_STATE.portfolio_intelligence = dashState.data.PORTFOLIO_STATE.portfolio_intelligence;
            }
        }
        
        // 🔍 DEEP DEBUG: Log assigned dashState
        console.log('🔍 dashState.data after API:', dashState.data);
        console.log('   ├─ market_status:', dashState.data.market_status);
        console.log('   ├─ macro:', dashState.data.macro);
        console.log('   ├─ news_intelligence:', dashState.data.news_intelligence);
        console.log('   ├─ market_sentiment:', dashState.data.market_sentiment);
        console.log('   └─ All keys:', Object.keys(dashState.data));

        publishNexusDashboardState();
        syncV7DashboardIframe(dashState.data || {});

        // 🔥 Fetch AI Bootstrap Metrics (Accuracy, Models, Regime) in the background.
        void api.fetch('/bootstrap', {
            cache: false,
            timeout: Math.max(8000, Math.floor(CONFIG.TIMEOUT / 2))
        }).then((bootstrapData) => {
            if (bootstrapData && bootstrapData.success && dashState.data) {
                if (bootstrapData.ai_performance) {
                    dashState.data.ai_performance = bootstrapData.ai_performance;
                }
                if (isNonEmptyObject(bootstrapData.cognitive_state)) {
                    dashState.data.ai_engine = bootstrapData.cognitive_state;
                    dashState.data.cognitive_state = bootstrapData.cognitive_state;
                    if (!window.NEURAL_STATE || typeof window.NEURAL_STATE !== 'object') {
                        window.NEURAL_STATE = {};
                    }
                    window.NEURAL_STATE.cognitive_state = bootstrapData.cognitive_state;
                    window.NEURAL_STATE.ai_engine = bootstrapData.cognitive_state;
                }
                if (CONFIG.DEBUG_MODE) console.log('🧠 AI Performance Bootstrap Sync:', dashState.data.ai_performance);
                publishNexusDashboardState();
                syncV7DashboardIframe(dashState.data || {});
                updateDashboardUI();
            }
        }).catch((err) => {
            console.error('AI Bootstrap fetch failed:', err);
        });

        dashState.lastUpdate.dashboard = Date.now();

        // 🔍 DEBUG: Before calling update functions
        console.log('🔍 About to call updateDashboardMarketIntelligenceCard with dashState.data:', dashState.data);
        
        // Update dashboard market cards with live data - PASS DATA AS PARAMETER
        updateDashboardMarketIntelligenceCard(dashState.data);
        // Always refresh market pulse so news stays current
        updateDashboardMarketPulseCard();
        if (window.NEURAL_STATE?.portfolio_intelligence) {
            updateDashboardPortfolioSnapshotCard(window.NEURAL_STATE.portfolio_intelligence);
        }

        updateDashboardUI();
        publishNexusDashboardState();
        syncV7DashboardIframe(dashState.data || {});
        renderPredictionsWorldState();

        if (CONFIG.DEBUG_MODE) console.log('âœ… Dashboard loaded');

        return true;



    } catch (error) {

        console.error('Dashboard error:', error);
        dashState.data = ensureDashboardFallbackState();
        updateDashboardMarketIntelligenceCard(dashState.data);
        updateDashboardUI();
        publishNexusDashboardState();
        syncV7DashboardIframe(dashState.data || {});
        updateDashboardMarketPulseCard();
        renderDashboardCards();
        renderPredictionsWorldState();

        return false;

    } finally {
        window.__DASH_INFLIGHT = false;
    }

}



async function loadStocks() {

    try {

        if (CONFIG.DEBUG_MODE) console.log('📊 Loading stocks...');
        console.log('🔍 About to fetch /stocks API...');
        const data = await api.fetch('/stocks?limit=20', {
            cache: true,
            timeout: Math.max(1, Math.floor(CONFIG.TIMEOUT * 0.5))
        });

        console.log('🔍 /stocks API Response:', data);
        console.log('🔍 /stocks API Response structure:', {
            has_data: !!data,
            has_success: !!data?.success,
            has_data_field: !!data?.data,
            data_type: typeof data?.data,
            data_is_array: Array.isArray(data?.data),
            data_length: Array.isArray(data?.data) ? data.data.length : 'N/A',
            first_stock: data?.data?.[0]
        });

        if (CONFIG.DEBUG_MODE) console.log('Stocks API response:', data);

        let stocksPayload = Array.isArray(data?.data) ? data.data
            : Array.isArray(data?.stocks) ? data.stocks
            : Array.isArray(data?.results) ? data.results
            : [];

        if (!stocksPayload.length) {
            console.error('❌ Stocks API failed - missing data or empty list:', {
                has_data: !!data,
                has_success: !!data?.success,
                payload_type: typeof data?.data,
                stocks_found: Array.isArray(data?.stocks),
                results_found: Array.isArray(data?.results)
            });
            const predictionFallback = Array.isArray(dashState.predictions) ? normalizePredictionsForTable(dashState.predictions) : [];
            if (predictionFallback.length) {
                console.warn('⚠️ Using live prediction rows as dashboard recommendations fallback', predictionFallback.length);
                stocksPayload = predictionFallback;
            }
        }
        if (!stocksPayload.length) {
            const fallbackStocks = Array.isArray(dashState.data?.top_stocks) ? dashState.data.top_stocks : [];
            if (fallbackStocks.length) {
                console.warn('⚠️ Using dashboard top_stocks fallback for stock recommendations', fallbackStocks.length);
                stocksPayload = fallbackStocks;
            }
        }
        if (!stocksPayload.length) {
            if (Array.isArray(dashState.stocks) && dashState.stocks.length) {
                console.log('📊 Using cached stocks:', dashState.stocks.length);
                renderStocksTable();
                return true;
            }
            console.log('📊 No cached stocks, showing empty state');
            renderStocksEmptyState('Live stock feed is syncing...');
            return false;
        }

        dashState.stocks = stocksPayload;

        dashState.lastUpdate.stocks = Date.now();
        publishNexusDashboardState();

        console.log('✅ Stocks loaded successfully:', dashState.stocks.length, 'stocks');

        if (CONFIG.DEBUG_MODE) {
            console.log(`✅ Loaded ${dashState.stocks.length} stocks`);
            console.log('First stock:', dashState.stocks[0]);
        }

        renderStocksTable();
        if (window.NEURAL_STATE?.portfolio_intelligence?.positions && isTabActive('portfolio')) {
            const mergedPositions = mergePortfolioWithLiveStocks(window.NEURAL_STATE.portfolio_intelligence.positions);
            updatePositionMetricHistory(mergedPositions);
            schedulePortfolioRender(mergedPositions, window.NEURAL_STATE?.portfolio_intelligence?.account_metrics || null, false);
        }

        return true;

    } catch (error) {

        console.error('❌ Stocks error:', error);
        console.log('🔍 Stocks error details:', { message: error.message, stack: error.stack });
        if (Array.isArray(dashState.stocks) && dashState.stocks.length) {
            console.log('📊 Using cached stocks after error:', dashState.stocks.length);
            renderStocksTable();
            return true;
        }
        console.log('📊 No cached stocks after error, showing empty state');
        renderStocksEmptyState('Live stock feed is syncing...');

        return false;

    }

}



async function loadPredictions() {
    if (window.__PRED_INFLIGHT) return false;
    window.__PRED_INFLIGHT = true;
    removeLegacyPredictionMatrixUI();
    try {
        const data = await safeFetchJSON("/api/predictions");
        if (!data || data.success === false) {
            if (isTabActive('predictions')) displayLivePredictions([]);
            return false;
        }
        const rows = normalizePredictionsForTable(data);
        dashState.predictions = rows;
        dashState.lastUpdate.predictions = Date.now();
        publishNexusDashboardState();
        if (!rows.length) {
            if (isTabActive('predictions')) displayLivePredictions([]);
            return true;
        }
        const normalizedData = { ...(data || {}), stocks: rows, predictions: rows };

        updatePredictionCards(normalizedData);
        updatePredictionTable(normalizedData);
        if (isTabActive('predictions')) {
            displayLivePredictions(rows.slice(0, 20));
        }
        return true;
    } finally {
        window.__PRED_INFLIGHT = false;
    }
}

// Adapter 1 — Cards
function updatePredictionCards(data) {
    const rows = normalizePredictionsForTable(data);
    const derivedConfidence = rows.length
        ? rows.reduce((sum, row) => sum + Number(row?.confidence ?? row?.confidences15d ?? row?.prediction?.confidence ?? 0), 0) / rows.length
        : null;
    const derivedModels = (() => {
        const modelSet = new Set();
        rows.forEach((row) => {
            const pred = (typeof row?.prediction === 'object' && row.prediction) ? row.prediction : row;
            const models = Array.isArray(pred?.models_used) ? pred.models_used : [];
            models.forEach((model) => modelSet.add(String(model)));
        });
        return modelSet.size || null;
    })();
    const derivedRegime = (() => {
        const regimes = rows.map((row) => String(row?.market_regime || row?.regime || '')).filter(Boolean);
        if (!regimes.length) return null;
        const counts = regimes.reduce((acc, regime) => {
            acc[regime] = (acc[regime] || 0) + 1;
            return acc;
        }, {});
        return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || null;
    })();

    const accEl = document.getElementById("globalAccuracyValue");
    if (accEl) {
        const acc = Number(data?.global_accuracy ?? derivedConfidence);
        accEl.textContent = Number.isFinite(acc) && acc > 0 ? `${acc.toFixed(1)}%` : "—";
    }

    const ensEl = document.getElementById("activeEnsemblesValue");
    if (ensEl) {
        const models = Number(data?.models_active ?? derivedModels);
        ensEl.textContent = Number.isFinite(models) && models >= 0 ? String(models) : "—";
    }

    const regEl = document.getElementById("marketRegimeValue");
    if (regEl) regEl.textContent = data?.market_regime || derivedRegime || "UNKNOWN";
    const strategyEl = document.getElementById("aiStrategyValue");
    if (strategyEl) strategyEl.textContent = String(data?.macro_context?.mode || data?.ai_mode || data?.market_regime || derivedRegime || 'ADAPTIVE').replaceAll('_', ' ');
}

// Adapter 2 — Matrix Bridge
function updatePredictionMatrix(data) {
    return;
}

// Adapter 3 — TABLE
function updatePredictionTable(data) {
    const rows = normalizePredictionsForTable(data);
    displayLivePredictions(rows.slice(0, 20));
}

function normalizePredictionsForTable(payload) {
    const rawRows = Array.isArray(payload)
        ? payload
        : (Array.isArray(payload?.stocks)
            ? payload.stocks
            : (Array.isArray(payload?.predictions) ? payload.predictions : []));

    const toNum = (v) => {
        const n = Number(v);
        return Number.isFinite(n) ? n : null;
    };

    const normalizeHorizon = (obj, fallbackTarget = null, fallbackReturnPct = null, currentPrice = null) => {
        const src = obj || {};
        let target = toNum(src.targetprice ?? src.target_price ?? fallbackTarget);
        let ret = toNum(src.returnpercent ?? src.return_percent ?? fallbackReturnPct);
        if (ret == null && target != null && currentPrice != null && currentPrice > 0) {
            ret = ((target - currentPrice) / currentPrice) * 100;
        }
        if (target == null && ret != null && currentPrice != null && currentPrice > 0) {
            target = currentPrice * (1 + ret / 100);
        }
        return { targetprice: target, returnpercent: ret };
    };
    const cleanTarget = (v) => {
        const n = toNum(v);
        return n != null && n > 0 ? n : null;
    };

    return rawRows
        .filter(Boolean)
        .map((row) => {
            const nested = (row && typeof row.prediction === 'object') ? row.prediction : {};
            const symbol = String(row.symbol || nested.symbol || row.ticker || '').toUpperCase();
            const current = toNum(
                row.currentprice ??
                row.current_price ??
                row.price ??
                nested.current_price ??
                nested.price
            );
            const fallbackTarget = toNum(row.target_price ?? nested.target_price);
            const fallbackReturn = toNum(row.predicted_return ?? nested.predicted_return);
            const pMap = row.predictions || nested.predictions || {};
            const forecastHorizons = row.forecast_horizons || nested.forecast_horizons || {};
            const p1d = normalizeHorizon(row.predictions1d || pMap['1d'] || forecastHorizons['1d'], fallbackTarget, fallbackReturn, current);
            const p1w = normalizeHorizon(row.predictions1w || pMap['1w'] || pMap['7d'] || forecastHorizons['1w'], null, null, current);
            const p1m = normalizeHorizon(row.predictions1m || pMap['1m'] || pMap['30d'] || forecastHorizons['1m'], null, null, current);
            const p15d = normalizeHorizon(row.predictions15d || pMap['15d'], null, null, current);
            const p3m = normalizeHorizon(row.predictions3m || pMap['3m'] || forecastHorizons['3m'], null, null, current);
            const p6mObj = row.predictions6m || pMap['6m'] || pMap['180d'] || pMap['half_year'] || forecastHorizons['6m'] || null;
            const p1yObj = row.predictions1y || pMap['1y'] || pMap['12m'] || pMap['365d'] || forecastHorizons['1y'] || null;
            let p6mTarget = cleanTarget(
                row.target_6m ??
                row.target6m ??
                nested.target_6m ??
                nested.target6m ??
                p6mObj?.target_price ??
                p6mObj?.targetprice
            );
            let p1yTarget = cleanTarget(
                row.target_1y ??
                row.target1y ??
                nested.target_1y ??
                nested.target1y ??
                p1yObj?.target_price ??
                p1yObj?.targetprice
            );
            if (p6mTarget == null && current != null && current > 0) {
                const p6mRet = toNum(p6mObj?.return_percent ?? p6mObj?.returnpercent);
                if (p6mRet != null) p6mTarget = current * (1 + p6mRet / 100);
            }
            if (p1yTarget == null && current != null && current > 0) {
                const p1yRet = toNum(p1yObj?.return_percent ?? p1yObj?.returnpercent);
                if (p1yRet != null) p1yTarget = current * (1 + p1yRet / 100);
            }
            const conf = toNum(
                row.confidences15d ??
                row.confidence_15d ??
                row.confidences?.['15d'] ??
                row.confidence ??
                nested.confidences?.['15d'] ??
                nested.confidence
            ) ?? 0;
            const momentum = String(
                row.marketconditions?.momentum ||
                row.market_conditions?.momentum ||
                nested.marketconditions?.momentum ||
                nested.market_conditions?.momentum ||
                row.market_regime ||
                row.regime ||
                nested.regime ||
                nested.direction ||
                'NEUTRAL'
            ).toUpperCase();
            const volLevel = String(
                row.marketconditions?.volatilitylevel ||
                row.market_conditions?.volatility_level ||
                nested.marketconditions?.volatilitylevel ||
                nested.market_conditions?.volatility_level ||
                row.risk_level ||
                nested.risk_level ||
                'NORMAL'
            ).toUpperCase();
            let aiSize = toNum(
                row.ai_size_pct ??
                row.allocation_pct ??
                row.weight_pct ??
                row.position_size ??
                row.ai_size ??
                row.kelly_percent ??
                nested.position_size ??
                nested.kelly_percent ??
                nested.kelly_fraction
            );
            if (aiSize != null) {
                aiSize = aiSize <= 1 ? (aiSize * 100) : aiSize;
                aiSize = Math.max(0, Math.min(100, aiSize));
            }

            return {
                ...row,
                symbol,
                name: row.name || nested.name || symbol,
                currentprice: current ?? 0,
                predictions1d: p1d,
                predictions1w: p1w,
                predictions1m: p1m,
                predictions15d: p15d,
                predictions3m: p3m,
                target_6m: p6mTarget,
                target_1y: p1yTarget,
                confidences15d: conf,
                ai_size_pct: aiSize,
                ai_signal: String(row.action || row.signal || nested.action || nested.signal || 'HOLD').toUpperCase(),
                marketconditions: { momentum, volatilitylevel: volLevel },
                market_conditions: { momentum, volatility_level: volLevel },
                action: String(row.action || row.signal || nested.action || nested.signal || 'HOLD').toUpperCase(),
                current_price: current ?? 0,
                target_price: p1d.targetprice ?? (current ?? 0),
                forecast_horizons: forecastHorizons,
                session_outlook: row.session_outlook || nested.session_outlook || null,
                prediction_change: row.prediction_change || nested.prediction_change || null
            };
        })
        .filter((row) => row.symbol);
}




// ═══ DATE FORMATTER ═══
function formatPortfolioDate(isoStr) {
    if (!isoStr) return '';
    try {
        const d = new Date(isoStr);
        if (isNaN(d.getTime())) return String(isoStr);
        return d.toLocaleDateString('en-GB', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        }).replace(/,/g, '');
    } catch {
        return String(isoStr);
    }
}

function formatPortfolioDateTime(isoStr) {
    if (!isoStr) return '';
    try {
        const d = new Date(isoStr);
        if (isNaN(d.getTime())) return String(isoStr);
        const date = d.toLocaleDateString('en-GB', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        }).replace(/,/g, '');
        const time = d.toLocaleTimeString('en-GB', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
        return `${date} ${time}`;
    } catch {
        return String(isoStr);
    }
}

// ═══ FORMAT LARGE NUMBERS ═══
function formatCompact(n) {
    if (n >= 10000000) return `₹${(n / 10000000).toFixed(2)}Cr`;
    if (n >= 100000) return `₹${(n / 100000).toFixed(2)}L`;
    return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

// 🚀 UNIVERSAL PORTFOLIO RENDERER — Live Prices + Real Metrics
// Columns: Asset | Market Price | Action | Confidence | Edge | Entropy | Kelly % | Risk | TP | SL (10 cols)
function renderPortfolio(forcedPositions = null, accountMetrics = null) {
    if (window.__PF_RENDERING) return;
    window.__PF_RENDERING = true;
    try {
        const container = document.getElementById("portfolioTableBody");
        if (!container) return;
        ensurePortfolioAlertStyles();
        if ((Date.now() - Number(window.__PF_TAX_LAST_REQ_AT || 0)) > 120000) {
            window.__PF_TAX_LAST_REQ_AT = Date.now();
            loadPortfolioTaxSummary();
        }

        const pi = window.NEURAL_STATE?.portfolio_intelligence || {};
        let positions = forcedPositions || pi.positions || [];
        const metrics = accountMetrics || pi.account_metrics || {};
        const piStatus = pi.status || 'UNKNOWN';
        const hasAI = piStatus === 'OPTIMIZED' || piStatus === 'BASE_HOLD' || (forcedPositions && forcedPositions.length > 0);

        // ═══ SORTING LOGIC ═══
        if (window.__PORTFOLIO_SORT) {
            const { column, direction } = window.__PORTFOLIO_SORT;
            positions.sort((a, b) => {
                let valA = a[column];
                let valB = b[column];

                // Handle numeric values
                const numA = parseFloat(valA);
                const numB = parseFloat(valB);
                if (!isNaN(numA) && !isNaN(numB)) {
                    valA = numA;
                    valB = numB;
                } else {
                    valA = String(valA || '').toLowerCase();
                    valB = String(valB || '').toLowerCase();
                }

                if (valA < valB) return direction === 'asc' ? -1 : 1;
                if (valA > valB) return direction === 'asc' ? 1 : -1;
                return 0;
            });
        }

        // ═══ THREE CARDS — Live account metrics (no hardcoding) ═══
        const edgeEl = document.getElementById("portfolioEdgeValue");
        const riskEl = document.getElementById("portfolioRiskValue");
        const regimeEl = document.getElementById("regimeFitValue");

        if (edgeEl) {
            if (metrics.edge != null) {
                edgeEl.textContent = `${(metrics.edge * 100).toFixed(2)}%`;
                edgeEl.style.color = metrics.edge > 0 ? 'var(--electric-green)' : 'var(--electric-yellow)';
            } else {
                edgeEl.innerHTML = '<span class="ai-thinking">AI warming up</span>';
                edgeEl.style.color = 'var(--electric-yellow)';
            }
        }
        if (riskEl) {
            if (metrics.total_risk != null) {
                riskEl.textContent = (metrics.total_risk).toFixed(3);
                riskEl.style.color = metrics.total_risk > 0.5 ? 'var(--electric-red)' : 'var(--electric-yellow)';
            } else {
                riskEl.innerHTML = '<span class="ai-thinking">scanning</span>';
                riskEl.style.color = 'var(--electric-yellow)';
            }
        }
        if (regimeEl) {
            if (metrics.regimeFit != null) {
                const rfPct = (metrics.regimeFit * 100).toFixed(1);
                regimeEl.textContent = `${rfPct}%`;
                regimeEl.style.color = metrics.regimeFit > 0.5 ? 'var(--electric-green)' : metrics.regimeFit > 0 ? 'var(--electric-yellow)' : 'var(--text-muted)';
            } else {
                regimeEl.innerHTML = '<span class="ai-thinking">calibrating</span>';
                regimeEl.style.color = 'var(--electric-yellow)';
            }
        }

        // Keep inline edit stable: don't let websocket re-renders collapse edit row.
        const activeEdit = window.__PF_INLINE_EDIT_SYMBOL;
        if (activeEdit) {
            if (document.getElementById(`edit_qty_${activeEdit}`)) {
                return;
            }
            window.__PF_INLINE_EDIT_SYMBOL = null;
        }

        const panelSig = `${positions.length}|${Number(metrics.edge || 0).toFixed(4)}|${Number(metrics.total_risk || 0).toFixed(4)}|${Number(metrics.regimeFit || 0).toFixed(4)}|${positions.slice(0, 8).map((p) => `${p.symbol}:${Number(p.current_price || 0).toFixed(2)}:${Number(p.open_qty ?? p.quantity ?? 0).toFixed(2)}`).join(',')}`;
        const panelDue = (Date.now() - Number(window.__PF_PANELS_LAST_AT || 0)) > 15000;
        if (positions.length === 0) {
            if (panelDue || panelSig !== window.__PF_PANELS_LAST_SIG) {
                renderPortfolioAdvancedPanel([], metrics);
                renderPortfolioIntelligencePanel([], metrics);
                window.__PF_PANELS_LAST_SIG = panelSig;
                window.__PF_PANELS_LAST_AT = Date.now();
            }
            container.innerHTML = `
            <tr><td colspan="10" style="text-align:center; padding:3rem; color:var(--text-muted);">
                <div style="font-size:1.4rem; color:var(--text-primary); margin-bottom:0.5rem;">No Active Positions</div>
                <div style="font-size:0.9rem;">Add a symbol to activate AI capital allocation</div>
            </td></tr>`;
            return;
        }

        if (panelDue || panelSig !== window.__PF_PANELS_LAST_SIG) {
            renderPortfolioAdvancedPanel(positions, metrics);
            renderPortfolioIntelligencePanel(positions, metrics);
            window.__PF_PANELS_LAST_SIG = panelSig;
            window.__PF_PANELS_LAST_AT = Date.now();
        }
        container.innerHTML = '';

        const totalRows = positions.length;
        const windowSize = Math.max(12, Number(window.__PF_ROW_WINDOW_SIZE || 36));
        if (window.__PF_ROW_WINDOW_START < 0) window.__PF_ROW_WINDOW_START = 0;
        if (window.__PF_ROW_WINDOW_START >= totalRows) window.__PF_ROW_WINDOW_START = Math.max(0, totalRows - windowSize);
        const expandedIdx = positions.findIndex((p) => String(p.symbol || '').toUpperCase() === String(window.__PF_EXPANDED_SYMBOL || '').toUpperCase());
        if (expandedIdx >= 0 && (expandedIdx < window.__PF_ROW_WINDOW_START || expandedIdx >= (window.__PF_ROW_WINDOW_START + windowSize))) {
            window.__PF_ROW_WINDOW_START = Math.floor(expandedIdx / windowSize) * windowSize;
        }
        const windowStart = window.__PF_ROW_WINDOW_START;
        const windowEnd = Math.min(totalRows, windowStart + windowSize);
        const visiblePositions = positions.slice(windowStart, windowEnd);
        if (totalRows > windowSize) bindPortfolioVirtualScroll(totalRows, windowSize);
        const topSpacerPx = Math.max(0, windowStart * 58);
        const bottomSpacerPx = Math.max(0, (totalRows - windowEnd) * 58);
        if (topSpacerPx > 0) {
            const spTop = document.createElement("tr");
            spTop.innerHTML = `<td colspan="10" style="height:${topSpacerPx}px; padding:0; border:none;"></td>`;
            container.appendChild(spTop);
        }

        // ═══ TOTAL PORTFOLIO VALUE ═══
        let totalMktVal = 0, totalCost = 0;
        const spreadPool = positions
            .map((p) => {
                const h = Number(p.day_high || 0);
                const l = Number(p.day_low || 0);
                const cp = Number(p.current_price || 0);
                return (h > 0 && l > 0 && cp > 0) ? ((h - l) / cp) : NaN;
            })
            .filter(Number.isFinite);
        const volPool = positions.map((p) => Number(p.volume || 0)).filter((v) => Number.isFinite(v) && v > 0);
        const medianOf = (arr) => {
            const a = (arr || []).slice().sort((x, y) => x - y);
            if (!a.length) return 0;
            const m = Math.floor(a.length / 2);
            return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
        };
        const spreadMedian = medianOf(spreadPool);
        const volumeMedian = medianOf(volPool);

        visiblePositions.forEach((pos) => {
            const symbol = pos.symbol;
            const livePrice = pos.current_price || 0;
            const avgPrice = pos.avg_price || 0;
            const isLive = pos.is_live_price || false;
            const changePct = pos.change_percent || 0;
            const qty = Number(pos.open_qty ?? pos.quantity ?? 0);
            const lotCurrentValue = Number(pos.current_value);
            const lotOpenCost = Number(pos.open_cost);
            const mktVal = Number.isFinite(lotCurrentValue) && lotCurrentValue > 0 ? lotCurrentValue : (qty * livePrice);
            const cost = Number.isFinite(lotOpenCost) && lotOpenCost > 0 ? lotOpenCost : (qty * avgPrice);
            const pnl = mktVal - cost;
            const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0;
            const pnlColor = pnl >= 0 ? 'var(--electric-green)' : 'var(--electric-red)';
            const changeColor = changePct >= 0 ? 'var(--electric-green)' : 'var(--electric-red)';

            totalMktVal += mktVal;
            totalCost += cost;

            const row = document.createElement("tr");
            row.className = "portfolio-row";
            row.id = `pf-row-${symbol}`;
            // NO auto-popup on row click — user requested explicit button only
            const urgencyScore = Number(pos.urgency_score || 0);
            if (urgencyScore >= 70) row.style.boxShadow = 'inset 2px 0 0 rgba(255,23,68,0.75)';
            else if (urgencyScore >= 45) row.style.boxShadow = 'inset 2px 0 0 rgba(255,241,0,0.6)';
            else row.style.boxShadow = 'none';

            let actionColor = 'var(--electric-yellow)';
            if (pos.action === 'ADD' || pos.action === 'BUY') actionColor = 'var(--electric-green)';
            if (pos.action === 'REDUCE' || pos.action === 'SELL') actionColor = 'var(--electric-red)';

            // AI metrics (show actual values when they exist)
            const confDisp = pos.confidence != null ? `${Number(pos.confidence).toFixed(1)}%` : '—';
            const edgeD = pos.edge != null ? `${Number(pos.edge).toFixed(3)}` : '—';
            const entropyD = pos.entropy != null ? `${Number(pos.entropy).toFixed(3)}` : '—';
            const rawKellyPct = Number(pos.kelly_percent);
            const rawKellyFrac = Number(pos.kelly_fraction || 0);
            const kellyEffective = Number.isFinite(rawKellyPct) && rawKellyPct > 0
                ? rawKellyPct
                : (rawKellyFrac > 0 ? rawKellyFrac * 100 : 0);
            const kellyDisp = (pos.kelly_percent != null || pos.kelly_fraction != null)
                ? (kellyEffective > 0 && kellyEffective < 0.01 ? '<0.01%' : `${kellyEffective.toFixed(2)}%`)
                : '—';
            const riskDisp = pos.risk != null ? `${Number(pos.risk).toFixed(3)}` : '—';
            const tpDisp = pos.tp ? `₹${Number(pos.tp).toFixed(0)}` : '—';
            const slDisp = pos.sl ? `₹${Number(pos.sl).toFixed(0)}` : '—';

            // Kelly bar
            const kellyW = Math.min(Math.max(kellyEffective || 0, 0), 100);
            const barColor = (pos.action === 'BUY' || pos.action === 'ADD') ? 'var(--electric-green)' : (pos.action === 'SELL' || pos.action === 'REDUCE') ? 'var(--electric-red)' : 'var(--electric-yellow)';
            const kellyBar = (pos.kelly_percent != null || pos.kelly_fraction != null) ? `<div style="width:100%;height:3px;background:rgba(255,255,255,0.05);border-radius:2px;margin-top:2px;"><div style="width:${kellyW}%;height:100%;background:${barColor};border-radius:2px;"></div></div>` : '';
            const overAllocWarn = kellyW > 35 ? ' <span style="color:var(--electric-red);font-size:9px;">⚠</span>' : '';
            const confW = Math.min(Math.max(Number(pos.confidence || 0), 0), 100);
            const confColor = confW >= 60 ? 'var(--electric-green)' : confW >= 40 ? 'var(--electric-yellow)' : 'var(--electric-red)';
            const confBar = pos.confidence != null
                ? `<div style="width:84px;height:3px;margin:3px auto 0;background:rgba(255,255,255,0.10);border-radius:2px;overflow:hidden;"><div style="width:${confW}%;height:100%;background:${confColor};border-radius:2px;"></div></div>`
                : '';

            // Date formatting
            const dateStr = formatPortfolioDate(pos.added_date);
            // Escape date for inline edit onclick
            const rawDate = (pos.added_date || '').replace(/'/g, "\\'");

            // TP/SL proximity visual cue (non-blocking, model-driven values only)
            const tp = Number(pos.tp || 0);
            const sl = Number(pos.sl || 0);
            const distTp = (livePrice > 0 && tp > 0) ? Math.abs(tp - livePrice) / livePrice : Number.POSITIVE_INFINITY;
            const distSl = (livePrice > 0 && sl > 0) ? Math.abs(livePrice - sl) / livePrice : Number.POSITIVE_INFINITY;
            const action = String(pos.action || 'HOLD').toUpperCase();
            const isAccumulationAction = action === 'ADD' || action === 'BUY';
            const isReduceAction = action === 'REDUCE' || action === 'SELL';
            const tpState = String(pos.tp_state || '').toUpperCase();
            const hasTp = tp > 0;
            const hasSl = sl > 0;
            const defensiveTp = hasTp && avgPrice > 0 && tp < avgPrice; // loss-control target (below cost basis)
            const tpCrossed = hasTp
                ? (defensiveTp ? (livePrice <= tp) : (livePrice >= tp))
                : false;
            const tpGap = hasTp
                ? (defensiveTp
                    ? (livePrice - tp) / Math.max(livePrice, 1e-9)
                    : (tp - livePrice) / Math.max(livePrice, 1e-9))
                : Number.POSITIVE_INFINITY;
            const nearTp = tpGap >= 0 && tpGap <= 0.015;
            const actionTargetConflict = ((isAccumulationAction && tpCrossed && tpState !== 'ROLLED') || (isReduceAction && distSl <= 0.01));
            const projectedMove = Number(pos.predicted_return || 0);
            const actualMove = Number(changePct || 0);
            const actualProjectedMismatch =
                Math.abs(projectedMove) > 0.05 &&
                Math.abs(actualMove) > 0.15 &&
                Math.sign(projectedMove) !== Math.sign(actualMove);
            let actionSignal = null;
            if (actionTargetConflict) {
                actionSignal = {
                    type: 'conflict',
                    badge: '⚠ Conflict',
                    note: 'Action vs target mismatch',
                    next: isAccumulationAction ? 'What now: wait for reset / pullback' : 'What now: reduce / tighten SL'
                };
            } else if (actualProjectedMismatch) {
                actionSignal = {
                    type: 'caution',
                    badge: '⚠ Caution',
                    note: 'Actual vs Projected diverging',
                    next: 'What now: wait / size down'
                };
            } else if (isAccumulationAction && tpState === 'ROLLED' && nearTp) {
                actionSignal = {
                    type: 'caution',
                    badge: '⚠ Caution',
                    note: 'Target already rolled',
                    next: 'What now: accumulate only on fresh setup'
                };
            }
            const actionCompact = actionSignal ? actionSignal.badge : '';
            let tpAlertStrip = '';
            let slAlertStrip = '';
            if (tpCrossed && defensiveTp) {
                slAlertStrip = `<div class="pf-alert-strip" title="Defensive target crossed; focus on stop-loss protection" style="color:var(--electric-red); background-image:linear-gradient(90deg, rgba(255,23,68,0.04), rgba(255,23,68,0.95), rgba(255,23,68,0.04));"></div>`;
            } else if (tpCrossed) {
                tpAlertStrip = `<div class="pf-alert-strip" title="Take-profit crossed, target rolled" style="color:var(--electric-yellow); background-image:linear-gradient(90deg, rgba(255,241,0,0.03), rgba(255,241,0,0.9), rgba(255,241,0,0.03));"></div>`;
            } else if (distSl <= 0.015 && sl <= livePrice) {
                slAlertStrip = `<div class="pf-alert-strip" title="Near Stop Loss" style="color:var(--electric-red); background-image:linear-gradient(90deg, rgba(255,23,68,0.04), rgba(255,23,68,0.95), rgba(255,23,68,0.04));"></div>`;
            } else if (isAccumulationAction && nearTp && hasSl) {
                // For ADD/BUY, emphasize protection first when target is near but action is still accumulation.
                slAlertStrip = `<div class="pf-alert-strip" title="Accumulation mode: protect downside (SL focus)" style="color:var(--electric-yellow); background-image:linear-gradient(90deg, rgba(255,241,0,0.03), rgba(255,241,0,0.88), rgba(255,241,0,0.03));"></div>`;
            } else if (nearTp && !defensiveTp && isReduceAction) {
                tpAlertStrip = `<div class="pf-alert-strip" title="Near Take Profit" style="color:var(--electric-green); background-image:linear-gradient(90deg, rgba(57,255,20,0.04), rgba(57,255,20,0.95), rgba(57,255,20,0.04));"></div>`;
            } else if (nearTp && !defensiveTp && isAccumulationAction && !hasSl) {
                tpAlertStrip = `<div class="pf-alert-strip" title="Near target zone while accumulation bias remains active" style="color:var(--electric-yellow); background-image:linear-gradient(90deg, rgba(255,241,0,0.03), rgba(255,241,0,0.9), rgba(255,241,0,0.03));"></div>`;
            }

            // 10 columns: Asset | Market Price | Action | Confidence | Edge | Entropy | Kelly % | Risk | TP | SL
            row.innerHTML = `
            <td style="padding:0.5rem;">
                <div style="display:flex; align-items:center; gap:6px;">
                    <span style="display:inline-block;width:3px;height:14px;border-radius:2px;background:${actionColor};box-shadow:0 0 7px ${actionColor};"></span>
                    <span onclick="event.stopPropagation(); togglePortfolioExpand('${symbol}')" style="font-weight:bold; color:var(--electric-cyan); font-size:13px; cursor:pointer;" title="Click for compact AI detail">${symbol}</span>
                    ${isLive ? '<span style="width:6px;height:6px;background:var(--electric-green);border-radius:50%;display:inline-block;" title="Live price"></span>' : ''}
                </div>
                <div style="font-size:9px; color:var(--text-muted);">${dateStr} · ${qty} shares @ ₹${avgPrice.toFixed(2)}</div>
                <div style="display:flex; gap:4px; margin-top:4px;">
                    <button onclick="event.stopPropagation(); showStockDetails('${symbol}')" title="View Details" style="background:rgba(0,243,255,0.08); border:1px solid rgba(0,243,255,0.2); color:var(--electric-cyan); cursor:pointer; padding:2px 6px; border-radius:4px; font-size:9px; transition:all 0.2s;" onmouseover="this.style.background='rgba(0,243,255,0.2)'" onmouseout="this.style.background='rgba(0,243,255,0.08)'">
                        <i class="fas fa-chart-line" style="font-size:9px;"></i> View
                    </button>
                    <button onclick="event.stopPropagation(); startInlineEdit('${symbol}', ${qty}, ${avgPrice}, '${rawDate}')" title="Modify Position" style="background:rgba(255,241,0,0.08); border:1px solid rgba(255,241,0,0.2); color:var(--electric-yellow); cursor:pointer; padding:2px 6px; border-radius:4px; font-size:9px; transition:all 0.2s;" onmouseover="this.style.background='rgba(255,241,0,0.2)'" onmouseout="this.style.background='rgba(255,241,0,0.08)'">
                        <i class="fas fa-pen" style="font-size:9px;"></i> Modify
                    </button>
                    <button onclick="event.stopPropagation(); openSellWorkflow('${symbol}', ${Number(qty || 0)}, ${Number(livePrice || 0)})" title="Sell Workflow" style="background:rgba(255,68,149,0.10); border:1px solid rgba(255,68,149,0.35); color:#ff7fcf; cursor:pointer; padding:2px 6px; border-radius:4px; font-size:9px; transition:all 0.2s;" onmouseover="this.style.background='rgba(255,68,149,0.20)'" onmouseout="this.style.background='rgba(255,68,149,0.10)'">
                        <i class="fas fa-arrow-trend-down" style="font-size:9px;"></i> Sell
                    </button>
                    <button onclick="event.stopPropagation(); deletePortfolioPosition('${symbol}', this)" title="Remove Position" style="background:rgba(255,50,50,0.05); border:1px solid rgba(255,50,50,0.15); color:rgba(255,255,255,0.2); cursor:pointer; padding:2px 6px; border-radius:4px; font-size:9px; transition:all 0.2s;" onmouseover="this.style.color='var(--electric-red)'; this.style.background='rgba(255,50,50,0.15)'" onmouseout="this.style.color='rgba(255,255,255,0.2)'; this.style.background='rgba(255,50,50,0.05)'">
                        <i class="fas fa-trash" style="font-size:9px;"></i>
                    </button>
                </div>
                <div style="width:100%;"></div>
            </td>
            <td style="text-align:right; font-family:monospace; padding:0.4rem;">
                <div style="color:white; font-weight:600; font-size:12px;">₹${livePrice.toFixed(2)}</div>
                <div style="color:${changeColor}; font-size:10px;">${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%</div>
                <div style="color:${pnlColor}; font-size:10px;">${pnl >= 0 ? '+' : ''}₹${pnl.toFixed(0)} (${pnlPct.toFixed(1)}%)</div>
            </td>
            <td style="font-weight:bold; color:${actionColor}; text-align:center;">
                <div>${pos.action || 'HOLD'}</div>
                <div style="font-size:9px; color:var(--text-muted); font-weight:500; line-height:1.25;">
                    <div>${humanizeToken(pos.intent_state || 'BALANCE')}</div>
                    <div>Urgency ${urgencyScore.toFixed(0)}/100</div>
                </div>
                ${actionSignal ? `<div title="${actionSignal.note} | ${actionSignal.next}" style="display:inline-block; margin-top:3px; font-size:9px; color:${actionSignal.type === 'conflict' ? 'var(--electric-red)' : 'var(--electric-yellow)'}; border:1px solid ${actionSignal.type === 'conflict' ? 'rgba(255,23,68,0.45)' : 'rgba(255,241,0,0.45)'}; border-radius:10px; padding:0 6px; white-space:nowrap;">${actionCompact}</div>` : ''}
            </td>
            <td style="text-align:center;">${confDisp}${confBar}</td>
            <td style="text-align:center;">${edgeD}</td>
            <td style="text-align:center;">${entropyD}</td>
            <td style="text-align:center;">${kellyDisp}${overAllocWarn}${kellyBar}</td>
            <td style="text-align:center; color:var(--electric-red);">${riskDisp}</td>
            <td style="text-align:center; color:var(--electric-green);">
                <div>${tpDisp}</div>
                ${tpAlertStrip}
            </td>
            <td style="text-align:center;">
                <div>${slDisp}</div>
                ${slAlertStrip}
            </td>
        `;
            container.appendChild(row);

            if (window.__PF_EXPANDED_SYMBOL === symbol) {
                const extra = document.createElement("tr");
                extra.className = "portfolio-row-detail";
                const news = (window.__PF_NEWS_CACHE[symbol] || {}).articles || [];
                const meta = window.__PF_SYMBOL_META_CACHE[symbol] || { name: symbol, sector: 'Unknown Industry' };
                const deep = (window.__PF_DEEP_CACHE[symbol] || {}).data || {};
                const lotInsights = (window.__PF_LOT_INSIGHTS_CACHE[symbol] || {}).data || {};
                const openLots = Array.isArray(lotInsights.open_lots) ? lotInsights.open_lots : [];
                const allLots = Array.isArray(lotInsights.all_lots) && lotInsights.all_lots.length
                    ? lotInsights.all_lots
                    : openLots;
                const nearLtcgLots = Array.isArray(lotInsights.near_ltcg) ? lotInsights.near_ltcg : [];
                const fySummary = lotInsights.fy_summary || window.__PF_TAX_SUMMARY_CACHE?.data || null;
                const realizedJournalRows = (window.__PF_REALIZED_JOURNAL_CACHE[symbol] || {}).data || [];
                const purchaseDates = allLots
                    .map((l) => new Date(l.buy_date))
                    .filter((d) => Number.isFinite(d.getTime()))
                    .sort((a, b) => a.getTime() - b.getTime());
                const firstPurchaseDate = purchaseDates.length ? formatPortfolioDate(purchaseDates[0]) : null;
                const lastPurchaseDate = purchaseDates.length ? formatPortfolioDate(purchaseDates[purchaseDates.length - 1]) : null;
                const tech = deep.technical_metrics || {};
                const pe = deep.pe_ratio ?? deep.pe ?? null;
                const eps = deep.eps ?? null;
                const pb = deep.pb_ratio ?? deep.price_to_book ?? deep.book_value_ratio ?? null;
                const roe = deep.roe ?? deep.return_on_equity ?? deep.returnOnEquity ?? null;
                const roce = deep.roce ?? deep.return_on_capital_employed ?? deep.returnOnCapitalEmployed ?? null;
                const deRatio = deep.debt_to_equity ?? deep.de_ratio ?? deep.debtToEquity ?? null;
                const dividendYield = deep.dividend_yield ?? deep.dividendYield ?? null;
                const dividendRate = deep.dividend_rate ?? deep.dividendRate ?? null;
                const faceValue = deep.face_value ?? deep.faceValue ?? null;
                const marketCap = deep.market_cap ?? deep.marketCap ?? null;
                const volume = deep.volume ?? tech.volume ?? null;
                const pos52w = tech.price_position_52w ?? deep.price_position_52w ?? null;
                const rsi = tech.rsi ?? null;
                const macd = tech.macd ?? null;
                const dayHigh = deep.day_high ?? deep.dayHigh ?? deep.high ?? null;
                const dayLow = deep.day_low ?? deep.dayLow ?? deep.low ?? null;
                const wk52High = tech.price_52w_high ?? deep.price_52w_high ?? deep.week52_high ?? deep.high_52week ?? null;
                const wk52Low = tech.price_52w_low ?? deep.price_52w_low ?? deep.week52_low ?? deep.low_52week ?? null;
                const fmtPx = (v) => (v == null || Number.isNaN(Number(v)) ? '—' : `₹${Number(v).toFixed(2)}`);
                const fmtPct = (v, digits = 1) => {
                    if (v == null || Number.isNaN(Number(v))) return '—';
                    let n = Number(v);
                    if (Math.abs(n) <= 1) n *= 100;
                    return `${n.toFixed(digits)}%`;
                };
                const fmtCr = (v) => {
                    if (v == null || Number.isNaN(Number(v))) return '—';
                    return `₹${(Number(v) / 10000000).toFixed(1)}Cr`;
                };
                const fmtVolCompact = (v) => {
                    if (v == null || Number.isNaN(Number(v))) return '—';
                    const n = Number(v);
                    if (n >= 10000000) return `${(n / 10000000).toFixed(2)}Cr`;
                    if (n >= 100000) return `${(n / 100000).toFixed(2)}L`;
                    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
                    return `${Math.round(n)}`;
                };
                const fmtInrVal = (v) => (v == null || Number.isNaN(Number(v)) ? '—' : `₹${Number(v).toFixed(2)}`);
                const fmtYield = (v) => {
                    if (v == null || Number.isNaN(Number(v))) return '—';
                    const n = Number(v);
                    return `${(Math.abs(n) <= 1 ? n * 100 : n).toFixed(2)}%`;
                };
                const newsHtml = buildExpanderNewsHtml(symbol, news, 10);
                const history = window.__PF_METRIC_HISTORY[symbol] || [];
                const riskSeries = history.map((h) => Number(h.risk || 0)).filter(Number.isFinite);
                const confSeries = history.map((h) => Number(h.confidence || 0)).filter(Number.isFinite);
                const riskShift = riskSeries.length > 1 ? (riskSeries[riskSeries.length - 1] - riskSeries[0]) : 0;
                const confTrendSpark = sparklineFromSeries(confSeries);
                const riskTrendSpark = sparklineFromSeries(riskSeries);
                const confTrendSummary = trendSummaryFromSeries(confSeries, Number(pos.confidence || 0), 1);
                const riskTrendSummary = trendSummaryFromSeries(riskSeries, Number(pos.risk || 0), 3);
                const confTrendInfo = confSeries.length >= 2
                    ? `${confTrendSpark} ${confTrendSummary}`
                    : `collecting (${confSeries.length}/2)`;
                const riskTrendInfo = riskSeries.length >= 2
                    ? `${riskTrendSpark} ${riskTrendSummary}`
                    : `collecting (${riskSeries.length}/2)`;
                const actionDir = (isAccumulationAction ? 1 : isReduceAction ? -1 : 0);
                const predDir = Math.sign(projectedMove);
                const driftDir = Math.sign(actualMove);
                const alignPred = actionDir === 0 ? 0.55 : (predDir === 0 ? 0.45 : (predDir === actionDir ? 1 : 0));
                const alignDrift = actionDir === 0 ? 0.5 : (driftDir === 0 ? 0.45 : (driftDir === actionDir ? 1 : 0));
                const consistencyPenalty = actionTargetConflict ? 0.25 : (actualProjectedMismatch ? 0.15 : 0);
                const decisionConsistency = clamp10((((alignPred * 0.45) + (alignDrift * 0.25) + ((1 - clamp01(Number(pos.risk || 0))) * 0.2) + ((1 - clamp01(Number(pos.entropy || 0))) * 0.1) - consistencyPenalty) * 10));
                const consistencyColor = decisionConsistency >= 7 ? 'var(--electric-green)' : decisionConsistency >= 4 ? 'var(--electric-yellow)' : 'var(--electric-red)';
                const kellyEffective = (Number(pos.kelly_percent || 0) > 0) ? Number(pos.kelly_percent || 0) : (Number(pos.kelly_fraction || 0) * 100);
                const conf01 = clamp01(Number(pos.confidence || 0) / 100);
                const risk01 = clamp01(Number(pos.risk || 0));
                const entropy01 = clamp01(Number(pos.entropy || 0));
                const regimeVol = clamp01(Number(window.NEURAL_STATE?.market?.volatility || 0) / 2);
                const regimeStability = clamp01(1 - regimeVol);
                const sizeConfidence = clamp01(((conf01 * 0.45) + ((1 - risk01) * 0.35) + ((1 - entropy01) * 0.20)) * (0.7 + regimeStability * 0.3));
                const sizedPct = Math.max(0, Math.min(100, (kellyEffective || 0) * sizeConfidence));
                const sizeLensColor = sizeConfidence >= 0.66 ? 'var(--electric-green)' : sizeConfidence >= 0.45 ? 'var(--electric-yellow)' : 'var(--electric-red)';
                const posSpread = (Number(dayHigh || 0) > 0 && Number(dayLow || 0) > 0 && livePrice > 0) ? ((Number(dayHigh) - Number(dayLow)) / livePrice) : spreadMedian;
                const volRatio = (volumeMedian > 0 && Number(volume || 0) > 0) ? (Number(volume) / volumeMedian) : 1;
                const execScore = clamp01((1 - Math.min(1, (posSpread / Math.max(0.0001, spreadMedian || posSpread || 0.01)) * 0.5)) * 0.45 + Math.min(1.2, volRatio) * 0.30 + (1 - risk01) * 0.25);
                const execLabel = execScore >= 0.66 ? 'Window favorable' : execScore >= 0.45 ? 'Window selective' : 'Window defensive';
                const execColor = execScore >= 0.66 ? 'var(--electric-green)' : execScore >= 0.45 ? 'var(--electric-yellow)' : 'var(--electric-red)';
                const eventLane = news.length
                    ? news.slice(0, 4).map((n) => {
                        const s = String(n.sentiment || 'neutral').toLowerCase();
                        const c = s === 'positive' ? 'var(--electric-green)' : s === 'negative' ? 'var(--electric-red)' : 'var(--electric-yellow)';
                        return `<span title="${escapeHtml(n.source || 'News')} · ${formatNewsAge(n.published || n.normalized_time || n.timestamp)}" style="display:inline-block; width:7px; height:7px; border-radius:50%; background:${c}; margin-right:6px;"></span>`;
                    }).join('')
                    : '<span style="color:var(--text-muted);">No events</span>';
                const shortTerm = (pos.action === 'ADD' || pos.action === 'BUY') ? 'Upward bias active' : (pos.action === 'REDUCE' || pos.action === 'SELL') ? 'Profit booking bias' : 'Sideways wait';
                const longTerm = (Number(pos.edge || 0) > 0.12 && Number(pos.risk || 0) < 0.35) ? 'Constructive long-term' : 'Selective long-term';
                const holdingDays = calcHoldingDays(pos.added_date);
                const stUnreal = Number(pos.stcg_unrealized);
                const ltUnreal = Number(pos.ltcg_unrealized);
                const stRealized = Number(pos.stcg_realized || 0);
                const ltRealized = Number(pos.ltcg_realized || 0);
                const stcg = Number.isFinite(stUnreal) ? stUnreal : (holdingDays <= 365 ? pnl : 0);
                const ltcg = Number.isFinite(ltUnreal) ? ltUnreal : (holdingDays > 365 ? pnl : 0);
                const currentWeight = totalMktVal > 0 ? (mktVal / totalMktVal) * 100 : 0;
                const targetWeight = Number(pos.kelly_percent || 0);
                const shift = targetWeight - currentWeight;
                const relocation = shift > 0.5 ? `Increase ${shift.toFixed(1)}%` : shift < -0.5 ? `Reduce ${Math.abs(shift).toFixed(1)}%` : 'Near optimal';
                const goReduceExit = Number(pos.risk || 0) >= 0.65 ? 'EXIT' : (pos.action === 'REDUCE' || pos.action === 'SELL') ? 'REDUCE' : 'GO';
                const goColor = goReduceExit === 'GO' ? 'var(--electric-green)' : goReduceExit === 'REDUCE' ? 'var(--electric-yellow)' : 'var(--electric-red)';
                const nearestLtcg = nearLtcgLots.length ? nearLtcgLots[0] : null;
                const ltcgHint = nearestLtcg
                    ? `${nearestLtcg.days_to_ltcg}d to LTCG on ${Number(nearestLtcg.open_quantity || 0).toFixed(2)}`
                    : 'No near LTCG lots';
                const fyHint = fySummary
                    ? `FY ${fySummary.fy}: STCG ${formatInr(fySummary.stcg_realized || 0)} · LTCG ${formatInr(fySummary.ltcg_realized || 0)}`
                    : 'FY realized summary unavailable';
                const simCacheKey = `${symbol}|${Math.round((Number(pos.open_qty ?? qty) || 0) * 1000) / 1000}|${Math.round((Number(livePrice || 0)) * 100) / 100}`;
                const simEntry = window.__PF_SELL_SIM_CACHE[simCacheKey] || null;
                const sim = simEntry?.data || null;
                const simLabel = sim?.recommended_method
                    ? `Exit Sim: ${sim.recommended_method} (tax-efficient proxy)`
                    : 'Exit Sim: calculating…';
                const realizedCount = Array.isArray(realizedJournalRows) ? realizedJournalRows.length : 0;
                const lotCount = Array.isArray(allLots) ? allLots.length : 0;
                const simFresh = simEntry && ((Date.now() - Number(simEntry.ts || 0)) < 30000);
                if (!sim && !simFresh && !window.__PF_SELL_SIM_LOADING?.[simCacheKey] && (Number(pos.open_qty ?? qty) > 0) && Number(livePrice) > 0) {
                    loadPortfolioSellSimulation(symbol, Number(pos.open_qty ?? qty), Number(livePrice)).then(() => {
                        if (window.__PF_EXPANDED_SYMBOL === symbol) renderPortfolio();
                    });
                }
                extra.innerHTML = `
                <td colspan="10" style="padding:8px 10px; background:rgba(0,255,255,0.03); border-top:1px solid rgba(0,255,255,0.15); border-bottom:1px solid rgba(0,255,255,0.08);">
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:6px;">
                        <div style="font-size:11px; color:var(--electric-yellow); font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(meta.name)} · ${escapeHtml(meta.sector)}</div>
                        <div style="font-size:10px; color:var(--text-muted);">Holding: ${holdingDays} days</div>
                    </div>
                    <div style="display:flex; justify-content:flex-end; align-items:center; gap:6px; margin-bottom:6px;">
                        <button onclick="event.stopPropagation(); exportExpandedSymbolExcel('${symbol}')" style="padding:2px 8px;border-radius:4px;border:1px solid rgba(57,255,20,0.45);background:rgba(57,255,20,0.10);color:var(--electric-green);font-size:10px;cursor:pointer;">Export Excel</button>
                        <button onclick="event.stopPropagation(); exportExpandedSymbolPDF('${symbol}')" style="padding:2px 8px;border-radius:4px;border:1px solid rgba(0,243,255,0.45);background:rgba(0,243,255,0.10);color:var(--electric-cyan);font-size:10px;cursor:pointer;">Export PDF</button>
                        <button onclick="event.stopPropagation(); togglePortfolioPin('${symbol}')" style="background:${window.__PF_EXPANDED_PINNED ? 'rgba(255,7,58,0.25)' : 'rgba(255,7,58,0.08)'}; color:${window.__PF_EXPANDED_PINNED ? '#ffd6df' : 'var(--electric-red)'}; border:1px solid rgba(255,7,58,0.55); border-radius:4px; padding:2px 8px; font-size:10px; cursor:pointer; font-weight:700;">
                            ${window.__PF_EXPANDED_PINNED ? 'PINNED' : 'PIN'}
                        </button>
                    </div>
                    <div style="display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; font-size:10px;">
                        <div style="padding-right:6px; border-right:1px solid rgba(255,255,255,0.08);">
                            <div style="color:var(--electric-cyan); font-weight:800; background:rgba(0,255,255,0.10); border:1px solid rgba(0,255,255,0.35); border-radius:4px; padding:2px 6px;">Summary</div>
                            <div style="margin-top:3px; color:${goColor}; font-weight:700;">${goReduceExit}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">${humanizeToken(pos.intent_state || 'BALANCE')}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">Invested ${formatInr(cost)} · Current ${formatInr(mktVal)}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">Open lots ${openLots.length} / Total lots ${allLots.length} · Qty ${Number(pos.open_qty || qty).toFixed(2)}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">Purchases ${firstPurchaseDate || '—'}${lastPurchaseDate && lastPurchaseDate !== firstPurchaseDate ? ` → ${lastPurchaseDate}` : ''}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">${ltcgHint}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">Day H/L: ${fmtPx(dayHigh)} / ${fmtPx(dayLow)}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">52W H/L: ${fmtPx(wk52High)} / ${fmtPx(wk52Low)}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">Decision Consistency: <span style="color:${consistencyColor};">${decisionConsistency.toFixed(1)}/10</span></div>
                        </div>
                        <div style="padding-right:6px; border-right:1px solid rgba(255,255,255,0.08);">
                            <div style="color:var(--electric-green); font-weight:800; background:rgba(57,255,20,0.10); border:1px solid rgba(57,255,20,0.35); border-radius:4px; padding:2px 6px;">P&L</div>
                            <div style="color:${pnl >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'}; margin-top:3px;">Unrealized: ${formatInr(pnl)}</div>
                            <div style="color:#d7f5ff; margin-top:3px;">${shortTerm}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">Horizon: ${longTerm}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">STCG U: <span style="color:${stcg >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'}">${formatInr(stcg)}</span> · R: <span style="color:${stRealized >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'}">${formatInr(stRealized)}</span></div>
                            <div style="color:var(--text-muted); margin-top:4px;">LTCG U: <span style="color:${ltcg >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'}">${formatInr(ltcg)}</span> · R: <span style="color:${ltRealized >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'}">${formatInr(ltRealized)}</span></div>
                            <div style="color:var(--text-muted); margin-top:4px;">${fyHint}</div>
                        </div>
                        <div style="padding-right:6px; border-right:1px solid rgba(255,255,255,0.08);">
                            <div style="color:var(--electric-yellow); font-weight:800; background:rgba(255,241,0,0.10); border:1px solid rgba(255,241,0,0.35); border-radius:4px; padding:2px 6px;">Fundamental</div>
                            <div style="color:var(--text-muted); margin-top:4px;">Weight: ${currentWeight.toFixed(2)}% / AI Size ${targetWeight.toFixed(2)}%</div>
                            <div style="color:var(--text-muted); margin-top:4px;">Valuation: PE ${pe != null ? Number(pe).toFixed(2) : '—'} · PB ${pb != null ? Number(pb).toFixed(2) : '—'}</div>
                            ${((roce != null || deRatio != null) ? `<div style="color:var(--text-muted); margin-top:4px;">ROCE ${fmtPct(roce)} · D/E ${deRatio != null ? Number(deRatio).toFixed(2) : '—'}</div>` : '')}
                            <div style="color:var(--text-muted); margin-top:4px;">Dividend ${fmtInrVal(dividendRate)} · Yield ${fmtYield(dividendYield)}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">Face Value ${fmtInrVal(faceValue)}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">MCap ${fmtCr(marketCap)} · Vol ${fmtVolCompact(volume)}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">52W Pos ${pos52w != null ? Number(pos52w).toFixed(1) + '%' : '—'} · ROE ${fmtPct(roe)}</div>
                        </div>
                        <div style="padding-right:6px; border-right:1px solid rgba(255,255,255,0.08);">
                            <div style="color:var(--electric-blue); font-weight:800; background:rgba(0,191,255,0.10); border:1px solid rgba(0,191,255,0.35); border-radius:4px; padding:2px 6px;">Technical</div>
                            <div style="color:var(--text-muted); margin-top:3px;">Conf ${Number(pos.confidence || 0).toFixed(1)} · Edge ${Number(pos.edge || 0).toFixed(3)}</div>
                            <div style="color:var(--text-muted); margin-top:3px;">Entropy ${Number(pos.entropy || 0).toFixed(3)} · Risk ${Number(pos.risk || 0).toFixed(3)}</div>
                            <div style="color:${sizeLensColor}; margin-top:3px;">Sizing Lens ${(sizeConfidence * 100).toFixed(0)}% · Alloc ${sizedPct.toFixed(2)}%</div>
                            <div style="color:var(--text-muted); margin-top:3px;">RSI ${rsi != null ? Number(rsi).toFixed(1) : '—'} · MACD ${macd != null ? Number(macd).toFixed(2) : '—'}</div>
                            <div style="color:${execColor}; margin-top:3px;">Execution: ${execLabel}</div>
                            <div style="color:var(--text-muted); margin-top:3px;">${simLabel}</div>
                            <div style="color:var(--text-muted); margin-top:3px;">Live drift: ΔR ${riskShift >= 0 ? '+' : ''}${riskShift.toFixed(3)}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">TP1 ₹${Number(pos.tp1 || pos.tp || 0).toFixed(0)} · TP2 ₹${Number(pos.tp2 || pos.tp || 0).toFixed(0)} · Trail SL ₹${Number(pos.trail_sl || pos.sl || 0).toFixed(0)}</div>
                            <div style="color:var(--text-muted); margin-top:4px;">AI Relocation: <span style="color:${shift > 0 ? 'var(--electric-green)' : shift < 0 ? 'var(--electric-red)' : 'var(--electric-yellow)'}">${relocation}</span></div>
                        </div>
                        <div>
                            <div style="color:var(--electric-pink); font-weight:800; background:rgba(255,20,147,0.10); border:1px solid rgba(255,20,147,0.35); border-radius:4px; padding:2px 6px;">Live News</div>
                            <div style="margin-top:3px; color:var(--text-muted);">Event Timeline: ${eventLane}</div>
                            <div style="margin-top:2px; color:#d7f5ff; max-height:130px; overflow:auto; padding-right:4px;">${newsHtml}</div>
                        </div>
                    </div>
                    <div class="pf-jl-wrap">
                        <div class="pf-jl-title">Journal & Ledger</div>
                        <div class="pf-jl-grid">
                            <details id="pf-lots-card-${symbol}" class="pf-jl-card" ontoggle="if(this.open){syncPortfolioLedgerPanels('${symbol}')}" >
                                <summary class="pf-jl-summary pf-jl-summary-cyan">Purchase Ledger (${lotCount})</summary>
                                <div id="pf-lots-${symbol}" class="pf-expander-scroll pf-jl-body" data-loaded="0"><div class="pf-expander-muted">Open to load purchase ledger</div></div>
                            </details>
                            <details id="pf-journal-card-${symbol}" class="pf-jl-card" ontoggle="if(this.open){syncPortfolioLedgerPanels('${symbol}')}" >
                                <summary class="pf-jl-summary pf-jl-summary-green">Realized Sell Journal (${realizedCount})</summary>
                                <div id="pf-journal-${symbol}" class="pf-expander-scroll pf-jl-body" data-loaded="0"><div class="pf-expander-muted">Open to load realized journal</div></div>
                            </details>
                        </div>
                    </div>
                </td>
            `;
                container.appendChild(extra);
            }
        });

        if (bottomSpacerPx > 0) {
            const spBottom = document.createElement("tr");
            spBottom.innerHTML = `<td colspan="10" style="height:${bottomSpacerPx}px; padding:0; border:none;"></td>`;
            container.appendChild(spBottom);
        }

        // ═══ TOTAL ROW ═══
        const totalPnl = totalMktVal - totalCost;
        const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost * 100) : 0;
        const totalColor = totalPnl >= 0 ? 'var(--electric-green)' : 'var(--electric-red)';
        const totalRow = document.createElement("tr");
        totalRow.innerHTML = `
        <td style="padding:0.5rem; border-top:1px solid rgba(255,255,255,0.1);">
            <div style="font-weight:bold; color:white; font-size:12px;">TOTAL PORTFOLIO</div>
            <div style="font-size:10px; color:var(--text-muted);">Invested: ${formatCompact(totalCost)}</div>
        </td>
        <td style="text-align:right; font-family:monospace; border-top:1px solid rgba(255,255,255,0.1);">
            <div style="color:white; font-weight:600; font-size:12px;">${formatCompact(totalMktVal)}</div>
            <div style="color:${totalColor}; font-size:10px;">${totalPnl >= 0 ? '+' : ''}₹${totalPnl.toFixed(0)} (${totalPnlPct.toFixed(1)}%)</div>
        </td>
        <td colspan="8" style="border-top:1px solid rgba(255,255,255,0.1);"></td>
    `;
        container.appendChild(totalRow);
    } finally {
        window.__PF_RENDERING = false;
        const pending = window.__PF_RENDER_PENDING;
        if (pending) {
            window.__PF_RENDER_PENDING = null;
            schedulePortfolioRender(pending.positions || null, pending.accountMetrics || null, false);
        }
    }
}

// ═══ LOT-LEVEL EDIT MODE ═══
function closeOverlayModal(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function startInlineEdit(symbol) {
    openLotEditor(symbol);
}

async function openLotEditor(symbol, page = 1) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base) return;
    closeOverlayModal('lotEditorModal');

    const wrap = document.createElement('div');
    wrap.id = 'lotEditorModal';
    wrap.style.cssText = 'position:fixed;inset:0;z-index:10020;background:rgba(0,0,0,0.45);display:flex;align-items:center;justify-content:center;padding:12px;';
    wrap.innerHTML = `
        <div style="width:min(980px,96vw);max-height:86vh;overflow:auto;background:linear-gradient(145deg, rgba(8,14,24,0.98), rgba(18,26,40,0.98));border:1px solid rgba(0,243,255,0.35);border-radius:10px;box-shadow:0 12px 30px rgba(0,0,0,0.45);padding:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px;">
                <div>
                    <div style="color:var(--electric-cyan);font-size:14px;font-weight:800;">Modify Purchase Lots · ${base}</div>
                    <div style="color:var(--text-muted);font-size:11px;">Each purchase date/rate is separate. Edit the exact lot you want.</div>
                </div>
                <button id="lotEditorClose" style="background:none;border:none;color:var(--electric-red);font-size:18px;cursor:pointer;">&times;</button>
            </div>
            <div id="lotEditorBody" style="font-size:11px;color:var(--text-muted);padding:10px 0;">Loading lots...</div>
            <div style="display:flex;justify-content:flex-end;margin-top:10px;">
                <button id="lotEditorDone" style="padding:6px 12px;border-radius:6px;border:1px solid rgba(0,243,255,0.45);background:rgba(0,243,255,0.12);color:var(--electric-cyan);cursor:pointer;font-weight:700;">Done</button>
            </div>
        </div>
    `;
    document.body.appendChild(wrap);
    wrap.querySelector('#lotEditorClose').addEventListener('click', () => closeOverlayModal('lotEditorModal'));
    wrap.querySelector('#lotEditorDone').addEventListener('click', () => closeOverlayModal('lotEditorModal'));
    wrap.addEventListener('mousedown', (e) => { if (e.target === wrap) closeOverlayModal('lotEditorModal'); });

    try {
        const pageSize = 50;
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), 12000);
        const r = await fetch(`/api/portfolio/lots?symbol=${encodeURIComponent(base)}&only_open=0&page=${Math.max(1, Number(page || 1))}&page_size=${pageSize}`, { signal: controller.signal });
        clearTimeout(t);
        if (!r.ok) throw new Error(`lots http ${r.status}`);
        const payload = await r.json();
        const rows = Array.isArray(payload?.data) ? payload.data : [];
        const pg = Number(payload?.page || page || 1);
        const pages = Math.max(1, Number(payload?.pages || 1));
        const total = Math.max(0, Number(payload?.total || rows.length));
        const body = wrap.querySelector('#lotEditorBody');
        if (!rows.length) {
            body.innerHTML = `<div style="color:var(--text-muted);">No lots found for ${base}.</div>`;
            return;
        }
        body.innerHTML = `
            <table style="width:100%;border-collapse:collapse;font-size:11px;">
                <thead>
                    <tr style="color:var(--electric-yellow);background:rgba(255,255,255,0.03);">
                        <th style="padding:6px;border:1px solid rgba(255,255,255,0.1);text-align:left;">Lot ID</th>
                        <th style="padding:6px;border:1px solid rgba(255,255,255,0.1);text-align:left;">Buy Date</th>
                        <th style="padding:6px;border:1px solid rgba(255,255,255,0.1);text-align:right;">Original Qty</th>
                        <th style="padding:6px;border:1px solid rgba(255,255,255,0.1);text-align:right;">Open Qty</th>
                        <th style="padding:6px;border:1px solid rgba(255,255,255,0.1);text-align:right;">Price</th>
                        <th style="padding:6px;border:1px solid rgba(255,255,255,0.1);text-align:center;">Status</th>
                        <th style="padding:6px;border:1px solid rgba(255,255,255,0.1);text-align:center;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map((lot) => {
            const lotId = Number(lot.id || 0);
            const dateVal = String(lot.buy_date || '').slice(0, 10);
            const originalQty = Number(lot.original_quantity || 0);
            const openQty = Number(lot.remaining_quantity || 0);
            const px = Number(lot.buy_price || 0);
            const soldQty = Math.max(0, originalQty - openQty);
            const isClosed = openQty <= 0;
            const canDelete = !isClosed && soldQty <= 1e-9;
            const status = isClosed ? 'Closed' : (soldQty > 1e-9 ? `Partial (${soldQty.toFixed(2)} sold)` : 'Open');
            const statusColor = isClosed ? 'var(--text-muted)' : (soldQty > 1e-9 ? 'var(--electric-yellow)' : 'var(--electric-green)');
            return `
                            <tr>
                                <td style="padding:6px;border:1px solid rgba(255,255,255,0.08);color:var(--electric-cyan);">${lotId}</td>
                                <td style="padding:6px;border:1px solid rgba(255,255,255,0.08);"><input id="lot_date_${lotId}" class="pf-themed-input pf-date-input" type="date" value="${dateVal}" ${isClosed ? 'disabled' : ''} style="width:150px;min-height:32px;"></td>
                                <td style="padding:6px;border:1px solid rgba(255,255,255,0.08);text-align:right;color:#d7f5ff;">${originalQty.toFixed(2)}</td>
                                <td style="padding:6px;border:1px solid rgba(255,255,255,0.08);text-align:right;"><input id="lot_qty_${lotId}" class="pf-themed-input pf-number-input" type="number" min="0.01" step="0.01" value="${openQty.toFixed(2)}" ${isClosed ? 'disabled' : ''} onblur="this.value=Number(this.value||0).toFixed(2)" style="width:118px;text-align:right;"></td>
                                <td style="padding:6px;border:1px solid rgba(255,255,255,0.08);text-align:right;"><input id="lot_px_${lotId}" class="pf-themed-input pf-number-input" type="number" min="0.01" step="0.01" value="${px}" ${isClosed ? 'disabled' : ''} onblur="this.value=Number(this.value||0).toFixed(2)" style="width:128px;text-align:right;"></td>
                                <td style="padding:6px;border:1px solid rgba(255,255,255,0.08);text-align:center;color:${statusColor};">${status}</td>
                                <td style="padding:6px;border:1px solid rgba(255,255,255,0.08);text-align:center;">
                                    ${isClosed ? `
                                        <span style="color:var(--text-muted);font-size:10px;">History</span>
                                    ` : `
                                        <button onclick="saveLotEdit(${lotId}, '${base}')" style="padding:4px 8px;border-radius:4px;border:1px solid rgba(57,255,20,0.45);background:rgba(57,255,20,0.10);color:var(--electric-green);cursor:pointer;">Save</button>
                                        <button onclick="deleteLotEntry(${lotId}, '${base}', ${soldQty.toFixed(8)})" title="${canDelete ? 'Delete lot' : 'Partial lot cannot be deleted; use Sell workflow'}" style="padding:4px 8px;border-radius:4px;border:1px solid rgba(255,23,68,0.45);background:${canDelete ? 'rgba(255,23,68,0.10)' : 'rgba(255,23,68,0.04)'};color:${canDelete ? 'var(--electric-red)' : 'rgba(255,255,255,0.45)'};cursor:${canDelete ? 'pointer' : 'not-allowed'};margin-left:6px;">Delete</button>
                                    `}
                                </td>
                            </tr>
                        `;
        }).join('')}
                </tbody>
            </table>
            <div style="margin-top:8px; border:1px dashed rgba(0,243,255,0.25); border-radius:6px; padding:8px;">
                <div style="font-size:11px; color:var(--electric-cyan); font-weight:700; margin-bottom:6px;">Add New Lot (${base})</div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:8px;align-items:end;">
                    <label style="font-size:10px;color:var(--text-muted);">Buy Date
                        <input id="new_lot_date_${base}" class="pf-themed-input pf-date-input" type="date" value="${new Date().toISOString().slice(0, 10)}" style="width:100%;min-height:32px;">
                    </label>
                    <label style="font-size:10px;color:var(--text-muted);">Qty
                        <input id="new_lot_qty_${base}" class="pf-themed-input pf-number-input" type="number" min="0.01" step="0.01" value="1.00" onblur="this.value=Number(this.value||0).toFixed(2)" style="width:100%;">
                    </label>
                    <label style="font-size:10px;color:var(--text-muted);">Price
                        <input id="new_lot_px_${base}" class="pf-themed-input pf-number-input" type="number" min="0.01" step="0.01" value="" onblur="this.value=Number(this.value||0).toFixed(2)" style="width:100%;">
                    </label>
                    <button onclick="addLotFromEditor('${base}', ${pg})" style="height:32px;min-width:76px;padding:0 9px;border-radius:5px;border:1px solid rgba(57,255,20,0.45);background:rgba(57,255,20,0.10);color:var(--electric-green);cursor:pointer;align-self:end;font-size:11px;line-height:1;font-weight:700;">Add Lot</button>
                </div>
            </div>
            <div style="margin-top:8px;display:flex;justify-content:space-between;align-items:center;gap:8px;">
                <div style="color:var(--text-muted);font-size:10px;">Open and closed lots are shown separately. Qty edits are restricted on partially sold lots to preserve realized tax history.</div>
                <div style="display:flex;align-items:center;gap:6px;">
                    <button ${pg <= 1 ? 'disabled' : ''} onclick="openLotEditor('${base}', ${Math.max(1, pg - 1)})" style="padding:3px 8px;border-radius:4px;border:1px solid rgba(0,243,255,0.35);background:rgba(0,243,255,0.08);color:var(--electric-cyan);cursor:${pg <= 1 ? 'not-allowed' : 'pointer'};opacity:${pg <= 1 ? 0.5 : 1};">Prev</button>
                    <span style="font-size:10px;color:var(--text-muted);">Page ${pg}/${pages} · ${total} lots</span>
                    <button ${pg >= pages ? 'disabled' : ''} onclick="openLotEditor('${base}', ${Math.min(pages, pg + 1)})" style="padding:3px 8px;border-radius:4px;border:1px solid rgba(0,243,255,0.35);background:rgba(0,243,255,0.08);color:var(--electric-cyan);cursor:${pg >= pages ? 'not-allowed' : 'pointer'};opacity:${pg >= pages ? 0.5 : 1};">Next</button>
                </div>
            </div>
        `;
    } catch (e) {
        const body = wrap.querySelector('#lotEditorBody');
        const isTimeout = e?.name === 'AbortError';
        body.innerHTML = `
            <div style="color:var(--electric-red);">
                ${isTimeout ? 'Lots request timed out. Backend is busy.' : `Failed to load lots: ${escapeHtml(e.message || 'unknown')}`}
            </div>
            <div style="margin-top:8px;">
                <button onclick="openLotEditor('${base}', ${Math.max(1, Number(page || 1))})" style="padding:4px 10px;border-radius:4px;border:1px solid rgba(0,243,255,0.45);background:rgba(0,243,255,0.10);color:var(--electric-cyan);cursor:pointer;">Retry</button>
            </div>
        `;
    }

    if (updatedAt) {
        const sourceTs = dashState.lastUpdate?.predictions || Date.now();
        updatedAt.textContent = `Updated ${new Date(sourceTs).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
}

async function saveLotEdit(lotId, symbol) {
    const qty = Number(Number(document.getElementById(`lot_qty_${lotId}`)?.value || 0).toFixed(2));
    const px = Number(Number(document.getElementById(`lot_px_${lotId}`)?.value || 0).toFixed(2));
    const dt = document.getElementById(`lot_date_${lotId}`)?.value || null;
    if (qty <= 0 || px <= 0) {
        showToast('Qty and price must be > 0', 'error');
        return;
    }
    try {
        const r = await fetch(`/api/portfolio/lots/${lotId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ qty: qty, buy_price: px, buy_date: dt })
        });
        const data = await r.json();
        if (data?.status === 'ok') {
            delete window.__PF_LOT_INSIGHTS_CACHE[symbol];
            window.__PF_INTEL_SUITE_CACHE = null;
            showToast(`Lot ${lotId} updated`, 'success');
            await openLotEditor(symbol);
        } else {
            showToast(data?.error || 'Lot update failed', 'error');
        }
    } catch (e) {
        showToast('Lot update failed', 'error');
    }
}

async function deleteLotEntry(lotId, symbol, soldQty = 0) {
    if (Number(soldQty || 0) > 1e-9) {
        showToast('Partial lot cannot be deleted. Use Sell workflow/history-safe edits.', 'error');
        return;
    }
    const ok = await showThemedConfirm(`Delete lot ${lotId} for ${symbol}?`);
    if (!ok) return;
    try {
        const r = await fetch(`/api/portfolio/lots/${lotId}`, { method: 'DELETE' });
        const data = await r.json();
        if (data?.status === 'ok') {
            delete window.__PF_LOT_INSIGHTS_CACHE[symbol];
            window.__PF_INTEL_SUITE_CACHE = null;
            showToast(`Lot ${lotId} removed`, 'success');
            await openLotEditor(symbol);
        } else {
            showToast(data?.error || 'Lot delete failed', 'error');
        }
    } catch {
        showToast('Lot delete failed', 'error');
    }
}

async function addLotFromEditor(symbol, page = 1) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    const qtyEl = document.getElementById(`new_lot_qty_${base}`);
    const pxEl = document.getElementById(`new_lot_px_${base}`);
    const dtEl = document.getElementById(`new_lot_date_${base}`);
    const parseField = (el) => Number(String(el?.value ?? '').replace(/,/g, '').trim());
    const qtyRaw = parseField(qtyEl);
    const pxRaw = parseField(pxEl);
    const qty = Number.isFinite(qtyRaw) ? Number(qtyRaw.toFixed(2)) : NaN;
    const px = Number.isFinite(pxRaw) ? Number(pxRaw.toFixed(2)) : NaN;
    const dt = dtEl?.value || null;
    if (!base || !dt) {
        showToast('Enter valid lot date', 'error');
        return;
    }
    if (!Number.isFinite(qty) || qty <= 0) {
        showToast('Enter valid quantity (> 0)', 'error');
        return;
    }
    if (!Number.isFinite(px) || px <= 0) {
        showToast('Enter valid price (> 0)', 'error');
        return;
    }
    try {
        const r = await fetch('/api/portfolio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: base,
                quantity: qty,
                avg_price: px,
                purchase_date: dt
            })
        });
        const data = await r.json();
        if (data?.status === 'ok' || data?.message) {
            delete window.__PF_LOT_INSIGHTS_CACHE[base];
            window.__PF_INTEL_SUITE_CACHE = null;
            showToast(`Lot added for ${base}`, 'success');
            await openLotEditor(base, page);
            await safeInit(() => loadPortfolioState(true));
        } else {
            showToast(data?.error || 'Failed to add lot', 'error');
        }
    } catch {
        showToast('Failed to add lot', 'error');
    }
}

// Ensure modal action handlers are always callable from inline button markup.
window.saveLotEdit = saveLotEdit;
window.deleteLotEntry = deleteLotEntry;
window.openLotEditor = openLotEditor;
window.addLotFromEditor = addLotFromEditor;

async function openSellWorkflow(symbol, maxQty, currentPrice) {
    const base = String(symbol || '').toUpperCase().replace('.NS', '').replace('.BO', '');
    if (!base) return;
    closeOverlayModal('sellWorkflowModal');
    const defaultQty = Math.max(0.01, Math.min(Number(maxQty || 0), 1));
    const defaultPx = Number(currentPrice || 0);
    const wrap = document.createElement('div');
    wrap.id = 'sellWorkflowModal';
    wrap.style.cssText = 'position:fixed;inset:0;z-index:10030;background:rgba(0,0,0,0.45);display:flex;align-items:center;justify-content:center;padding:12px;';
    wrap.innerHTML = `
        <div style="width:min(760px,96vw);max-height:86vh;overflow:visible;background:linear-gradient(145deg, rgba(8,14,24,0.98), rgba(18,26,40,0.98));border:1px solid rgba(255,127,207,0.45);border-radius:10px;box-shadow:0 12px 30px rgba(0,0,0,0.45);padding:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px;">
                <div>
                    <div style="color:#ff9ee6;font-size:14px;font-weight:800;">Sell Workflow · ${base}</div>
                    <div style="color:var(--text-muted);font-size:11px;">Simulate FIFO/LIFO/HIFO first, then execute with selected method.</div>
                </div>
                <button id="sellWorkflowClose" style="background:none;border:none;color:var(--electric-red);font-size:18px;cursor:pointer;">&times;</button>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;align-items:end;">
                <label style="color:var(--text-muted);font-size:11px;">Qty
                    <input id="sell_qty_${base}" class="pf-themed-input pf-number-input" type="number" min="0.01" step="0.01" value="${defaultQty.toFixed(2)}" onblur="this.value=Number(this.value||0).toFixed(2)" style="width:100%;">
                </label>
                <label style="color:var(--text-muted);font-size:11px;">Sell Price
                    <input id="sell_px_${base}" class="pf-themed-input pf-number-input" type="number" min="0.01" step="0.01" value="${defaultPx > 0 ? defaultPx.toFixed(2) : ''}" onblur="this.value=Number(this.value||0).toFixed(2)" style="width:100%;">
                </label>
                <label style="color:var(--text-muted);font-size:11px;">Method
                    <select id="sell_method_${base}" style="width:100%;background:rgba(10,18,32,0.98);border:1px solid rgba(0,243,255,0.45);color:#eaf7ff;padding:6px;border-radius:4px;appearance:none;">
                        <option value="FIFO">FIFO</option>
                        <option value="LIFO">LIFO</option>
                        <option value="HIFO">HIFO</option>
                        <option value="AI_TAX_OPT">AI-TAX-OPT</option>
                    </select>
                </label>
                <div style="display:flex;gap:6px;">
                    <button id="sellSimBtn_${base}" style="padding:6px 10px;border-radius:4px;border:1px solid rgba(0,243,255,0.35);background:rgba(0,243,255,0.12);color:var(--electric-cyan);cursor:pointer;">Simulate</button>
                    <button id="sellExecBtn_${base}" style="padding:6px 10px;border-radius:4px;border:1px solid rgba(255,23,68,0.45);background:rgba(255,23,68,0.16);color:var(--electric-red);cursor:pointer;">Sell</button>
                </div>
            </div>
            <div style="margin-top:6px;font-size:10px;color:var(--text-muted);">AI-TAX-OPT = auto-chooses FIFO/LIFO/HIFO with lowest tax-impact proxy from live simulation.</div>
            <div id="sellTaxDelta_${base}" style="margin-top:8px;font-size:11px;color:var(--text-muted);">Projected tax delta: run simulation</div>
            <div id="sellSimOut_${base}" style="margin-top:6px;font-size:11px;color:var(--text-muted);">Run simulation to compare methods.</div>
        </div>
    `;
    document.body.appendChild(wrap);
    wrap.querySelector('#sellWorkflowClose').addEventListener('click', () => closeOverlayModal('sellWorkflowModal'));
    wrap.addEventListener('mousedown', (e) => { if (e.target === wrap) closeOverlayModal('sellWorkflowModal'); });
    const methodSel = document.getElementById(`sell_method_${base}`);
    if (methodSel) {
        Array.from(methodSel.options || []).forEach((opt) => {
            opt.style.background = '#0b1220';
            opt.style.color = '#eaf7ff';
        });
    }
    document.getElementById(`sellSimBtn_${base}`)?.addEventListener('click', () => runSellSimulationUI(base));
    document.getElementById(`sellExecBtn_${base}`)?.addEventListener('click', () => executeSellOrderUI(base));
}

async function runSellSimulationUI(symbol) {
    const qty = Number(document.getElementById(`sell_qty_${symbol}`)?.value || 0);
    const price = Number(document.getElementById(`sell_px_${symbol}`)?.value || 0);
    const out = document.getElementById(`sellSimOut_${symbol}`);
    const deltaEl = document.getElementById(`sellTaxDelta_${symbol}`);
    if (!out) return;
    if (qty <= 0 || price <= 0) {
        out.innerHTML = `<span style="color:var(--electric-red);">Enter valid qty and sell price.</span>`;
        return;
    }
    const inflightKey = `${symbol}|${Math.round(qty * 100) / 100}|${Math.round(price * 100) / 100}`;
    if (window.__PF_UI_SELL_SIM_LOADING[inflightKey]) return;
    window.__PF_UI_SELL_SIM_LOADING[inflightKey] = true;
    out.textContent = 'Simulating...';
    try {
        const data = await loadPortfolioSellSimulation(symbol, qty, price);
        if (!data || !Array.isArray(data.scenarios)) {
            out.innerHTML = `<span style="color:var(--electric-red);">Simulation unavailable</span>`;
            if (deltaEl) deltaEl.textContent = 'Projected tax delta: unavailable';
            return;
        }
        const rec = data.recommended_method || 'FIFO';
        const sel = document.getElementById(`sell_method_${symbol}`);
        if (sel && sel.value !== 'AI_TAX_OPT') sel.value = rec;
        const fifoScenario = data.scenarios.find((s) => String(s.method || '').toUpperCase() === 'FIFO') || null;
        const recScenario = data.scenarios.find((s) => String(s.method || '').toUpperCase() === String(rec).toUpperCase()) || null;
        if (deltaEl) {
            if (fifoScenario && recScenario) {
                const fifoProxy = Number(fifoScenario.tax_impact_proxy || 0);
                const recProxy = Number(recScenario.tax_impact_proxy || 0);
                const delta = fifoProxy - recProxy;
                const color = delta > 0 ? 'var(--electric-green)' : delta < 0 ? 'var(--electric-red)' : 'var(--text-muted)';
                deltaEl.innerHTML = `Projected tax delta vs FIFO: <span style="color:${color};">${delta >= 0 ? '+' : ''}${formatInr(delta)}</span> (${rec})`;
            } else {
                deltaEl.textContent = 'Projected tax delta: unavailable';
            }
        }
        out.innerHTML = `
            <div style="color:var(--electric-yellow);font-weight:700;margin-bottom:6px;">Recommended: ${rec} (lower tax-impact proxy)</div>
            <table style="width:100%;border-collapse:collapse;">
                <tr style="color:var(--electric-cyan);">
                    <th style="text-align:left;padding:4px;border-bottom:1px solid rgba(255,255,255,0.15);">Method</th>
                    <th style="text-align:right;padding:4px;border-bottom:1px solid rgba(255,255,255,0.15);">Realized</th>
                    <th style="text-align:right;padding:4px;border-bottom:1px solid rgba(255,255,255,0.15);">STCG</th>
                    <th style="text-align:right;padding:4px;border-bottom:1px solid rgba(255,255,255,0.15);">LTCG</th>
                </tr>
                ${data.scenarios.map((s) => `
                    <tr>
                        <td style="padding:4px;">${s.method}</td>
                        <td style="padding:4px;text-align:right;color:${Number(s.realized_gain || 0) >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'};">${formatInr(s.realized_gain || 0)}</td>
                        <td style="padding:4px;text-align:right;">${formatInr(s.realized_stcg || 0)}</td>
                        <td style="padding:4px;text-align:right;">${formatInr(s.realized_ltcg || 0)}</td>
                    </tr>
                `).join('')}
            </table>
        `;
    } catch (e) {
        out.innerHTML = `<span style="color:var(--electric-red);">Simulation failed.</span>`;
    } finally {
        delete window.__PF_UI_SELL_SIM_LOADING[inflightKey];
    }
}

async function executeSellOrderUI(symbol) {
    const qty = Number(document.getElementById(`sell_qty_${symbol}`)?.value || 0);
    const price = Number(document.getElementById(`sell_px_${symbol}`)?.value || 0);
    const methodChoice = String(document.getElementById(`sell_method_${symbol}`)?.value || 'FIFO').toUpperCase();
    if (qty <= 0 || price <= 0) {
        showToast('Enter valid qty and sell price', 'error');
        return;
    }
    try {
        let method = methodChoice;
        if (methodChoice === 'AI_TAX_OPT') {
            const sim = await loadPortfolioSellSimulation(symbol, qty, price);
            method = String(sim?.recommended_method || 'FIFO').toUpperCase();
            if (!['FIFO', 'LIFO', 'HIFO'].includes(method)) method = 'FIFO';
        }
        const r = await fetch('/api/portfolio/sell', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, qty, sell_price: price, method })
        });
        const payload = await r.json();
        if (payload?.status === 'ok') {
            const g = Number(payload?.data?.realized_gain || 0);
            showToast(`Sell executed (${method}) · Realized ${formatInr(g)}`, 'success');
            closeOverlayModal('sellWorkflowModal');
            delete window.__PF_LOT_INSIGHTS_CACHE[symbol];
            delete window.__PF_REALIZED_JOURNAL_CACHE[symbol];
            window.__PF_INTEL_SUITE_CACHE = null;
            loadPortfolioTaxSummary(true);
        } else {
            showToast(payload?.error || 'Sell failed', 'error');
        }
    } catch {
        showToast('Sell failed', 'error');
    }
}

// 🚀 STEP 3 — ADD POSITION LOGIC
// DELETED SYMBOL RESOLUTION (As per Unified AI Architecture rules)

function normalizeSymbol(s) {
    if (!s) return "";
    s = s.trim().toUpperCase();
    return s.replace(/\.(NS|BO|BSE|NSE)$/, "");
}

function setAddButtonState(enabled, text) {
    const btn = document.getElementById("pf_add_btn");
    if (!btn) return;
    btn.disabled = !enabled;
    btn.textContent = text || (enabled ? "ADD" : "Select symbol");
    btn.classList.toggle("syncing", !enabled && text === "SYNCING...");
}

function bindPortfolioControls() {
    console.log("🔗 Binding Portfolio Controls (Neural Ready)");
    const addBtn = document.getElementById("pf_add_btn");
    if (addBtn) {
        addBtn.addEventListener("click", addPortfolioPosition);
        console.log("  ✅ ADD button bound");
    } else {
        console.warn("  ❌ pf_add_btn NOT FOUND");
    }

    // Portfolio search authority binding
    const pfInput = document.getElementById("pf_symbol");
    if (pfInput) {
        pfInput.addEventListener("input", (e) => {
            const query = e.target.value.trim();
            if (e.target.dataset.selected === 'true' && query.toUpperCase() !== (e.target.dataset.baseSymbol || '')) {
                e.target.dataset.selected = 'false';
                delete e.target.dataset.baseSymbol;
                SymbolAuthority.activeSelection = null;
                setAddButtonState(false, "Select symbol");
            }
            if (CONFIG.DEBUG_MODE) console.log(`🔍 PF Input event fired: "${query}"`);
            SymbolAuthority.performSearch(query, 'pf_symbol', 'pf_autocomplete_list');
        });
        pfInput.addEventListener("focus", (e) => {
            const query = (e.target.value || '').trim();
            if (query.length >= 1) {
                SymbolAuthority.performSearch(query, 'pf_symbol', 'pf_autocomplete_list');
            }
        });
        console.log("  ✅ pf_symbol input listener bound");
    } else {
        console.warn("  ❌ pf_symbol input NOT FOUND in DOM");
    }

    const globalInput = document.getElementById("globalSearch");
    if (globalInput) {
        globalInput.addEventListener("focus", (e) => {
            const query = (e.target.value || '').trim();
            if (query.length >= 1) {
                SymbolAuthority.performSearch(query, 'globalSearch', 'searchResults');
            }
        });
    }

    // ⚡ Load existing positions from DB immediately
    refreshPortfolio();
}

// ==============================================================================
// 🌐 MASTER SYMBOL AUTHORITY (Unifies Symbol Discovery)
// ==============================================================================

window.SymbolAuthority = {
    activeSelection: null,
    _debounceTimer: null,
    _abortController: null,
    _requestSeq: 0,
    _latestAppliedSeq: 0,
    _resultCache: {},

    getSelected(inputId) {
        const input = document.getElementById(inputId);
        if (!input || input.dataset.selected !== 'true') return null;
        return input.dataset.tradableSymbol || input.dataset.baseSymbol || this.activeSelection?.tradable || this.activeSelection?.base || null;
    },

    async performSearch(query, inputId, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        if (!query || query.length < 1) {
            container.innerHTML = '';
            container.style.display = 'none';
            return;
        }

        const requestSeq = ++this._requestSeq;

        // Debounce: keep responsive while avoiding request spam
        clearTimeout(this._debounceTimer);
        // faster debounce for instant feel
        this._debounceTimer = setTimeout(async () => {
            try {
                const results = await this.fetchResults(query);
                if (results === null) return;
                if (requestSeq < this._latestAppliedSeq) return;
                const input = document.getElementById(inputId);
                if (!input || input.value.trim() !== query) return;
                this._latestAppliedSeq = requestSeq;
                if (CONFIG.DEBUG_MODE) console.log(`🔍 Search "${query}": ${results.length} results`);
                this.renderResults(results, inputId, containerId);
            } catch (e) {
                console.error("Search failed:", e);
                this.renderResults([], inputId, containerId);
            }
        }, 60);
    },

    async fetchResults(query) {
        const key = String(query || '').toUpperCase();
        const cached = this._resultCache[key];
        if (cached && (Date.now() - cached.ts) < 15000) return cached.rows;

        if (this._abortController) this._abortController.abort();
        this._abortController = new AbortController();

        try {
            // comprehensive endpoint covers full NSE+BSE universe and is optimized
            const resp = await fetch(`/api/search/comprehensive?q=${encodeURIComponent(query)}&limit=30`, {
                signal: this._abortController.signal,
                cache: 'no-store'
            });
            if (!resp.ok) throw new Error(`search http ${resp.status} `);
            const data = await resp.json();
            const rows = Array.isArray(data) ? data : (data.success ? data.results : []);
            this._resultCache[key] = { ts: Date.now(), rows };
            return rows;
        } catch (err) {
            if (err && err.name === 'AbortError') return null;
            throw err;
        }
    },

    renderResults(results, inputId, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (results.length === 0) {
            container.innerHTML = '<div style="padding:0.6rem 1rem; color:rgba(255,255,255,0.4); font-size:12px;">No results found</div>';
            container.style.display = 'block';
            return;
        }

        container.style.display = 'block';
        container.innerHTML = results.map(stock => {
            const sym = stock.display || stock.symbol;
            const name = stock.name || sym;
            const exchange = stock.exchange || (String(sym).toUpperCase().endsWith('.BO') ? 'BSE' : 'NSE');
            const priceRaw = Number(stock.current_price ?? stock.price);
            const changePctRaw = Number(stock.change_percent);
            const changeValueRaw = Number(stock.change_value ?? stock.price_change);
            const hasPrice = Number.isFinite(priceRaw) && priceRaw > 0;
            const hasChangePct = Number.isFinite(changePctRaw);
            const hasChangeValue = Number.isFinite(changeValueRaw);
            const effectiveChangeValue = hasChangeValue
                ? changeValueRaw
                : (hasPrice && hasChangePct ? (priceRaw * changePctRaw / 100) : null);
            const changeColor = hasChangePct
                ? (changePctRaw >= 0 ? 'var(--electric-green)' : 'var(--electric-red)')
                : 'var(--text-muted)';
            const priceText = hasPrice ? `₹${priceRaw.toFixed(2)}` : '--';
            const changeText = (hasChangePct || effectiveChangeValue != null)
                ? `${effectiveChangeValue != null && effectiveChangeValue >= 0 ? '+' : ''}${effectiveChangeValue != null ? effectiveChangeValue.toFixed(2) : '--'} (${hasChangePct ? `${changePctRaw >= 0 ? '+' : ''}${changePctRaw.toFixed(2)}%` : '--'})`
                : '--';
            const safeName = (name || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const safeSymbol = String(stock.symbol || sym || '').replace(/'/g, "\\'");
            const safeDisplay = String(sym || stock.symbol || '').replace(/'/g, "\\'");
            return `
            <div class="search-result-item" onclick="SymbolAuthority.select('${safeSymbol}', '${safeName}', '${inputId}', '${containerId}', '${safeDisplay}')"
                style="padding:0.75rem 1rem; cursor:pointer; border-bottom:1px solid rgba(255,255,255,0.05); transition:all 0.2s; display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; flex-direction:column; gap:2px; max-width:65%;">
                    <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                        <span style="color:var(--electric-yellow); font-weight:700; font-family:monospace; font-size:14px;">${sym}</span>
                        <span style="font-size:9px;color:var(--electric-cyan);border:1px solid rgba(0,255,255,0.22);border-radius:999px;padding:1px 6px;">${exchange}</span>
                    </div>
                    <div style="color:var(--text-muted); font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${name}</div>
                </div>
                <div style="text-align:right;">
                    <div style="color:white; font-weight:700; font-family:monospace; font-size:13px;">${priceText}</div>
                    <div style="color:${changeColor}; font-size:11px; font-weight:bold;">${changeText}</div>
                </div>
            </div>`;
        }).join('');
    },

    select(symbol, name, inputId, containerId, displaySymbol = null) {
        const display = String(displaySymbol || symbol || "").toUpperCase();
        const base = display.replace(".NS", "").replace(".BO", "");
        const tradable = display.includes(".") ? display : `${base}.NS`;
        const input = document.getElementById(inputId);
        if (input) {
            input.value = tradable;
            input.dataset.selected = 'true';
            input.dataset.baseSymbol = base;
            input.dataset.tradableSymbol = tradable;
        }

        this.activeSelection = { base, tradable, display: tradable, name };
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '';
            container.style.display = 'none';
        }

        console.log(`\ud83c\udfaf Symbol Selected: ${base} `);

        // Open stock analysis modal ONLY for global search, NOT for portfolio add
        if (inputId !== 'pf_symbol') {
            if (typeof showStockDetails === 'function') {
                showStockDetails(tradable);
            } else if (window.dashboard && window.dashboard.showStockDetails) {
                window.dashboard.showStockDetails(tradable);
            }
        }

        // Enable ADD button if it was for portfolio
        if (inputId === 'pf_symbol') {
            const addBtn = document.getElementById("pf_add_btn");
            if (addBtn) {
                addBtn.disabled = false;
                addBtn.textContent = "ADD";
            }
        }
    }
};

// Global click listener for all autocomplete lists
document.addEventListener('click', (e) => {
    // 1. Portfolio Search
    const pfInput = document.getElementById('pf_symbol');
    const pfList = document.getElementById('pf_autocomplete_list');
    if (pfInput && pfList && !pfInput.contains(e.target) && !pfList.contains(e.target)) {
        pfList.innerHTML = '';
        pfList.style.display = 'none';
    }

    // 2. Global Search
    const globalInput = document.getElementById('globalSearch');
    const globalList = document.getElementById('searchResults');
    if (globalInput && globalList && !globalInput.contains(e.target) && !globalList.contains(e.target)) {
        globalList.innerHTML = '';
        globalList.style.display = 'none';
    }

    if (window.__PF_EXPANDED_SYMBOL && !window.__PF_EXPANDED_PINNED) {
        const withinPortfolioTable = e.target && (e.target.closest('#portfolioTableBody') || e.target.closest('.portfolio-row-detail'));
        const toggler = e.target && e.target.closest('[title="Click for compact AI detail"]');
        if (!withinPortfolioTable && !toggler) {
            window.__PF_EXPANDED_SYMBOL = null;
            schedulePortfolioRender(window.NEURAL_STATE?.portfolio_intelligence?.positions || null, window.NEURAL_STATE?.portfolio_intelligence?.account_metrics || null, true);
        }
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    closeOverlayModal('sellWorkflowModal');
    closeOverlayModal('lotEditorModal');
    closeOverlayModal('nexusThemedConfirm');
    if (window.__PF_EXPANDED_SYMBOL && !window.__PF_EXPANDED_PINNED) {
        window.__PF_EXPANDED_SYMBOL = null;
        schedulePortfolioRender(window.NEURAL_STATE?.portfolio_intelligence?.positions || null, window.NEURAL_STATE?.portfolio_intelligence?.account_metrics || null, true);
    }
});

// Add focus listeners to ensure only one search list is active at a time
document.addEventListener('focusin', (e) => {
    if (e.target.id === 'pf_symbol') {
        const globalList = document.getElementById('searchResults');
        if (globalList) { globalList.innerHTML = ''; globalList.style.display = 'none'; }
    }
    if (e.target.id === 'globalSearch') {
        const pfList = document.getElementById('pf_autocomplete_list');
        if (pfList) { pfList.innerHTML = ''; pfList.style.display = 'none'; }
    }
});

function sortPortfolio(column) {
    if (window.__PORTFOLIO_SORT.column === column) {
        window.__PORTFOLIO_SORT.direction = window.__PORTFOLIO_SORT.direction === 'asc' ? 'desc' : 'asc';
    } else {
        window.__PORTFOLIO_SORT.column = column;
        window.__PORTFOLIO_SORT.direction = 'asc';
    }

    // Rerender with current state
    const pi = window.NEURAL_STATE?.portfolio_intelligence || {};
    renderPortfolio(pi.positions, pi.account_metrics);
}

async function addPortfolioPosition() {
    const symbol = SymbolAuthority.getSelected("pf_symbol");
    const pf_price = document.getElementById("pf_price");
    const pf_date = document.getElementById("pf_date");

    if (!symbol) {
        showToast("Select a symbol from search", "error");
        return;
    }

    setAddButtonState(false, "SYNCING...");

    const payload = {
        symbol: symbol,
        qty: Number(pf_qty.value),
        avg_price: Number(pf_price.value || 0),
        purchase_date: pf_date.value || null
    };

    try {
        const res = await fetch("/api/portfolio", {
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (data.status !== "ok") {
            showToast(data.error || "Add failed", "error");
            setAddButtonState(true, "RETRY");
            return;
        }

        // Wait for websocket confirmation before success toast.
        window.__PF_INTEL_SUITE_CACHE = null;
        const timeoutId = setTimeout(() => {
            if (window.__PENDING_PORTFOLIO_ADD && window.__PENDING_PORTFOLIO_ADD.symbol === symbol) {
                window.__PENDING_PORTFOLIO_ADD = null;
                safeInit(() => loadPortfolioState(true));
                showToast(`WS delayed. Synced ${symbol} from API state.`, "success");
                setAddButtonState(true, "ADD");
            }
        }, 12000);
        window.__PENDING_PORTFOLIO_ADD = { symbol, timeoutId };

        // UI Cleanup
        const symbolEl = document.getElementById("pf_symbol");
        if (symbolEl) {
            symbolEl.value = "";
            symbolEl.dataset.selected = "false";
        }
        if (pf_qty) pf_qty.value = "1";
        if (pf_price) pf_price.value = "";
        if (pf_date) pf_date.value = "";

    } catch (e) {
        console.error("addPosition error", e);
        showToast("Add failed", "error");
        setAddButtonState(true, "FAILED - RETRY");
    }
}

async function refreshPortfolio() {
    await safeInit(() => loadPortfolioState(true));
    setAddButtonState(false, "Select symbol");
}


async function deletePortfolioPosition(symbol, anchorEl = null) {
    const shouldDelete = await showThemedConfirm(`Remove ${symbol} from AI Capital Manager ?`, anchorEl);
    if (!shouldDelete) return;

    try {
        const res = await fetch(`/api/portfolio/${symbol}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'deleted' || data.status === 'success' || data.success) {
            window.__PF_INTEL_SUITE_CACHE = null;
            showToast(`${symbol} delete synced to AI queue`, 'success');
        } else {
            showToast(data.error || 'Delete failed', 'error');
        }
    } catch (e) {
        showToast('Delete failed — check network', 'error');
    }
}




async function loadAnalytics() {

    try {

        const data = await api.fetch('/analytics', {
            timeout: Math.max(1, Math.floor(CONFIG.TIMEOUT * 0.5))
        });

        if (!data || !data.success) {
            renderAnalyticsFallback();
            return false;

        }



        dashState.analytics = data.data;

        dashState.lastUpdate.analytics = Date.now();



        renderAnalytics();

        return true;



    } catch (error) {
        console.error('Analytics error:', error);
        renderAnalyticsFallback();
        return false;
    }
}

// ============================================================================
// MISSING RENDER FUNCTIONS (Restored)
// ============================================================================



// ----------------------------------------------------------------------------
// PORTFOLIO ACTIONS (Add/Delete) - Event Driven Architecture
// ----------------------------------------------------------------------------

// DELETED REPLACED FUNCTIONS

// ----------------------------------------------------------------------------
// UTILITIES
// ----------------------------------------------------------------------------

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.innerText = message;

    // Inline Styles for Robustness
    Object.assign(toast.style, {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        backgroundColor: type === 'error' ? 'rgba(255, 7, 58, 0.9)' : 'rgba(57, 255, 20, 0.9)',
        color: type === 'error' ? 'white' : 'black',
        padding: '12px 24px',
        borderRadius: '4px',
        zIndex: '10000',
        boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
        fontWeight: '600',
        opacity: '0',
        transform: 'translateY(20px)',
        transition: 'all 0.3s ease-out'
    });

    document.body.appendChild(toast);

    // Animate In
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });

    // Animate Out & Remove
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function showThemedConfirm(message, anchor = null) {
    return new Promise((resolve) => {
        const existing = document.getElementById("confirmPopover");
        if (existing) existing.remove();

        const pop = document.createElement("div");
        pop.id = "confirmPopover";
        pop.style.position = "fixed";
        pop.style.zIndex = "10050";
        pop.style.minWidth = "260px";
        pop.style.maxWidth = "320px";
        pop.style.background = "linear-gradient(145deg, rgba(8,14,24,0.98), rgba(18,26,40,0.98))";
        pop.style.border = "1px solid rgba(0,243,255,0.4)";
        pop.style.borderRadius = "8px";
        pop.style.boxShadow = "0 12px 28px rgba(0,0,0,0.45)";
        pop.style.padding = "10px";
        pop.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div style="color:var(--electric-cyan); font-size:12px; font-weight:700;">Confirm Delete</div>
                <button id="confirmCloseBtn" style="background:none;border:none;color:var(--electric-red);font-size:14px;cursor:pointer;">&times;</button>
            </div>
            <div style="color:#d7e6f5; font-size:12px; margin-bottom:10px; line-height:1.35;">${escapeHtml(message)}</div>
            <div style="display:flex; gap:8px; justify-content:flex-end;">
                <button id="confirmCancelBtn" style="padding:6px 11px; border:1px solid rgba(255,255,255,0.25); border-radius:6px; color:var(--text-muted); background:rgba(255,255,255,0.04); cursor:pointer;">Cancel</button>
                <button id="confirmOkBtn" style="padding:6px 11px; border:1px solid var(--electric-red); background:rgba(255,7,58,0.15); color:var(--electric-red); border-radius:6px; cursor:pointer;">Delete</button>
            </div>
        `;

        pop.style.left = `${Math.max(8, (window.innerWidth - 320) / 2)}px`;
        pop.style.top = `${Math.max(8, (window.innerHeight - 160) / 2)}px`;

        const onKey = (ev) => {
            if (ev.key === 'Escape') close(false);
        };

        const onDocClick = (ev) => {
            if (!pop.contains(ev.target)) close(false);
        };

        const close = (result) => {
            document.removeEventListener("keydown", onKey);
            document.removeEventListener("mousedown", onDocClick);
            pop.remove();
            resolve(result);
        };

        document.addEventListener("keydown", onKey);
        setTimeout(() => document.addEventListener("mousedown", onDocClick), 0);
        pop.querySelector("#confirmCloseBtn").addEventListener("click", () => close(false));
        pop.querySelector("#confirmCancelBtn").addEventListener("click", () => close(false));
        pop.querySelector("#confirmOkBtn").addEventListener("click", () => close(true));

        document.body.appendChild(pop);
    });
}

function renderAnalytics() {
    // Basic implementation to prevent error
    console.log("Rendering Analytics...", dashState.analytics);
    const content = document.getElementById('analyticsContent');
    if (content) content.innerHTML = '<div class="text-center" style="padding:2rem;">Analytics Dashboard Active (Charts Loading...)</div>';
}



async function loadNews() {
    try {
        const data = await api.fetch('/news/market', {
            timeout: Math.max(1, Math.floor(CONFIG.TIMEOUT * 0.5))
        });

        console.log('🔍 News API payload:', data);

        const rawArticles = data?.articles || data?.news || data?.items || [];
        const liveNews = Array.isArray(rawArticles) ? rawArticles : [];

        if (!data || !liveNews.length) {
            console.error("❌ News API failed or no articles", data);
            if (Array.isArray(dashState.news) && dashState.news.length) {
                renderMarketSentiment();
                renderNews();
                updateDashboardMarketIntelligenceCard();
                updateDashboardMarketPulseCard();
                renderPredictionsWorldState();
                return true;
            }
            renderNewsFallback();
            return false;
        }
        dashState.news = liveNews;

        // 🔥 LIVE market sentiment
        dashState.marketSentiment = data.sentiment;
        dashState.newsSectorwise = data.sectorwise || {};
        dashState.newsNarratives = data.narratives || [];
        dashState.newsNarrativeMomentum = data.narrative_momentum || [];
        dashState.newsShockPropagation = data.shock_propagation || [];
        dashState.newsIntelligence = data.market_intelligence || {};
        dashState.portfolioNewsAlerts = data.portfolio_alerts || [];
        dashState.newsPredictionContext = data.prediction_context || [];
        dashState.infoAdvantage = data.information_advantage || {};

        dashState.lastUpdate.news = Date.now();
        publishNexusDashboardState();
        renderMarketSentiment();
        renderNews();
        updateDashboardMarketIntelligenceCard();
        updateDashboardMarketPulseCard();
        renderPredictionsWorldState();
        syncV7DashboardIframe(dashState.data || {});
        return true;

    } catch (error) {
        console.error('News error:', error);
        if (Array.isArray(dashState.news) && dashState.news.length) {
            renderMarketSentiment();
            renderNews();
            updateDashboardMarketIntelligenceCard();
            renderPredictionsWorldState();
            syncV7DashboardIframe(dashState.data || {});
            return true;
        }
        renderNewsFallback();
        return false;
    }
}

// ============================================================================

// UI UPDATE FUNCTIONS

// ============================================================================



function updateDashboardUI() {

    if (!dashState.data) {

        console.warn('âš ï¸ No dashboard data available');

        return;

    }



    const data = dashState.data;

    if (CONFIG.DEBUG_MODE) console.log('📊 Updating dashboard UI with data:', data);



    // ================================================================

    // KEY INDICES - 100% Dynamic from API (NO hardcoded values)

    // ================================================================

    if (data.live_indices && Array.isArray(data.live_indices) && data.live_indices.length > 0) {

        if (CONFIG.DEBUG_MODE) console.log(`📊 Processing ${data.live_indices.length} indices`);



        data.live_indices.forEach(index => {

            const name = (index.name || '').toUpperCase();

            if (CONFIG.DEBUG_MODE) console.log(`  Processing: ${name} `, index);



            // Dynamic element ID mapping (NO hardcoded IDs)

            const mappings = [
                { test: /NIFTY\s*50|^NIFTY$/i, id: 'nifty50' },
                { test: /BANK\s*NIFTY|^BANK$/i, id: 'banknifty' },
                { test: /SENSEX/i, id: 'sensex' },
                { test: /S&P\s*500|SP500/i, id: 'sp500' },
                { test: /DOW\s*JONES|DJI|DOW/i, id: 'dowJones' },
                { test: /NASDAQ/i, id: 'nasdaq' }
            ];
            const found = mappings.find(m => m.test.test(name));
            const elementId = found ? found.id : null;






            if (elementId) {

                const valueEl = document.getElementById(elementId);

                const changeEl = document.getElementById(elementId + '-change');



                // Update VALUE with color coding

                if (valueEl) {

                    const value = parseFloat(index.value || 0);



                    if (value > 0) {

                        valueEl.textContent = value.toLocaleString('en-IN', {

                            minimumFractionDigits: 2,

                            maximumFractionDigits: 2

                        });



                        // Color code value based on change

                        const changePoints = parseFloat(index.change_points || 0);

                        if (changePoints > 0) {

                            valueEl.style.color = '#39FF14'; // Green

                        } else if (changePoints < 0) {

                            valueEl.style.color = '#ff4444'; // Red

                        } else {

                            valueEl.style.color = '#00D9FF'; // Cyan (neutral)

                        }



                        if (CONFIG.DEBUG_MODE) console.log(`  âœ… Updated ${elementId}: ${value.toFixed(2)} `);

                    } else {

                        valueEl.textContent = '--';

                        valueEl.style.color = '#666';

                        console.warn(`  âš ï¸ ${elementId}: No valid value`);

                    }

                } else {

                    console.error(`  âŒ Element #${elementId} NOT FOUND`);

                }



                // Update CHANGE with points + percentage

                if (changeEl) {

                    const changePoints = parseFloat(index.change_points || 0);

                    const changePercent = parseFloat(index.change || index.change_percent || 0);



                    if (changePoints !== 0 || changePercent !== 0) {

                        const sign = changePoints >= 0 ? '+' : '';



                        // Format: "+140.25 (+0.54%)" or "-50.30 (-0.25%)"

                        changeEl.textContent = `${sign}${changePoints.toFixed(2)} (${sign}${changePercent.toFixed(2)}%)`;



                        // Color code

                        if (changePoints > 0) {

                            changeEl.style.color = '#39FF14'; // Green

                            changeEl.className = 'positive';

                        } else if (changePoints < 0) {

                            changeEl.style.color = '#ff4444'; // Red

                            changeEl.className = 'negative';

                        } else {

                            changeEl.style.color = '#00D9FF'; // Cyan

                            changeEl.className = 'neutral';

                        }



                        if (CONFIG.DEBUG_MODE) console.log(`  âœ… ${elementId} -change: ${sign}${changePoints.toFixed(2)} (${sign}${changePercent.toFixed(2)}%)`);

                    } else {

                        changeEl.textContent = '--';

                        changeEl.style.color = '#666';

                    }

                } else {

                    console.error(`  âŒ Element #${elementId} -change NOT FOUND`);

                }

            } else {

                console.warn(`  âš ï¸ No element mapping for: ${name} `);

            }

        });

    } else {

        console.warn('âš ï¸ No live_indices data - elements will show "--"');



        // Set all indices to "--" if no data

        ['nifty50', 'sensex', 'banknifty'].forEach(id => {

            const valueEl = document.getElementById(id);

            const changeEl = document.getElementById(id + '-change');

            if (valueEl) {

                valueEl.textContent = '--';

                valueEl.style.color = '#666';

            }

            if (changeEl) {

                changeEl.textContent = '--';

                changeEl.style.color = '#666';

            }

        });

    }



    // ================================================================

    // MARKET STATUS - 100% Dynamic

    // ================================================================

    const marketStatusData = data.market_status || {};



    if (Object.keys(marketStatusData).length > 0) {

        const statusValue = marketStatusData.status || 'UNKNOWN';

        const isOpen = statusValue.toUpperCase() === 'OPEN';



        if (CONFIG.DEBUG_MODE) console.log(`📊 Market status: ${statusValue} (isOpen: ${isOpen})`);



        // Status text

        const statusElement = document.getElementById('marketStatusText');

        if (statusElement) {

            statusElement.textContent = statusValue.toUpperCase();

            statusElement.style.color = isOpen ? '#39FF14' : '#ef4444';

            statusElement.style.fontWeight = '700';

            statusElement.style.fontSize = '0.85rem';

            statusElement.style.textAlign = 'left !important';

            statusElement.style.display = 'block';

            if (CONFIG.DEBUG_MODE) console.log(`âœ… Market status: ${statusValue} `);

        }



        // Session time

        const sessionElement = document.getElementById('marketSession');

        if (sessionElement) {

            const sessionTime = marketStatusData.session_time || '--';

            sessionElement.textContent = sessionTime;

            if (CONFIG.DEBUG_MODE) console.log(`âœ… Session time: ${sessionTime} `);

        }



        // Next open

        const nextOpenElement = document.getElementById('nextOpen');

        if (nextOpenElement) {

            const nextOpen = marketStatusData.next_open || '--';

            nextOpenElement.textContent = nextOpen;

            if (CONFIG.DEBUG_MODE) console.log(`âœ… Next open: ${nextOpen} `);

        }

    } else {

        console.warn('âš ï¸ No market_status data');

        // Set to "--" if no data

        ['marketStatusText', 'marketSession', 'nextOpen'].forEach(id => {

            const el = document.getElementById(id);

            if (el) el.textContent = '--';

        });

    }



    // ================================================================

    // AI PERFORMANCE - 100% Dynamic, REAL AI VALUES

    // ================================================================

    const aiPerformance = data.ai_performance || {};
    const aiEngine =
        (isNonEmptyObject(data.ai_engine) && data.ai_engine)
        || (isNonEmptyObject(data.cognitive_state) && data.cognitive_state)
        || (isNonEmptyObject(window.NEURAL_STATE?.ai_engine) && window.NEURAL_STATE.ai_engine)
        || (isNonEmptyObject(window.NEURAL_STATE?.cognitive_state) && window.NEURAL_STATE.cognitive_state)
        || {};
    const portfolioSnapshot = data.PORTFOLIO_STATE || {};
    const portfolioIntelligence = window.NEURAL_STATE?.portfolio_intelligence || portfolioSnapshot.portfolio_intelligence || {};
    const portfolioPositions = Array.isArray(portfolioIntelligence.positions) ? portfolioIntelligence.positions : [];
    const portfolioMetrics = portfolioSnapshot.account_metrics || portfolioIntelligence.account_metrics || {};
    const formatCompact = (value) => {
        const num = Number(value);
        return Number.isFinite(num) ? num.toLocaleString('en-IN', { maximumFractionDigits: 0 }) : '--';
    };
    const signedPercent = (value) => {
        const num = Number(value);
        if (!Number.isFinite(num)) return '--';
        return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
    };
    const liveIndices = Array.isArray(data.live_indices) ? data.live_indices : [];
    const niftyIndex = liveIndices.find(index => String(index?.name || '').toUpperCase().includes('NIFTY'));
    const totalPredictions = Number(
        aiPerformance.total_predictions ??
        aiPerformance.predictions_today ??
        aiEngine.total_predictions ??
        aiEngine.predictions_today ??
        data.total_predictions ??
        0
    );
    const accuracyValue = Number(
        aiPerformance.accuracy ??
        aiPerformance.prediction_accuracy ??
        aiPerformance.accuracy_percent ??
        aiEngine.accuracy ??
        aiEngine.prediction_accuracy ??
        0
    );
    const portfolioValueRaw = Number(portfolioMetrics.total_value || portfolioMetrics.portfolio_value || 0);
    const portfolioValue = Number.isFinite(portfolioValueRaw) && portfolioValueRaw > 0
        ? portfolioValueRaw
        : portfolioPositions.length
            ? portfolioPositions.reduce((sum, pos) => sum + Number(pos?.value ?? pos?.current_value ?? pos?.market_value ?? 0), 0)
            : 0;
    const portfolioPnlPercentRaw = Number(portfolioMetrics.total_pnl_percent || portfolioMetrics.day_pnl_percent || 0);
    const portfolioPnlPercent = Number.isFinite(portfolioPnlPercentRaw) && portfolioPnlPercentRaw !== 0
        ? portfolioPnlPercentRaw
        : (() => {
            if (!portfolioPositions.length) return 0;
            const invested = portfolioPositions.reduce((sum, pos) => sum + Number(pos?.invested ?? (Number(pos?.quantity || 0) * Number(pos?.avg_price || 0)) ?? 0), 0);
            const value = portfolioPositions.reduce((sum, pos) => sum + Number(pos?.value ?? pos?.current_value ?? pos?.market_value ?? 0), 0);
            return invested > 0 && value > 0 ? ((value - invested) / invested) * 100 : 0;
        })();



    if (CONFIG.DEBUG_MODE) console.log('📊 AI Performance Data:', aiPerformance);



    if (Object.keys(aiPerformance).length > 0) {

        // Prediction Accuracy

        const accuracyEl = document.getElementById('predictionAccuracy');

        if (accuracyEl) {

            const accuracy = parseFloat(

                aiPerformance.accuracy ||

                aiPerformance.prediction_accuracy ||

                0

            );



            if (accuracy > 0) {

                accuracyEl.textContent = `${accuracy.toFixed(1)}% `;

                accuracyEl.style.color = accuracy >= 85 ? '#39FF14' :

                    accuracy >= 70 ? '#FFFF00' : '#FF8C00';

                if (CONFIG.DEBUG_MODE) console.log(`âœ… Prediction Accuracy: ${accuracy.toFixed(1)}% `);

            } else {

                accuracyEl.textContent = 'Calculating...';

                accuracyEl.style.color = '#8b949e';

            }

        }



        // Models Active

        const modelsEl = document.getElementById('modelsActive');

        if (modelsEl) {

            const models = parseInt(

                aiPerformance.models_active ||

                aiPerformance.active_models ||

                0

            );



            if (models > 0) {

                modelsEl.textContent = models;

                modelsEl.style.color = models >= 3 ? '#39FF14' : '#00BFFF';

                if (CONFIG.DEBUG_MODE) console.log(`âœ… Models Active: ${models} `);

            } else {

                modelsEl.textContent = 'Initializing...';

                modelsEl.style.color = '#8b949e';

            }

        }



        // Data Points Per Minute

        const dataPointsEl = document.getElementById('dataPoints');

        if (dataPointsEl) {

            const points = parseInt(

                aiPerformance.data_points ||

                aiPerformance.total_data_points ||

                aiPerformance.data_points_min ||

                0

            );



            if (points > 0) {

                dataPointsEl.textContent = points.toLocaleString('en-IN');

                dataPointsEl.style.color = points >= 1000 ? '#39FF14' : '#00BFFF';

                console.log(`âœ… Data Points: ${points.toLocaleString()} `);

            } else {

                dataPointsEl.textContent = 'Collecting...';

                dataPointsEl.style.color = '#8b949e';

            }

        }

    } else {

        console.warn('âš ï¸ No ai_performance data in API response');



        // Show loading state instead of "--"

        const accuracyEl = document.getElementById('predictionAccuracy');

        const modelsEl = document.getElementById('modelsActive');

        const dataPointsEl = document.getElementById('dataPoints');



        if (accuracyEl) {

            accuracyEl.textContent = 'Initializing AI...';

            accuracyEl.style.color = '#8b949e';

        }

        if (modelsEl) {

            modelsEl.textContent = 'Loading...';

            modelsEl.style.color = '#8b949e';

        }

        if (dataPointsEl) {

            dataPointsEl.textContent = 'Analyzing...';

            dataPointsEl.style.color = '#8b949e';

        }

    }

    const dashboardGain = document.querySelector('.sb-card--dashboard .sb-stat-green');
    if (dashboardGain) dashboardGain.textContent = totalPredictions > 0 ? `+ ${formatCompact(totalPredictions)}` : '--';

    const dashboardBadge = document.querySelector('.sb-card--dashboard .sb-badge-green');
    if (dashboardBadge) dashboardBadge.textContent = accuracyValue > 0 ? `${accuracyValue.toFixed(0)}%` : '--';

    const dashboardReturn = document.querySelector('.sb-card--dashboard .sb-row-val');
    if (dashboardReturn) dashboardReturn.textContent = portfolioValue > 0 ? `$ ${formatCompact(portfolioValue)}` : '--';

    const dashboardReturnPct = document.querySelector('.sb-card--dashboard .sb-row-pct');
    if (dashboardReturnPct) dashboardReturnPct.textContent = portfolioPnlPercent !== 0 ? signedPercent(portfolioPnlPercent) : '--';

    const chartPct = document.querySelector('.sb-card--chart .sb-chart-pct');
    if (chartPct) chartPct.textContent = accuracyValue > 0 ? (accuracyValue / 10).toFixed(1) : '--';

    const chartChange = document.querySelector('.sb-card--chart .sb-chart-change-pos');
    if (chartChange) chartChange.textContent = accuracyValue > 0 ? signedPercent(accuracyValue) : '--';

    const chartPrice = document.querySelector('.sb-card--chart .sb-chart-price');
    if (chartPrice && Number.isFinite(Number(niftyIndex?.value))) {
        chartPrice.textContent = Number(niftyIndex.value).toLocaleString('en-IN', { maximumFractionDigits: 2 });
    }

    const chartChangeSm = document.querySelector('.sb-card--chart .sb-stat-green-sm');
    if (chartChangeSm) chartChangeSm.textContent = Number.isFinite(Number(niftyIndex?.change_percent)) ? signedPercent(niftyIndex.change_percent) : '--';

    const momentum = document.querySelector('.sb-section .sb-val-green-dot');
    if (momentum) momentum.textContent = Number.isFinite(Number(data.market_sentiment?.vix)) ? `${Number(data.market_sentiment.vix).toFixed(1)}%` : '--';

    const cycleBadge = document.querySelector('.sb-section .sb-badge-cyan');
    if (cycleBadge) cycleBadge.textContent = Number.isFinite(Number(aiPerformance.models_active || aiPerformance.active_models)) ? `Cycle: ${Math.max(1, Math.round(Number(aiPerformance.models_active || aiPerformance.active_models)))}` : 'Cycle: --';

    const syncFill = document.querySelector('.sb-card--sync .sb-sync-fill');
    if (syncFill) syncFill.style.width = accuracyValue > 0 ? `${Math.max(0, Math.min(100, accuracyValue))}%` : '0%';

    const selfLearnFill = document.querySelector('.sb-card--selflearn .sb-selflearn-fill');
    if (selfLearnFill) selfLearnFill.style.width = totalPredictions > 0 ? `${Math.max(0, Math.min(100, totalPredictions / 10))}%` : '0%';

    updateDashboardAIPredictionCard(aiPerformance, window.NEURAL_STATE || null);




    // ================================================================

    // SYSTEM HEALTH - 100% Dynamic (can add backend endpoint later)

    // ================================================================

    try {

        const apiStatusElement = document.getElementById('apiStatus');

        const newsFeedElement = document.getElementById('newsFeed');

        const responseTimeElement = document.getElementById('responseTime');



        // For now, show status based on successful API response

        const isApiWorking = data.live_indices && data.live_indices.length > 0;



        if (apiStatusElement) {

            apiStatusElement.textContent = isApiWorking ? 'Online' : 'Offline';

            apiStatusElement.style.color = isApiWorking ? '#39FF14' : '#ff4444';

        }



        if (newsFeedElement) {

            newsFeedElement.textContent = isApiWorking ? 'Active' : 'Inactive';

            newsFeedElement.style.color = isApiWorking ? '#39FF14' : '#ff4444';

        }



        if (responseTimeElement) {

            // Calculate response time from timestamp if available

            if (data.timestamp) {

                const now = new Date();

                const apiTime = new Date(data.timestamp);

                const diff = now - apiTime;

                responseTimeElement.textContent = diff < 1000 ? '<1s' : `${Math.round(diff / 1000)} s`;

                responseTimeElement.style.color = diff < 1000 ? '#39FF14' : '#FFA500';

            } else {

                responseTimeElement.textContent = '--';

                responseTimeElement.style.color = '#666';

            }

        }



        console.log('âœ… System health updated');

    } catch (error) {

        console.error('Error updating system health:', error);

    }



    console.log('â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•');


    // Update Prediction Metrics Cards
    renderPredictionCards();
    if (window.NEURAL_STATE?.portfolio_intelligence) {
        updateDashboardPortfolioCardsFromPI(window.NEURAL_STATE.portfolio_intelligence);
    } else {
        updateDashboardMarketIntelligenceCard();
    }

    console.log('âœ… Dashboard UI update COMPLETE');

    console.log('â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•');

}




function renderPredictionCards(passedData) {
    // Support both direct data and dashed state
    const ai = passedData || (dashState.data ? dashState.data.ai_performance : null);

    // Safety check - if we have raw state from WS, map it
    if (ai && ai.market_state) {
        // Mapping from get_realtime_cognitive_state structure
        ai.accuracy = ai.accuracy;
        const activeModelsRaw = ai.active_models_list ?? ai.active_models ?? ai.models_active ?? [];
        ai.active_models = Array.isArray(activeModelsRaw) ? activeModelsRaw.length : (Number(activeModelsRaw) || 0);
        ai.regime = ai.current_regime;
        ai.strategy = ai.active_strategy;
    }

    const accuracyEl = document.getElementById('globalAccuracyValue');
    const ensemblesEl = document.getElementById('activeEnsemblesValue');
    const regimeEl = document.getElementById('marketRegimeValue');
    const stratEl = document.getElementById('aiStrategyValue');

    if (!ai) {
        if (accuracyEl) accuracyEl.textContent = "INITIALIZING";
        if (ensemblesEl) ensemblesEl.textContent = "--";
        if (regimeEl) {
            regimeEl.textContent = "WAITING";
            regimeEl.style.color = "var(--text-muted)";
        }
        if (stratEl) stratEl.textContent = "--";
        return;
    }

    /* REAL ACCURACY */
    if (accuracyEl) {
        const acc = parseFloat(ai.accuracy || 0);
        accuracyEl.textContent = `${acc.toFixed(1)}% `;
        accuracyEl.style.color = '#39ff14';
    }

    /* ACTIVE MODELS */
    if (ensemblesEl) {
        // active_models might be array or number
        let count = 0;
        if (Array.isArray(ai.active_models)) count = ai.active_models.length;
        else if (typeof ai.active_models === 'number') count = ai.active_models;
        else if (ai.models_active) count = ai.models_active.length; // Compat

        ensemblesEl.textContent = count > 0 ? count : "--";
        ensemblesEl.style.color = '#00e5ff';
    }

    /* REGIME */
    if (regimeEl) {
        const regime = (ai.current_regime || ai.regime || "UNKNOWN").toUpperCase();
        console.log("Regime Update:", regime);

        const colors = {
            "TRENDING_BULL": '#39ff14',
            "TRENDING_BEAR": '#ff1744',
            "VOLATILE_OPPORTUNITY": '#BF00FF',
            "COMPLACENT": '#FFFF00',
            "EXTREME_FEAR": '#ff4444',
            "NEUTRAL_TRANSITION": '#00e5ff',
            "UNKNOWN": '#666'
        };

        regimeEl.textContent = regime.replace('_', ' ');
        regimeEl.style.color = colors[regime] || '#00e5ff';
    }

    /* STRATEGY */
    if (stratEl) {
        const strat = (ai.active_strategy || ai.strategy || "--").toUpperCase();
        stratEl.textContent = strat.replace('_', ' ');
    }
}

function updateMarketStatus(marketState) {
    if (!marketState) return;

    // Here we can update any separate market status elements if they exist
    // For now, mostly handled by renderPredictionCards via state
    // but we can extend this for specific indices etc.
}

function updateElement(id, value, className = '') {

    const element = document.getElementById(id);

    if (!element) return;

    if (value !== undefined) element.textContent = value;

    if (className) element.className = className;

}



// ============================================================================

// TABLE RENDERING - USES CSS CLASSES FROM STYLE.CSS

// ============================================================================



function sortStocksTable(sortKey) {
    if (!sortKey) return;
    const current = window.__STOCK_SORT || { key: 'symbol', direction: 'asc' };
    if (current.key === sortKey) {
        current.direction = current.direction === 'asc' ? 'desc' : 'asc';
    } else {
        current.key = sortKey;
        current.direction = 'asc';
    }
    window.__STOCK_SORT = current;
    renderStocksTable();
}

function updateStockSortIcons() {
    const sortState = window.__STOCK_SORT || { key: 'symbol', direction: 'asc' };
    const iconIds = {
        symbol: 'stockSortSymbol',
        name: 'stockSortName',
        price: 'stockSortPrice',
        change: 'stockSortChange',
        volume: 'stockSortVolume',
        signal: 'stockSortSignal',
        confidence: 'stockSortConfidence',
        target: 'stockSortTarget',
        aiSize: 'stockSortAiSize'
    };

    Object.entries(iconIds).forEach(([key, id]) => {
        const icon = document.getElementById(id);
        if (!icon) return;
        icon.className = 'fas fa-sort';
        if (sortState.key === key) {
            icon.className = sortState.direction === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down';
        }
    });
}

function renderStocksTable() {
    if (CONFIG.DEBUG_MODE) console.log('📄 Rendering stocks table with CSS classes...');

    const tbody = document.getElementById('stocksTableBody') ||
        document.querySelector('#stocksTable tbody') ||
        document.querySelector('tbody');

    if (!tbody) {
        console.error('❌ Table tbody not found');
        return;
    }

    const dashState = window.dashState || {};
    const stocks = Array.isArray(dashState.stocks) ? dashState.stocks.slice() : [];
    const sortState = window.__STOCK_SORT || { key: 'symbol', direction: 'asc' };

    if (!stocks.length) {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center">Live stock feed is syncing...</td></tr>';
        if (CONFIG.DEBUG_MODE) console.warn('⚠ No stocks data');
        updateStockSortIcons();
        return;
    }

    const sortValue = (stock, key) => {
        switch (key) {
            case 'price': return Number(stock.current_price ?? stock.last_price ?? stock.price ?? 0);
            case 'change': return Number(stock.change_percent ?? stock.change_pct ?? stock.change ?? stock.price_change ?? 0);
            case 'volume': return Number(stock.volume ?? stock.total_volume ?? stock.trading_volume ?? stock.qty ?? 0);
            case 'confidence': return Number(stock.prediction_confidence ?? stock.confidence ?? stock.confidence_percent ?? 0);
            case 'target': return Number(stock.target_price ?? stock.target ?? stock.price ?? 0);
            case 'aiSize': return Number(stock.allocation ?? stock.allocation_pct ?? stock.ai_size ?? 0);
            case 'name': return String(stock.name || stock.company_name || '').toLowerCase();
            case 'signal': return String(stock.prediction_signal ?? stock.signal ?? '').toLowerCase();
            default: return String(stock.symbol || '').toLowerCase();
        }
    };

    stocks.sort((a, b) => {
        const aVal = sortValue(a, sortState.key);
        const bVal = sortValue(b, sortState.key);
        if (typeof aVal === 'string' || typeof bVal === 'string') {
            const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true, sensitivity: 'base' });
            return sortState.direction === 'asc' ? cmp : -cmp;
        }
        return sortState.direction === 'asc' ? Number(aVal) - Number(bVal) : Number(bVal) - Number(aVal);
    });

    if (CONFIG.DEBUG_MODE) {
        console.log(`✅ Rendering ${stocks.length} stocks with CSS classes`);
        console.log('Sample stock:', stocks[0]);
    }

    tbody.innerHTML = stocks.map((stock) => {
        const symbol = (stock.symbol || '').replace('.NS', '').replace('.BO', '');
        const name = stock.name || stock.company_name || symbol;
        const exchange = stock.exchange || stock.market || 'NSE';
        const price = Number(stock.current_price ?? stock.last_price ?? stock.price ?? 0);
        const change = Number(stock.change_percent ?? stock.change_pct ?? stock.change ?? stock.price_change ?? 0);
        const volume = Number(stock.volume ?? stock.total_volume ?? stock.trading_volume ?? stock.qty ?? 0);
        const signal = String(stock.prediction_signal ?? stock.signal ?? 'HOLD').toUpperCase().trim();
        const confidence = Number(stock.prediction_confidence ?? stock.confidence ?? stock.confidence_percent ?? 0);
        const target = Number(stock.target_price ?? stock.target ?? price ?? 0);
        const aiSize = Number(stock.allocation ?? stock.allocation_pct ?? stock.ai_size ?? 0);

        let signalClass = 'hold';
        if (signal.includes('STRONG BUY')) signalClass = 'strongbuy';
        else if (signal.includes('BUY')) signalClass = 'buy';
        else if (signal.includes('STRONG SELL')) signalClass = 'strongsell';
        else if (signal.includes('SELL')) signalClass = 'sell';

        const signalText = signal.replace(/_/g, ' ');
        const volumeDisplay = volume > 0 ? formatVolume(volume) : '--';
        const confidenceDisplay = Number.isFinite(confidence) ? confidence.toFixed(0) : '0';
        const targetDisplay = Number.isFinite(target) ? `₹${target.toFixed(2)}` : '--';
        const priceDisplay = Number.isFinite(price) ? `₹${price.toFixed(2)}` : '--';
        const aiSizeDisplay = Number.isFinite(aiSize) ? `${aiSize.toFixed(2)}%` : '--';

        return `
            <tr onclick="showStockDetails('${symbol}')">
                <td>
                    <div class="stock-symbol">${symbol}</div>
                    <div class="exchange">${exchange}</div>
                </td>
                <td>
                    <div class="company-name">${name}</div>
                </td>
                <td class="price">${priceDisplay}</td>
                <td class="change ${change >= 0 ? 'positive' : 'negative'}">
                    ${change >= 0 ? '+' : ''}${change.toFixed(2)}%
                </td>
                <td class="volume">${volumeDisplay}</td>
                <td>
                    <span class="prediction-badge ${signalClass}">${signalText}</span>
                </td>
                <td class="confidence">
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${Math.min(100, Math.max(0, confidence))}%"></div>
                    </div>
                    <div class="confidence-value">${confidenceDisplay}%</div>
                </td>
                <td class="target-price">${targetDisplay}</td>
                <td class="ai-size" style="font-weight:bold; color:var(--electric-yellow);">
                    ${aiSizeDisplay}
                </td>
                <td>
                    <button class="btn-detail" onclick="event.stopPropagation(); showStockDetails('${symbol}')">
                        Analyze
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    updateStockSortIcons();

    if (CONFIG.DEBUG_MODE) {
        console.log(`✅ Successfully rendered ${stocks.length} stock rows with CSS styling`);
    }
}
function initNeuralPredictionMatrix(opportunities) {
    // Intentionally disabled.
    // Predictions are rendered through `displayLivePredictions` only.
    return;
}

// Helper for quick add from matrix
async function addPortfolioPositionFromName(sym, price) {
    try {
        const baseSymbol = String(sym || '').toUpperCase();
        const res = await api.post('/portfolio', { symbol: baseSymbol, qty: 1, avg_price: price });
        if (res.status === "ok") {
            showToast("Sent to AI engine", 'success');
        } else {
            showToast(res.error, 'error');
        }
    } catch (e) {
        showToast("Quick Add failed", "error");
    }
}



// ============================================================================
// DYNAMIC TICKER ADD/REMOVE (Predictions Tab)
// ============================================================================

function setupTickerEditor() {
    const addBtn = document.getElementById('addTickerBtn');
    const inputContainer = document.getElementById('tickerInputContainer');
    const input = document.getElementById('addTickerInput');
    const resultsDiv = document.getElementById('tickerSearchResults');

    if (!addBtn || !input || !inputContainer) return;
    if (addBtn.dataset.bound === 'true') return;
    addBtn.dataset.bound = 'true';

    let debounceTimer;

    // Open Editor
    addBtn.addEventListener('click', () => {
        addBtn.style.display = 'none';
        inputContainer.style.display = 'block'; // Show wrapper
        input.style.display = 'block';          // Ensure input is visible
        input.focus();
    });

    // Autocomplete Search
    input.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(debounceTimer);

        if (query.length < 2) {
            resultsDiv.style.display = 'none';
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const results = typeof SymbolAuthority?.fetchResults === 'function'
                    ? await SymbolAuthority.fetchResults(query)
                    : [];

                if (Array.isArray(results) && results.length > 0) {
                    resultsDiv.innerHTML = results.map((r) => {
                        const displaySymbol = r.display || r.symbol;
                        const displayName = r.name || r.company || 'Live search result';
                        const priceRaw = Number(r.current_price ?? r.price);
                        const changePctRaw = Number(r.change_percent);
                        const changeValueRaw = Number(r.change_value ?? r.price_change);
                        const hasPrice = Number.isFinite(priceRaw) && priceRaw > 0;
                        const hasChangePct = Number.isFinite(changePctRaw);
                        const hasChangeValue = Number.isFinite(changeValueRaw);
                        const effectiveChangeValue = hasChangeValue
                            ? changeValueRaw
                            : (hasPrice && hasChangePct ? (priceRaw * changePctRaw / 100) : null);
                        const changeColor = hasChangePct
                            ? (changePctRaw >= 0 ? 'var(--electric-green)' : 'var(--electric-red)')
                            : 'var(--text-muted)';
                        const priceText = hasPrice ? `₹${priceRaw.toFixed(2)}` : '--';
                        const changeText = (hasChangePct || effectiveChangeValue != null)
                            ? `${effectiveChangeValue != null && effectiveChangeValue >= 0 ? '+' : ''}${effectiveChangeValue != null ? effectiveChangeValue.toFixed(2) : '--'} (${hasChangePct ? `${changePctRaw >= 0 ? '+' : ''}${changePctRaw.toFixed(2)}%` : '--'})`
                            : '--';
                        return `
        <div class="search-result-item ticker-result-item" data-symbol="${r.symbol}" style="padding:0.75rem 1rem; cursor:pointer; border-bottom:1px solid rgba(255,255,255,0.05); transition:all 0.2s; display:flex; justify-content:space-between; align-items:center;">
                            <div style="display:flex; flex-direction:column; gap:2px; max-width:65%;">
                                <div style="color:var(--electric-yellow); font-weight:700; font-family:monospace; font-size:14px;">${displaySymbol}</div>
                                <div style="color:var(--text-muted); font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${displayName}</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="color:white; font-weight:700; font-family:monospace; font-size:13px;">${priceText}</div>
                                <div style="color:${changeColor}; font-size:11px; font-weight:bold;">${changeText}</div>
                            </div>
                        </div>`;
                    }).join('');

                    resultsDiv.style.display = 'block';

                    // Add click listeners to items
                    resultsDiv.querySelectorAll('.ticker-result-item').forEach(item => {
                        item.addEventListener('click', async (e) => {
                            e.stopPropagation();
                            const sym = item.getAttribute('data-symbol');
                            input.value = sym;
                            resultsDiv.style.display = 'none';
                            await addTicker(sym);
                        });
                        item.addEventListener('mouseenter', () => item.style.background = 'rgba(0,255,255,0.08)');
                        item.addEventListener('mouseleave', () => item.style.background = 'transparent');
                    });
                } else {
                    resultsDiv.style.display = 'none';
                }
            } catch (err) {
                console.error(err);
            }
        }, 300);
    });

    // Add Ticker Helper
    async function addTicker(symbol) {
        if (!symbol) return;
        symbol = normalizePredictionSymbol(symbol);
        await addPredictionCard(symbol);

        // Reset UI
        input.value = '';
        resultsDiv.style.display = 'none';
        inputContainer.style.display = 'none';
        addBtn.style.display = 'inline-flex';
    }

    // Enter / Escape
    input.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
            await addTicker(input.value.trim());
        }
        if (e.key === 'Escape') {
            input.value = '';
            resultsDiv.style.display = 'none';
            inputContainer.style.display = 'none';
            addBtn.style.display = 'inline-flex';
        }
    });

    // Close on click outside
    document.addEventListener('click', (e) => {
        if (!inputContainer.contains(e.target) && !addBtn.contains(e.target)) {
            resultsDiv.style.display = 'none';
            inputContainer.style.display = 'none';
            addBtn.style.display = 'inline-flex';
        }
    });
}

async function addPredictionCard(symbol) {
    try {
        if (typeof loadIntelligencePredictions === 'function') {
            const normalizedSymbol = normalizePredictionSymbol(symbol);
            if (!normalizedSymbol) return;
            if (!dashState.userTickers.includes(normalizedSymbol)) {
                dashState.userTickers.push(normalizedSymbol);
            }
            dashState.hiddenTickers = dashState.hiddenTickers.filter((item) => normalizePredictionSymbol(item) !== normalizedSymbol);
            await syncTickers();
            await loadIntelligencePredictions();
            console.log(`✅ Added prediction row: ${normalizedSymbol} `);
            return;
        }
        // Auto-append .NS for NSE stocks if not already present
        const fetchSymbol = symbol.includes('.') ? symbol : symbol + '.NS';

        const response = await fetch(`/api/stock/${fetchSymbol}`);
        const json = await response.json();

        if (!json.success || !json.data) {
            console.warn(`No data for ${fetchSymbol}`);
            return;
        }

        const container = document.getElementById('prediction-cards');
        if (!container) return;

        // Remove "loading" text if present
        const loading = container.querySelector('.loading');
        if (loading) loading.remove();

        const card = document.createElement('div');
        card.className = 'neural-card active';
        card.setAttribute('data-symbol', fetchSymbol);
        card.style.cssText = 'padding:12px; margin-bottom:8px; border-radius:8px; background:rgba(255,255,255,0.03); border:1px solid rgba(0,255,255,0.1); cursor:pointer;';

        const d = json.data;
        const pred = d.prediction || {};
        const signal = pred.signal || 'HOLD';
        const confidence = pred.confidence || 0;
        const price = d.current_price || '--';
        const target = pred.target_price || '--';

        const signalColor = signal.includes('BUY') ? 'var(--electric-green)' :
            signal.includes('SELL') ? 'var(--electric-red)' : 'var(--accent-cyan)';

        card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-weight:700; font-size:14px; color:var(--text-primary);">${fetchSymbol}</div>
                    <div style="font-size:11px; color:var(--text-secondary);">\u20B9${price}</div>
                </div>
                <div style="text-align:right; display:flex; align-items:center; gap:12px;">
                    <div>
                        <div style="font-weight:700; color:${signalColor}; font-size:12px;">${signal}</div>
                        <div style="font-size:10px; color:var(--text-secondary);">${confidence}% conf</div>
                    </div>
                    <i class="fas fa-times remove-ticker" style="color: var(--accent-red, #ff4444); cursor:pointer; font-size:12px; padding:4px;"></i>
                </div>
            </div>
        `;

        container.appendChild(card);

        // Click card → show stock details (DISABLED as per user request to unlink)
        /*
        card.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-ticker')) return;
            if (typeof showStockDetails === 'function') showStockDetails(fetchSymbol);
        });
        */

        // Remove button
        card.querySelector('.remove-ticker').addEventListener('click', async (e) => {
            e.stopPropagation();
            removeTicker(fetchSymbol, card);
            await syncTickers();
        });

        console.log(`\u2705 Added prediction card: ${fetchSymbol} `);
    } catch (err) {
        console.error(`Add ticker failed for ${symbol}: `, err);
    }
}

function removeTicker(symbol, cardElement) {
    // 1. If in userTickers, remove it
    if (dashState.userTickers.includes(symbol)) {
        dashState.userTickers = dashState.userTickers.filter(s => s !== symbol);
    }
    // 2. If NOT in userTickers (must be a default active stock), hide it
    else {
        if (!dashState.hiddenTickers.includes(symbol)) {
            dashState.hiddenTickers.push(symbol);
        }
    }

    if (cardElement) cardElement.remove();
    console.log(`\u274c Removed / Hidden ticker: ${symbol} `);
    syncTickers();
}

async function syncTickers() {
    try {
        await fetch('/api/user_tickers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                added: dashState.userTickers,
                hidden: dashState.hiddenTickers
            })
        });
        console.log('\u2705 Tickers synced:', { added: dashState.userTickers, hidden: dashState.hiddenTickers });
    } catch (err) {
        console.error('Ticker sync failed:', err);
    }
}






function displayLivePredictionsLegacy(predictionsData) {

    const content = document.getElementById('predictionsTableContent');



    if (!predictionsData || predictionsData.length === 0) {

        content.innerHTML = '<p style="text-align:center;color:var(--text-secondary);">No prediction data available.</p>';

        return;

    }



    content.innerHTML = `

        <table >

            <thead>

                <tr>

                    <th>Stock</th>

                    <th>Current Price</th>

                    <th>1D Target</th>

                    <th>15D Target</th>

                    <th>3M Target</th>

                    <th>6M Target</th>

                    <th>1Y Target</th>

                    <th>Confidence</th>

                    <th>Market Trend</th>

                </tr>

            </thead>

            <tbody>

                ${predictionsData.map(stock => `

                    <tr onclick="window.openResearchCockpitForSymbol('${stock.symbol}')" style="cursor:pointer;" class="prediction-row">

                        <td>

                            <div class="stock-symbol">${stock.symbol}</div>

                            <div class="stock-symbol">${stock.symbol}</div>

                            <div style="font-size:0.8em;color:var(--text-secondary);">${stock.name}</div>

                        </td>

                        <td class="price">₹${stock.currentprice.toFixed(2)}</td>

                        <td class="${stock.predictions1d.returnpercent >= 0 ? 'text-success' : 'text-danger'}">

                            ${stock.predictions1d.returnpercent >= 0 ? '+' : ''}${stock.predictions1d.returnpercent.toFixed(2)}%

                            <div style="font-size:0.8em;color:var(--text-secondary);">₹${stock.predictions1d.targetprice}</div>

                        </td>

                        <td class="${stock.predictions15d.returnpercent >= 0 ? 'text-success' : 'text-danger'}">

                            ${stock.predictions15d.returnpercent >= 0 ? '+' : ''}${stock.predictions15d.returnpercent.toFixed(2)}%

                            <div style="font-size:0.8em;color:var(--text-secondary);">₹${stock.predictions15d.targetprice}</div>

                        </td>

                        <td class="${stock.predictions3m.returnpercent >= 0 ? 'text-success' : 'text-danger'}">

                            ${stock.predictions3m.returnpercent >= 0 ? '+' : ''}${stock.predictions3m.returnpercent.toFixed(2)}%

                            <div style="font-size:0.8em;color:var(--text-secondary);">₹${stock.predictions3m.targetprice}</div>

                        </td>

                        <td class="${(stock.target_6m - stock.currentprice) >= 0 ? 'text-success' : 'text-danger'}">

                            ${((stock.target_6m - stock.currentprice) / stock.currentprice * 100).toFixed(2)}%

                            <div style="font-size:0.8em;color:var(--text-secondary);">₹${stock.target_6m}</div>

                        </td>

                        <td class="${(stock.target_1y - stock.currentprice) >= 0 ? 'text-success' : 'text-danger'}">

                            ${((stock.target_1y - stock.currentprice) / stock.currentprice * 100).toFixed(2)}%

                            <div style="font-size:0.8em;color:var(--text-secondary);">₹${stock.target_1y}</div>

                        </td>

                        </td>

                        <td>

                            <div class="confidence-bar" style="width:60px;height:8px;background:rgba(255,255,255,0.2);border-radius:4px;position:relative;">

                                <div style="width:${stock.confidences15d}%;height:100%;background:var(--electric-green);border-radius:4px;"></div>

                            </div>

                            <div style="font-size:0.9em;margin-top:2px;">${stock.confidences15d}%</div>
                        </td>
                        <td>
                            <span class="prediction-badge ${stock.market_conditions.momentum.toLowerCase()}">
                                ${stock.market_conditions.momentum}
                            </span>
                            <div style="font-size: 0.8em; color: var(--text-secondary);">
                                ${stock.market_conditions.volatility_level} Vol
                            </div>
                        </td>
                        <!-- AI SIZE VALUE -->
                        <td class="ai-size" style="font-weight:bold; color:var(--electric-yellow);">
                            ${(function () {
            const sym = stock.symbol.replace('.NS', '');
            const cog = window.AI_COGNITION?.opportunities?.find(o => o.symbol === sym || o.symbol === stock.symbol);
            return cog ? (cog.allocation * 100).toFixed(2) + '%' : '0.00%';
        })()}
                        </td>
                    </tr>

                `).join('')}

            </tbody>

        </table>

        `;



    console.log(`âœ… Rendered ${predictionsData.length} clickable prediction rows`);

}



function updateSidebar(data) {

    console.log("📊 Intelligent Sidebar Update:", data);



    // ============================================================

    // AI-DRIVEN FIELD NAME DETECTION

    // ============================================================

    const aiPick = (...fields) =>

        fields.find(f => data[f] !== undefined) ? data[fields.find(f => data[f] !== undefined)] : null;



    // Dynamic index list detection

    const indices = aiPick('live_indices', 'market_indices', 'indices') || [];



    // ============================================================

    // INDEX MAPPER (AI-style DOM matcher â€“ no hardcoding)

    // ============================================================

    const matchElement = (name) => {

        const clean = name.toLowerCase().replace(/\s+/g, '');

        return document.querySelector(`[data - index= "${clean}"], #${clean}, #${clean} -value`);

    };



    indices.forEach(index => {

        const label = index.name || index.symbol || "";

        const element = matchElement(label);

        if (!element) return;



        const value = Number(index.value ?? index.current ?? index.last ?? 0);

        const change = Number(index.change ?? index.change_percent ?? 0);



        // VALUE

        const valueEl = element.querySelector(".value") || element;

        if (valueEl && value > 0) {

            valueEl.textContent = value.toLocaleString("en-IN", {

                minimumFractionDigits: 2,

                maximumFractionDigits: 2

            });

        }



        // CHANGE

        const changeEl = element.querySelector(".change") || document.getElementById(`${element.id} -change`);

        if (changeEl) {

            changeEl.textContent = `${change >= 0 ? "+" : ""}${change.toFixed(2)}% `;

            changeEl.classList.toggle("positive", change >= 0);

            changeEl.classList.toggle("negative", change < 0);

        }

    });



    // ============================================================

    // MARKET STATUS (zero hardcoding, NLP-based normalization)

    // ============================================================

    const statusBlock = aiPick("market_status", "status", "market") || {};

    const normalize = (txt) => (txt || "").toString().toLowerCase();



    const state = normalize(statusBlock.status || statusBlock.state);

    const isOpen = ["open", "opened", "live", "active"].some(k => state.includes(k));



    const statusEl = document.getElementById("marketStatusText")

        || document.querySelector("[data-field='marketStatus']")

        || document.querySelector(".status-indicator span");



    if (statusEl) statusEl.textContent = isOpen ? "OPEN" : "CLOSED";



    // Time fields (auto-detect)

    const sessionEl = document.getElementById("marketSession");

    const nextOpenEl = document.getElementById("nextOpen");



    if (sessionEl) {

        const timeField = statusBlock.session_time || statusBlock.time;

        sessionEl.textContent = timeField || new Date().toLocaleTimeString("en-IN", {

            hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false

        });

    }



    if (nextOpenEl) {

        if (!isOpen && statusBlock.next_open) {

            const d = new Date(statusBlock.next_open);

            nextOpenEl.textContent = d.toLocaleString("en-IN", {

                day: "2-digit",

                month: "short",

                year: "numeric",

                hour: "2-digit",

                minute: "2-digit"

            });

        } else {

            nextOpenEl.textContent = isOpen ? "Live Trading" : "Closed";

        }

    }



    // ============================================================

    // AI PERFORMANCE (auto-detect)

    // ============================================================

    const aiData = aiPick("ai_performance", "ai_insights");

    if (aiData) {

        const bind = (id, val) => {

            const el = document.getElementById(id);

            if (el && val !== undefined) el.textContent = val;

        };



        bind("predictionAccuracy", (typeof aiData.accuracy === 'number' && aiData.accuracy > 0) ? `${aiData.accuracy.toFixed(1)}%` : (typeof aiData.prediction_accuracy === 'number' ? `${aiData.prediction_accuracy.toFixed(1)}%` : null));

        bind("modelsActive", aiData.models_active);

        bind("dataPoints", aiData.data_points?.toLocaleString());

    }



    console.log("âœ… Intelligent sidebar update completed");

}



// ============================================================================

// SEARCH FUNCTIONALITY - 100% DYNAMIC

// ============================================================================






// ============================================================================

// STOCK DETAILS MODAL - 100% DYNAMIC

// ============================================================================



async function showStockDetails(symbol) {

    if (CONFIG.DEBUG_MODE) console.log(`📊 Opening details for ${symbol}`);



    let stock = (dashState.stocks || []).find(s =>

        s.symbol === symbol ||

        s.symbol === symbol + '.NS' ||

        s.symbol.replace('.NS', '').replace('.BO', '') === symbol

    );



    // If not in predictions list, create minimal stock object for direct API analysis
    if (!stock) {
        stock = { symbol: symbol, name: symbol, current_price: 0 };
    }




    // Find or create modal

    let modal = document.getElementById('stockModal');

    if (!modal) {

        modal = document.createElement('div');

        modal.id = 'stockModal';

        modal.className = 'modal';

        modal.innerHTML = `

        <div class="modal-overlay" onclick="closeModal()"></div>

            <div class="modal-content">

                <div class="modal-header">

                    <h2 id="modalTitle"></h2>

                    <button class="modal-close" onclick="closeModal()">Ã—</button>

                </div>

                <div class="modal-body" id="modalBody"></div>

            </div>

    `;

        document.body.appendChild(modal);

    }



    const title = document.getElementById('modalTitle');

    const body = document.getElementById('modalBody');

    const cleanSymbol = symbol.replace('.NS', '').replace('.BO', '');



    title.textContent = `${stock.name || cleanSymbol} (${cleanSymbol})`;

    body.innerHTML = '<div class="loading">Loading comprehensive AI analysis...</div>';

    modal.style.display = 'flex';



    // Fetch detailed data & Sentiment in parallel
    await Promise.all([
        loadDetailedAnalysis(cleanSymbol, stock),
        loadSymbolSentiment(cleanSymbol)
    ]);

}



async function loadDetailedAnalysis(symbol, basicStock) {

    try {

        const response = await fetch(`/api/stock/analysis/${symbol}`);

        const data = await response.json();



        if (data.success && data.data) {

            displayDetailedAnalysis({ ...basicStock, ...data.data });

        } else {

            displayDetailedAnalysis(basicStock);

        }
    } catch (error) {

        console.error('Details fetch error:', error);

        displayDetailedAnalysis(basicStock);

    }

}



function displayDetailedAnalysis(stock) {
    const body = document.getElementById('modalBody');
    if (!body) return;

    // ═══ SAFE DATA EXTRACTION ═══
    const symbol = (stock.symbol || '').replace('.NS', '').replace('.BO', '');
    const name = stock.company_name || stock.name || symbol;
    const sector = stock.sector || '';
    const price = parseFloat(stock.current_price || (stock.technical_metrics || {}).current_price || 0);
    const change = parseFloat(stock.change_percent || 0);
    const volume = parseFloat(stock.volume || 0);
    const dayHigh = parseFloat(stock.day_high || 0);
    const dayLow = parseFloat(stock.day_low || 0);

    // AI Analysis
    const an = stock.analysis || {};
    const signal = (an.recommendation || stock.prediction_signal || 'HOLD').toUpperCase();
    const confidence = parseFloat(an.confidence || stock.prediction_confidence || 0);
    const dataPoints = an.data_points_analyzed || 0;
    const modelsUsed = an.models_used || [];

    // Technical Metrics
    const tm = stock.technical_metrics || {};
    const safe = (v, d = 0) => (v != null && !isNaN(v)) ? Number(v) : d;
    const targetPrice = safe(tm.target_price || stock.target_price, price);
    const ma20 = safe(tm.ma_20);
    const ma50 = safe(tm.ma_50);
    const ma200 = safe(tm.ma_200);
    const rsi = safe(tm.rsi);
    const macd = safe(tm.macd);
    const signalLine = safe(tm.signal_line);
    const bbUpper = safe(tm.bb_upper);
    const bbMiddle = safe(tm.bb_middle);
    const bbLower = safe(tm.bb_lower);
    const volatility = safe(tm.volatility);
    const high52w = safe(tm.price_52w_high);
    const low52w = safe(tm.price_52w_low);
    const pos52w = safe(tm.price_position_52w);
    const volRatio = safe(tm.volume_ratio, 1);

    // Fundamentals
    const peRatio = parseFloat(stock.pe_ratio || stock.pe || 0);
    const eps = parseFloat(stock.eps || 0);
    const marketCap = parseFloat(stock.market_cap || stock.marketcap || 0);
    const capDisplay = formatMarketCap(marketCap);

    // Risk
    const rm = stock.risk_metrics || {};
    const riskLevel = rm.risk_level || 'MEDIUM';
    const volPercentile = safe(rm.volatility_percentile, 50);
    const predictedReturn = safe(rm.predicted_return);

    // Key Factors
    const kf = stock.key_factors || [];

    // Computed
    const upside = price > 0 ? ((targetPrice - price) / price * 100) : 0;
    const changeColor = change >= 0 ? 'var(--electric-green)' : 'var(--electric-red)';
    const changeSign = change >= 0 ? '+' : '';
    const changeAbs = price > 0 ? Math.abs(change * price / 100) : 0;

    // Signal colors
    const sigColors = {
        'BUY': { bg: 'rgba(0,255,100,0.15)', border: 'var(--electric-green)', text: 'var(--electric-green)' },
        'SELL': { bg: 'rgba(255,50,50,0.15)', border: 'var(--electric-red)', text: 'var(--electric-red)' },
        'HOLD': { bg: 'rgba(255,241,0,0.15)', border: 'var(--electric-yellow)', text: 'var(--electric-yellow)' },
        'STRONG BUY': { bg: 'rgba(0,255,100,0.25)', border: 'var(--electric-green)', text: 'var(--electric-green)' }
    };
    const sc = sigColors[signal] || sigColors['HOLD'];

    // Risk colors
    const riskColors = { 'LOW': 'var(--electric-green)', 'MEDIUM': 'var(--electric-yellow)', 'HIGH': 'var(--electric-red)' };
    const riskColor = riskColors[riskLevel] || 'var(--electric-yellow)';

    // RSI interpretation
    const rsiColor = rsi > 70 ? 'var(--electric-red)' : rsi < 30 ? 'var(--electric-green)' : 'var(--electric-yellow)';
    const rsiLabel = rsi > 70 ? 'Overbought' : rsi < 30 ? 'Oversold' : 'Neutral';

    // Day range bar position
    const dayRange = dayHigh - dayLow;
    const dayPos = dayRange > 0 ? ((price - dayLow) / dayRange * 100) : 50;

    // Key factors HTML
    const factorsHTML = kf.length > 0 ? kf.map(f => {
        const status = (f.status || '').toLowerCase();
        const fColor = status.includes('positive') || status.includes('above') || status.includes('oversold')
            ? 'var(--electric-green)'
            : status.includes('negative') || status.includes('below') || status.includes('overbought')
                ? 'var(--electric-red)' : 'var(--electric-yellow)';
        return `<div style="display:flex; justify-content:space-between; align-items:center; padding:10px 14px; background:rgba(255,255,255,0.03); border-radius:8px; border-left:3px solid ${fColor};">
            <div>
                <span style="color:white; font-weight:600; font-size:13px;">${f.factor || ''}</span>
                <span style="color:${fColor}; font-weight:700; margin-left:10px; font-size:12px;">${f.status || ''}</span>
            </div>
            <span style="color:rgba(255,255,255,0.4); font-size:11px; max-width:45%; text-align:right;">${f.detail || ''}</span>
        </div> `;
    }).join('') : '<div style="color:var(--text-muted); text-align:center; padding:1rem;">Awaiting AI analysis cycle...</div>';

    // ═══ RENDER UNIFIED MODAL ═══
    body.innerHTML = `
        <div style="font-family:'Inter',sans-serif;">
            <!-- Header: Symbol + Price + Change -->
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px; padding-bottom:16px; border-bottom:1px solid rgba(255,255,255,0.06);">
                <div>
                    ${sector ? `<span style="display:inline-block; background:rgba(147,51,234,0.15); color:var(--electric-purple); font-size:10px; padding:2px 8px; border-radius:10px; margin-bottom:6px; letter-spacing:0.5px;">${sector}</span>` : ''}
                    <div style="font-size:28px; font-weight:800; color:var(--electric-cyan); font-family:monospace; letter-spacing:-1px;">
                        ₹${price.toFixed(2)}
                    </div>
                    <div style="font-size:14px; color:${changeColor}; font-weight:600; margin-top:2px;">
                        ${changeSign}${change.toFixed(2)}% ${changeAbs > 0 ? `(${changeSign}₹${changeAbs.toFixed(2)})` : ''}
                    </div>
                </div>
                <div style="text-align:right;">
                    ${dataPoints > 0 ? `<div style="font-size:10px; color:var(--text-muted); margin-bottom:4px;">${dataPoints.toLocaleString()} data points analyzed</div>` : ''}
                    ${modelsUsed.length > 0 ? `<div style="font-size:10px; color:rgba(255,255,255,0.25); background:rgba(255,255,255,0.04); padding:3px 8px; border-radius:4px; display:inline-block;">${modelsUsed.join(' · ')}</div>` : ''}
                </div>
            </div>

            <!-- ═══ AI DECISION PANEL ═══ -->
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:12px; margin-bottom:20px;">
            <div style="background:${sc.bg}; border:1px solid ${sc.border}; border-radius:10px; padding:14px; text-align:center;">
                <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Signal</div>
                <div style="font-size:18px; font-weight:800; color:${sc.text};">${signal}</div>
            </div>
            <div style="background:rgba(0,243,255,0.06); border:1px solid rgba(0,243,255,0.15); border-radius:10px; padding:14px; text-align:center;">
                <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Confidence</div>
                <div style="font-size:18px; font-weight:800; color:var(--electric-cyan);">${confidence.toFixed(1)}%</div>
                <div style="width:100%; height:3px; background:rgba(255,255,255,0.06); border-radius:2px; margin-top:6px;">
                    <div style="width:${Math.min(confidence, 100)}%; height:100%; background:var(--electric-cyan); border-radius:2px;"></div>
                </div>
            </div>
            <div style="background:rgba(255,241,0,0.06); border:1px solid rgba(255,241,0,0.12); border-radius:10px; padding:14px; text-align:center;">
                <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Target</div>
                <div style="font-size:18px; font-weight:800; color:var(--electric-yellow);">₹${targetPrice.toFixed(2)}</div>
            </div>
            <div style="background:rgba(${upside >= 0 ? '0,255,100' : '255,50,50'},0.06); border:1px solid rgba(${upside >= 0 ? '0,255,100' : '255,50,50'},0.15); border-radius:10px; padding:14px; text-align:center;">
                <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Upside</div>
                <div style="font-size:18px; font-weight:800; color:${upside >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'};">${upside >= 0 ? '+' : ''}${upside.toFixed(2)}%</div>
            </div>
        </div>

            ${dayHigh > 0 && dayLow > 0 ? `
            <!-- ═══ DAY RANGE BAR ═══ -->
            <div style="margin-bottom:20px; padding:10px 14px; background:rgba(255,255,255,0.02); border-radius:8px;">
                <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted); margin-bottom:6px;">
                    <span>Day Low: ₹${dayLow.toFixed(2)}</span>
                    <span style="color:white; font-weight:600;">₹${price.toFixed(2)}</span>
                    <span>Day High: ₹${dayHigh.toFixed(2)}</span>
                </div>
                <div style="width:100%; height:6px; background:linear-gradient(90deg, var(--electric-red), var(--electric-yellow), var(--electric-green)); border-radius:3px; position:relative;">
                    <div style="position:absolute; top:-3px; left:${dayPos}%; width:12px; height:12px; background:white; border-radius:50%; transform:translateX(-50%); box-shadow:0 0 8px rgba(0,243,255,0.6);"></div>
                </div>
            </div>` : ''
        }

            <!-- Two-column: Price info + technical indicators -->
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">
                <!-- Price Information -->
                <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:10px; padding:16px;">
                    <h4 style="color:var(--electric-cyan); font-size:12px; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px;">📊 Price Information</h4>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        <div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted); font-size:12px;">Volume</span><span style="color:white; font-size:12px; font-weight:600;">${formatVolume(volume)}</span></div>
                        ${high52w > 0 ? `<div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted); font-size:12px;">52W High</span><span style="color:var(--electric-green); font-size:12px; font-weight:600;">₹${high52w.toFixed(2)}</span></div>` : ''}
                        ${low52w > 0 ? `<div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted); font-size:12px;">52W Low</span><span style="color:var(--electric-red); font-size:12px; font-weight:600;">₹${low52w.toFixed(2)}</span></div>` : ''}
                        ${pos52w > 0 ? `<div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted); font-size:12px;">52W Position</span><span style="color:${pos52w > 75 ? 'var(--electric-green)' : pos52w < 25 ? 'var(--electric-red)' : 'var(--electric-yellow)'}; font-size:12px; font-weight:600;">${pos52w.toFixed(1)}%</span></div>` : ''}
                        ${volRatio > 0 ? `<div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted); font-size:12px;">Volume Ratio</span><span style="color:${volRatio > 1.2 ? 'var(--electric-green)' : volRatio < 0.8 ? 'var(--electric-red)' : 'var(--electric-yellow)'}; font-size:12px; font-weight:600;">${volRatio.toFixed(1)}x</span></div>` : ''}
                    </div>
                </div>
                <!-- Technical Indicators -->
                <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:10px; padding:16px;">
                    <h4 style="color:var(--electric-pink, #ff69b4); font-size:12px; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px;">⚡ Technical Indicators</h4>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        ${ma20 > 0 ? `<div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted); font-size:12px;">MA20</span><span style="color:white; font-size:12px; font-family:monospace;">₹${ma20.toFixed(2)}</span></div>` : ''}
                        ${ma50 > 0 ? `<div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted); font-size:12px;">MA50</span><span style="color:white; font-size:12px; font-family:monospace;">₹${ma50.toFixed(2)}</span></div>` : ''}
                        ${rsi > 0 ? `<div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted); font-size:12px;">RSI (14)</span><span style="color:${rsiColor}; font-size:12px; font-weight:700;">${rsi.toFixed(1)} <span style="font-size:9px; opacity:0.7;">${rsiLabel}</span></span></div>` : ''}
                        ${volatility > 0 ? `<div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted); font-size:12px;">Volatility</span><span style="color:${volatility > 30 ? 'var(--electric-red)' : 'var(--electric-yellow)'}; font-size:12px; font-weight:600;">${volatility.toFixed(1)}%</span></div>` : ''}
                        ${macd !== 0 ? `<div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted); font-size:12px;">MACD</span><span style="color:${macd > signalLine ? 'var(--electric-green)' : 'var(--electric-red)'}; font-size:12px; font-family:monospace;">${macd.toFixed(2)}</span></div>` : ''}
                        ${peRatio > 0 ? `<div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted); font-size:12px;">P/E Ratio</span><span style="color:white; font-size:12px;">${peRatio.toFixed(1)}</span></div>` : ''}
                    </div>
                </div>
            </div>

            <!-- ═══ FUNDAMENTAL METRICS ═══ -->
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-bottom:20px;">
                <div style="background:rgba(0,243,255,0.04); border:1px solid rgba(0,243,255,0.1); border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">P/E Ratio</div>
                    <div style="font-size:20px; font-weight:800; color:var(--electric-cyan);">${peRatio > 0 ? peRatio.toFixed(2) : 'N/A'}</div>
                </div>
                <div style="background:rgba(57,255,20,0.04); border:1px solid rgba(57,255,20,0.1); border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">EPS</div>
                    <div style="font-size:20px; font-weight:800; color:var(--electric-green);">₹${eps > 0 ? eps.toFixed(2) : 'N/A'}</div>
                </div>
                <div style="background:rgba(255,241,0,0.04); border:1px solid rgba(255,241,0,0.1); border-radius:10px; padding:14px; text-align:center;">
                    <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">Market Cap</div>
                    <div style="font-size:20px; font-weight:800; color:var(--electric-yellow);">${capDisplay}</div>
                </div>
            </div>

            <!-- ═══ KEY FACTORS ANALYSIS ═══ -->
        ${kf.length > 0 ? `
            <div style="margin-bottom:20px;">
                <h4 style="color:var(--electric-orange, #ff9500); font-size:12px; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px;">🔑 Key Factors</h4>
                <div style="display:flex; flex-direction:column; gap:6px;">
                    ${factorsHTML}
                </div>
            </div>` : ''
        }

            <!-- Risk assessment -->
            <div style="background:rgba(255,50,50,0.04); border:1px solid rgba(255,50,50,0.08); border-radius:10px; padding:16px; margin-bottom:20px;">
                <h4 style="color:var(--electric-red); font-size:12px; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px;">⚠ Risk Assessment</h4>
                <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px;">
                    <div style="text-align:center;">
                        <div style="font-size:10px; color:var(--text-muted); margin-bottom:4px;">Risk Level</div>
                        <div style="font-size:16px; font-weight:800; color:${riskColor};">${riskLevel}</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:10px; color:var(--text-muted); margin-bottom:4px;">Volatility Percentile</div>
                        <div style="font-size:16px; font-weight:800; color:white;">${volPercentile}%</div>
                        <div style="width:100%; height:4px; background:rgba(255,255,255,0.06); border-radius:2px; margin-top:4px;">
                            <div style="width:${volPercentile}%; height:100%; background:${volPercentile > 70 ? 'var(--electric-red)' : volPercentile > 40 ? 'var(--electric-yellow)' : 'var(--electric-green)'}; border-radius:2px;"></div>
                        </div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:10px; color:var(--text-muted); margin-bottom:4px;">Predicted Return</div>
                        <div style="font-size:16px; font-weight:800; color:${predictedReturn >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'};">${predictedReturn !== 0 ? (predictedReturn >= 0 ? '+' : '') + predictedReturn.toFixed(2) + '%' : 'N/A'}</div>
                    </div>
                </div>
            </div>

            <!-- ═══ AI REASONING ═══ -->
        <div style="background:rgba(57,255,20,0.03); border:1px solid rgba(57,255,20,0.08); border-radius:10px; padding:16px;">
            <h4 style="color:var(--electric-green); font-size:12px; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">🧠 AI Reasoning</h4>
            <p style="color:rgba(255,255,255,0.7); font-size:13px; line-height:1.6; margin:0;">
                ${stock.ai_reason || stock.reasoning || stock.ai_analysis || `Neural network analysis of ${symbol} indicates a <strong style="color:${sc.text}">${signal}</strong> signal with <strong>${confidence.toFixed(1)}%</strong> confidence. ${targetPrice > price ? `Target price ₹${targetPrice.toFixed(2)} suggests ${upside.toFixed(1)}% upside potential.` : `Current price is near target level ₹${targetPrice.toFixed(2)}.`} ${rsi > 0 ? `RSI at ${rsi.toFixed(1)} (${rsiLabel}).` : ''} ${volatility > 0 ? `Annual volatility: ${volatility.toFixed(1)}%.` : ''}`}
            </p>
        </div>
        </div>
        `;
    // 🔗 Wire live sentiment AFTER modal is rendered
    if (typeof loadSymbolSentiment === 'function') {
        loadSymbolSentiment(symbol);
    }
    console.log('✅ Unified stock details displayed');
}



function closeModal() {

    const modal = document.getElementById('stockModal');

    if (modal) {

        modal.style.display = 'none';

    }

}



// ============================================================================

// PREDICTIONS TABLE - CLICKABLE ROWS

// ============================================================================



window.__PRED_SORT = window.__PRED_SORT || { key: 'confidence', direction: 'desc' };
window.__PRED_LIVE_ROWS = window.__PRED_LIVE_ROWS || [];

function predSortIcon(key) {
    const s = window.__PRED_SORT || {};
    if (s.key !== key) return 'fa-sort';
    return s.direction === 'asc' ? 'fa-sort-up' : 'fa-sort-down';
}

function predBadgeClass(signal) {
    const s = String(signal || 'HOLD').toUpperCase();
    if (s.includes('BUY') || s.includes('ADD') || s.includes('ACCUMULATE') || s.includes('BULL')) return 'buy';
    if (s.includes('SELL') || s.includes('REDUCE') || s.includes('DISTRIBUTE') || s.includes('BEAR')) return 'sell';
    return 'hold';
}

function sortLivePredictionsTable(key) {
    const cur = window.__PRED_SORT || { key: 'confidence', direction: 'desc' };
    if (cur.key === key) {
        cur.direction = cur.direction === 'asc' ? 'desc' : 'asc';
    } else {
        cur.key = key;
        cur.direction = ['confidence', 'ai_size', 'reliability', 'edge', 'scenario'].includes(key) ? 'desc' : 'asc';
    }
    window.__PRED_SORT = cur;
    if (Array.isArray(window.__PRED_LIVE_ROWS) && window.__PRED_LIVE_ROWS.length) {
        displayLivePredictions(window.__PRED_LIVE_ROWS);
    }
}
window.sortLivePredictionsTable = sortLivePredictionsTable;

function removeLegacyPredictionMatrixUI() {
    try {
        const host = document.getElementById('prediction-cards');
        if (!host) return;
        const headers = host.querySelectorAll('h2, h3');
        headers.forEach((el) => {
            const t = String(el.textContent || '').trim().toUpperCase();
            if (t.includes('NEURAL PREDICTION MATRIX') || t.includes('PREDICTION ACCURACY BY TIMEFRAME')) {
                const section = el.closest('.tab-section');
                if (section) section.remove();
            }
        });
        const chart = document.getElementById('accuracyChart');
        if (chart) {
            const section = chart.closest('.tab-section');
            if (section) section.remove();
        }
    } catch (_) { }
}

// ============================================================================
// AI MARKET INTELLIGENCE CONSOLE — Helper Renderers
// ============================================================================

/**
 * Renders a colour-coded reliability badge.
 * Falls back gracefully when intelligence data is absent.
 */
function renderReliabilityBadge(gate, score) {
    const g = String(gate || '').toUpperCase();
    const colorMap = { RELIABLE: '#39ff14', UNCERTAIN: '#ffcc00', WEAK: '#ff4757' };
    const color = colorMap[g] || '#aaa';
    const label = g || 'UNKNOWN';
    const scoreStr = score != null ? ` ${Number(score).toFixed(0)}` : '';
    return `<span class="reliability-badge reliability-badge-${label.toLowerCase()}" style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:700;letter-spacing:0.5px;border:1px solid ${color};color:${color};background:${color}18;">${label}${scoreStr}</span>`;
}

/**
 * Renders a colour-coded decision badge.
 */
function renderDecisionBadge(decision) {
    const d = String(decision || 'HOLD').toUpperCase();
    const colorMap = {
        ENTER:  '#39ff14',
        ADD:    '#00e5ff',
        HOLD:   '#ffcc00',
        WAIT:   '#ff9f43',
        REDUCE: '#ff6b35',
        EXIT:   '#ff4757'
    };
    const color = colorMap[d] || '#aaa';
    return `<span class="decision-badge decision-badge-${d.toLowerCase()}" style="display:inline-flex;align-items:center;padding:3px 10px;border-radius:14px;font-size:11px;font-weight:800;letter-spacing:0.8px;background:${color}22;border:1px solid ${color};color:${color};">${d}</span>`;
}

function formatPercentValue(value, decimals = 1) {
    const num = Number(value);
    if (!Number.isFinite(num)) return '--';
    const sign = num >= 0 ? '+' : '';
    return `${sign}${num.toFixed(decimals)}%`;
}

function formatCurrency(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) return '—';
    return `₹${num.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function letterGrade(score) {
    const val = Number(score);
    if (!Number.isFinite(val)) return '—';
    if (val >= 80) return 'A';
    if (val >= 65) return 'B+';
    if (val >= 50) return 'B';
    if (val >= 35) return 'C';
    return 'D';
}

function renderDashboardCards() {
    const marketCard = document.getElementById('marketIntelligenceCard');
    const portfolioCard = document.getElementById('portfolioSnapshotCard');
    const predictionsCard = document.getElementById('topPredictionsCard');
    const newsCard = document.getElementById('marketPulseCard');
    if (!marketCard || !portfolioCard || !predictionsCard || !newsCard) return;

    const marketIntel = dashState.newsIntelligence || {};
    const status = dashState.data?.market_status || {};
    const nextEvent = marketIntel.next_market_event || {};
    const liveIndices = Array.isArray(dashState.data?.live_indices) ? dashState.data.live_indices : [];
    const indicesByName = { };
    liveIndices.forEach(idx => {
        const name = (idx?.name || '').toUpperCase();
        if (name.includes('S&P')) indicesByName.sp = idx;
        if (name.includes('NASDAQ')) indicesByName.nasdaq = idx;
        if (name.includes('NIFTY')) indicesByName.nifty = idx;
    });

    const sentimentLabel = String(marketIntel.global_sentiment || dashState.marketSentiment?.label || 'Neutral');
    const regimeLabel = String(marketIntel.market_regime || 'UNKNOWN');
    const mpi = Number.isFinite(+marketIntel.market_pressure_index) ? Number(marketIntel.market_pressure_index) : null;
    const globalSync = [
        `S&P ${indicesByName.sp?.change_percent?.toFixed(2) ?? '--'}%`,
        `Nasdaq ${indicesByName.nasdaq?.change_percent?.toFixed(2) ?? '--'}%`,
        `Nifty ${indicesByName.nifty?.change_percent?.toFixed(2) ?? '--'}%`
    ].join(' | ');

    marketCard.innerHTML = `
        <div class="card-title">Market Intelligence</div>
        <div class="card-body">
            <div>Market Status: ${escapeHtml(status.status || 'SYNC')}</div>
            <div>Next Event: ${escapeHtml(nextEvent.label || nextEvent.name || '—')}</div>
            <div>Regime: ${escapeHtml(regimeLabel)}</div>
            <div>Global Sentiment: ${escapeHtml(sentimentLabel)}</div>
            <div>MPI: ${mpi != null ? `${mpi.toFixed(2)} (${mpi >= 0 ? 'Bullish' : 'Bearish'})` : '--'}</div>
            <div>Global Sync: ${escapeHtml(globalSync)}</div>
            <div>Macro: USD ${escapeHtml(String(marketIntel.usd_index ?? marketIntel.global_view?.usd_index ?? '--'))} | Crude ${escapeHtml(String(marketIntel.crude_price ?? marketIntel.global_view?.crude_price ?? '--'))}</div>
            <div>Crypto: BTC ${escapeHtml(String(marketIntel.crypto_price ?? marketIntel.global_view?.btc_price ?? '--'))}</div>
        </div>
    `;

    const portfolio = window.NEURAL_STATE?.portfolio_intelligence || {};
    const positions = Array.isArray(portfolio.positions) ? portfolio.positions : [];
    const dayChange = Number(portfolio.account_metrics?.day_return || 0);
    const topGainer = positions.sort((a, b) => (Number(b.change_percent) || 0) - (Number(a.change_percent) || 0))[0];
    const topAlert = dashState.portfolioNewsAlerts?.find(alert => Array.isArray(alert.symbols) ? alert.symbols.some(Boolean) : alert.symbol) || null;

    portfolioCard.innerHTML = `
        <div class="card-title">Portfolio Snapshot</div>
        <div class="card-body">
            <div>${formatCurrency(portfolio.account_metrics?.total_value || 0)} (${formatPercentValue(portfolio.account_metrics?.total_return || 0)})</div>
            <div>Positions: ${positions.length} (${positions.filter(p => Number(p.change_percent || 0) > 0).length} green)</div>
            <div>Top Gainer: ${topGainer ? `${topGainer.symbol} ${formatPercentValue(topGainer.change_percent, 1)}` : '–'}</div>
            <div>Top Alert: ${topAlert ? escapeHtml(topAlert.title || topAlert.symbol) : 'None'}</div>
        </div>
        <div class="card-actions">
            <button class="btn-link" onclick="switchTab('portfolio')">View Full Portfolio →</button>
            <button class="btn-link" onclick="switchTab('predictions')">Add Stock →</button>
        </div>
    `;

    const topRows = (Array.isArray(window.__INTEL_PRED_ROWS) ? window.__INTEL_PRED_ROWS : [])
        .slice()
        .sort((a, b) => (Number(b.opportunity_score || b.reliability_score || 0) - Number(a.opportunity_score || a.reliability_score || 0)))
        .slice(0, 5);
    const predictionRowsHtml = topRows.length
        ? topRows.map(row => `
            <tr>
                <td>${escapeHtml(row.symbol || '--')}</td>
                <td>${escapeHtml(row.ai_signal || row.decision || 'WAIT')}</td>
                <td>${formatPercentValue(row.confidence, 1)}</td>
                <td>${letterGrade(row.reliability_score)}</td>
                <td>${escapeHtml(row.decision || row.signal_gate || 'WAIT')}</td>
                <td>${row.portfolio_context?.is_held ? `✓ ${formatPercentValue(row.position_size, 1)}` : '—'}</td>
            </tr>
        `).join('')
        : `<tr><td colspan="6" style="text-align:center; color:var(--text-secondary);">Live signals are syncing…</td></tr>`;

    predictionsCard.innerHTML = `
        <div class="card-title">Top Predictions</div>
        <div class="card-body">
            <table class="mini-table">
                <thead>
                    <tr>
                        <th>Symbol</th><th>Signal</th><th>Conf</th><th>SRS</th><th>Decision</th><th>In Portfolio</th>
                    </tr>
                </thead>
                <tbody>${predictionRowsHtml}</tbody>
            </table>
        </div>
        <div class="card-actions">
            <button class="btn-link" onclick="switchTab('predictions')">View All Predictions →</button>
            <button class="btn-link" onclick="switchTab('news')">Scan Market →</button>
        </div>
    `;

    const newsItems = Array.isArray(dashState.news) ? dashState.news.slice(0, 3) : [];
    const newsHtml = newsItems.map(item => `
        <div class="news-card">
            <div class="news-title">${escapeHtml(item.title || item.headline || 'Live news')}</div>
            <div class="news-meta">Impact: ${escapeHtml(item.impact || 'Medium')} | Sentiment: ${escapeHtml(item.sentiment || 'Neutral')}</div>
        </div>
    `).join('');
    newsCard.innerHTML = `
        <div class="card-title">Market Pulse</div>
        <div class="card-body">
            ${newsHtml || '<div style="color:var(--text-secondary);">Top news will appear here.</div>'}
        </div>
        <div class="card-actions">
            <button class="btn-link" onclick="switchTab('news')">View All News →</button>
            <button class="btn-link" onclick="switchTab('alerts')">Filter by Sector →</button>
        </div>
    `;
}

/**
 * Renders a compact scenario probability bar.
 */
function renderScenarioMini(scenarios) {
    if (!scenarios || typeof scenarios !== 'object') return '<span style="color:var(--text-muted);font-size:10px;">—</span>';
    const bull  = Number(scenarios.bullish  || 0);
    const neut  = Number(scenarios.neutral  || 0);
    const bear  = Number(scenarios.bearish  || 0);
    return `<div class="scenario-mini" title="Bull:${bull}% Neutral:${neut}% Bear:${bear}%" style="display:grid;grid-template-rows:auto auto;gap:4px;min-width:118px;">
        <div class="scenario-bar" style="display:grid;grid-template-columns:${Math.max(bull, 1)}fr ${Math.max(neut, 1)}fr ${Math.max(bear, 1)}fr;height:6px;border-radius:999px;overflow:hidden;">
            <div style="background:#39ff14;"></div>
            <div style="background:#ffcc00;"></div>
            <div style="background:#ff4757;"></div>
        </div>
        <div style="font-size:9px;color:var(--text-muted);display:flex;justify-content:space-between;gap:6px;">
            <span>▲${bull}%</span>
            <span>◆${neut}%</span>
            <span>▼${bear}%</span>
        </div>
    </div>`;
}

/**
 * XAI Panel HTML for a single prediction row.
 */
function renderXAIPanel(drivers, symbol, stability, macro_risk, detail = {}) {
    const companyProfile = detail?.company_profile || {};
    const horizons = detail?.forecast_horizons || {};
    const sessionOutlook = detail?.session_outlook || {};
    const predictionChange = detail?.prediction_change || {};
    const adaptiveEnsemble = detail?.adaptive_ensemble || {};
    const driftIntelligence = detail?.drift_intelligence || {};
    const riskIntelligence = detail?.risk_intelligence || {};
    const globalContext = detail?.global_context || {};
    const marketNetwork = detail?.market_network || {};
    const timingIntelligence = detail?.timing_intelligence || {};
    const liquidityIntelligence = detail?.liquidity_intelligence || {};
    const trapIntelligence = detail?.trap_intelligence || {};
    const strategyIntelligence = detail?.strategy_intelligence || {};
    const newsContext = detail?.news_context || {};
    const horizonHtml = Object.entries(horizons)
        .map(([label, payload]) => {
            const ret = Number(payload?.return_percent);
            const tgt = Number(payload?.target_price);
            if (!Number.isFinite(ret) && !Number.isFinite(tgt)) return '';
            const retClass = Number.isFinite(ret) ? (ret >= 0 ? 'var(--electric-green)' : 'var(--electric-red)') : 'var(--text-secondary)';
            return `<div style="display:flex;justify-content:space-between;gap:10px;padding:3px 0;">
                <span style="color:var(--electric-cyan);font-weight:700;text-transform:uppercase;">${label}</span>
                <span style="color:${retClass};">${Number.isFinite(ret) ? `${ret >= 0 ? '+' : ''}${ret.toFixed(2)}%` : '—'}</span>
                <span style="color:var(--text-muted);">${Number.isFinite(tgt) ? `₹${tgt.toFixed(2)}` : '—'}</span>
            </div>`;
        })
        .filter(Boolean)
        .join('');
    const sessionHtml = ['expected_close', 'next_open'].map((key) => {
        const payload = sessionOutlook?.[key] || {};
        const ret = Number(payload?.return_percent);
        const tgt = Number(payload?.target_price);
        return `<div style="display:flex;justify-content:space-between;gap:10px;padding:3px 0;">
            <span style="color:var(--electric-yellow);font-weight:700;text-transform:uppercase;">${key.replace('_', ' ')}</span>
            <span style="color:${ret >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'};">${Number.isFinite(ret) ? `${ret >= 0 ? '+' : ''}${ret.toFixed(2)}%` : '—'}</span>
            <span style="color:var(--text-muted);">${Number.isFinite(tgt) ? `₹${tgt.toFixed(2)}` : '—'}</span>
        </div>`;
    }).join('');
    const changeHtml = predictionChange?.available ? `
        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.08);">
            <div><div style="font-size:10px;color:var(--text-muted);">Prev Signal</div><div style="color:var(--text-primary);font-weight:700;">${predictionChange.previous_signal || '—'}</div></div>
            <div><div style="font-size:10px;color:var(--text-muted);">Conf Δ</div><div style="color:${Number(predictionChange.confidence_delta) >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'};font-weight:700;">${Number(predictionChange.confidence_delta || 0).toFixed(1)}</div></div>
            <div><div style="font-size:10px;color:var(--text-muted);">Return Δ</div><div style="color:${Number(predictionChange.return_delta) >= 0 ? 'var(--electric-green)' : 'var(--electric-red)'};font-weight:700;">${Number(predictionChange.return_delta || 0).toFixed(2)}%</div></div>
            <div><div style="font-size:10px;color:var(--text-muted);">Elapsed</div><div style="color:var(--text-primary);font-weight:700;">${predictionChange.elapsed_minutes != null ? `${predictionChange.elapsed_minutes}m` : '—'}</div></div>
        </div>` : '';
    const adaptiveHtml = Object.keys(adaptiveEnsemble?.weights || {}).length ? `
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.08);">
            <div style="color:var(--electric-yellow);font-size:10px;font-weight:700;margin-bottom:6px;">ADAPTIVE ENSEMBLE</div>
            <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;">
                <div style="font-size:10px;color:var(--text-secondary);">Regime: <span style="color:var(--text-primary);font-weight:700;">${adaptiveEnsemble.regime || 'UNKNOWN'}</span></div>
                <div style="font-size:10px;color:var(--text-secondary);">Agreement: <span style="color:var(--text-primary);font-weight:700;">${Number(adaptiveEnsemble.agreement_score || 0).toFixed(1)}%</span></div>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">
                ${Object.entries(adaptiveEnsemble.weights || {}).map(([name, weight]) => `<span style="font-size:10px;padding:2px 8px;border-radius:999px;border:1px solid rgba(0,229,255,0.25);color:var(--electric-cyan);">${escapeHtml(name)} ${(Number(weight || 0) * 100).toFixed(1)}%</span>`).join('')}
            </div>
        </div>` : '';
    const riskHtml = (riskIntelligence?.scenario_engine || riskIntelligence?.kelly_fraction != null) ? `
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.08);display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;">
            <div><div style="font-size:10px;color:var(--text-muted);">Tail Risk</div><div style="color:var(--text-primary);font-weight:700;">${riskIntelligence.tail_risk_state || 'UNKNOWN'}</div></div>
            <div><div style="font-size:10px;color:var(--text-muted);">Kelly</div><div style="color:var(--electric-yellow);font-weight:700;">${Number((riskIntelligence.kelly_fraction || 0) * 100).toFixed(2)}%</div></div>
            <div><div style="font-size:10px;color:var(--text-muted);">Payoff</div><div style="color:var(--text-primary);font-weight:700;">${Number(riskIntelligence.payoff_ratio || 0).toFixed(2)}x</div></div>
            <div><div style="font-size:10px;color:var(--text-muted);">Fragility</div><div style="color:var(--text-primary);font-weight:700;">${riskIntelligence?.scenario_engine?.fragility || 'UNKNOWN'}</div></div>
        </div>` : '';
    const driftHtml = driftIntelligence?.status ? `
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.08);display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;">
            <div><div style="font-size:10px;color:var(--text-muted);">Drift Status</div><div style="color:var(--text-primary);font-weight:700;">${driftIntelligence.status}</div></div>
            <div><div style="font-size:10px;color:var(--text-muted);">Drift Score</div><div style="color:var(--text-primary);font-weight:700;">${Number(driftIntelligence.score || 0).toFixed(3)}</div></div>
            <div><div style="font-size:10px;color:var(--text-muted);">Macro Risk</div><div style="color:var(--text-primary);font-weight:700;">${globalContext.context_risk || macro_risk || 'LOW'}</div></div>
            <div><div style="font-size:10px;color:var(--text-muted);">Index Dispersion</div><div style="color:var(--text-primary);font-weight:700;">${Number(globalContext.index_dispersion || 0).toFixed(3)}</div></div>
        </div>` : '';
    const newsHtml = newsContext?.headline || newsContext?.narrative || newsContext?.event_type ? `
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.08);">
            <div style="color:var(--electric-pink);font-size:10px;font-weight:700;margin-bottom:6px;">NEWS CONTEXT</div>
            <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;">
                <div><div style="font-size:10px;color:var(--text-muted);">Narrative</div><div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(newsContext.narrative || 'UNMAPPED'))}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Event</div><div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(newsContext.event_type || 'GENERAL'))}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Impact</div><div style="color:var(--text-primary);font-weight:700;">${Number(newsContext.impact_score || 0).toFixed(2)}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Decay</div><div style="color:var(--text-primary);font-weight:700;">${Number(newsContext.duration_decay || 0).toFixed(2)}</div></div>
            </div>
            ${Array.isArray(newsContext.affected_sectors) && newsContext.affected_sectors.length ? `<div style="margin-top:8px;color:var(--text-secondary);font-size:10px;">Affected: ${escapeHtml(newsContext.affected_sectors.join(', '))}</div>` : ''}
            ${newsContext.headline ? `<div style="margin-top:8px;color:var(--text-secondary);font-size:11px;line-height:1.45;">${escapeHtml(String(newsContext.headline))}</div>` : ''}
        </div>` : '';
    const whyHtml = `
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.08);display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;">
            <div>
                <div style="font-size:10px;color:var(--text-muted);">Why Signal</div>
                <div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(drivers?.[0]?.factor || adaptiveEnsemble?.regime || 'Model alignment'))}</div>
            </div>
            <div>
                <div style="font-size:10px;color:var(--text-muted);">Why Decision</div>
                <div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(timingIntelligence?.state || liquidityIntelligence?.state || trapIntelligence?.state || 'Context gating'))}</div>
            </div>
            <div>
                <div style="font-size:10px;color:var(--text-muted);">What Changed</div>
                <div style="color:var(--text-primary);font-weight:700;">${predictionChange?.available ? escapeHtml(`${Number(predictionChange.confidence_delta || 0).toFixed(1)} conf / ${Number(predictionChange.return_delta || 0).toFixed(2)} ret`) : 'First live reading'}</div>
            </div>
        </div>`;
    const executionHtml = (timingIntelligence?.state || liquidityIntelligence?.state || trapIntelligence?.state || strategyIntelligence?.strategy_id) ? `
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.08);">
            <div style="color:var(--electric-cyan);font-size:10px;font-weight:700;margin-bottom:6px;">EXECUTION CONTEXT</div>
            <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;">
                <div><div style="font-size:10px;color:var(--text-muted);">Timing</div><div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(timingIntelligence.state || 'UNCERTAIN'))}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Liquidity</div><div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(liquidityIntelligence.state || 'NEUTRAL'))}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Trap Risk</div><div style="color:var(--text-primary);font-weight:700;">${Number(trapIntelligence.trap_probability || 0).toFixed(2)}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Authenticity</div><div style="color:var(--text-primary);font-weight:700;">${Number(trapIntelligence.authenticity_score || 0).toFixed(1)}%</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Strategy</div><div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(strategyIntelligence.strategy_id || '--'))}</div></div>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:8px;">
                <div><div style="font-size:10px;color:var(--text-muted);">Network</div><div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(marketNetwork.leader_follower_state || 'ALIGNED'))}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Sector</div><div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(marketNetwork.sector || 'UNMAPPED'))}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Strategy Quality</div><div style="color:var(--text-primary);font-weight:700;">${Number(strategyIntelligence.quality_score || 0).toFixed(2)}</div></div>
            </div>
        </div>` : '';
    const profileHtml = `
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:10px 12px;margin-bottom:10px;">
            <div style="color:var(--electric-cyan);font-size:10px;font-weight:700;margin-bottom:8px;">MARKET SNAPSHOT</div>
            <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;">
                <div><div style="font-size:10px;color:var(--text-muted);">Company</div><div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(companyProfile.company_name || symbol))}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Sector</div><div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(companyProfile.sector || 'UNMAPPED'))}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Risk</div><div style="color:var(--text-primary);font-weight:700;">${escapeHtml(String(companyProfile.risk_level || 'UNKNOWN'))}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Price</div><div style="color:var(--text-primary);font-weight:700;">${Number.isFinite(Number(companyProfile.current_price)) ? `â‚¹${Number(companyProfile.current_price).toFixed(2)}` : 'â€”'}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">Target</div><div style="color:var(--text-primary);font-weight:700;">${Number.isFinite(Number(companyProfile.target_price)) ? `â‚¹${Number(companyProfile.target_price).toFixed(2)}` : 'â€”'}</div></div>
                <div><div style="font-size:10px;color:var(--text-muted);">PE</div><div style="color:var(--text-primary);font-weight:700;">${Number.isFinite(Number(companyProfile.pe_ratio)) ? Number(companyProfile.pe_ratio).toFixed(2) : 'â€”'}</div></div>
            </div>
        </div>`;

    if (!Array.isArray(drivers) || drivers.length === 0) {
        return `<tr class="xai-row" id="xai-${symbol}" style="display:none;"><td colspan="9" style="padding:0 1rem 0.8rem;"><div class="xai-panel" style="background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.15);border-radius:8px;padding:0.8rem 1rem;font-size:11px;color:var(--text-secondary);">No driver data available.</div></td></tr>`;
    }
    const driverHtml = drivers.slice(0, 6).map(d => `
        <div style="display:grid;grid-template-columns:130px 1fr auto;align-items:center;gap:10px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
            <span style="color:var(--electric-cyan);font-weight:600;">${d.factor || '—'}</span>
            <span style="color:var(--text-primary);">${d.strength || '—'}</span>
            <span style="color:var(--text-muted);text-align:right;">${d.direction || ''}</span>
        </div>`).join('');
    const stabilityColor = stability === 'STABLE' ? '#39ff14' : stability === 'OSCILLATING' ? '#ffcc00' : '#ff4757';
    const macroColor = macro_risk === 'HIGH' ? '#ff4757' : macro_risk === 'MEDIUM' ? '#ffcc00' : '#39ff14';
    return `<tr class="xai-row" id="xai-${symbol}" style="display:none;">
        <td colspan="9" style="padding:0 1rem 0.8rem;">
            <div class="xai-panel" style="background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.15);border-radius:8px;padding:0.9rem 1rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px;">
                    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                        <span style="font-size:11px;font-weight:800;color:var(--electric-cyan);letter-spacing:0.5px;">AI REASONING • ${symbol}</span>
                        <span style="font-size:10px;padding:2px 8px;border-radius:999px;border:1px solid ${stabilityColor};color:${stabilityColor};font-weight:700;">${stability || 'UNKNOWN'}</span>
                        <span style="font-size:10px;padding:2px 8px;border-radius:999px;border:1px solid ${macroColor};color:${macroColor};font-weight:700;">MACRO ${macro_risk || 'LOW'}</span>
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:1.2fr 0.8fr;gap:16px;align-items:start;">
                    <div style="min-width:0;">
                        ${profileHtml}
                        <div style="color:var(--electric-yellow);font-size:10px;font-weight:700;margin-bottom:6px;">PRIMARY DRIVERS</div>
                        <div style="font-size:11px;color:var(--text-secondary);background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:10px 12px;">${driverHtml}</div>
                        ${whyHtml}
                        ${changeHtml}
                    </div>
                    <div style="min-width:0;display:grid;gap:10px;">
                        ${executionHtml}
                        ${newsHtml}
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:12px;">
                    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:10px 12px;">
                        <div style="color:var(--electric-yellow);font-size:10px;font-weight:700;margin-bottom:6px;">MULTI-HORIZON OUTLOOK</div>
                        ${horizonHtml || '<div style="color:var(--text-muted);font-size:10px;">No horizon data</div>'}
                    </div>
                    <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:10px 12px;">
                        <div style="color:var(--electric-yellow);font-size:10px;font-weight:700;margin-bottom:6px;">SESSION OUTLOOK</div>
                        ${sessionHtml}
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:12px;">
                    <div style="min-width:0;">
                        ${adaptiveHtml}
                        ${riskHtml}
                    </div>
                    <div style="min-width:0;">
                        ${driftHtml}
                    </div>
                </div>
            </div>
        </td>
    </tr>`;
}

/**
 * Toggle XAI panel for a prediction row.
 */
function toggleXAIPanel(symbol) {
    const xaiRow = document.getElementById(`xai-${symbol}`);
    if (!xaiRow) return;
    const hidden = xaiRow.style.display === 'none' || !xaiRow.style.display;
    xaiRow.style.display = hidden ? 'table-row' : 'none';
}

function ensurePredictionHeaderAssist() {
    const tip = ensureMetricTooltipEl();
    const defs = {
        symbol: { title: 'Symbol', desc: 'The stock currently being tracked in the intelligence console.', score: 5, better: 'Use this to open detail and compare updates.' },
        price: { title: 'Price', desc: 'Latest live traded price feeding the downstream intelligence layer.', score: 6, better: 'Refreshes with live market state.' },
        signal: { title: 'Signal', desc: 'Direction from the existing model output after post-processing.', score: 7, better: 'BUY, SELL or HOLD bias.' },
        confidence: { title: 'Confidence', desc: 'How strongly the ensemble supports the active signal.', score: 8, better: 'Higher is stronger support.' },
        reliability: { title: 'Reliability', desc: 'Confidence adjusted by entropy, volatility, agreement and context.', score: 9, better: 'Higher means cleaner signal quality.' },
        edge: { title: 'Edge', desc: 'Expected return from the latest prediction state.', score: 7, better: 'Positive favors upside.' },
        decision: { title: 'Decision', desc: 'Execution guidance derived after risk and reliability gating.', score: 8, better: 'ENTER, WAIT or REDUCE are actionable cues.' },
        scenario: { title: 'Scenario', desc: 'Bull, neutral and bear path balance from scenario analysis.', score: 8, better: 'Shows path distribution, not certainty.' },
        ai_size: { title: 'AI Size', desc: 'Suggested exposure from edge, reliability and volatility context.', score: 7, better: 'Use as sizing guidance.' }
    };

    document.querySelectorAll('[data-intel-tip]').forEach((el) => {
        if (el.dataset.tipBound === 'true') return;
        el.dataset.tipBound = 'true';
        const def = defs[el.dataset.intelTip];
        if (!def) return;
        el.addEventListener('mouseenter', (event) => {
            const fillColor = scoreColor(def.score);
            tip.innerHTML = `
                <div class="mt-title">${def.title}</div>
                <div class="mt-desc">${def.desc}</div>
                <div class="mt-row"><span>Meaning</span><span>${def.better}</span></div>
                <div class="mt-bar"><div class="mt-fill" style="width:${(def.score / 10) * 100}%;background:${fillColor};"></div></div>
            `;
            const rect = event.currentTarget.getBoundingClientRect();
            tip.style.left = `${Math.max(10, Math.min(window.innerWidth - 280, rect.left))}px`;
            tip.style.top = `${Math.max(10, rect.bottom + 8)}px`;
            tip.style.display = 'block';
        });
        el.addEventListener('mouseleave', hideMetricTooltip);
    });
}

function syncPredictionCognitivePanelVisibility(visible) {
    const section = document.getElementById('aiCognitivePanel')?.closest('section');
    if (!section) return;
    section.style.display = visible ? '' : 'none';
}

function renderPredictionConsoleSummary(rows) {
    const safeRows = Array.isArray(rows) ? rows : [];
    const toNumber = (value) => {
        const numeric = Number(value);
        return Number.isFinite(numeric) ? numeric : null;
    };
    const average = (values) => values.length ? (values.reduce((sum, value) => sum + value, 0) / values.length) : null;
    const confidenceValues = safeRows.map((row) => toNumber(row?.confidence ?? row?.confidences15d ?? row?.prediction?.confidence)).filter((value) => value != null);
    const reliabilityValues = safeRows.map((row) => toNumber(row?.reliability_score)).filter((value) => value != null);
    const sizeValues = safeRows.map((row) => toNumber(row?.ai_size ?? row?.recommended_position_size)).filter((value) => value != null);
    const regimes = safeRows.map((row) => String(row?.market_regime || row?.regime || '')).filter(Boolean);
    const dominantRegime = regimes.length
        ? Object.entries(regimes.reduce((acc, regime) => {
            acc[regime] = (acc[regime] || 0) + 1;
            return acc;
        }, {})).sort((a, b) => b[1] - a[1])[0]?.[0]
        : 'UNKNOWN';

    const cells = [
        ['Regime', dominantRegime || 'UNKNOWN'],
        ['Avg Confidence', average(confidenceValues) != null ? `${average(confidenceValues).toFixed(1)}%` : '—'],
        ['Avg Reliability', average(reliabilityValues) != null ? `${average(reliabilityValues).toFixed(1)}` : '—'],
        ['AI Size', average(sizeValues) != null ? `${average(sizeValues).toFixed(1)}%` : '—']
    ];

    return `
        <div class="intel-console-summary">
            ${cells.map(([label, value]) => `
                <div style="min-width:0;">
                    <div class="intel-console-summary-label">${label}</div>
                    <div class="intel-console-summary-value">${value}</div>
                </div>
            `).join('')}
        </div>
    `;
}

// ============================================================================
// OPPORTUNITY SCANNER CONTROLS
// ============================================================================
function renderOpportunityScannerControls() {
    return `
    <div class="opportunity-controls" id="opportunityControls">
        <span class="opportunity-controls-label">Scanner</span>
        <select id="sectorScanFilter" class="intel-console-select" onchange="applyIntelligenceFilters()">
            <option value="">All Sectors</option>
        </select>
        <select id="topNScanFilter" class="intel-console-select" onchange="applyIntelligenceFilters()">
            <option value="0">Show All</option>
            <option value="5">Top 5</option>
            <option value="10" selected>Top 10</option>
            <option value="20">Top 20</option>
            <option value="50">Top 50</option>
        </select>
        <select id="gateScanFilter" class="intel-console-select" onchange="applyIntelligenceFilters()">
            <option value="">All Signals</option>
            <option value="RELIABLE">Reliable Only</option>
            <option value="UNCERTAIN">Uncertain</option>
        </select>
        <span id="scannerResultCount" class="opportunity-controls-count"></span>
    </div>`;
}

function normalizePredictionSymbol(symbol) {
    const raw = String(symbol || '').trim().toUpperCase();
    if (!raw) return '';
    return raw.endsWith('.NS') || raw.endsWith('.BO') ? raw : `${raw}.NS`;
}

function collectAvailablePredictionSectors(rows) {
    const sectors = new Set();
    (Array.isArray(rows) ? rows : []).forEach((row) => {
        const sector = String(row?.sector || '').trim();
        if (sector) sectors.add(sector);
    });
    return Array.from(sectors).sort((a, b) => a.localeCompare(b));
}

function refreshScannerSectorOptions(rows) {
    const select = document.getElementById('sectorScanFilter');
    if (!select) return;
    const previousValue = String(select.value || '');
    const sectors = collectAvailablePredictionSectors(rows);
    select.innerHTML = [
        '<option value="">All Sectors</option>',
        ...sectors.map((sector) => `<option value="${escapeHtml(sector)}">${escapeHtml(sector)}</option>`)
    ].join('');
    if (previousValue && sectors.includes(previousValue)) {
        select.value = previousValue;
    }
}

function buildPredictionRowFromStockPayload(stockPayload) {
    const payload = stockPayload?.data || stockPayload;
    if (!payload || typeof payload !== 'object') return null;
    const prediction = payload.prediction || {};
    return {
        symbol: String(payload.symbol || '').toUpperCase(),
        name: String(payload.name || payload.company || payload.symbol || '').trim(),
        current_price: Number(payload.current_price ?? payload.price ?? 0),
        currentprice: Number(payload.current_price ?? payload.price ?? 0),
        volatility: Number(payload?.indicators?.volatility ?? payload.volatility ?? 0),
        prediction: {
            signal: prediction.signal || payload.signal || 'HOLD',
            confidence: Number(prediction.confidence ?? payload.confidence ?? 0),
            target_price: Number(prediction.target_price ?? payload.target_price ?? payload.current_price ?? 0),
            predicted_return: Number(prediction.predicted_return ?? payload.predicted_return ?? 0),
            risk_level: prediction.risk_level || payload.risk_level || 'MEDIUM',
            models_used: Array.isArray(prediction.models_used) ? prediction.models_used : []
        },
        timestamp: payload.timestamp || new Date().toISOString(),
        history: Array.isArray(payload.history) ? payload.history : []
    };
}

async function mergePinnedPredictionRows(rows) {
    const normalizedRows = Array.isArray(rows) ? rows.slice() : [];
    const hidden = new Set((dashState.hiddenTickers || []).map((symbol) => normalizePredictionSymbol(symbol)));
    const existing = new Set(normalizedRows.map((row) => normalizePredictionSymbol(row?.symbol)));
    const desired = Array.from(new Set((dashState.userTickers || []).map((symbol) => normalizePredictionSymbol(symbol))))
        .filter((symbol) => symbol && !hidden.has(symbol) && !existing.has(symbol));

    if (!desired.length) return normalizedRows;

    const additions = [];
    dashState._predictionTickerFailures = dashState._predictionTickerFailures || {};
    await Promise.allSettled(desired.map(async (symbol) => {
        try {
            const response = await api.fetch(`/stock/${encodeURIComponent(symbol)}`, {
                cache: false,
                timeout: CONFIG.TIMEOUT
            });
            if (!response?.success || !response?.data) return;
            const built = buildPredictionRowFromStockPayload(response);
            if (!built) return;
            delete dashState._predictionTickerFailures[symbol];
            additions.push(...normalizePredictionsForTable([built]));
        } catch (_) {
            const failures = Number(dashState._predictionTickerFailures[symbol] || 0) + 1;
            dashState._predictionTickerFailures[symbol] = failures;
            if (failures >= 2) {
                dashState.userTickers = (dashState.userTickers || []).filter((item) => normalizePredictionSymbol(item) !== symbol);
                dashState.hiddenTickers = Array.from(new Set([...(dashState.hiddenTickers || []), symbol]));
                syncTickers().catch(() => {});
            }
        }
    }));

    return additions.concat(normalizedRows);
}

function getPredictionContextLookup() {
    const items = Array.isArray(dashState.newsPredictionContext) ? dashState.newsPredictionContext : [];
    return items.reduce((acc, item) => {
        const raw = String(item?.symbol || item?.asset || '').trim();
        if (!raw) return acc;
        acc[normalizePredictionSymbol(raw)] = item;
        return acc;
    }, {});
}

function getLivePredictionRowsFromState() {
    const state = window.NEURAL_STATE || {};
    const rawRows = []
        .concat(Array.isArray(state?.predictions) ? state.predictions : [])
        .concat(Array.isArray(state?.ai_engine?.predictions) ? state.ai_engine.predictions : []);
    if (!rawRows.length && Array.isArray(state?.opportunities)) {
        rawRows.push(...state.opportunities);
    }
    const normalized = normalizePredictionsForTable(rawRows);
    if (normalized.length) return normalized;
    return Array.isArray(dashState.predictions) ? normalizePredictionsForTable(dashState.predictions) : [];
}

/**
 * Apply sector/top-N/gate filters in-memory to the cached predicti    removeLegacyPredictionMatrixUI();

    let content = document.getElementById('predictionsTableContent');
    if (!content) {
        const host = document.getElementById('prediction-cards');
        if (host) {
            host.innerHTML = `
                <div class="tab-section intel-console-section">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.8rem;">
                        <h3 style="margin:0;color:var(--electric-pink);">🧠 AI Market Intelligence Console</h3>
                        <div id="addTickerBtn" style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; padding:6px 14px; border-radius:6px; font-size:11px; font-weight:700; color:var(--accent-cyan, #00e5ff); letter-spacing:0.5px; border:1px solid var(--accent-cyan, #00e5ff); background:rgba(0, 229, 255, 0.08); box-shadow:0 0 8px rgba(0, 229, 255, 0.15); transition:all 0.3s ease;">
                            <i class="fas fa-plus"></i> ADD TICKER
                        </div>
                    </div>
                    ${renderOpportunityScannerControls()}
                    <div class="table-card intel-table-card">
                        <div id="predictionsTableContent"></div>
                    </div>
                </div>
            `;
            if (typeof setupTickerEditor === 'function') {
                try { setupTickerEditor(); } catch { }
            }
            content = document.getElementById('predictionsTableContent');
        }
    }

    if (!content) {
        console.warn('⚠️ Intel console container not found');
        return;
    }

    if (!predictionsData || predictionsData.length === 0) {
        content.innerHTML = '<p style="text-align:center;color:var(--text-secondary);padding:2rem;">No prediction data available. AI engine is warming up…</p>';
        return;
    }

    // Cache full rows for in-memory scanner filtering
    window.__PRED_LIVE_ROWS   = Array.isArray(predictionsData) ? predictionsData.slice() : [];
    window.__INTEL_PRED_ROWS  = window.__PRED_LIVE_ROWS;

    // Sort by opportunity_score desc (with confidence fallback)
    const sortedRows = window.__PRED_LIVE_ROWS.slice().sort((a, b) => {
        const aScore = Number(a.opportunity_score ?? a.confidence ?? 0);
        const bScore = Number(b.opportunity_score ?? b.confidence ?? 0);
        return bScore - aScore;
    });

    // Apply top-N from scanner control if already rendered
    const topNEl = document.getElementById('topNScanFilter');
    const topN   = topNEl ? parseInt(topNEl.value || '0', 10) : 0;
    const display = topN > 0 ? sortedRows.slice(0, topN) : sortedRows;

    const countEl = document.getElementById('scannerResultCount');
    if (countEl) countEl.textContent = `${display.length} signal${display.length !== 1 ? 's' : ''}`;

    _renderIntelligenceTable(display);

    if (CONFIG.DEBUG_MODE) console.log(`✅ Intelligence Console: ${display.length} rows rendered`);
}

/**
 * Core intelligence table renderer (also called by applyIntelligenceFilters for instant in-memory filtering).
 */
function _renderIntelligenceTableLegacyUnused(rows) {
    const content = document.getElementById('predictionsTableContent');
    if (!content) return;
    if (!rows || rows.length === 0) {
        content.innerHTML = '<p style="text-align:center;color:var(--text-secondary);padding:2rem;">No signals match the current filter.</p>';
        return;
    }

    const toNum = (v) => { const n = Number(v); return Number.isFinite(n) ? n : null; };
    const pct   = (v) => v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
    const inr   = (v) => v == null ? '—' : `₹${v.toFixed(2)}`;
    const cls   = (v) => v == null ? '' : (v >= 0 ? 'text-success' : 'text-danger');

    // Edge = predicted_return as a quick proxy
    const edgeStr = (row) => {
        const pr = toNum(row.predicted_return ?? (row.prediction||{}).predicted_return);
        return pr != null ? `<span class="${cls(pr)}" style="font-weight:700;">${pct(pr)}</span>` : '<span style="color:var(--text-muted);">—</span>';
    };

    // Horizon context from existing multi-timeframe fields
    const horizonLabel = (row) => {
        const h1d = toNum((row.predictions1d || {}).returnpercent);
        const h15d = toNum((row.predictions15d || {}).returnpercent);
        if (h1d != null)  return `<span style="font-size:10px;color:var(--text-muted);">1D: <b class="${cls(h1d)}">${pct(h1d)}</b></span>`;
        if (h15d != null) return `<span style="font-size:10px;color:var(--text-muted);">15D: <b class="${cls(h15d)}">${pct(h15d)}</b></span>`;
        return '<span style="color:var(--text-muted);font-size:10px;">—</span>';
    };

    const tableRows = rows.map(row => {
        const symbol   = String(row.symbol || '').replace('.NS','').replace('.BO','');
        const pred     = (typeof row.prediction === 'object' && row.prediction) ? row.prediction : row;
        const name     = row.name || pred.name || symbol;
        const current  = toNum(row.current_price ?? row.currentprice ?? pred.current_price ?? 0);

        // Intelligence fields (from backend enrichment) with fallbacks
        const gate        = row.signal_gate  || null;
        const relScore    = toNum(row.reliability_score);
        const decision    = row.decision     || null;
        const scenarios   = row.scenarios    || null;
        const drivers     = row.explain_drivers || [];
        const stability   = row.stability    || 'UNKNOWN';
        const macro_risk  = row.macro_risk   || 'LOW';
        const opScore     = toNum(row.opportunity_score);
        const sector      = row.sector       || '';

        // Legacy signal (backward compat)
        const signalRaw   = pred.signal || row.signal || row.ai_signal || 'HOLD';
        const signalUpper = String(signalRaw).toUpperCase();
        const sigColor    = signalUpper.includes('BUY') ? '#39ff14' : signalUpper.includes('SELL') ? '#ff4757' : '#ffcc00';

        // Confidence
        const conf = Math.max(0, Math.min(100, toNum(pred.confidence ?? row.confidence ?? 0) || 0));
        const confBar = `<div style="width:56px;height:5px;background:rgba(255,255,255,0.1);border-radius:3px;margin-top:3px;overflow:hidden;"><div style="width:${conf}%;height:100%;background:${conf>=60?'#39ff14':conf>=40?'#ffcc00':'#ff4757'};border-radius:3px;"></div></div>`;

        const reliabilityHtml  = gate    ? renderReliabilityBadge(gate, relScore) : `<span style="color:var(--text-muted);font-size:10px;">${signalUpper}</span>`;
        const decisionHtml     = decision? renderDecisionBadge(decision) : `<span style="color:${sigColor};font-weight:700;font-size:11px;">${signalUpper}</span>`;
        const scenarioHtml     = renderScenarioMini(scenarios);
        const opScoreHtml      = opScore != null ? `<span style="color:var(--electric-yellow);font-weight:700;font-size:12px;">${opScore.toFixed(1)}</span>` : '—';

        const xaiPanel = renderXAIPanel(drivers, symbol, stability, macro_risk);

        return `
            <tr onclick="toggleXAIPanel('${symbol}')" style="cursor:pointer;" class="prediction-row intel-row">
                <td>
                    <div class="stock-symbol">${symbol}</div>
                    <div style="font-size:0.75em;color:var(--text-secondary);">${name.length > 20 ? name.slice(0,20)+'…' : name}</div>
                    ${sector ? `<div style="font-size:9px;color:var(--electric-purple);margin-top:1px;">${sector}</div>` : ''}
                </td>
                <td class="price">${inr(current)}</td>
                <td>${reliabilityHtml}</td>
                <td>
                    <div style="font-size:12px;font-weight:700;">${conf.toFixed(1)}%</div>
                    ${confBar}
                </td>
                <td>${edgeStr(row)}</td>
                <td>${horizonLabel(row)}</td>
                <td>${decisionHtml}</td>
                <td>${scenarioHtml}</td>
                <td>${opScoreHtml}</td>
            </tr>
            ${xaiPanel}
        `;
    }).join('');

    content.innerHTML = `
        <table class="predictions-table intel-console-table" style="width:100%;border-collapse:separate;border-spacing:0 3px;">
            <thead>
                <tr style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.6px;">
                    <th style="cursor:pointer;padding:8px 10px;" onclick="sortLivePredictionsTable('symbol')">Symbol <i class="fas ${predSortIcon('symbol')}"></i></th>
                    <th style="cursor:pointer;" onclick="sortLivePredictionsTable('current')">Price <i class="fas ${predSortIcon('current')}"></i></th>
                    <th>Reliability</th>
                    <th style="cursor:pointer;" onclick="sortLivePredictionsTable('confidence')">Confidence <i class="fas ${predSortIcon('confidence')}"></i></th>
                    <th>Edge</th>
                    <th>Horizon</th>
                    <th>Decision</th>
                    <th>Scenario</th>
                    <th style="cursor:pointer;" onclick="sortLivePredictionsTable('opp_score')" title="Opportunity Score">Opp↑</th>
                </tr>
            </thead>
            <tbody>${tableRows}</tbody>
        </table>
    `;
}






function applyIntelligenceFilters() {
    const sourceRows = Array.isArray(window.__INTEL_PRED_ROWS) ? window.__INTEL_PRED_ROWS.slice() : [];
    const sectorValue = String(document.getElementById('sectorScanFilter')?.value || '').toLowerCase();
    const topNValue = parseInt(document.getElementById('topNScanFilter')?.value || '0', 10);
    const gateValue = String(document.getElementById('gateScanFilter')?.value || '').toUpperCase();

    let rows = sourceRows.filter((row) => {
        const sector = String(row?.sector || '').toLowerCase();
        const gate = String(row?.signal_gate || '').toUpperCase();
        return (!sectorValue || sector.includes(sectorValue)) && (!gateValue || gate === gateValue);
    });

    const sortState = window.__PRED_SORT || { key: 'confidence', direction: 'desc' };
    const sortValue = (row) => {
        switch (sortState.key) {
            case 'symbol': return String(row?.symbol || '');
            case 'current': return Number(row?.current_price ?? row?.currentprice ?? 0);
            case 'signal': return String(row?.signal || row?.ai_signal || row?.prediction?.signal || '');
            case 'confidence': return Number(row?.confidence ?? row?.prediction?.confidence ?? row?.confidences15d ?? 0);
            case 'reliability': return Number(row?.reliability_score ?? 0);
            case 'edge': return Number(row?.predicted_return ?? row?.prediction?.predicted_return ?? 0);
            case 'decision': return String(row?.decision || '');
            case 'scenario': return Number(row?.scenarios?.bullish ?? 0);
            case 'ai_size': return Number(row?.ai_size ?? row?.recommended_position_size ?? 0);
            default: return Number(row?.opportunity_score ?? row?.ai_size ?? row?.confidence ?? 0);
        }
    };
    rows.sort((a, b) => {
        const aVal = sortValue(a);
        const bVal = sortValue(b);
        if (typeof aVal === 'string' || typeof bVal === 'string') {
            const cmp = String(aVal).localeCompare(String(bVal));
            return sortState.direction === 'asc' ? cmp : -cmp;
        }
        const cmp = Number(aVal || 0) - Number(bVal || 0);
        return sortState.direction === 'asc' ? cmp : -cmp;
    });
    if (topNValue > 0) rows = rows.slice(0, topNValue);

    const countEl = document.getElementById('scannerResultCount');
    if (countEl) countEl.textContent = `${rows.length} signal${rows.length === 1 ? '' : 's'}`;
    const summaryMount = document.getElementById('predictionConsoleSummaryMount');
    if (summaryMount) summaryMount.innerHTML = renderPredictionConsoleSummary(rows);

    renderIntelligenceConsoleTable(rows);
}

function displayLivePredictions(predictionsData) {
    removeLegacyPredictionMatrixUI();
    syncPredictionCognitivePanelVisibility(false);

    let content = document.getElementById('predictionsTableContent');
    if (!content) {
        const host = document.getElementById('prediction-cards');
        if (host) {
            host.innerHTML = `
                <div class="tab-section intel-console-section">
                    <div class="intel-console-header" style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.8rem; gap:0.75rem; flex-wrap:wrap;">
                        <h3 style="margin:0;color:var(--electric-pink);">AI Market Intelligence Console</h3>
                        <div style="display:flex; align-items:center; gap:10px;">
                            <div id="addTickerBtn" class="intel-console-add-btn" style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; padding:6px 14px; border-radius:6px; font-size:11px; font-weight:700; color:var(--accent-cyan, #00e5ff); letter-spacing:0.5px; border:1px solid var(--accent-cyan, #00e5ff); background:rgba(0, 229, 255, 0.08); box-shadow:0 0 8px rgba(0, 229, 255, 0.15); transition:all 0.3s ease;">
                                <i class="fas fa-plus"></i> ADD TICKER
                            </div>
                            <div id="tickerInputContainer" style="display:none; position:relative;">
                                <div class="search-box intel-ticker-search">
                                    <i class="fas fa-search"></i>
                                <input type="text" id="addTickerInput" placeholder="e.g. SBIN, WIPRO" autocomplete="off"
                                    style="width: 100%; display:block;" />
                                    <div id="tickerSearchResults" class="search-results"
                                        style="position:absolute; width:100%; top:100%; left:0; z-index:200; max-height:400px; overflow-y:auto; background:rgba(10, 12, 18, 0.97); border:1px solid rgba(0, 255, 255, 0.2); border-radius:6px; backdrop-filter:blur(10px); display:none;">
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div id="predictionConsoleSummaryMount"></div>
                    ${renderOpportunityScannerControls()}
                    <div class="table-card intel-table-card">
                        <div id="predictionsTableContent"></div>
                    </div>
                </div>
            `;
            if (typeof setupTickerEditor === 'function') {
                try { setupTickerEditor(); } catch (_) { }
            }
            content = document.getElementById('predictionsTableContent');
        }
    }

    if (!content) return;

    if (!Array.isArray(predictionsData) || predictionsData.length === 0) {
        window.__PRED_LIVE_ROWS = [];
        window.__INTEL_PRED_ROWS = [];
        content.innerHTML = '<p style="text-align:center;color:var(--text-secondary);padding:2rem;">No prediction data available. AI engine is warming up...</p>';
        return;
    }

    window.__PRED_LIVE_ROWS = predictionsData.slice();
    window.__INTEL_PRED_ROWS = predictionsData.slice();
    const summaryMount = document.getElementById('predictionConsoleSummaryMount');
    if (summaryMount) summaryMount.innerHTML = renderPredictionConsoleSummary(window.__INTEL_PRED_ROWS);
    refreshScannerSectorOptions(window.__INTEL_PRED_ROWS);
    applyIntelligenceFilters();
}

function renderIntelligenceConsoleTable(rows) {
    const content = document.getElementById('predictionsTableContent');
    if (!content) return;
    if (!rows || rows.length === 0) {
        content.innerHTML = '<p style="text-align:center;color:var(--text-secondary);padding:2rem;">No signals match the current filter.</p>';
        return;
    }

    const toNum = (v) => {
        const n = Number(v);
        return Number.isFinite(n) ? n : null;
    };
    const fmtPct = (v) => (v == null ? '&mdash;' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`);
    const fmtPrice = (v) => (v == null ? '&mdash;' : `₹${v.toFixed(2)}`);
    const signClass = (v) => (v == null ? '' : (v >= 0 ? 'text-success' : 'text-danger'));
    const hdr = (key, label, sortKey = key, withTip = true) => `<th${withTip ? ` data-intel-tip="${key}"` : ''} style="cursor:pointer;" onclick="sortLivePredictionsTable('${sortKey}')">${label} <i class="fas ${predSortIcon(sortKey)}"></i></th>`;
    const cleanName = (value) => String(value || '').replace(/\.(NS|BO)$/i, '').trim();
    const predictionContextLookup = getPredictionContextLookup();

    const tableRows = rows.map((row) => {
        const symbol = String(row?.symbol || '').replace('.NS', '').replace('.BO', '');
        const canonicalSymbol = normalizePredictionSymbol(row?.symbol || symbol);
        const pred = (typeof row?.prediction === 'object' && row.prediction) ? row.prediction : row;
        const companyName = cleanName(row?.company_name || row?.name || pred?.company_name || pred?.name || '');
        const displayName = companyName && companyName.toUpperCase() !== symbol.toUpperCase() ? companyName : '';
        const current = toNum(row?.current_price ?? row?.currentprice ?? pred?.current_price);
        const signal = String(pred?.signal || row?.signal || row?.ai_signal || 'HOLD').toUpperCase();
        const confidence = Math.max(0, Math.min(100, toNum(pred?.confidence ?? row?.confidence ?? 0) || 0));
        const edge = toNum(row?.predicted_return ?? pred?.predicted_return);
        const aiSize = toNum(row?.ai_size ?? row?.recommended_position_size);
        const sector = row?.sector || '';
        const detail = {
            company_profile: {
                company_name: displayName || symbol,
                sector,
                pe_ratio: toNum(row?.pe_ratio ?? row?.pe ?? pred?.pe_ratio),
                market_cap: row?.market_cap ?? row?.marketCap ?? pred?.market_cap,
                volume: toNum(row?.volume ?? pred?.volume),
                current_price: current,
                target_price: toNum(pred?.target_price ?? row?.target_price),
                risk_level: pred?.risk_level || row?.risk_level || 'UNKNOWN'
            },
            forecast_horizons: row?.forecast_horizons || {},
            session_outlook: row?.session_outlook || {},
            prediction_change: row?.prediction_change || {},
            adaptive_ensemble: row?.adaptive_ensemble || {},
            drift_intelligence: row?.drift_intelligence || {},
            risk_intelligence: row?.risk_intelligence || {},
            global_context: row?.global_context || {},
            market_network: row?.market_network || {},
            timing_intelligence: row?.timing_intelligence || {},
            liquidity_intelligence: row?.liquidity_intelligence || {},
            trap_intelligence: row?.trap_intelligence || {},
            strategy_intelligence: row?.strategy_intelligence || {},
            news_context: predictionContextLookup[canonicalSymbol] || {}
        };

        return `
            <tr onclick="toggleXAIPanel('${symbol}')" style="cursor:pointer;" class="prediction-row intel-row">
                <td>
                    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
                        <div class="stock-symbol">${symbol}</div>
                        <button onclick="event.stopPropagation(); removeTicker('${row?.symbol || symbol}');" title="Remove ticker" style="background:rgba(255,71,87,0.08);border:1px solid rgba(255,71,87,0.30);color:#ff4757;border-radius:999px;padding:4px 8px;font-size:10px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;"><i class="fas fa-trash" style="font-size:10px;"></i></button>
                    </div>
                    ${displayName ? `<div style="font-size:0.78em;color:var(--text-primary);font-weight:600;line-height:1.3;">${escapeHtml(displayName.length > 34 ? `${displayName.slice(0, 34)}...` : displayName)}</div>` : ''}
                    ${sector ? `<div style="font-size:10px;color:var(--electric-purple);margin-top:2px;text-transform:capitalize;">${escapeHtml(sector)}</div>` : ''}
                </td>
                <td class="price">${fmtPrice(current)}</td>
                <td><span class="signal-badge ${predBadgeClass(signal)}">${signal}</span></td>
                <td>
                    <div style="font-size:12px;font-weight:700;">${confidence.toFixed(1)}%</div>
                    <div style="width:56px;height:5px;background:rgba(255,255,255,0.1);border-radius:3px;margin-top:3px;overflow:hidden;">
                        <div style="width:${confidence}%;height:100%;background:${confidence >= 60 ? '#39ff14' : confidence >= 40 ? '#ffcc00' : '#ff4757'};"></div>
                    </div>
                </td>
                <td>${renderReliabilityBadge(row?.signal_gate || signal, toNum(row?.reliability_score))}</td>
                <td class="srs-grade" style="font-weight:bold; color:var(--electric-cyan);">
                    ${letterGrade(row?.reliability_score)}
                </td>
                <td>${edge == null ? '<span style="color:var(--text-muted);">&mdash;</span>' : `<span class="${signClass(edge)}" style="font-weight:700;">${fmtPct(edge)}</span>`}</td>
                <td>${renderDecisionBadge(row?.decision || signal)}</td>
                <td>${renderScenarioMini(row?.scenarios)}</td>
                <td>${aiSize == null ? '<span style="color:var(--text-muted);">&mdash;</span>' : `<span style="color:var(--electric-yellow);font-weight:700;font-size:12px;">${aiSize.toFixed(1)}%</span>`}</td>
                <td class="portfolio-status" style="font-weight:600; color:var(--electric-green);">
                    ${row?.portfolio_context?.is_held ? `✓ ${formatPercentValue(row?.position_size, 1)}` : '—'}
                </td>
                <td class="allocation-size" style="font-weight:600; color:var(--electric-cyan);">
                    ${formatPercentValue(row?.allocation_percent ?? row?.position_size, 1)}
                </td>
            </tr>
            ${renderXAIPanel(Array.isArray(row?.explain_drivers) ? row.explain_drivers : [], symbol, row?.stability || 'UNKNOWN', row?.macro_risk || 'LOW', detail)}
        `;
    }).join('');

    content.innerHTML = `
        <table class="predictions-table intel-console-table" style="width:100%;border-collapse:separate;border-spacing:0 3px;">
            <thead>
                <tr style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.6px;">
                    ${hdr('symbol', 'Symbol', 'symbol', false)}
                    ${hdr('price', 'Price', 'current')}
                    ${hdr('signal', 'Signal', 'signal')}
                    ${hdr('confidence', 'Confidence', 'confidence')}
                    ${hdr('srs', 'SRS', 'reliability')}
                    ${hdr('edge', 'Edge', 'edge')}
                    ${hdr('decision', 'Decision', 'decision')}
                    ${hdr('scenario', 'Scenario', 'scenario')}
                    ${hdr('ai_size', 'AI Size', 'ai_size')}
                    ${hdr('portfolio', 'Portfolio', 'portfolio')}
                    ${hdr('allocation', 'Sizing', 'allocation')}
                </tr>
            </thead>
            <tbody>${tableRows}</tbody>
        </table>
    `;
    ensurePredictionHeaderAssist();
    ensureMetricTooltips();
}

// Final compatibility shim: any legacy call path now routes into the
// single active intelligence renderer above.
function _renderIntelligenceTable(rows) {
    return renderIntelligenceConsoleTable(rows);
}

async function loadIntelligencePredictions() {
    if (window.__INTEL_PRED_INFLIGHT) return false;
    window.__INTEL_PRED_INFLIGHT = true;
    try {
        const intelligenceTimeout = Math.max(1, Math.floor(CONFIG.TIMEOUT * 0.5));
        let payload = await api.fetch('/predictions/intelligence?top_n=100', {
            cache: false,
            timeout: intelligenceTimeout
        });
        let rows = normalizePredictionsForTable(payload?.rows || payload?.predictions || payload?.stocks || payload?.opportunities || []);
        if (!rows.length) {
            payload = await api.fetch('/predictions', {
                cache: true,
                timeout: CONFIG.TIMEOUT
            });
            rows = normalizePredictionsForTable(payload);
        }
        if (!rows.length) {
            rows = getLivePredictionRowsFromState();
            payload = payload || {};
        }
        rows = await mergePinnedPredictionRows(rows);
        if (!rows.length) {
            if (isTabActive('predictions')) displayLivePredictions([]);
            renderPredictionsWorldState(true);
            return false;
        }
        dashState.predictions = rows;
        dashState.lastUpdate.predictions = Date.now();
        updatePredictionCards({
            ...(payload || {}),
            stocks: rows,
            predictions: rows,
            global_accuracy: payload?.global_accuracy,
            models_active: payload?.models_active,
            market_regime: payload?.market_regime || payload?.macro_context?.dominant_regime
        });
        if (isTabActive('predictions')) displayLivePredictions(rows);
        renderPredictionsWorldState(true);
        if (document.getElementById('aiCognitivePanel')) {
            renderCognitivePanel(buildCognitiveFallbackState(window.NEURAL_STATE || {}));
        }
        return true;
    } catch (error) {
        console.warn('Intelligence predictions load failed:', error);
        const fallbackRows = getLivePredictionRowsFromState();
        if (fallbackRows.length) {
            dashState.predictions = fallbackRows;
            if (isTabActive('predictions')) displayLivePredictions(fallbackRows);
            renderPredictionsWorldState(true);
            if (document.getElementById('aiCognitivePanel')) {
                renderCognitivePanel(buildCognitiveFallbackState(window.NEURAL_STATE || {}));
            }
            return true;
        }
        if (isTabActive('predictions')) displayLivePredictions([]);
        return false;
    } finally {
        window.__INTEL_PRED_INFLIGHT = false;
    }
}

const loadPredictionsBase = loadPredictions;
loadPredictions = async function () {
    const ok = await loadIntelligencePredictions();
    if (ok) return true;
    return loadPredictionsBase();
};

addPredictionCard = async function (symbol) {
    try {
        const normalizedSymbol = normalizePredictionSymbol(symbol);
        if (!normalizedSymbol) return;
        dashState._predictionTickerFailures = dashState._predictionTickerFailures || {};
        delete dashState._predictionTickerFailures[normalizedSymbol];
        dashState.hiddenTickers = (dashState.hiddenTickers || []).filter((item) => normalizePredictionSymbol(item) !== normalizedSymbol);
        if (dashState.userTickers.includes(normalizedSymbol)) {
            showToast(`${normalizedSymbol} is already in Predictions`, 'info');
            return;
        }
        dashState.userTickers.push(normalizedSymbol);
        await syncTickers();
        if (typeof loadIntelligencePredictions === 'function') {
            await loadIntelligencePredictions();
        } else if (typeof loadPredictions === 'function') {
            await loadPredictions();
        }
        showToast(`${normalizedSymbol} added to Predictions`, 'success');
    } catch (err) {
        console.error(`Add ticker failed for ${symbol}: `, err);
        showToast(`Failed to add ${normalizePredictionSymbol(symbol) || 'ticker'}`, 'error');
    }
};

removeTicker = function (symbol, cardElement) {
    symbol = normalizePredictionSymbol(symbol);
    if (!symbol) return;
    const existed = dashState.userTickers.includes(symbol) || (window.__PRED_LIVE_ROWS || []).some((row) => normalizePredictionSymbol(row?.symbol) === symbol);
    if (dashState.userTickers.includes(symbol)) {
        dashState.userTickers = dashState.userTickers.filter(s => s !== symbol);
    }
    if (!dashState.hiddenTickers.includes(symbol)) {
        dashState.hiddenTickers.push(symbol);
    }
    window.__PRED_LIVE_ROWS = (window.__PRED_LIVE_ROWS || []).filter((row) => normalizePredictionSymbol(row?.symbol) !== symbol);
    window.__INTEL_PRED_ROWS = (window.__INTEL_PRED_ROWS || []).filter((row) => normalizePredictionSymbol(row?.symbol) !== symbol);
    if (cardElement) cardElement.remove();
    syncTickers().finally(() => {
        if (typeof loadIntelligencePredictions === 'function') {
            loadIntelligencePredictions();
        }
        showToast(existed ? `${symbol} removed from Predictions` : `${symbol} hidden from Predictions`, 'success');
    });
};

window.applyIntelligenceFilters = applyIntelligenceFilters;
window.loadIntelligencePredictions = loadIntelligencePredictions;

// ============================================================================

// HELPER FUNCTIONS

// ============================================================================



function formatVolume(volume) {

    if (volume >= 1e9) return `${(volume / 1e9).toFixed(2)} B`;

    if (volume >= 1e7) return `${(volume / 1e7).toFixed(2)} Cr`;

    if (volume >= 1e5) return `${(volume / 1e5).toFixed(2)} L`;

    if (volume >= 1e3) return `${(volume / 1e3).toFixed(2)} K`;

    return volume.toString();

}



function formatMarketCap(value) {

    if (value >= 1e12) return `₹${(value / 1e12).toFixed(2)} T`;

    if (value >= 1e9) return `₹${(value / 1e9).toFixed(2)} B`;

    if (value >= 1e7) return `₹${(value / 1e7).toFixed(2)} Cr`;

    if (value >= 1e5) return `₹${(value / 1e5).toFixed(2)} L`;

    return value > 0 ? `₹${value.toFixed(2)} ` : 'N/A';

}



// ============================================================================

// AUTO-REFRESH SYSTEM

// ============================================================================

function updateAIUI(state) {
    // This function will be called when 'ai_state' event is received
    // It should update relevant parts of the UI based on the new AI state
    if (CONFIG.DEBUG_MODE) console.log("Updating AI UI with new state:", state);

    // Example: Update predictions and portfolio if they are part of the state
    if (state.opportunities) {
        dashState.predictions = state.opportunities;
    }
    // Update other AI-related UI elements as needed
    updatePredictionCards(state); // Assuming this can handle the full state object
    updateMarketStatus(state.market_state); // Assuming this can handle the market_state object
}


// SECURE INITIALIZER (Arch Phase 5)
async function safeInit(fn) {
    try {
        if (typeof fn === 'function') await fn();
    }
    catch (e) { console.warn("Module failed:", fn.name || 'Anonymous', e); }
}

async function startAutoRefresh() {
    if (window.__AUTO_REFRESH_STARTED) return;
    window.__AUTO_REFRESH_STARTED = true;

    if (CONFIG.DEBUG_MODE) console.log('â±ï¸ Starting auto-refresh system...');

    // Initial load is handled by initialize(); avoid duplicate startup pressure.

    window.__AUTO_REFRESH_DASH = setInterval(async () => {
        if (window.__NEXUS_DASH_REFRESH_INFLIGHT) return;
        window.__NEXUS_DASH_REFRESH_INFLIGHT = true;
        try {
            const wsDisconnected = !(window.NEXUS_SOCKET && window.NEXUS_SOCKET.connected);
            const dashboardActive = isTabActive('dashboard');
            const portfolioActive = isTabActive('portfolio');
            const predictionsActive = isTabActive('predictions');
            const portfolioBusy = !!(window.__PF_EXPANDED_SYMBOL || document.getElementById('lotEditorModal') || document.getElementById('sellWorkflowModal'));

            if (dashboardActive || (wsDisconnected && !portfolioBusy && !portfolioActive && !predictionsActive)) {
                await loadDashboard();
            }

            const stocksLast = Number(dashState?.lastUpdate?.stocks || 0);
            const due = (Date.now() - stocksLast) >= (CONFIG.REFRESH_INTERVALS.stocks - 1000);
            if ((dashboardActive || predictionsActive || wsDisconnected) && due) {
                await safeInit(loadStocks);
            }
            const predsLast = Number(dashState?.lastUpdate?.predictions || 0);
            const predsDue = (Date.now() - predsLast) >= (CONFIG.REFRESH_INTERVALS.predictions - 1000);
            if ((predictionsActive || wsDisconnected) && predsDue) {
                await safeInit(loadPredictions);
            }
            const pfLast = Number(dashState?.lastUpdate?.portfolio || 0);
            const pfDue = (Date.now() - pfLast) >= (CONFIG.REFRESH_INTERVALS.portfolio - 1000);
            if ((portfolioActive && pfDue && !portfolioBusy) || (wsDisconnected && portfolioActive && !portfolioBusy)) {
                await safeInit(() => loadPortfolioState(wsDisconnected));
                dashState.lastUpdate.portfolio = Date.now();
            }
        } finally {
            window.__NEXUS_DASH_REFRESH_INFLIGHT = false;
        }
    }, CONFIG.REFRESH_INTERVALS.dashboard);


    window.__AUTO_REFRESH_ANALYTICS = setInterval(() => {
        if (isTabActive('analytics')) safeInit(loadAnalytics);
    }, CONFIG.REFRESH_INTERVALS.analytics);

    window.__AUTO_REFRESH_NEWS = setInterval(() => {
        if (isTabActive('news')) safeInit(loadNews);
    }, CONFIG.REFRESH_INTERVALS.news);



    if (CONFIG.DEBUG_MODE) console.log('âœ… Auto-refresh active');

}



// ============================================================================

// INITIALIZATION

// ============================================================================



async function initialize() {
    const bootStartedAt = Date.now();

    // START LOADER IMMEDIATELY - deterministic, no event-timing dependency
    window.__DASHBOARD_BOOTSTRAP_READY = false;
    window.__DASHBOARD_BOOTSTRAP_HIDDEN = false;
    if (typeof integrateLoaderSequence === 'function') integrateLoaderSequence();
    window.setTimeout(() => {
        if (!window.__DASHBOARD_BOOTSTRAP_HIDDEN) {
            console.warn('⚠️ Initialization timed out, forcing UI display');
            window.__DASHBOARD_BOOTSTRAP_READY = true;
            hideLoader();
            window.__DASHBOARD_BOOTSTRAP_HIDDEN = true;
        }
    }, 8000);

    console.log('🚀 NEXUS QUANTUM AI v13.0 Starting...');

    console.log('â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•');



    // Load all data in parallel

    console.log('📊 Loading all data...');



    // Phase-1 critical boot: first paint should not wait for every slow endpoint.
    await safeInit(loadDashboard);
    const minLoaderVisibleMs = 2200;
    const elapsed = Date.now() - bootStartedAt;
    if (elapsed < minLoaderVisibleMs) {
        await new Promise((resolve) => setTimeout(resolve, minLoaderVisibleMs - elapsed));
    }
    window.__DASHBOARD_BOOTSTRAP_READY = true;
    if (!window.__DASHBOARD_BOOTSTRAP_HIDDEN) {
        hideLoader();
        window.__DASHBOARD_BOOTSTRAP_HIDDEN = true;
    }

    // Phase-2 modules: start in parallel without blocking UI.
    Promise.allSettled([
        safeInit(loadStocks),
        safeInit(loadPortfolioState),
        safeInit(loadPredictions),
        safeInit(loadAnalytics),
        safeInit(loadNews)
    ]);

    // Setup search





    // Setup dynamic ticker editor

    setupTickerEditor();



    // Start auto-refresh

    startAutoRefresh();



    console.log('âœ… All modules loaded');

    console.log('âœ… System Ready');

    console.log('â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•');

}



// Start when DOM is ready

if (document.readyState === 'loading') {

    document.addEventListener('DOMContentLoaded', () => {
        initialize().catch((error) => {
            console.error('Initialization failed:', error);
            hideLoader();
        });
    });

} else {

    initialize().catch((error) => {
        console.error('Initialization failed:', error);
        hideLoader();
    });

}



console.log('âœ… app.js LOADED - 100% Dynamic | No Hardcoding');





// ============================================================================

// INTELLIGENCE COCKPIT - Advanced Feature Integration

// ============================================================================



async function showIntelligence(symbol) {

    console.log(`[INTELLIGENCE] Initializing Deep Neural Interface for ${symbol}`);
    const sym = String(symbol || '').toUpperCase();
    window.__COCKPIT_BUSY_UNTIL = window.__COCKPIT_BUSY_UNTIL || {};
    if (Number(window.__COCKPIT_BUSY_UNTIL[sym] || 0) > Date.now()) {
        return;
    }



    // 1. Switch to Analytics tab

    if (typeof switchTab === 'function') {

        switchTab('analytics');

    } else if (typeof dashboard !== 'undefined' && dashboard && typeof dashboard.switchTab === 'function') {

        dashboard.switchTab('analytics');

    }



    // 2. Prepare UI State

    const loader = document.getElementById('cockpitLoader');

    const display = document.getElementById('cockpitDisplay');

    const statusText = document.getElementById('engineStatusText');

    const loaderFill = document.getElementById('loaderFill');



    if (!loader || !display) {

        console.error('[CRITICAL] Cockpit UI components missing');

        return;

    }



    // Reset View

    display.classList.add('hidden');

    loader.classList.remove('hidden');

    loaderFill.style.width = '0%';
    loaderFill.style.background = '';



    // 3. Simulated Loading Sequence (Aesthetics)

    const stages = [

        { progress: 10, text: "Establishing Secure Quantum Link..." },

        { progress: 30, text: "Synchronizing Neural Layers..." },

        { progress: 50, text: "Fetching Multi-World Probabilities..." },

        { progress: 80, text: "Aggregating 28 Intelligence Engines..." },

        { progress: 100, text: "Interface Ready." }

    ];



    for (const stage of stages) {

        statusText.textContent = stage.text;

        loaderFill.style.width = `${stage.progress}% `;

        await new Promise(r => setTimeout(r, 150));

    }



    // 4. Fetch Real Data

    try {

        const ctl = new AbortController();
        const t = setTimeout(() => ctl.abort(), 10000);
        const response = await fetch(`/api/evolved-prediction/${symbol}`, { signal: ctl.signal });
        clearTimeout(t);
        if (!response.ok) {
            if (response.status === 503) {
                window.__COCKPIT_BUSY_UNTIL[sym] = Date.now() + 15000;
                throw new Error('Intelligence core is warming up. Retry in 15s.');
            }
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();



        if (!data || data.error) {
            throw new Error(data?.error || 'Intelligence Data Unavailable');
        }

        // Backend returns the evolved prediction directly
        renderIntelligenceCockpit(symbol, data);



        // Final Transition

        loader.classList.add('hidden');

        display.classList.remove('hidden');



    } catch (error) {

        console.error('[ERROR] Cockpit Link Failed:', error);

        const fallbackMessage = 'INTELLIGENCE OFFLINE — showing fallback view.';
        statusText.textContent = `LINK FAILURE: ${error.message}`;
        loaderFill.style.background = 'var(--electric-red)';
        loader.classList.add('hidden');
        display.classList.remove('hidden');

        let offlineNotice = document.getElementById('cockpitOfflineNotice');
        if (!offlineNotice) {
            offlineNotice = document.createElement('div');
            offlineNotice.id = 'cockpitOfflineNotice';
            offlineNotice.style.cssText = 'color: var(--electric-red); font-size:12px; text-align:center; margin-bottom:1rem;';
            display.prepend(offlineNotice);
        }
        offlineNotice.textContent = fallbackMessage;

    }

}



function renderIntelligenceCockpit(symbol, intelligence) {

    console.log(`[RENDER] Populating 28 engines for ${symbol}`);

    // ------------------------------------------------------------------
    // Header
    // ------------------------------------------------------------------
    const symbolEl = document.getElementById('cockpitSymbol');
    const nameEl = document.getElementById('cockpitName');

    if (symbolEl) symbolEl.textContent = symbol.replace('.NS', '').replace('.BO', '');
    if (nameEl) nameEl.textContent = intelligence.company_name || intelligence.symbol || 'Market Asset';

    const confidence =
        intelligence.confidence_adjusted ??
        intelligence.base_prediction?.confidence ??
        0;

    const confEl = document.getElementById('cockpitConfidence');
    if (confEl) {
        confEl.textContent = `${confidence.toFixed(1)}% `;
        confEl.className =
            'value ' +
            (confidence > 70 ? 'text-green' :
                confidence > 50 ? 'text-yellow' : 'text-red');
    }

    // ------------------------------------------------------------------
    // Engines Grid
    // ------------------------------------------------------------------
    const enginesGrid = document.getElementById('enginesGrid');
    if (!enginesGrid) return;
    enginesGrid.innerHTML = '';

    const engineDefinitions = [
        { label: "Fear Index", path: "emotional_state.fear", type: "percent" },
        { label: "Greed Index", path: "emotional_state.greed", type: "percent" },
        { label: "Fatigue Engine", path: "emotional_state.fatigue", type: "percent" },
        {
            label: "Panic Monitor", path: "emotional_state.regime",
            val: v => v === 'PANIC' ? 'ACTIVE' : 'STABLE',
            status: v => v === 'PANIC' ? 'CRITICAL' : 'OK'
        },
        {
            label: "Euphoria Scan", path: "emotional_state.regime",
            val: v => v === 'EUPHORIA' ? 'HIGH' : 'LOW'
        },
        { label: "Complacency Shield", path: "emotional_state.regime_strength", type: "percent", invert: true },
        { label: "Caution Radar", path: "global_risk.strength", type: "percent" },

        { label: "RF Ensemble", path: "base_prediction.model_details.Technical Layer.confidence", type: "percent" },
        { label: "GB Booster", path: "base_prediction.model_details.Quantum Ensemble.confidence", type: "percent" },
        { label: "LSTM Neural", path: "base_prediction.model_details.LSTM Engine.confidence", type: "percent" },

        {
            label: "Risk Agent", path: "futures.fragility",
            val: v => v ?? 'STABLE',
            status: v => v === 'EXTREME' ? 'CRITICAL'
                : v === 'HIGH' ? 'WARNING'
                    : v === 'MODERATE' ? 'CAUTION' : 'SAFE'
        },

        { label: "RL Optimizer", path: "recommended_position_size", type: "percent" },
        { label: "Meta Weighter", path: "governance_personality.personality_score", type: "percent" },
        { label: "Consensus Driver", path: "ai_debate.verdict", val: v => v ?? 'NEUTRAL' },

        { label: "Regime Detector", path: "emotional_state.regime" },
        { label: "Vol Cluster", path: "futures.volatility", type: "percent" },

        {
            label: "Momentum Pulse", path: "futures.expected_return",
            val: v => typeof v === 'number' ? (v * 100).toFixed(2) + '%' : '—'
        },

        {
            label: "Volume Profile", path: "base_prediction.volume_ratio",
            val: v => typeof v === 'number' ? v.toFixed(1) + 'x' : '—'
        },

        {
            label: "Liquidity Stress", path: "global_risk.state",
            val: v => v === 'RISK_OFF' ? 'HIGH' : v === 'RISK_ON' ? 'LOW' : '—'
        },

        {
            label: "Drift Monitor", path: "regime_drift",
            val: v => v === true ? 'DRIFT' : v === false ? 'STABLE' : '—'
        },

        {
            label: "Anomaly Shield", path: "black_swan_risk",
            val: v => v === true ? 'ALERT' : v === false ? 'CLEAN' : '—',
            status: v => v === true ? 'WARNING' : v === false ? 'SAFE' : 'UNKNOWN'
        },

        {
            label: "Hyper Foresight", path: "multi_year_outlook.base",
            val: v => typeof v === 'number' ? (v * 100).toFixed(0) + '%' : '—'
        },

        { label: "World Simulator", path: "future_cone", val: v => v ? '100 PATHS' : 'ACTIVE' },
        { label: "Governance Hub", path: "governance.decision" },
        { label: "Asset Memory", path: "ai_market_memory", val: v => v || 'NEUTRAL' },
        { label: "Macro Pressure", path: "macro_pressure", type: "percent" },
        { label: "Hypothesis Gen", path: "ai_hypothesis", val: v => v ? 'TESTED' : 'ACTIVE' },
        {
            label: "Debate Resolver", path: "ai_debate.disagreement_score",
            val: v => typeof v === 'number' ? (v * 100).toFixed(0) + '%' : '0%'
        }
    ];

    engineDefinitions.forEach(eng => {
        const card = document.createElement('div');
        card.className = 'engine-card active';

        let value = '—';
        const current = getDeepValue(intelligence, eng.path);

        if (eng.type === 'percent' && typeof current === 'number') {
            const v = eng.invert ? (100 - current) : current;
            value = `${v.toFixed(1)}% `;
        } else if (eng.val) {
            value = eng.val(current);
        } else if (current !== undefined && current !== null) {
            value = current;
        }

        card.innerHTML = `
        <div class="engine-label"> ${eng.label}</div>
            <div class="engine-value">${value}</div>
            <div class="engine-status">
                ${eng.status ? eng.status(current) : 'NOMINAL'}
            </div>
    `;
        enginesGrid.appendChild(card);
    });

    // ------------------------------------------------------------------
    // Technical Indicators (SAFE DOM)
    // ------------------------------------------------------------------
    const tech = intelligence.technical_context || {};

    const safeSet = (id, val) => {
        const el = document.getElementById(id);
        if (el && typeof val === 'number') el.textContent = val;
    };

    safeSet('rsiValue', tech.rsi?.toFixed(1));
    safeSet('macdValue', tech.macd?.toFixed(2));
    safeSet('sma50Value', tech.sma_50?.toFixed(1));
    safeSet('sma200Value', tech.sma_200?.toFixed(1));

    // ------------------------------------------------------------------
    // Reasoning & Verdict
    // ------------------------------------------------------------------
    const reasonEl = document.getElementById('aiReasoning');
    if (reasonEl)
        reasonEl.textContent =
            intelligence.why_this_signal ||
            intelligence.ai_reason ||
            'Analysis synthesis complete.';

    const verdictBox = document.getElementById('strategicVerdict');
    if (verdictBox) {
        const decision = intelligence.governance?.decision || 'HOLD';
        verdictBox.textContent = `STRATEGIC VERDICT: ${decision} `;
        verdictBox.className =
            'strategic-box ' +
            (decision === 'BUY' ? 'text-green' :
                decision === 'SELL' ? 'text-red' : 'text-yellow');
    }

    drawProbabilityCone(intelligence.future_cone || []);
    renderTechnicalOverlays(intelligence);
}


function renderTechnicalOverlays(intelligence) {
    const tech = intelligence.technical_context;
    if (!tech) return;

    drawSMA(tech.sma_50, '#00ffcc');
    drawSMA(tech.sma_200, '#ff9f1a');
    drawRSIGradient(tech.rsi);
    drawMACDRibbon(tech.macd);

    console.log("TECH CONTEXT OK:", tech);
}

function drawSMA(value, color) {
    if (typeof value !== 'number') return;
    console.log(`SMA plotted: ${value} `, color);
}

function drawRSIGradient(rsi) {
    if (typeof rsi !== 'number') return;
    console.log(`RSI plotted: ${rsi} `);
}

function drawMACDRibbon(macd) {
    if (typeof macd !== 'number') return;
    console.log(`MACD plotted: ${macd} `);
}

function getDeepValue(obj, path) {
    if (!obj || !path) return undefined;

    // Support dot paths + quoted keys
    const parts = path
        .replace(/\["([^"]+)"\]/g, '.$1')
        .replace(/\['([^']+)'\]/g, '.$1')
        .split('.')
        .filter(Boolean);

    let current = obj;
    for (const p of parts) {
        if (current && Object.prototype.hasOwnProperty.call(current, p)) {
            current = current[p];
        } else {
            return undefined;
        }
    }
    return current;
}



function drawProbabilityCone(coneData) {
    const canvas = document.getElementById('foresightCanvas');
    if (!canvas || !Array.isArray(coneData) || coneData.length === 0) return;

    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.parentElement.clientWidth;
    const h = canvas.height = 180;

    ctx.clearRect(0, 0, w, h);

    // Normalize data
    const returns = coneData.map(p => p.expected_return);
    const minR = Math.min(...returns);
    const maxR = Math.max(...returns);

    const scaleX = i => 20 + (i / (returns.length - 1)) * (w - 40);
    const scaleY = r => h / 2 - ((r - minR) / (maxR - minR)) * (h / 2 - 20);

    // Draw cone envelope
    ctx.beginPath();
    coneData.forEach((p, i) => ctx.lineTo(scaleX(i), scaleY(p.p95)));
    for (let i = coneData.length - 1; i >= 0; i--) {
        ctx.lineTo(scaleX(i), scaleY(coneData[i].p5));
    }
    ctx.closePath();

    const grad = ctx.createLinearGradient(0, 0, w, 0);
    grad.addColorStop(0, 'rgba(0,255,255,0.05)');
    grad.addColorStop(1, 'rgba(0,255,255,0.25)');
    ctx.fillStyle = grad;
    ctx.fill();

    // Median path
    ctx.beginPath();
    coneData.forEach((p, i) =>
        ctx.lineTo(scaleX(i), scaleY(p.expected_return))
    );
    ctx.strokeStyle = '#FF1493';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.font = '11px Inter, monospace';
    ctx.fillStyle = '#aaa';
    ctx.fillText('NOW', 10, h - 10);
    ctx.fillText('FUTURE DISTRIBUTION', w - 150, h - 10);
}

// Global Exports

window.showIntelligence = showIntelligence;

// ============================================================================
// SENTIMENT INTELLIGENCE RENDERING (LIVE)
// ============================================================================

function renderMarketSentiment() {
    const s = dashState.marketSentiment;
    if (!s) return;

    const container = document.getElementById('newsContent');
    if (!container) return;

    let sentimentHeader = document.getElementById('marketSentimentHeader');
    if (!sentimentHeader) {
        sentimentHeader = document.createElement('div');
        sentimentHeader.id = 'marketSentimentHeader';
        sentimentHeader.className = 'sentiment-dashboard';
        sentimentHeader.style.marginBottom = '1rem';
        sentimentHeader.innerHTML = `
        <div class="sentiment-card" style="display:flex; flex-direction:column; gap:1rem; background:rgba(0,0,0,0.3); padding:1rem; border-radius:8px;">
                <div style="display:flex; gap:1rem; align-items:center;">
                    <div style="text-align:center;">
                        <div style="color:var(--text-secondary); font-size:0.8em;">SENTIMENT</div>
                        <div class="sentiment-value" id="marketSentimentValue" style="font-size:1.5em; font-weight:bold;">—</div>
                    </div>
                    <div style="flex:1; text-align:center;">
                        <div style="color:var(--text-secondary); font-size:0.8em;">MOOD</div>
                        <div class="sentiment-label" id="marketSentimentLabel" style="font-size:1.2em; font-weight:bold;">ANALYZING</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="color:var(--text-secondary); font-size:0.8em;">SOURCES</div>
                        <div class="sentiment-meta" id="marketSentimentArticles">0</div>
                    </div>
                </div>
                
                <!-- Confidence heatmap -->
        <div class="confidence-heatmap" id="marketHeatmap" style="display:flex; gap:2px; height:8px; width:100%; margin-top:0.5rem; background:rgba(255,255,255,0.05); border-radius:4px; overflow:hidden;"></div>
        <div class="news-intel-quickbar" style="display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:0.75rem; margin-top:0.25rem;">
            <div><div style="color:var(--text-secondary); font-size:0.75em;">IAS</div><div id="marketIASValue" style="font-weight:700; color:var(--electric-cyan);">â€”</div></div>
            <div><div style="color:var(--text-secondary); font-size:0.75em;">Narrative</div><div id="marketNarrativeFocus" style="font-weight:700; color:var(--electric-pink);">â€”</div></div>
            <div><div style="color:var(--text-secondary); font-size:0.75em;">Next Event</div><div id="marketNextEvent" style="font-weight:700; color:var(--electric-yellow);">â€”</div></div>
            <div><div style="color:var(--text-secondary); font-size:0.75em;">Regime</div><div id="marketNewsRegime" style="font-weight:700; color:var(--electric-green);">â€”</div></div>
        </div>
            </div>
        `;
        container.insertBefore(sentimentHeader, container.firstChild);
    }

    const valEl = document.getElementById('marketSentimentValue');
    const labelEl = document.getElementById('marketSentimentLabel');
    const artsEl = document.getElementById('marketSentimentArticles');
    const heatmapEl = document.getElementById('marketHeatmap');
    const iasEl = document.getElementById('marketIASValue');
    const narrativeEl = document.getElementById('marketNarrativeFocus');
    const nextEventEl = document.getElementById('marketNextEvent');
    const regimeEl = document.getElementById('marketNewsRegime');

    // ✅ ARTICLES COUNT
    if (artsEl) artsEl.innerText = Number(s.total_articles || 0);

    // ✅ SCORE
    if (valEl && typeof s.overall_score === 'number') {
        valEl.innerText = `${s.overall_score.toFixed(1)}% `;
        valEl.style.color = s.overall_score > 60 ? 'var(--electric-green)' : s.overall_score < 40 ? 'var(--electric-red)' : 'var(--electric-yellow)';
    }

    // ✅ LABEL
    if (labelEl) {
        labelEl.innerText = s.label || 'NEUTRAL';
        labelEl.style.color = s.label === 'POSITIVE' ? 'var(--electric-green)' : s.label === 'NEGATIVE' ? 'var(--electric-red)' : 'var(--electric-yellow)';
    }

    // ✅ HEATMAP
    if (heatmapEl && Array.isArray(s.heatmap)) {
        heatmapEl.innerHTML = s.heatmap.map(h => `
        <div class="heatmap-bar ${h.sentiment}"
    style="width:${(h.confidence * 100)}%; background:${h.sentiment === 'positive' ? 'var(--electric-green)' : h.sentiment === 'negative' ? 'var(--electric-red)' : 'var(--text-secondary)'};"
    title = "${h.title} (${Math.round(h.confidence * 100)}%)">
            </div>
        `).join('');
    }

    if (iasEl) {
        const ias = Number(dashState?.infoAdvantage?.score);
        iasEl.textContent = Number.isFinite(ias) ? `${Math.round(ias * 100)}% ${humanizeToken(dashState?.infoAdvantage?.label)}` : 'â€”';
    }
    if (narrativeEl) {
        narrativeEl.textContent = humanizeToken(dashState?.newsIntelligence?.narrative_focus || dashState?.newsNarratives?.[0]?.label || 'None');
    }
    if (nextEventEl) {
        const nextEvent = dashState?.newsIntelligence?.next_market_event || {};
        nextEventEl.textContent = nextEvent.label ? `${nextEvent.label}: ${nextEvent.bias || '--'}` : 'â€”';
    }
    if (regimeEl) {
        regimeEl.textContent = humanizeToken(dashState?.newsIntelligence?.market_regime || 'Unknown');
    }
}


function renderNarrativeInsightBlock() {
    const narratives = Array.isArray(dashState.newsNarrativeMomentum) ? dashState.newsNarrativeMomentum.slice(0, 4) : [];
    if (!narratives.length) return '';
    return `
        <section class="news-intel-block">
            <h3 class="news-intel-title">Narrative Insights</h3>
            <div class="news-intel-grid">
                ${narratives.map((item) => `
                    <article class="news-intel-card">
                        <div class="news-intel-card-kicker">${escapeHtml(humanizeToken(item.momentum))}</div>
                        <div class="news-intel-card-title">${escapeHtml(item.label || 'Narrative')}</div>
                        <div class="news-intel-card-meta">Coverage ${Number(item.coverage || 0)} · Spread ${Number(item.spread || 0)}</div>
                        <div class="news-intel-card-score">${Math.round(Number(item.score || 0) * 100)}%</div>
                    </article>
                `).join('')}
            </div>
        </section>
    `;
}

function getRankedNewsArticles() {
    const articles = Array.isArray(dashState.news) ? dashState.news.slice() : [];
    const query = String(window.__NEWS_QUERY || '').trim().toLowerCase();
    return articles
        .filter((item) => item && item.title)
        .filter((item) => {
            if (!query) return true;
            const blob = [
                item?.title,
                item?.narrative,
                item?.event_type,
                item?.sector,
                ...(Array.isArray(item?.affected_sectors) ? item.affected_sectors : [])
            ].join(' ').toLowerCase();
            return blob.includes(query);
        })
        .sort((a, b) => {
            const impactA = Number(a?.impact_score ?? a?.impact_strength ?? 0);
            const impactB = Number(b?.impact_score ?? b?.impact_strength ?? 0);
            const freshA = Number(a?.freshness ?? 0);
            const freshB = Number(b?.freshness ?? 0);
            const relA = Number(a?.relevance ?? 0);
            const relB = Number(b?.relevance ?? 0);
            return (impactB - impactA) || (freshB - freshA) || (relB - relA);
        });
}

function renderNewsCompactCard(article) {
    const headline = escapeHtml(String(article?.title || 'Untitled'));
    const impact = Number(article?.impact_score ?? article?.impact_strength ?? 0);
    const sentimentScore = Number(article?.sentiment_score ?? 0);
    const sentimentText = String(article?.sentiment || 'neutral').toUpperCase();
    const sector = escapeHtml(String(article?.sector || article?.affected_sectors?.[0] || 'GENERAL'));
    const eventType = escapeHtml(humanizeToken(article?.event_type || 'GENERAL'));
    const publishedTime = formatNewsAge(article?.normalized_time || article?.published || article?.timestamp || '');
    const impactPct = Math.round(Math.max(0, Math.min(1, impact)) * 100);
    const sentimentColor = sentimentScore > 0.05 ? 'var(--electric-green)' : sentimentScore < -0.05 ? 'var(--electric-red)' : 'var(--electric-yellow)';
    const impactColor = impactPct >= 70 ? 'var(--electric-red)' : impactPct >= 40 ? 'var(--electric-yellow)' : 'var(--electric-cyan)';
    const href = escapeHtml(String(article?.url || '#'));

    return `
        <article class="news-intel-card" onclick="openNewsCard('${href}')" style="display:grid; gap:8px; cursor:${article?.url ? 'pointer' : 'default'};">
            <div style="display:flex; justify-content:space-between; gap:8px; align-items:flex-start;">
                <div style="color:var(--text-primary); font-weight:700; line-height:1.35;">${headline}</div>
                <div style="white-space:nowrap; color:${impactColor}; font-weight:800;">${impactPct}%</div>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:6px; font-size:10px;">
                <span class="prediction-badge" style="border-color:${impactColor}; color:${impactColor};">${eventType}</span>
                <span class="prediction-badge" style="border-color:${sentimentColor}; color:${sentimentColor};">${sentimentText}</span>
                <span class="prediction-badge" style="border-color:var(--electric-purple); color:var(--electric-purple);">${sector}</span>
                <span class="prediction-badge" style="border-color:rgba(255,255,255,0.18); color:var(--text-secondary);">${publishedTime}</span>
            </div>
        </article>
    `;
}

function renderTopImpactNewsBlock() {
    const topNews = getRankedNewsArticles().slice(0, 12);
    if (!topNews.length) return '';
    return `
        <section class="news-intel-block">
            <h3 class="news-intel-title">Top Impact News</h3>
            <div class="news-intel-grid">
                ${topNews.map(renderNewsCompactCard).join('')}
            </div>
        </section>
    `;
}

function renderSectorNewsBlock() {
    const sectorwise = dashState.newsSectorwise || {};
    const sectorEntries = Object.entries(sectorwise)
        .map(([sector, articles]) => {
            const rows = Array.isArray(articles) ? articles : [];
            const ranked = rows.slice().sort((a, b) => Number(b?.impact_score ?? 0) - Number(a?.impact_score ?? 0));
            const score = ranked.length ? ranked.reduce((sum, item) => sum + Number(item?.impact_score ?? 0), 0) / ranked.length : 0;
            return [sector, ranked, score];
        })
        .filter(([, rows]) => rows.length)
        .sort((a, b) => b[2] - a[2])
        .slice(0, 8);
    if (!sectorEntries.length) return '';
    return `
        <section class="news-intel-block">
            <h3 class="news-intel-title">Sector Impact Map</h3>
            <div class="news-intel-grid">
                ${sectorEntries.map(([sector, rows, score]) => `
                    <article class="news-intel-card">
                        <div class="news-intel-card-kicker">${escapeHtml(sector)}</div>
                        <div class="news-intel-card-title">${escapeHtml(rows[0]?.title || 'No active narrative')}</div>
                        <div class="news-intel-card-meta">${rows.length} mapped items · ${(score * 100).toFixed(0)}% avg impact</div>
                    </article>
                `).join('')}
            </div>
        </section>
    `;
}

function renderNewsCommandBar() {
    const total = getRankedNewsArticles().length;
    return `
        <section class="news-intel-block" style="padding:10px 12px;">
            <div style="display:flex; gap:10px; align-items:center; justify-content:space-between; flex-wrap:wrap;">
                <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                    <div class="search-box intel-ticker-search" style="min-width:280px;">
                        <i class="fas fa-search"></i>
                        <input type="text" id="newsImpactSearch" placeholder="Search headline, sector, event, narrative" value="${escapeHtml(String(window.__NEWS_QUERY || ''))}" />
                    </div>
                    <div style="font-size:11px; color:var(--text-secondary);">
                        ${total} live item${total === 1 ? '' : 's'} ranked by impact, freshness, and relevance
                    </div>
                </div>
                <div style="font-size:11px; color:var(--electric-cyan); font-weight:700;">
                    Hot flow: ${escapeHtml(humanizeToken(dashState?.newsIntelligence?.narrative_focus || dashState?.newsNarratives?.[0]?.label || 'Scanning'))}
                </div>
            </div>
        </section>
    `;
}

function renderPortfolioAlertsBlock() {
    const alerts = Array.isArray(dashState.portfolioNewsAlerts) ? dashState.portfolioNewsAlerts.slice(0, 6) : [];
    if (!alerts.length) return '';
    return `
        <section class="news-intel-block">
            <h3 class="news-intel-title">Portfolio Alerts</h3>
            <div class="news-alert-list">
                ${alerts.map((alert) => `
                    <div class="news-alert-row">
                        <div class="news-alert-symbols">${escapeHtml((alert.symbols || []).join(', '))}</div>
                        <div class="news-alert-headline">${escapeHtml(alert.headline || 'Portfolio narrative update')}</div>
                        <div class="news-alert-meta">${escapeHtml(humanizeToken(alert.event_type || 'General'))} · ${Math.round(Number(alert.impact_score || 0) * 100)}%</div>
                    </div>
                `).join('')}
            </div>
        </section>
    `;
}

function renderShockPropagationBlock() {
    // Cross-Market Shock space reallocated for additional news content
    return '';
}

function renderNews() {
    const container = document.getElementById('newsContent');
    if (!container) return;

    const loading = container.querySelector('.loading');
    if (loading) loading.remove();

    let list = document.getElementById('newsList');
    if (!list) {
        list = document.createElement('div');
        list.id = 'newsList';
        list.className = 'news-grid';
        list.style.display = 'grid';
        list.style.gap = '1rem';
        container.appendChild(list);
    }

    if (!Array.isArray(dashState.news) || dashState.news.length === 0) {
        list.innerHTML = `
            ${renderNewsCommandBar()}
            ${renderNarrativeInsightBlock()}
            ${renderPortfolioAlertsBlock()}
            ${renderShockPropagationBlock()}
        `;
        bindNewsSearch();
        return;
    }

    list.innerHTML = `
        <div class="news-intel-layout">
            ${renderNewsCommandBar()}
            ${renderTopImpactNewsBlock()}
            ${renderNarrativeInsightBlock()}
            ${renderSectorNewsBlock()}
            ${renderPortfolioAlertsBlock()}
            ${renderShockPropagationBlock()}
        </div>
    `;
    bindNewsSearch();
}

function bindNewsSearch() {
    const input = document.getElementById('newsImpactSearch');
    if (!input || input.dataset.bound === 'true') return;
    input.dataset.bound = 'true';
    input.addEventListener('input', (event) => {
        window.__NEWS_QUERY = event.target.value || '';
        renderNews();
    });
}

function openNewsCard(url) {
    const href = String(url || '').trim();
    if (!href || href === '#') return;
    window.open(href, '_blank', 'noopener,noreferrer');
}
window.openNewsCard = openNewsCard;

function _renderNewsCardLegacyUnused(article) {
    const publishedTime = article.normalized_time
        ? new Date(article.normalized_time).toLocaleString()
        : 'Time unknown';

    const glow = article.confidence_band
        ? `0 0 ${Math.round(article.confidence_band * 20)}px rgba(255, 165, 0, ${article.confidence_band})`
        : 'none';

    return `
        <div class="news-card"
    style="
    background: rgba(255, 255, 255, 0.05);
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow:${glow};
    ">

        <div class="news-header"
    style="display:flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
    font-size: 0.8em;
    color: var(--text-secondary); ">

        <span class="source"> ${article.source || ''}</span>
            <span class="time">${publishedTime}</span>
            </div>

        <h4 style="margin:0 0 0.5rem 0;">
            <a href="${article.url || '#'}"
                target="_blank"
                style="color:var(--text-primary);
                          text-decoration:none;">
                ${article.title || ''}
            </a>
        </h4>

            ${renderSentimentBar(
        article.sentiment_score != null
            ? Math.round((article.sentiment_score + 1) * 50)
            : null
    )
        }

            <div class="why-ai">
                AI Insight: ${article.why_it_matters || 'No further context available.'}
            </div>

            <div class="news-footer"
                 style="display:flex;
                        justify-content:space-between;
                        font-size:0.8em;">

                <span class="sentiment-badge"
                      style="color:${article.sentiment === 'positive'
            ? 'var(--electric-green)'
            : article.sentiment === 'negative'
                ? 'var(--electric-red)'
                : 'var(--text-secondary)'
        };">
                    ${(article.sentiment || 'neutral').toUpperCase()}
                </span>

                <span class="relevance">
                    Impact: ${article.confidence_band ?? '—'}
                </span>
            </div>
        </div>
        `;
}

function renderSentimentBar(score) {
    if (score == null) return '';

    return `
        <div class="sentiment-bar">
            <div class="fill"
                style="width:${score}%;
                        background:${score > 60 ? 'var(--electric-green)' :
            score < 40 ? 'var(--electric-red)' :
                'var(--electric-orange)'
        }">
            </div>
        </div>
        `;
}


async function loadSymbolSentiment(symbol) {
    if (!symbol) return;
    try {
        const data = await api.fetch(`/news/symbol/${symbol}`);
        if (!data || data.success === false || data.available === false) {
            console.log(`No sentiment available for ${symbol}`);
            return;
        }

        if (!dashState.symbolSentiment) dashState.symbolSentiment = {};

        // Store the sentiment data
        dashState.symbolSentiment[symbol] = data;

        renderSymbolSentiment(symbol, data);
    } catch (e) {
        console.error(`Symbol sentiment error for ${symbol}: `, e);
    }
}

// 🔁 Ensure global news + sentiment intelligence is available
if (!dashState.news || !dashState.marketSentiment) {
    loadNews(); // live intelligence, already cached & rate-safe
}


function renderSymbolSentiment(symbol, data) {
    const s = data.sentiment;
    if (!s || s.overall_score == null) return;

    const modalBody = document.getElementById('modalBody');
    if (!modalBody) return;

    let section = document.getElementById('symbolSentimentSection');
    if (!section) {
        section = document.createElement('div');
        section.id = 'symbolSentimentSection';
        section.className = 'analysis-section';
        modalBody.appendChild(section);
    }

    section.innerHTML = `
        <h3 > Market Sentiment</h3>
        <div class="detail-row">
            <span>News Sentiment</span>
            <span class="${s.overall_score > 60 ? 'positive' : s.overall_score < 40 ? 'negative' : ''}">
                ${s.overall_score.toFixed(1)}%
            </span>
        </div>
        <div class="detail-row">
            <span>Mood</span>
            <span>${s.label}</span>
        </div>
        <div class="detail-row">
            <span>Articles</span>
            <span>${s.total_articles}</span>
        </div>
        <div class="detail-row">
            <span>Updated</span>
            <span>${new Date(s.timestamp).toLocaleTimeString()}</span>
        </div>
    `;
}

// ============================================================================
// CANONICAL ANALYSIS → INTELLIGENCE ORCHESTRATION
// ============================================================================

if (typeof showStockDetails === 'function') {
    const originalShowStockDetails = showStockDetails;

    window.showStockDetails = async function (symbol) {
        // 1️⃣ Always show detailed analysis first
        await originalShowStockDetails(symbol);

        // 2️⃣ Then trigger intelligence cockpit
        if (typeof showIntelligence === 'function') {
            showIntelligence(symbol);
        }

        // 3️⃣ Symbol sentiment is already wired inside displayDetailedAnalysis
        // ❌ DO NOT call loadSymbolSentiment here (avoid duplication)
    };
}

// ============================================================================
// GLOBAL LOADER MANAGEMENT
// ============================================================================

function updateLoader(progress, status) {
    const progressEl = document.getElementById('globalLoaderProgress');
    const statusEl = document.getElementById('globalLoaderStatus');
    if (progressEl) progressEl.style.width = progress + '%';
    if (statusEl) statusEl.innerText = status;
}

function hideLoader() {
    const loader = document.getElementById('globalLoader');
    if (loader && loader.dataset.loaderHidden !== '1') {
        loader.dataset.loaderHidden = '1';
        loader.style.transition = 'opacity 0.8s ease, visibility 0.8s';
        loader.style.opacity = '0';
        setTimeout(() => {
            loader.style.visibility = 'hidden';
            loader.style.display = 'none';
            loader.classList.add('hidden');
            console.log("🧠 Neural Interface Synced (Loader Hidden)");
        }, 800);
    }
}

// Loader integration hook - call from initialize()
function integrateLoaderSequence() {
    if (window.__LOADER_SEQUENCE_STARTED) return;
    window.__LOADER_SEQUENCE_STARTED = true;

    updateLoader(20, "Establishing Neural Link...");

    setTimeout(() => updateLoader(40, "Loading Market Intelligence..."), 400);
    setTimeout(() => updateLoader(60, "Syncing 28 Neural Engines..."), 800);
    setTimeout(() => updateLoader(80, "Calibrating Quantum Predictions..."), 1200);
    setTimeout(() => {
        updateLoader(100, "Deep Restoration Complete");
    }, 1800);
}

// Auto-start loader - guard: app.js loads at bottom of body so DOMContentLoaded may have already fired
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', integrateLoaderSequence);
} else {
    integrateLoaderSequence();
}

// ============================================================================
// PROFESSIONAL COCKPIT - RESEARCH AI TAB
// ============================================================================

let cockpitChart = null;
let cockpitSymbol = null;
let cockpitTimeUpdater = null;

// ========================================================
// SEARCH COCKPIT SYMBOL - User can search any stock
// ========================================================
function searchCockpitSymbol() {
    const searchInput = document.getElementById('cockpitSearchInput');
    if (!searchInput) return;

    let symbol = searchInput.value.trim().toUpperCase();
    if (!symbol) {
        alert('Please enter a stock symbol');
        return;
    }

    // Auto-append .NS for Indian stocks if not present
    if (!symbol.includes('.')) {
        symbol = symbol + '.NS';
    }

    console.log(`🔍 Searching for symbol: ${symbol} `);

    // Show loading state
    safeSet('cockpitSymbol', symbol.replace('.NS', '').replace('.BO', ''));
    safeSet('cockpitPrice', 'Loading...');
    safeSet('cockpitChange', '...');

    // Load data for the searched symbol
    loadCockpitData(symbol);

    // Clear search input
    searchInput.value = '';
}

// Make searchCockpitSymbol globally available
window.searchCockpitSymbol = searchCockpitSymbol;

// Update session badge (AM/PM/PRE/POST)
function updateSessionBadge() {
    const sessionEl = document.getElementById('cockpitSession');
    if (!sessionEl) return;

    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const time = hours * 60 + minutes;

    // Indian market hours (9:15 AM to 3:30 PM IST)
    const marketOpen = 9 * 60 + 15;  // 9:15 AM
    const marketMid = 12 * 60 + 30;  // 12:30 PM
    const marketClose = 15 * 60 + 30; // 3:30 PM

    let session = 'CLOSED';
    if (time >= marketOpen && time < marketMid) {
        session = 'AM';
    } else if (time >= marketMid && time < marketClose) {
        session = 'PM';
    } else if (time >= 9 * 60 && time < marketOpen) {
        session = 'PRE';
    } else if (time >= marketClose && time < 16 * 60) {
        session = 'POST';
    }

    sessionEl.textContent = session;
}


// Load cockpit data from evolved prediction API
async function loadCockpitData(symbol) {
    cockpitSymbol = symbol;
    console.log(`🔬 Loading Research Cockpit for: ${symbol} `);

    try {
        const response = await api.fetch(`/evolved-prediction/${encodeURIComponent(symbol)}`);

        if (response && response.prediction) {
            populateCockpit(response.prediction, response);
        } else if (response) {
            populateCockpit(response, response);
        }
    } catch (error) {
        console.error('Cockpit data load failed:', error);
        // Still populate with what we have from dashState
        populateCockpitFromDashboard(symbol);
    }
}

// Load dashboard-level data for cockpit left panel
async function loadCockpitDashboardData() {
    // Use existing dashState data
    if (dashState.dashboard) {
        populateCockpitSectors(dashState.dashboard);
    }
    if (dashState.predictions) {
        populateCockpitSignals(dashState.predictions);
    }
}

// Populate cockpit with evolved prediction data
function populateCockpit(prediction, fullResponse) {
    console.log('📊 Populating cockpit with prediction data');

    // Header
    safeSet('cockpitSymbol', prediction.symbol || cockpitSymbol);
    safeSet('cockpitPrice', `₹${formatNumber(prediction.current_price || prediction.price || 0)} `);

    const change = prediction.predicted_change || prediction.change_percent || 0;
    const changeEl = document.getElementById('cockpitChange');
    if (changeEl) {
        changeEl.textContent = `${change >= 0 ? '+' : ''}${formatNumber(change)}% `;
        changeEl.className = `cockpit - change ${change >= 0 ? 'positive' : 'negative'} `;
    }

    safeSet('cockpitExchange', prediction.exchange || 'NSE');
    safeSet('cockpitChartTitle', prediction.symbol || cockpitSymbol);

    // Confidence
    const confidence = prediction.confidence_adjusted || prediction.confidence || prediction.overall_confidence || 0;
    safeSet('cockpitConfidence', `${formatNumber(confidence * 100)}% `);
    safeSet('cockpitConfidenceLabel', getConfidenceLabel(confidence));
    safeSet('cockpitSignal', prediction.final_action || prediction.signal || 'ANALYZING');

    // Evolution
    safeSet('cockpitEvolutionTrend', `↑ ${formatNumber(confidence * 100)}% `);
    const evolutionPath = document.getElementById('cockpitEvolutionPath');
    if (evolutionPath) evolutionPath.style.width = `${confidence * 100}% `;

    // Probability Cone - Futures
    if (prediction.futures) {
        const futures = prediction.futures;
        safeSet('cockpitUpside', `↑ ${formatNumber(futures.upside_potential || futures.p95 || 0)}% `);
        safeSet('cockpitTarget', `₹${formatNumber(futures.target_price || prediction.current_price || 0)} `);
        safeSet('cockpitDownside', `↓ ${formatNumber(futures.downside_risk || futures.p5 || 0)}% `);
    }

    // AI Market Memory
    if (prediction.ai_market_memory || prediction.market_memory) {
        const memory = prediction.ai_market_memory || prediction.market_memory;
        safeSet('cockpitRecallRate', `${formatNumber(memory.recall_rate || memory.pattern_recall || 0)}% `);
        safeSet('cockpitInstances', memory.total_instances || memory.matches || '--');
        safeSet('cockpitSuccessRate', memory.success_rate || memory.hit_rate || '--');
        safeSet('cockpitAccuracy', memory.accuracy_label || 'Advanced');
    }

    // Regime Timeline
    populateCockpitRegime(prediction);

    // 28 Neural Engines
    populateCockpitEngines(prediction);

    // Risk Chart
    populateCockpitRisk(prediction);

    // AI Reasoning Console
    if (prediction.ai_reasoning || prediction.reasoning) {
        safeSet('cockpitAIReasoning', prediction.ai_reasoning || prediction.reasoning);
        safeSet('cockpitAIConsole', prediction.ai_reasoning || prediction.reasoning);
        safeSet('cockpitAIStrategy', prediction.ai_reasoning || prediction.reasoning);
        safeSet('cockpitConsoleText', (prediction.ai_reasoning || prediction.reasoning).substring(0, 50) + '...');
    }

    // Alerts
    populateCockpitAlerts(prediction);

    // Correlated Assets
    populateCorrelatedAssets(prediction);

    // Draw chart
    drawCockpitChart(prediction);
}

// Fallback: populate from dashboard data
function populateCockpitFromDashboard(symbol) {
    const stock = dashState.stocks?.find(s => s.symbol === symbol || s.ticker === symbol);
    if (stock) {
        safeSet('cockpitSymbol', stock.symbol || stock.ticker);
        safeSet('cockpitPrice', `₹${formatNumber(stock.current_price || stock.ltp || 0)} `);
        safeSet('cockpitChange', `${formatNumber(stock.change_percent || 0)}% `);
    }
}

// Populate 28 Neural Engines
function populateCockpitEngines(prediction) {
    const container = document.getElementById('cockpitEngines');
    if (!container) return;

    // Define 28 engines and their data mappings
    const engines = [
        { label: 'Emotional', key: 'emotional_state.emotion', getValue: p => p.emotional_state?.emotion || p.emotion || 'NEUTRAL' },
        { label: 'Confidence', key: 'confidence', getValue: p => `${formatNumber((p.confidence_adjusted || p.confidence || 0) * 100)}% ` },
        { label: 'Futures', key: 'futures_mode', getValue: p => p.futures?.mode || 'MULTIWORLD' },
        { label: 'Governance', key: 'governance', getValue: p => p.governance?.approved ? 'APPROVE' : 'PENDING' },
        { label: 'Memory', key: 'memory', getValue: p => p.ai_market_memory ? 'RECALL' : 'READY' },
        { label: 'Contagion', key: 'contagion', getValue: p => p.contagion?.level || 'LOW' },
        { label: 'Regime', key: 'regime', getValue: p => p.emotional_state?.regime || p.regime || 'STABLE' },
        { label: 'Momentum', key: 'momentum', getValue: p => p.momentum?.signal || 'NEUTRAL' },
        { label: 'RSI', key: 'rsi', getValue: p => formatNumber(p.technical_indicators?.rsi || p.rsi || 50) },
        { label: 'MACD', key: 'macd', getValue: p => p.technical_indicators?.macd?.signal || 'NEUTRAL' },
        { label: 'Volatility', key: 'volatility', getValue: p => p.volatility?.level || 'NORMAL' },
        { label: 'Trend', key: 'trend', getValue: p => p.trend?.direction || 'SIDEWAYS' },
        { label: 'Support', key: 'support', getValue: p => `₹${formatNumber(p.support || p.key_levels?.support || 0)} ` },
        { label: 'Resistance', key: 'resistance', getValue: p => `₹${formatNumber(p.resistance || p.key_levels?.resistance || 0)} ` },
        { label: 'Risk Score', key: 'risk', getValue: p => formatNumber((p.global_risk?.composite || 0) * 100) + '%' },
        { label: 'Greed Index', key: 'greed', getValue: p => formatNumber(p.emotional_state?.greed_index || 50) },
        { label: 'Fear Index', key: 'fear', getValue: p => formatNumber(p.emotional_state?.fear_index || 50) },
        { label: 'Pattern', key: 'pattern', getValue: p => p.pattern_recognition?.primary || 'SCANNING' },
        { label: 'Volume', key: 'volume', getValue: p => p.volume?.signal || 'NORMAL' },
        { label: 'Liquidity', key: 'liquidity', getValue: p => p.liquidity?.level || 'ADEQUATE' },
        { label: 'Sector', key: 'sector', getValue: p => p.sector_strength || 'NEUTRAL' },
        { label: 'Market Sync', key: 'market_sync', getValue: p => p.market_correlation || 'SYNCED' },
        { label: 'LSTM', key: 'lstm', getValue: p => p.model_health?.lstm || 'ACTIVE' },
        { label: 'XGBoost', key: 'xgboost', getValue: p => p.model_health?.xgboost || 'ACTIVE' },
        { label: 'Ensemble', key: 'ensemble', getValue: p => p.model_health?.ensemble || 'ACTIVE' },
        { label: 'News Pulse', key: 'news', getValue: p => p.sentiment?.news || 'NEUTRAL' },
        { label: 'Social', key: 'social', getValue: p => p.sentiment?.social || 'NEUTRAL' },
        { label: 'Final Action', key: 'action', getValue: p => p.final_action || 'HOLD' }
    ];

    let html = '';
    engines.forEach((engine, idx) => {
        const value = engine.getValue(prediction);
        const isActive = value && value !== '--' && value !== 'NEUTRAL' && value !== '0%';
        html += `
        <div class="neural-card${isActive ? ' active' : ''}">
                <div class="neural-label">${engine.label}</div>
                <div class="neural-value">${value}</div>
                <div class="neural-status">${isActive ? 'LIVE' : 'READY'}</div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Populate Regime Timeline
function populateCockpitRegime(prediction) {
    const bar = document.getElementById('cockpitRegimeBar');
    if (!bar) return;

    const regimes = prediction.regime_history || [
        { type: 'ranging', label: 'RANGING', weight: 15 },
        { type: 'trending', label: 'TRENDING', weight: 45 },
        { type: 'volatility', label: 'HIGH VOL', weight: 25 },
        { type: 'trending', label: 'TRENDING', weight: 15 }
    ];

    bar.innerHTML = regimes.map(r => `
        <div class="regime-segment ${r.type}" style="flex: ${r.weight};">
            <span>${r.label}</span>
        </div>
        `).join('');
}

// Populate Risk Chart
function populateCockpitRisk(prediction) {
    const chart = document.getElementById('cockpitRiskChart');
    if (!chart) return;

    const risks = prediction.global_risk || { market: 0.3, volatility: 0.5, liquidity: 0.4, sector: 0.35, model: 0.25 };
    const riskValues = Object.values(risks).slice(0, 5);

    chart.innerHTML = riskValues.map((v, i) => `
        <div class="risk-bar" style="height: ${(v || 0.3) * 100}%;"></div>
            `).join('');
}

// Populate Alerts
function populateCockpitAlerts(prediction) {
    const container = document.getElementById('cockpitAlerts');
    if (!container) return;

    const alerts = prediction.alerts || [
        { text: 'Neural engines active', time: 'Now' },
        { text: 'Pattern recognition running', time: '5m ago' },
        { text: 'Market sync complete', time: '10m ago' }
    ];

    container.innerHTML = alerts.slice(0, 3).map(a => `
            <div class="alert-item warning">
            <strong>${a.text || a.message}</strong>
            <div class="alert-time">${a.time || 'Recent'}</div>
        </div>
        `).join('');
}

// Populate Sectors from dashboard - Dynamic sector trends
function populateCockpitSectors(dashboard) {
    const container = document.getElementById('cockpitSectors');
    if (!container) return;

    // Get sector data from dashboard or generate from market data
    const sectorData = dashboard?.sectors || dashboard?.sector_performance;

    // Map to display format matching target design
    const sectors = [
        { name: 'Tech', value: sectorData?.tech?.change || sectorData?.Technology?.avg_return || calculateSectorStrength('tech') },
        { name: 'Finance', value: sectorData?.finance?.change || sectorData?.Financial?.avg_return || calculateSectorStrength('finance') },
        { name: 'Energy', value: sectorData?.energy?.change || sectorData?.Energy?.avg_return || calculateSectorStrength('energy') },
        { name: 'Industrial', value: sectorData?.industrial?.change || sectorData?.Industrial?.avg_return || calculateSectorStrength('industrial') }
    ];

    container.innerHTML = sectors.map(s => {
        const value = parseFloat(s.value) || 0;
        const absVal = Math.abs(value);
        const barWidth = Math.min(absVal * 2, 100); // Scale: 50% market move = 100% bar
        return `
        <div class="sector-item">
                <span class="sector-name">${s.name}</span>
                <div class="sector-bar-container">
                    <div class="sector-bar${value < 0 ? ' negative' : ''}" style="width: ${barWidth}%;"></div>
                </div>
                <span class="sector-percent">${value >= 0 ? '+' : ''}${formatNumber(value)}%</span>
            </div>
        `;
    }).join('');
}

// Populate AI Signals from predictions
function populateCockpitSignals(predictions) {
    const container = document.getElementById('cockpitSignals');
    if (!container) return;

    let buyCount = 0, holdCount = 0, sellCount = 0;
    const preds = Array.isArray(predictions) ? predictions : predictions?.predictions || [];

    preds.forEach(p => {
        const signal = (p.final_action || p.signal || 'HOLD').toUpperCase();
        if (signal === 'BUY' || signal === 'STRONG BUY') buyCount++;
        else if (signal === 'SELL' || signal === 'STRONG SELL') sellCount++;
        else holdCount++;
    });

    const total = buyCount + holdCount + sellCount || 1;
    const buyPct = Math.round((buyCount / total) * 100);
    const holdPct = Math.round((holdCount / total) * 100);
    const sellPct = Math.round((sellCount / total) * 100);

    container.innerHTML = `
        <div class="signal-item">
            <div class="signal-label"><i class="fas fa-arrow-up"></i> BUY</div>
            <div class="signal-bar"><div class="signal-fill" style="width: ${buyPct}%;"></div></div>
            <div class="signal-count">${buyCount}</div>
            <div class="signal-percent">${buyPct}%</div>
        </div>
        <div class="signal-item">
            <div class="signal-label"><i class="fas fa-pause"></i> HOLD</div>
            <div class="signal-bar"><div class="signal-fill" style="width: ${holdPct}%; background: var(--accent-blue);"></div></div>
            <div class="signal-count">${holdCount}</div>
            <div class="signal-percent">${holdPct}%</div>
        </div>
        <div class="signal-item">
            <div class="signal-label"><i class="fas fa-arrow-down"></i> SELL</div>
            <div class="signal-bar"><div class="signal-fill" style="width: ${sellPct}%; background: var(--accent-red);"></div></div>
            <div class="signal-count">${sellCount}</div>
            <div class="signal-percent">${sellPct}%</div>
        </div>
    `;
}

// Draw cockpit main chart
function drawCockpitChart(prediction) {
    const canvas = document.getElementById('cockpitMainChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Destroy existing chart
    if (cockpitChart) {
        cockpitChart.destroy();
    }

    // Use only real price history supplied by the model or API.
    const priceHistory = Array.isArray(prediction.price_history) && prediction.price_history.length
        ? prediction.price_history
        : Array.isArray(prediction.history) && prediction.history.length
            ? prediction.history
            : [];
    if (!priceHistory.length) {
        return;
    }

    cockpitChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: priceHistory.map((_, i) => `D${i + 1} `),
            datasets: [{
                label: 'Price',
                data: priceHistory,
                borderColor: '#00ffff',
                backgroundColor: 'rgba(0, 255, 255, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    display: false
                },
                y: {
                    display: true,
                    grid: { color: 'rgba(0, 255, 255, 0.1)' },
                    ticks: { color: '#8b949e' }
                }
            }
        }
    });
}

// Real-history fallback intentionally returns no synthetic series.
function generatePriceData(basePrice) {
    return [];
}

// Helper functions
function safeSet(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '--';
    return parseFloat(num).toFixed(2);
}

function getConfidenceLabel(confidence) {
    if (confidence >= 0.7) return 'HIGH CONFIDENCE';
    if (confidence >= 0.5) return 'CONFIDENT';
    if (confidence >= 0.3) return 'MODERATE';
    return 'LOW CONFIDENCE';
}

// Calculate sector strength dynamically from dashboard stocks
function calculateSectorStrength(sectorName) {
    if (!dashState.stocks || dashState.stocks.length === 0) {
        // Return reasonable defaults based on sector
        const defaults = { tech: 35, finance: 28, energy: 22, industrial: 15 };
        return defaults[sectorName] || 20;
    }

    // Map sector names to stock symbols
    const sectorStocks = {
        tech: ['TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM'],
        finance: ['HDFCBANK', 'ICICIBANK', 'KOTAKBANK', 'AXISBANK', 'SBIN'],
        energy: ['RELIANCE', 'ONGC', 'NTPC', 'POWERGRID', 'COALINDIA'],
        industrial: ['LT', 'BHARTIARTL', 'ADANIENT', 'ULTRACEMCO', 'BAJFINANCE']
    };

    const stocks = sectorStocks[sectorName] || [];
    let totalChange = 0;
    let count = 0;

    stocks.forEach(sym => {
        const stock = dashState.stocks.find(s =>
            s.symbol?.includes(sym) || s.ticker?.includes(sym)
        );
        if (stock && stock.change_percent !== undefined) {
            totalChange += parseFloat(stock.change_percent) || 0;
            count++;
        }
    });

    return count > 0 ? (totalChange / count * 10) : 0;
}

// Populate Correlated Assets circles
function populateCorrelatedAssets(prediction) {
    const container = document.getElementById('cockpitCorrelations');
    if (!container) return;

    const correlations = prediction?.correlations || prediction?.correlated_assets || [];

    container.innerHTML = correlations.slice(0, 3).map(c => `
        <div class="correlation-circle" style="--circle-color: ${c.color || '#00ffff'};">
            <span class="correlation-value">${c.value}%</span>
            <span class="correlation-name">${c.name}</span>
        </div>
        `).join('');
}

// Wire Research AI tab click to open cockpit
document.addEventListener('DOMContentLoaded', () => {
    console.log('✅ app.js lifecycle hooks active');
    // REMOVED global fetchCognition() - logic moved to startCognitionStream()
});

// ============================================================================
// AI COGNITIVE PANEL (Backend-Driven Display)
// ============================================================================

// Lifecycle Management
let cognitionSocket = null;
let cognitionConnectHandler = null;
let cognitionUpdateHandler = null;

function startCognitionStream() {
    const now = Date.now();
    if (window.__COG_LAST_ACTION === 'start' && (now - Number(window.__COG_LAST_ACTION_AT || 0)) < 2500) return;
    if (cognitionSocket) return;
    window.__COG_LAST_ACTION = 'start';
    window.__COG_LAST_ACTION_AT = now;

    if (CONFIG.DEBUG_MODE) console.log('🧠 Starting Cognition Stream...');

    // Connect to dedicated namespace if backend supports it, or default
    // Using default namespace as per user instruction "socketio.emit('cognition_update', ..., namespace='/ws')" 
    // Wait, user said namespace='/ws' in backend instruction? 
    // "socketio.emit("cognition_update", cognition_state, namespace="/ws")"
    // So frontend should connect to '/ws'

    // Use consolidated window.NEXUS_SOCKET
    cognitionSocket = window.NEXUS_SOCKET;
    cognitionConnectHandler = () => {
        console.log('🧠 Cognition Linked');
    };
    cognitionSocket.on('connect', cognitionConnectHandler);

    cognitionUpdateHandler = (state) => {
        window.AI_COGNITION = state; // Cache for other tabs
        renderCognitivePanel(state);
    };
    cognitionSocket.on('cognition_update', cognitionUpdateHandler);

    // Initial fetch to populate immediately
    api.fetch('/system/cognition', { cache: false, timeout: Math.max(1, Math.floor(CONFIG.TIMEOUT * 0.5)) })
        .then(json => {
            // Handle both wrapped {success: true, data: ...} and direct object
            const data = (json.success && json.data) ? json.data : json;
            if (data && (data.opportunities || data.market_state)) {
                window.AI_COGNITION = data; // Cache initial load
                renderCognitivePanel(data);
            } else {
                renderCognitivePanel(buildCognitiveFallbackState(window.NEURAL_STATE || {}));
            }
        })
        .catch(e => {
            console.error('Initial cognition fetch failed:', e);
            renderCognitivePanel(buildCognitiveFallbackState(window.NEURAL_STATE || {}));
        });
}

function stopCognitionStream() {
    const now = Date.now();
    if (window.__COG_LAST_ACTION === 'stop' && (now - Number(window.__COG_LAST_ACTION_AT || 0)) < 2500) return;
    if (!cognitionSocket) return;
    window.__COG_LAST_ACTION = 'stop';
    window.__COG_LAST_ACTION_AT = now;
    if (CONFIG.DEBUG_MODE) console.log('🧠 Stopping Cognition Stream...');
    if (cognitionConnectHandler) cognitionSocket.off('connect', cognitionConnectHandler);
    if (cognitionUpdateHandler) cognitionSocket.off('cognition_update', cognitionUpdateHandler);
    cognitionConnectHandler = null;
    cognitionUpdateHandler = null;
    cognitionSocket = null;
}


function buildCognitiveFallbackState(state) {
    const predictions = Array.isArray(dashState.predictions) ? dashState.predictions : [];
    const marketSentiment = dashState.marketSentiment || {};
    const systemConfidence = predictions.length
        ? predictions.reduce((sum, row) => sum + Number(row?.confidence ?? row?.confidences15d ?? row?.prediction?.confidence ?? 0), 0) / predictions.length
        : Number(state?.ai_performance?.prediction_accuracy || 0);

    const opportunities = predictions
        .slice()
        .sort((a, b) => Number(b?.opportunity_score ?? b?.reliability_score ?? b?.confidence ?? 0) - Number(a?.opportunity_score ?? a?.reliability_score ?? a?.confidence ?? 0))
        .slice(0, 10)
        .map((row, index) => {
            const signal = String(row?.decision || row?.signal || row?.ai_signal || row?.prediction?.signal || 'HOLD').toUpperCase();
            return {
                rank: index + 1,
                symbol: String(row?.symbol || '').replace('.NS', '').replace('.BO', ''),
                edge: `${Number(row?.predicted_return ?? row?.prediction?.predicted_return ?? 0).toFixed(2)}%`,
                agreement: Math.max(0, Math.min(1, Number(row?.reliability_score ?? 0) / 100)),
                risk: Number(row?.volatility ?? row?.prediction?.volatility ?? 0).toFixed(2),
                allocation_pct: Number(row?.ai_size ?? row?.ai_size_pct ?? 0).toFixed(1),
                action: signal
            };
        });

    const consensus = opportunities.slice(0, 5).map((item) => ({
        symbol: item.symbol,
        direction: /BUY|ENTER|ADD/.test(item.action) ? 'UP' : /SELL|EXIT|REDUCE/.test(item.action) ? 'DOWN' : 'FLAT',
        agreement: item.agreement,
        confidence: Math.round(item.agreement * 100)
    }));

    return {
        market_state: {
            regime: state?.ai_engine?.regime || state?.market_state?.regime || document.getElementById('marketRegimeValue')?.textContent?.trim() || 'UNKNOWN',
            volatility: Number(state?.ai_engine?.volatility ?? state?.market_state?.volatility ?? 0).toFixed(2),
            ai_mode: state?.ai_mode || state?.market_state?.ai_mode || '--',
            system_confidence: Number(systemConfidence || 0).toFixed(1)
        },
        consensus,
        opportunities,
        market_sentiment: marketSentiment
    };
}


function renderCognitivePanel(state) {
    const container = document.getElementById('aiCognitivePanel');
    if (!container) return;

    const effectiveState = (state && state.market_state) ? state : buildCognitiveFallbackState(window.NEURAL_STATE || {});
    if (!effectiveState || !effectiveState.market_state) {
        container.innerHTML = '<div class="panel-loading">Live intelligence is syncing...</div>';
        return;
    }

    // Module 1: Signal Consensus
    const consensusRows = effectiveState.consensus ? effectiveState.consensus.slice(0, 5).map(item => `
        <tr >
            <td style="color:var(--text-primary); font-weight:700;">${item.symbol}</td>
            <td style="color:${item.direction === 'UP' ? 'var(--electric-green)' : item.direction === 'DOWN' ? 'var(--electric-red)' : 'var(--text-secondary)'}">${item.direction}</td>
            <td>
                <div class="agreement-bar">
                    <div class="agreement-fill" style="width:${item.agreement * 100}%"></div>
                </div>
            </td>
            <td style="text-align:right;">${item.confidence}%</td>
        </tr>
        `).join('') : '';

    const module1 = `
        <div class="cog-module">
            <div class="cog-header">
                <span class="cog-title">Signal Consensus</span>
                <i class="fas fa-network-wired" style="color:var(--electric-cyan); font-size:10px;"></i>
            </div>
            <table class="consensus-table">
                <thead>
                    <tr>
                        <th>Asset</th>
                        <th>Dir</th>
                        <th>Agree</th>
                        <th style="text-align:right;">Conf</th>
                    </tr>
                </thead>
                <tbody>
                    ${consensusRows}
                </tbody>
            </table>
        </div>
        `;

    // Module 2: Market State Engine
    const ms = effectiveState.market_state;
    const regimeColor = ms.regime.includes('BULL') ? 'var(--electric-green)' :
        ms.regime.includes('VOLATILE') ? 'var(--electric-yellow)' :
            ms.regime.includes('STABLE') ? 'var(--electric-blue)' : 'var(--electric-purple)';

    const module2 = `
        <div class="cog-module">
            <div class="cog-header">
                <span class="cog-title">Market State Engine</span>
                <i class="fas fa-microchip" style="color:var(--electric-pink); font-size:10px;"></i>
            </div>
            <div class="state-grid">
                <div class="state-metric">
                    <div class="state-label">Regime</div>
                    <div class="state-value" style="color:${regimeColor}; font-size:11px;">${ms.regime.replace('_', ' ')}</div>
                </div>
                <div class="state-metric">
                    <div class="state-label">Volatility</div>
                    <div class="state-value" style="color:var(--electric-yellow);">${ms.volatility}%</div>
                </div>
                <div class="state-metric">
                    <div class="state-label">AI Mode</div>
                    <div class="state-value" style="color:var(--electric-cyan);">${ms.ai_mode}</div>
                </div>
                <div class="state-metric">
                    <div class="state-label">Sys Conf</div>
                    <div class="state-value" style="color:var(--electric-green);">${ms.system_confidence}%</div>
                </div>
            </div>
        </div>
        `;

    // Module 3: Opportunity Radar
    const oppRows = effectiveState.opportunities ? effectiveState.opportunities.slice(0, 10).map(opp => `
        <div class="opp-row action-${opp.action}" style="display: grid; grid-template-columns: 0.4fr 0.8fr 0.8fr 0.8fr 0.8fr 0.8fr 0.6fr; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
            <div class="opp-rank" style="color:var(--text-secondary); font-size:10px;">#${opp.rank}</div>
            <div class="opp-symbol" style="font-weight:bold; color:var(--text-primary);">${opp.symbol}</div>
            <div class="opp-edge" style="color:var(--electric-cyan);">${opp.edge}</div>
            <div class="opp-agree" style="color:${opp.agreement > 0.7 ? 'var(--electric-green)' : 'var(--electric-purple)'};">${(opp.agreement * 100).toFixed(0)}%</div>
            <div class="opp-risk" style="color:${opp.risk > 50 ? 'var(--electric-red)' : 'var(--text-secondary)'};">${opp.risk}</div>
            <div class="opp-alloc" style="color:${opp.allocation_pct > 5 ? 'var(--electric-green)' : opp.allocation_pct > 1 ? 'var(--electric-yellow)' : 'var(--text-secondary)'}; font-weight:bold;">${opp.allocation_pct}%</div>
            <div class="opp-action action-${opp.action}" style="text-align:right; font-weight:bold;">${opp.action}</div>
        </div>
        `).join('') : '';

    const module3 = `
        <div class="cog-module">
            <div class="cog-header">
                <span class="cog-title">Opportunity Radar</span>
                <i class="fas fa-crosshairs" style="color:var(--electric-green); font-size:10px;"></i>
            </div>
            <div class="opp-header" style="display: grid; grid-template-columns: 0.4fr 0.8fr 0.8fr 0.8fr 0.8fr 0.8fr 0.6fr; color:var(--text-secondary); font-size:10px; padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <div>Rank</div>
                <div>Asset</div>
                <div>Edge</div>
                <div>Agree</div>
                <div>Risk</div>
                <div>Alloc%</div>
                <div style="text-align:right;">Action</div>
            </div>
            <div class="opp-list">
                ${oppRows}
            </div>
        </div>
        `;

    container.innerHTML = module1 + module2 + module3;
}
