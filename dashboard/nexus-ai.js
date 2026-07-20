/**
 * ╔══════════════════════════════════════════════════════════╗
 * ║  NEXUS AI QUANTUM  |  nexus-ai.js  |  v5 FINAL         ║
 * ╠══════════════════════════════════════════════════════════╣
 * ║  API – wire your model in one call:                     ║
 * ║  window.NexusAPI.refresh({ ...data })                   ║
 * ╚══════════════════════════════════════════════════════════╝
 */
'use strict';

/* ── Chart.js global defaults ── */
Chart.defaults.color = '#888890';
Chart.defaults.font.family = 'Inter, sans-serif';
Chart.defaults.font.size = 10.5;
Chart.defaults.plugins.legend.display = false;
Chart.defaults.plugins.tooltip.backgroundColor = '#1c1c22';
Chart.defaults.plugins.tooltip.titleColor = '#4fd1c5';
Chart.defaults.plugins.tooltip.bodyColor = '#e2e2e4';
Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.08)';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.cornerRadius = 6;
Chart.defaults.plugins.tooltip.padding = 8;
Chart.defaults.plugins.tooltip.displayColors = false;

const C = {};  // chart registry

/* ══ STATE UTILITIES ══ */
function isNonEmptyObject(value) {
  return !!value && typeof value === 'object' && Object.keys(value).length > 0;
}

function toFiniteNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function getLiveDashboardState() {
  try {
    if (
      window.__NEXUS_LIVE_PAYLOAD__
      && typeof window.__NEXUS_LIVE_PAYLOAD__ === 'object'
      && Object.keys(window.__NEXUS_LIVE_PAYLOAD__).length
    ) {
      return window.__NEXUS_LIVE_PAYLOAD__;
    }
    if (
      window.__NEXUS_DASHBOARD_STATE
      && typeof window.__NEXUS_DASHBOARD_STATE === 'object'
      && Object.keys(window.__NEXUS_DASHBOARD_STATE).length
    ) {
      return window.__NEXUS_DASHBOARD_STATE;
    }
    if (window.parent && window.parent !== window && window.parent.dashState && typeof window.parent.dashState === 'object') {
      return window.parent.dashState;
    }
  } catch (error) {
    // Cross-window access can fail during bootstrap; fall back to the local cache.
  }

  if (window.dashState && typeof window.dashState === 'object') {
    return window.dashState;
  }

  return {};
}

function normalizeSentimentGauge(sentiment = {}) {
  const bullishCount = toFiniteNumber(sentiment.bullish_count || sentiment.bull);
  const neutralCount = toFiniteNumber(sentiment.neutral_count || sentiment.neutral);
  const bearishCount = toFiniteNumber(sentiment.bearish_count || sentiment.bear);
  const counts = [bullishCount, neutralCount, bearishCount].map((value) => (Number.isFinite(value) && value > 0 ? value : 0));
  const total = counts.reduce((sum, value) => sum + value, 0);

  if (total > 0) {
    const bull = Math.round((counts[0] / total) * 100);
    const neutral = Math.round((counts[1] / total) * 100);
    const bear = Math.max(0, 100 - bull - neutral);
    return { bull, neutral, bear };
  }

  return { bull: 0, neutral: 0, bear: 0 };
}

function buildMiniSeries(state = {}) {
  const series = Array.isArray(state.predictions) && state.predictions.length
    ? state.predictions
    : Array.isArray(state.reality) && state.reality.length
      ? state.reality
      : [];

  return series
    .map((value) => toFiniteNumber(value))
    .filter((value) => value !== null)
    .slice(-10);
}

function collectCurrentState() {
  const dashState = getLiveDashboardState();
  const data = dashState.data || {};
  const aiEngine = (isNonEmptyObject(data.ai_engine) && data.ai_engine)
    || (isNonEmptyObject(data.cognitive_state) && data.cognitive_state)
    || (isNonEmptyObject(dashState.ai_engine) && dashState.ai_engine)
    || (isNonEmptyObject(dashState.cognitive_state) && dashState.cognitive_state)
    || (() => {
    try {
      return window.parent && window.parent !== window ? ((isNonEmptyObject(window.parent.NEURAL_STATE?.cognitive_state) && window.parent.NEURAL_STATE.cognitive_state) || (isNonEmptyObject(window.parent.NEURAL_STATE?.ai_engine) && window.parent.NEURAL_STATE.ai_engine) || {}) : ((isNonEmptyObject(window.NEURAL_STATE?.cognitive_state) && window.NEURAL_STATE.cognitive_state) || (isNonEmptyObject(window.NEURAL_STATE?.ai_engine) && window.NEURAL_STATE.ai_engine) || {});
    } catch (error) {
      return (isNonEmptyObject(window.NEURAL_STATE?.cognitive_state) && window.NEURAL_STATE.cognitive_state) || (isNonEmptyObject(window.NEURAL_STATE?.ai_engine) && window.NEURAL_STATE.ai_engine) || {};
    }
  })();
  const aiPerformance = data.ai_performance || dashState.ai_performance || {};
  const portfolioSnapshot = data.PORTFOLIO_STATE || dashState.PORTFOLIO_STATE || dashState.portfolioState || {};
  const parentPortfolio = (() => {
    try {
      return window.parent && window.parent !== window ? (window.parent.NEURAL_STATE?.portfolio_intelligence || null) : null;
    } catch (error) {
      return null;
    }
  })();
  const portfolio = parentPortfolio || window.NEURAL_STATE?.portfolio_intelligence || portfolioSnapshot || {};
  const account = portfolio.account_metrics || {};
  const portfolioPositions = Array.isArray(portfolio.positions) ? portfolio.positions : [];
  const liveIndices = Array.isArray(data.live_indices)
    ? data.live_indices
    : Array.isArray(dashState.live_indices)
      ? dashState.live_indices
      : [];
  const indexMap = {};

  liveIndices.forEach(item => {
    const name = String(item?.name || '').toUpperCase();
    if (name.includes('NIFTY')) indexMap.nifty = item;
    if (name.includes('SENSEX')) indexMap.sensex = item;
    if (name.includes('BANK')) indexMap.bank = item;
  });

  const sentiment = dashState.marketSentiment || data.market_sentiment || {};
  const gauge = normalizeSentimentGauge(sentiment);
  const resolvedGauge = [dashState.bull, dashState.neutral, dashState.bear].every((value) => Number.isFinite(Number(value)))
    ? {
        bull: Number(dashState.bull),
        neutral: Number(dashState.neutral),
        bear: Number(dashState.bear)
      }
    : gauge;
  const fallbackPredictions = Array.isArray(dashState.predictions) ? dashState.predictions.length : null;
  const totalPredictions = toFiniteNumber(
    aiPerformance.predictions_today
    || aiPerformance.total_predictions
    || aiPerformance.data_points
    || aiPerformance.data_points_per_minute
    || aiEngine.total_predictions
    || aiEngine.predictions_today
    || aiEngine.data_points
    || aiEngine.prediction_count
    || dashState.totalPredictions
    || fallbackPredictions
  );
  const accuracy = toFiniteNumber(aiPerformance.accuracy || aiPerformance.prediction_accuracy || aiPerformance.accuracy_percent || aiEngine.accuracy || aiEngine.prediction_accuracy || aiEngine.market_state?.system_confidence || dashState.accuracy);
  const modelsActive = toFiniteNumber(aiPerformance.models_active || aiPerformance.active_models || aiEngine.models_active || aiEngine.active_models?.length || aiEngine.active_models || dashState.modelsActive);
  let portfolioValue = toFiniteNumber(
    account.total_value
    || account.portfolio_value
    || portfolio.total_value
    || dashState.portfolioValue
    || data.portfolio_value
    || data.total_portfolio_value
  );
  if ((!Number.isFinite(portfolioValue) || portfolioValue <= 0) && portfolioPositions.length) {
    const derivedValue = portfolioPositions.reduce((sum, pos) => sum + Number(pos?.value ?? pos?.current_value ?? pos?.market_value ?? 0), 0);
    if (Number.isFinite(derivedValue) && derivedValue > 0) portfolioValue = derivedValue;
  }
  const portfolioPnl = toFiniteNumber(
    account.total_pnl
    || account.day_pnl
    || portfolio.total_pnl
    || portfolio.day_pnl
    || dashState.portfolioPnl
  );
  let portfolioChangePercent = toFiniteNumber(
    account.total_pnl_percent
    || account.day_pnl_percent
    || portfolio.total_pnl_percent
    || portfolio.day_pnl_percent
    || dashState.portfolioChangePercent
  );
  if ((!Number.isFinite(portfolioChangePercent) || portfolioChangePercent === 0) && portfolioPositions.length) {
    const invested = portfolioPositions.reduce((sum, pos) => sum + Number(pos?.invested ?? (Number(pos?.quantity || 0) * Number(pos?.avg_price || 0)) ?? 0), 0);
    const value = portfolioPositions.reduce((sum, pos) => sum + Number(pos?.value ?? pos?.current_value ?? pos?.market_value ?? 0), 0);
    if (Number.isFinite(invested) && invested > 0 && Number.isFinite(value) && value > 0) {
      portfolioChangePercent = ((value - invested) / invested) * 100;
    }
  }

  return {
    success: true,
    bull: resolvedGauge.bull,
    neutral: resolvedGauge.neutral,
    bear: resolvedGauge.bear,
    portfolioValue,
    totalReturn: portfolioPnl,
    totalReturnPct: portfolioChangePercent,
    activePositions: portfolioPositions.length,
    portfolioVar: toFiniteNumber(account.var_95 || account.var95 || portfolio.var_95 || portfolio.var95),
    aiIndex: toFiniteNumber(aiEngine.market_state?.regime_strength ?? aiEngine.system_health ?? indexMap.nifty?.value ?? 0),
    aiIndexChange: toFiniteNumber(aiEngine.market_state?.regime_drift ?? indexMap.nifty?.change ?? 0),
    aiIndexPrice: toFiniteNumber(indexMap.nifty?.value ?? 0),
    aiIndexPeriod: aiEngine.market_state?.regime || 'Neutral',
    aiIndexTrend: aiEngine.market_state?.market_phase || 'Stabilizing',
    modelAccuracy: accuracy,
    totalPredictions,
    modelsActive,
    predictions: Array.isArray(dashState.predictions) ? dashState.predictions : [],
    predLabels: Array.isArray(dashState.predLabels) ? dashState.predLabels : [],
    reality: Array.isArray(dashState.reality) ? dashState.reality : [],
    stocks: Array.isArray(data.stocks) ? data.stocks : [],
    fxPairs: Array.isArray(data.fxPairs) ? data.fxPairs : [],
    commodities: Array.isArray(data.commodities) ? data.commodities : [],
    rates: Array.isArray(data.rates) ? data.rates : [],
    crypto: Array.isArray(data.crypto) ? data.crypto : [],
    indices: liveIndices,
    ticker: dashState.ticker || null,
    alerts: Array.isArray(dashState.alerts) ? dashState.alerts : []
  };
}

function destroyChart(key) {
  if (C[key]) {
    C[key].destroy();
    C[key] = null;
  }
}

function initSparkMini(series = []) {
  const el = document.getElementById('sparkMini');
  if (!el || !window.Chart) return;
  const values = Array.isArray(series) ? series.map((value) => toFiniteNumber(value)).filter((value) => value !== null).slice(-8) : [];
  if (!values.length) return;
  el.innerHTML = '';
  const canvas = document.createElement('canvas');
  canvas.height = 28;
  canvas.width = 64;
  canvas.style.width = '64px';
  el.appendChild(canvas);
  destroyChart('spark');
  C.spark = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: values.map((_, i) => i),
      datasets: [{
        data: values,
        borderColor: '#4fd1c5',
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.42,
        fill: false
      }]
    },
    options: {
      responsive: false,
      maintainAspectRatio: false,
      animation: { duration: 600 },
      scales: { x: { display: false }, y: { display: false } },
      plugins: { legend: { display: false }, tooltip: { enabled: false } }
    }
  });
}

function initP2MiniSpark(series = []) {
  const el = document.getElementById('p2Spark');
  const values = Array.isArray(series) ? series.map((value) => toFiniteNumber(value)).filter((value) => value !== null).slice(-6) : [];
  if (el && window.Chart && values.length) {
    el.innerHTML = '';
    const canvas = document.createElement('canvas');
    canvas.height = 22;
    canvas.width = 50;
    canvas.style.width = '50px';
    el.appendChild(canvas);
    destroyChart('p2Spark');
    C.p2Spark = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: values.map((_, i) => i),
        datasets: [{
          data: values,
          borderColor: '#a78bfa',
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.42,
          fill: false
        }]
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
        scales: { x: { display: false }, y: { display: false } },
        plugins: { legend: { display: false }, tooltip: { enabled: false } }
      }
    });
  }

  const bars = document.getElementById('p2MiniBars');
  if (bars && values.length) {
    const min = Math.min(...values);
    const max = Math.max(...values);
    const spread = Math.max(max - min, 1);
    bars.innerHTML = '';
    values.forEach((value) => {
      const height = 4 + Math.round(((value - min) / spread) * 14);
      const bar = document.createElement('span');
      bar.style.height = `${height}px`;
      bars.appendChild(bar);
    });
  }
}

/* ══ 1. SIDEBAR MINI SPARKLINE ══ */
function initMiniChart() {
  const el = document.getElementById('miniChart');
  if (!el) return;
  const liveSeries = buildMiniSeries(getLiveDashboardState());
  if (!liveSeries.length) {
    destroyChart('mini');
    return;
  }
  if (C.mini) C.mini.destroy();
  const ctx = el.getContext('2d');
  const g = ctx.createLinearGradient(0, 0, 0, 50);
  g.addColorStop(0, 'rgba(74,222,128,0.36)');
  g.addColorStop(1, 'rgba(74,222,128,0)');
  C.mini = new Chart(ctx, {
    type: 'line',
    data: {
      labels: liveSeries.map((_, i) => i),
      datasets:[{ data:liveSeries, borderColor:'#4ade80',
        backgroundColor:g, fill:true, pointRadius:0, borderWidth:1.6, tension:.42 }]
    },
    options:{ responsive:true, maintainAspectRatio:false, animation:{duration:900},
      scales:{x:{display:false},y:{display:false}},
      plugins:{legend:{display:false},tooltip:{enabled:false}} }
  });
}

/* ══ 2. GAUGE (semi-circle doughnut) ══ */
function initGauge(bull=null, neutral=null, bear=null) {
  const el = document.getElementById('gaugeCanvas');
  if (!el) return;
  const liveState = getLiveDashboardState();
  const liveGauge = normalizeSentimentGauge(liveState.marketSentiment || liveState.market_sentiment || {});
  const values = [bull, neutral, bear].map((value, idx) => {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
    return [liveGauge.bull, liveGauge.neutral, liveGauge.bear][idx];
  });
  if (!values.every((value) => Number.isFinite(Number(value)))) {
    destroyChart('gauge');
    const s = id => document.getElementById(id);
    if(s('gvBull')) s('gvBull').textContent = '--';
    if(s('gvNeutral')) s('gvNeutral').textContent = '--';
    if(s('gsBull')) s('gsBull').textContent = '--';
    if(s('gsNeutral')) s('gsNeutral').textContent = '--';
    if(s('gsBear')) s('gsBear').textContent = '--';
    return;
  }
  if (C.gauge) C.gauge.destroy();
  C.gauge = new Chart(el.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: ['Bull','Neutral','Bear'],
      datasets:[{ data:values,
        backgroundColor:['#4ade80','#fb923c','#f87171'],
        borderColor:'transparent', borderWidth:0,
        circumference:180, rotation:270, cutout:'68%' }]
    },
    options:{ responsive:false, animation:{duration:1100, easing:'easeOutCubic'},
      plugins:{legend:{display:false},
        tooltip:{enabled:true, callbacks:{label:c=>` ${c.label}: ${c.parsed}%`}}} }
  });
  const s = id => document.getElementById(id);
  if(s('gvBull'))   s('gvBull').textContent   = values[0]+'%';
  if(s('gvNeutral'))s('gvNeutral').textContent = values[1]+'%';
  if(s('gsBull'))   s('gsBull').textContent    = values[0]+'%';
  if(s('gsNeutral'))s('gsNeutral').textContent = values[1]+'%';
  if(s('gsBear'))   s('gsBear').textContent    = values[2]+'%';
}

/* ══ 3. PREDICTION CHART ══ */
const predSeries = {
  '1D2': {
    labels:[],
    ai:[],
    real:[]
  },
  '1B': {
    labels:[],
    ai:[],
    real:[]
  }
};

function initPredChart(key='1D2') {
  const el = document.getElementById('predChart');
  if (!el) return;
  if (C.pred) C.pred.destroy();
  const d = predSeries[key] || predSeries['1D2'];
  const plottedValues = [...(Array.isArray(d.ai) ? d.ai : []), ...(Array.isArray(d.real) ? d.real : [])]
    .map((value) => toFiniteNumber(value))
    .filter((value) => value !== null);
  const yBounds = plottedValues.length
    ? (() => {
        const low = Math.min(...plottedValues);
        const high = Math.max(...plottedValues);
        const padding = Math.max(Math.abs(high - low), Math.abs(high), Math.abs(low)) * 0.05;
        return { min: low - padding, max: high + padding };
      })()
    : {};
  const ctx = el.getContext('2d');
  const fillG = ctx.createLinearGradient(0,0,0,210);
  fillG.addColorStop(0,'rgba(79,209,197,0.18)');
  fillG.addColorStop(1,'rgba(79,209,197,0)');
  C.pred = new Chart(ctx, {
    type:'line',
    data:{
      labels:d.labels,
      datasets:[
        { label:'AI Prediction', data:d.ai, borderColor:'#4fd1c5', backgroundColor:fillG,
          fill:true, borderWidth:2.2, pointRadius:5, pointBackgroundColor:'#4fd1c5',
          pointBorderColor:'#0c0c0e', pointBorderWidth:2, tension:.42 },
        { label:'Observed Reality', data:d.real, borderColor:'rgba(79,209,197,0.44)',
          borderWidth:1.5, borderDash:[5,4], pointRadius:3.5,
          pointBackgroundColor:'rgba(79,209,197,0.65)', fill:false, tension:.42 }
      ]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      animation:{duration:1200, easing:'easeInOutQuart'},
      plugins:{
        legend:{display:true, position:'top', align:'end',
          labels:{color:'#888890', font:{size:10}, boxWidth:18, padding:10}},
        tooltip:{enabled:true}
      },
      scales:{
        x:{grid:{color:'rgba(255,255,255,0.035)'}, ticks:{color:'#666'}},
        y:{...yBounds, grid:{color:'rgba(255,255,255,0.035)'}, ticks:{color:'#666'}}
      }
    }
  });
}

/* ══ 4. SIDEBAR SPARKLINE (SVG) ══ */
function buildSparklines() {
  const s1 = document.getElementById('sparkMini');
  const liveState = collectCurrentState();
  const sparkSeries = buildMiniSeries(liveState);
  if (s1) {
    s1.innerHTML = '';
    if (sparkSeries.length) initSparkMini(sparkSeries);
  }
  const s2 = document.getElementById('p2Spark');
  if (s2) {
    s2.innerHTML = '';
    if (Array.isArray(liveState.predictions) && liveState.predictions.length) initP2MiniSpark(liveState.predictions);
    else if (Array.isArray(liveState.reality) && liveState.reality.length) initP2MiniSpark(liveState.reality);
  }
}

/* ══ 5. PA2 MINI BARS ══ */
function buildPA2Bars() {
  const el = document.getElementById('p2MiniBars');
  if (!el) return;
  el.innerHTML = '';
  const liveState = collectCurrentState();
  const values = Array.isArray(liveState.predictions) && liveState.predictions.length
    ? liveState.predictions
    : Array.isArray(liveState.reality) && liveState.reality.length
      ? liveState.reality
      : [];
  if (values.length) initP2MiniSpark(values);
}

function formatNumber(value, decimals = 0) {
  if (!Number.isFinite(Number(value))) return '--';
  return Number(value).toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function formatCurrencyINR(value, decimals = 2) {
  if (!Number.isFinite(Number(value))) return '--';
  return `₹${Number(value).toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
}

function formatPercent(value, decimals = 2) {
  if (!Number.isFinite(Number(value))) return '--';
  const v = Number(value);
  return `${v >= 0 ? '+' : ''}${v.toFixed(decimals)}%`;
}

function setTextById(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setSyncProgress(value) {
  const el = document.getElementById('syncFill');
  if (!el || !Number.isFinite(Number(value))) return;
  el.style.width = `${Math.max(0, Math.min(100, Number(value)))}%`;
}

function setTickerState(ticker) {
  if (typeof ticker !== 'object' || ticker === null) return;
  const price = Number.isFinite(Number(ticker.price)) ? formatNumber(ticker.price, 2) : '--';
  const change = Number.isFinite(Number(ticker.change)) ? formatPercent(ticker.change, 2) : '--';
  const time = ticker.time || ticker.updatedAt || ticker.timestamp || new Date().toLocaleTimeString();
  setTextById('tickerPrice', price);
  setTextById('tickerChange', change);
  setTextById('tickerTime', time);
}

function setDashboardSummary(data = {}) {
  if (data.totalReturn !== undefined) {
    setTextById('sbTotalReturn', `↑ ${formatCurrencyINR(data.totalReturn, 2)}`);
    setTextById('sbTotalReturnValue', formatCurrencyINR(data.totalReturn, 2));
  }
  if (data.totalReturnPct !== undefined) {
    setTextById('sbReturnPct', formatPercent(data.totalReturnPct, 0));
    setTextById('sbTotalReturnPct', formatPercent(data.totalReturnPct, 1));
  }
}

function setAiIndexCard(data = {}) {
  if (data.aiIndex !== undefined) setTextById('sbIndexValue', formatNumber(data.aiIndex, 1));
  if (data.aiIndexChange !== undefined) setTextById('sbIndexChange', formatPercent(data.aiIndexChange, 1));
  if (data.aiIndexPrice !== undefined) setTextById('sbIndexPrice', formatNumber(data.aiIndexPrice, 2));
  if (data.aiIndexPeriod !== undefined) setTextById('sbIndexPeriod', data.aiIndexPeriod);
  if (data.aiIndexTrend !== undefined) setTextById('sbIndexTrend', data.aiIndexTrend);
}

function setSignalQuality(data = {}) {
  if (data.signalHeadline !== undefined) setTextById('p2Stat', data.signalHeadline);
  if (data.directionalAccuracy !== undefined) setTextById('p2Accuracy', formatPercent(data.directionalAccuracy, 1));
  if (data.liquidityScore !== undefined) setTextById('p2BigVal', formatPercent(data.liquidityScore, 2));
  if (data.liquidityChange !== undefined) setTextById('p2ChangePos', formatPercent(data.liquidityChange, 1));
}

function setPortfolioSummary(data = {}) {
  if (data.activePositions !== undefined) {
    const row = document.querySelector('.wp-portfolio .wp-port-item:nth-child(2) div');
    if (row) row.innerHTML = `<b>${formatNumber(data.activePositions, 0)}</b><em>${data.activePositionsChange || ''}</em>`;
  }
  if (data.portfolioVar !== undefined) {
    const row = document.querySelector('.wp-portfolio .wp-port-item.no-border div');
    if (row) row.innerHTML = `<b class="${data.portfolioVar < 0 ? 'red-val' : 'p2-big-val'}">${formatPercent(data.portfolioVar, 1)}</b><em>${data.portfolioVarChange || ''}</em>`;
  }
}

function normalizeIndexList(data, changeMap) {
  if (!data) return [];
  if (Array.isArray(data)) return data.map((idx) => ({ name: idx.name || idx.symbol || '', value: idx.value ?? idx.last ?? idx.price ?? 0, change: idx.change ?? idx.change_percent ?? 0 }));
  return Object.entries(data).map(([name, value]) => ({ name, value, change: changeMap && changeMap[name] !== undefined ? changeMap[name] : undefined }));
}

function normalizeFxRows(source = []) {
  return Array.isArray(source)
    ? source.map((item) => {
        const price = Number(item?.price ?? item?.value ?? item?.rate ?? item?.last);
        const change = Number(item?.change ?? item?.change_percent ?? item?.delta ?? item?.move ?? 0);
        const status = String(item?.status || (Number.isFinite(change) ? (change > 0 ? 'BUY' : change < 0 ? 'SELL' : 'HOLD') : '--')).toUpperCase();
        return { pair: String(item?.pair || item?.symbol || item?.name || '--'), price, status };
      }).filter((row) => row.pair && row.pair !== '--')
    : [];
}

function normalizeCommodityRows(source = []) {
  return Array.isArray(source)
    ? source.map((item) => ({
        name: String(item?.name || item?.symbol || '--'),
        price: Number(item?.price ?? item?.value ?? item?.last),
        change: Number(item?.change ?? item?.change_percent ?? item?.delta ?? 0)
      })).filter((row) => row.name && row.name !== '--')
    : [];
}

function normalizeRateRows(source = []) {
  return Array.isArray(source)
    ? source.map((item) => ({
        bank: String(item?.bank || item?.name || item?.symbol || '--'),
        rate: Number(item?.rate ?? item?.value ?? item?.last ?? item?.price),
        trend: String(item?.trend || item?.direction || (Number(item?.change ?? item?.delta ?? 0) < 0 ? 'Cut ↓' : 'Hold'))
      })).filter((row) => row.bank && row.bank !== '--')
    : [];
}

function normalizeCryptoRows(source = []) {
  return Array.isArray(source)
    ? source.map((item) => ({
        symbol: String(item?.symbol || item?.name || '--'),
        price: Number(item?.price ?? item?.value ?? item?.last),
        change: Number(item?.change ?? item?.change_percent ?? item?.delta ?? 0)
      })).filter((row) => row.symbol && row.symbol !== '--')
    : [];
}

function generateSeries(length, base, drift = 0, volatility = 1.2) {
  const count = Math.max(0, Number(length) || 0);
  const start = Number(base) || 0;
  const step = Number(drift) || 0;
  return Array.from({ length: count }, (_, index) => Number((start + (index * step)).toFixed(1)));
}

function generateLiveFallbackState() {
  return collectCurrentState();
}

/* ══ 6. LIVE CLOCK ══ */
function startClock() {
  const el = document.getElementById('liveClock');
  if (!el) return;
  const tick = () => {
    const n = new Date();
    el.textContent = `${n.getDate()}, ${String(n.getHours()).padStart(2,'0')}:`
      +`${String(n.getMinutes()).padStart(2,'0')}:`
      +`${String(n.getSeconds()).padStart(2,'0')}`;
  };
  tick(); setInterval(tick, 1000);
}

/* ══ 7. COUNTER ANIMATION ══ */
function animCounter(id, target, prefix='₹ ', dur=1800) {
  const el = document.getElementById(id);
  if (!el) return;
  const t0 = performance.now();
  (function tick(now){
    const p = Math.min((now-t0)/dur,1), e = 1-Math.pow(1-p,3);
    const value = Number.isFinite(Number(target)) ? Number(target * e) : 0;
    el.textContent = prefix + value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (p<1) requestAnimationFrame(tick);
    else el.textContent = prefix + Number(target).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  })(performance.now());
}

/* ══ 8. PREDICTION TAB SWITCHER ══ */
window.switchTab = function(btn, key) {
  document.querySelectorAll('.ptab').forEach(b => b.classList.remove('pred-btn--active'));
  if (btn) btn.classList.add('pred-btn--active');
  initPredChart(key);
};

/* ══ 9. TABLE RENDERERS ══ */
function renderStocks(data) {
  const tb = document.getElementById('stocksTbl');
  if (!tb||!data) return;
  tb.innerHTML = data.map(s=>{
    const price = Number(s.price);
    const change = Number(s.change);
    const pos = Number.isFinite(change) && change >= 0;
    return `<tr><td class="sym sym-t">${s.symbol}</td>
      <td class="price-cell">${Number.isFinite(price) ? formatCurrencyINR(price, 2) : '--'}</td>
      <td><span class="${pos?'chg-g':'chg-r'}">${pos?'↑':'↓'} ${formatNumber(Number(s.change), 2)}%</span></td></tr>`;
  }).join('');
}
function renderFX(data) {
  const tb = document.getElementById('fxTbl');
  if (!tb||!data) return;
  const map={HOLD:'sbadge-h',BUY:'sbadge-b',SELL:'sbadge-s'};
  tb.innerHTML = data.map(p=>{
    const price = Number(p.price);
    const status = String(p.status || '--').toUpperCase();
    return `<tr><td class="sym sym-t">${p.pair || '--'}</td>
      <td class="price-cell">${Number.isFinite(price) ? formatNumber(price, 2) : '--'}</td>
      <td><span class="sbadge ${map[status]||'sbadge-h'}">${status}</span></td></tr>`;
  }).join('');
}
function renderCommodities(data) {
  const tb = document.getElementById('cmdTbl');
  if (!tb||!data) return;
  tb.innerHTML = data.map(c=>{const price=Number(c.price); const change=Number(c.change); const pos=Number.isFinite(change)&&change>=0;
    return `<tr><td class="sym">${c.name || '--'}</td><td class="price-cell">${Number.isFinite(price) ? `$${formatNumber(price, 2)}` : '--'}</td>
      <td><span class="${pos?'chg-g':'chg-r'}">${Number.isFinite(change) ? `${pos?'+':''}${Math.abs(change).toFixed(2)}%` : '--'}</span></td></tr>`;
  }).join('');
}
function renderRates(data) {
  const tb = document.getElementById('ratesTbl');
  if (!tb||!data) return;
  tb.innerHTML = data.map(r=>{
    const rate = Number(r.rate);
    const trend = String(r.trend || '--');
    return `<tr><td class="sym">${r.bank || '--'}</td>
      <td class="price-cell">${Number.isFinite(rate) ? `${formatNumber(rate, 2)}%` : '--'}</td>
      <td><span class="${trend==='Cut ↓'?'chg-g':'chg-r'}">${trend}</span></td></tr>`;
  }).join('');
}
function renderCrypto(data) {
  const tb = document.getElementById('cryptoTbl');
  if (!tb||!data) return;
  tb.innerHTML = data.map(c=>{const price=Number(c.price); const change=Number(c.change); const pos=Number.isFinite(change)&&change>=0;
    return `<tr><td class="sym sym-t">${c.symbol || '--'}</td><td class="price-cell">${Number.isFinite(price) ? `${formatNumber(price, 2)}` : '--'}</td>
      <td><span class="${pos?'chg-g':'chg-r'}">${Number.isFinite(change) ? `${pos?'+':''}${Math.abs(change).toFixed(2)}%` : '--'}</span></td></tr>`;
  }).join('');
}
function renderIndices(data, changeData) {
  const mapping = {
    'NIFTY 50':'nifty50','BANK NIFTY':'bankNifty','SENSEX':'sensex',
    'S&P 500':'sp500','DOW JONES':'dowJones','NASDAQ':'nasdaq',
    'NIFTY50':'nifty50','BANKNIFTY':'bankNifty','SENSEX':'sensex',
    'SP500':'sp500','DOWJONES':'dowJones','NASDAQ':'nasdaq'
  };
  if (!data) return;
  const items = Array.isArray(data)
    ? data
    : Object.entries(data).map(([name, value]) => ({ name, value, change: changeData?.[name] }));
  items.forEach(idx => {
    const name = String(idx.name || idx.symbol || '').toUpperCase();
    const normalized = name.replace(/\s+/g, '');
    const elId = mapping[name] || mapping[normalized];
    if (!elId) return;
    const el = document.getElementById(elId);
    if (el) el.textContent = formatNumber(idx.value, 2);
    const parent = el && el.closest('.mkt-index-item');
    if (parent) {
      let em = parent.querySelector('em');
      if (!em) { em = document.createElement('em'); parent.appendChild(em); }
      const change = Number(idx.change);
      if (Number.isFinite(change)) {
        const pos = change >= 0;
        em.className = pos ? 'pos' : 'neg';
        em.textContent = formatPercent(change, 2);
      } else {
        em.className = '';
        em.textContent = '--';
      }
    }
  });
}

function setNewsSentiment(data = {}) {
  const primary = document.querySelector('.card--news > .news-item:not(.news-item--secondary)');
  const secondary = document.querySelector('.card--news .news-item.news-item--secondary');
  const newsItems = Array.isArray(data.newsItems)
    ? data.newsItems
    : Array.isArray(data.news)
      ? data.news
      : Array.isArray(data.news_items)
        ? data.news_items
        : [];
  const newsIntelligence = data.newsIntelligence || data.news_intelligence || {};
  const primaryItem = newsItems[0] || {};
  const secondaryItem = newsItems[1] || {};
  const headline = primaryItem.headline || newsIntelligence.top_headline || data.primaryHeadline || 'Live news feed syncing';
  const sentiment = primaryItem.sentiment_pct ?? newsIntelligence.sentiment_score ?? data.sentiment_pct;
  if (primary) {
    const sourceEl = primary.querySelector('.news-item-source');
    const sentimentEl = primary.querySelector('.news-sentiment-pos');
    if (sourceEl) sourceEl.textContent = headline;
    if (sentimentEl) sentimentEl.textContent = `Sentiment: ${Number.isFinite(Number(sentiment)) ? formatPercent(sentiment, 2) : (primaryItem.sentiment || '—')}`;
  }
  if (secondary) {
    const titleEl = secondary.querySelector('.news-item-title');
    const descEl = secondary.querySelector('.news-item-desc');
    const jalrtEl = secondary.querySelector('.news-item-jalrt');
    const statsEl = secondary.querySelector('.news-item-stats');
    if (titleEl) titleEl.textContent = secondaryItem.title || secondaryItem.headline || newsIntelligence.secondary_headline || 'Live signal update';
    if (descEl) descEl.textContent = secondaryItem.summary || secondaryItem.description || newsIntelligence.secondary_summary || 'Live feed analysis will populate here when the model sync completes.';
    if (jalrtEl) jalrtEl.textContent = secondaryItem.tag || secondaryItem.alert_type || newsIntelligence.alert_label || '--';
    if (statsEl) {
      const statSpans = statsEl.querySelectorAll('.news-stat, .news-stat-green, .news-stat-yellow, .news-age');
      if (statSpans && statSpans.length >= 5) {
        statSpans[0].textContent = `● ${secondaryItem.category || newsIntelligence.category || '--'}`;
        statSpans[1].textContent = secondaryItem.impact ? `${formatPercent(secondaryItem.impact, 1)}` : '';
        statSpans[2].textContent = `● ${secondaryItem.market || newsIntelligence.market || '--'}`;
        statSpans[3].textContent = `● ${secondaryItem.asset_class || newsIntelligence.asset_class || '--'}`;
        statSpans[4].textContent = secondaryItem.age || '--';
      } else {
        statsEl.innerHTML = `
          <span class="news-stat">● ${secondaryItem.category || newsIntelligence.category || '--'}</span>
          <span class="news-stat-green">${secondaryItem.impact ? `${formatPercent(secondaryItem.impact, 1)}` : ''}</span>
          <span class="news-stat">● ${secondaryItem.market || newsIntelligence.market || '--'}</span>
          <span class="news-stat">● ${secondaryItem.asset_class || newsIntelligence.asset_class || '--'}</span>
          <span class="news-age">${secondaryItem.age || '--'}</span>
        `;
      }
    }
  }
}

/* ══ 10. ALERT INJECTOR ══ */
function renderTopThreeLiveNews(data = {}) {
  const items = (Array.isArray(data.newsItems) ? data.newsItems : Array.isArray(data.news) ? data.news : Array.isArray(data.news_items) ? data.news_items : [])
    .filter((item) => item && typeof item === 'object' && (item.headline || item.title));
  const primary = document.querySelector('.card--news > .news-item:not(.news-item--secondary)');
  const secondary = document.querySelector('.card--news .news-item.news-item--secondary');
  if (!items.length || !primary || !secondary) return;

  const percent = (value) => {
    const number = toFiniteNumber(value);
    if (number === null) return '--';
    return formatPercent(Math.abs(number) <= 1 ? number * 100 : number, 1);
  };
  const sentiment = (item) => String(item.sentiment || item.label || item.sentiment_label || 'NEUTRAL').toUpperCase();
  const impact = (item) => percent(item.impact_score ?? item.impact_strength ?? item.impact);
  const confidence = (item) => percent(item.confidence ?? item.confidence_band);
  const first = items[0];
  primary.querySelector('.news-item-source').textContent = first.headline || first.title;
  primary.querySelector('.news-sentiment-pos').textContent = `Sentiment: ${sentiment(first)} | Impact: ${impact(first)} | Confidence: ${confidence(first)}`;

  const card = secondary.closest('.card--news');
  card.querySelectorAll('.news-item--live-extra').forEach((node) => node.remove());
  const storyNodes = [secondary];
  while (storyNodes.length < items.length && storyNodes.length < 3) {
    const node = secondary.cloneNode(true);
    node.classList.add('news-item--live-extra');
    card.appendChild(node);
    storyNodes.push(node);
  }
  items.slice(1, storyNodes.length + 1).forEach((item, index) => {
    const node = storyNodes[index];
    node.querySelector('.news-item-title').textContent = item.title || item.headline;
    node.querySelector('.news-item-desc').textContent = item.summary || item.description || item.why_it_matters || '';
    node.querySelector('.news-item-jalrt').textContent = item.event_type || item.tag || sentiment(item);
    const stats = node.querySelectorAll('.news-stat, .news-stat-green, .news-stat-yellow, .news-age');
    if (stats.length >= 5) {
      stats[0].textContent = `Sentiment ${sentiment(item)}`;
      stats[1].textContent = `Impact ${impact(item)}`;
      stats[2].textContent = `Confidence ${confidence(item)}`;
      stats[3].textContent = item.event_type || item.category || '';
      stats[4].textContent = item.age || item.published || item.normalized_time || '';
    }
  });
}

function clearAlerts() {
  const card = document.getElementById('alertsCard');
  if (!card) return;
  card.querySelectorAll('.ait').forEach(el => el.remove());
}

function pushAlert(type, title, desc, change) {
  const card = document.getElementById('alertsCard');
  if (!card) return;
  const dotClass={red:'alert-dot--red',green:'alert-dot--green',yellow:'alert-dot--yellow'}[type]||'alert-dot--green';
  const chgColor=parseFloat(change)>=0?'var(--green)':'var(--red)';
  const div=document.createElement('div');
  div.className='ait alert-item'; div.style.cssText='opacity:0;transition:opacity .3s ease';
  div.innerHTML=`<div class="ait-row" style="display:flex;align-items:center;gap:8px;margin-bottom:2px;">
    <div class="adot alert-dot ${dotClass}"></div>
    <span class="ait-title alert-title">${title}</span>
    <span style="margin-left:auto;font-size:10.5px;font-weight:600;color:${chgColor}">${change || ''}</span></div>
    <div class="ait-desc alert-desc" style="padding-left:16px;">${desc}</div>`;
  const existing=card.querySelectorAll('.ait');
  if(existing.length>=3)existing[0].remove();
  card.querySelector('.alerts-hd').insertAdjacentElement('afterend',div);
  requestAnimationFrame(()=>{div.style.opacity='1';});
}

/* ══ ALERT DOT PULSE ══ */
function startAlertPulse(){
  setInterval(()=>{
    document.querySelectorAll('.alert-dot').forEach(d=>{
      d.style.transform='scale(1.4)';
      setTimeout(()=>d.style.transform='scale(1)',280);
    });
  },2200);
}

/* ════════════════════════════════════════════════════════════
   ██  N E X U S   A P I  ██
   ════════════════════════════════════════════════════════════
   Use from your Flask/Python model:

   window.NexusAPI.refresh({
     bull: 61, neutral: 22, bear: 17,
     portfolioValue: 1720000,
     modelAccuracy: 74.33,
     totalPredictions: 1482,
     predLabels: ['Jan','Feb','Mar'],
     predictions: [93, 95, 96],
     reality: [92, 94, 95],
     stocks: [{symbol:'INFY', price:'230', change:1.2}],
     fxPairs: [{pair:'USD/INR', price:'0.3', status:'BUY'}],
     commodities: [{name:'Gold', price:'2400', change:0.9}],
     rates: [{bank:'RBI (India)', rate:'6.25', trend:'Hold'}],
     crypto: [{symbol:'BTC', price:'65000', change:2.1}],
     indices: [{name:'NIFTY 50', value:'24500', change:0.8}]
   });
   ════════════════════════════════════════════════════════════ */
const NexusAPI = {
  setGauge(b,n,r){initGauge(b,n,r);},
  setPred(l,p,r){
    predSeries['1D2']={labels:l,ai:p,real:r};
    initPredChart('1D2');
  },
  setPortfolio(v){animCounter('portVal',v,'$ ',1200);},
  setAccuracy(p){const el=document.getElementById('sbAccuracy'); if(el) el.textContent = Number.isFinite(Number(p)) ? `${Number(p).toFixed(2)}%` : '--';},
  setTotalPred(n){const el=document.getElementById('sbTotalPred'); if(el) el.textContent = Number.isFinite(Number(n)) ? Number(n).toLocaleString('en-IN') : '--';},
  setStocks(a){renderStocks(a);},
  setFX(a){renderFX(a);},
  setCommodities(a){renderCommodities(a);},
  setRates(a){renderRates(a);},
  setCrypto(a){renderCrypto(a);},
  setIndices(a,c){renderIndices(a,c);},
  setNews(data){ setNewsSentiment(data); },
  setTotalReturn(v){ setDashboardSummary({ totalReturn: v }); },
  setTotalReturnPct(v){ setDashboardSummary({ totalReturnPct: v }); },
  setAiIndex(ai, aiDelta, price, period, trend){ setAiIndexCard({ aiIndex: ai, aiIndexChange: aiDelta, aiIndexPrice: price, aiIndexPeriod: period, aiIndexTrend: trend }); },
  setSignalQuality(data){ setSignalQuality(data); },
  setPortfolioStatus(data){ setPortfolioSummary(data); },
  setTicker(ticker){ setTickerState(ticker); },
  addAlert(t,ti,d,c){pushAlert(t,ti,d,c);},
  setAlerts(alerts){ if (Array.isArray(alerts) && alerts.length) { clearAlerts(); alerts.slice(0,6).forEach((alert) => { const type = alert.severity || alert.level || alert.type || 'info'; const style = type === 'critical' || type === 'warning' ? 'red' : type === 'alert' || type === 'neutral' ? 'yellow' : 'green'; pushAlert(style, alert.title || alert.headline || 'Market alert', alert.description || alert.summary || '', alert.change ?? alert.change_pct ?? ''); }); } },
  refresh(data={}){
    const macro = data.macro || {};
    const aiPerformance = data.ai_performance || {};
    const aiEngine = data.ai_engine || data.cognitive_state || {};
    const signalHeadline = data.signalHeadline || aiPerformance.signal_headline || aiPerformance.summary || aiEngine.signal_headline || aiEngine.regime || aiEngine.market_state?.regime || data.aiIndexTrend;
    const directionalAccuracy = data.directionalAccuracy ?? aiPerformance.directional_accuracy ?? aiPerformance.prediction_accuracy ?? aiPerformance.accuracy ?? aiEngine.market_state?.system_confidence;
    const liquidityScore = data.liquidityScore ?? aiPerformance.liquidity_score ?? aiPerformance.liquidity ?? aiEngine.liquidity_score ?? aiEngine.liquidity;
    const liquidityChange = data.liquidityChange ?? aiPerformance.liquidity_change ?? aiEngine.liquidity_change;
    if (data.bull !== undefined) this.setGauge(data.bull, data.neutral || 0, data.bear || 0);
    if (data.portfolioValue !== undefined) this.setPortfolio(data.portfolioValue);
    if (data.totalReturn !== undefined) this.setTotalReturn(data.totalReturn);
    if (data.totalReturnPct !== undefined) this.setTotalReturnPct(data.totalReturnPct);
    if (data.activePositions !== undefined) this.setPortfolioStatus({ activePositions: data.activePositions, activePositionsChange: data.activePositionsChange });
    if (data.portfolioVar !== undefined || data.portfolioVarChange !== undefined) this.setPortfolioStatus({ portfolioVar: data.portfolioVar, portfolioVarChange: data.portfolioVarChange });
    if (data.aiIndex !== undefined || data.aiIndexChange !== undefined || data.aiIndexPrice !== undefined || data.aiIndexPeriod !== undefined || data.aiIndexTrend !== undefined) this.setAiIndex(data.aiIndex, data.aiIndexChange, data.aiIndexPrice, data.aiIndexPeriod, data.aiIndexTrend);
    if (data.modelAccuracy !== undefined) this.setAccuracy(data.modelAccuracy);
    if (data.totalPredictions !== undefined) this.setTotalPred(data.totalPredictions);
    if (data.predLabels) this.setPred(data.predLabels, data.predictions || [], data.reality || []);
    if (data.stocks || data.topStocks || data.top_stocks) this.setStocks(data.stocks || data.topStocks || data.top_stocks);
    const fxRows = data.fxPairs || normalizeFxRows(macro.forex || macro.fx || macro.fx_rates || macro.forex_rates || []);
    const commodityRows = data.commodities || normalizeCommodityRows(macro.commodities || []);
    const rateRows = data.rates || normalizeRateRows(macro.interest_rates || macro.rates || []);
    const cryptoRows = data.crypto || normalizeCryptoRows(macro.crypto || macro.cryptocurrencies || []);
    if (fxRows && fxRows.length) this.setFX(fxRows);
    if (commodityRows && commodityRows.length) this.setCommodities(commodityRows);
    if (rateRows && rateRows.length) this.setRates(rateRows);
    if (cryptoRows && cryptoRows.length) this.setCrypto(cryptoRows);
    if (data.indices || data.live_indices) this.setIndices(data.indices || data.live_indices, data.indicesChangePercent || data.indicesChange);
    if (data.ticker) this.setTicker(data.ticker);
    if (signalHeadline !== undefined || directionalAccuracy !== undefined || liquidityScore !== undefined || liquidityChange !== undefined) this.setSignalQuality({ signalHeadline, directionalAccuracy, liquidityScore, liquidityChange });
    if (data.newsItems || data.news || data.news_items || data.newsIntelligence || data.news_intelligence) {
      this.setNews({
        newsItems: data.newsItems || data.news || data.news_items || [],
        newsIntelligence: data.newsIntelligence || data.news_intelligence || {}
      });
    }
    if (data.alerts || data.portfolio_alerts) {
      this.setAlerts(data.alerts || data.portfolio_alerts);
    }
    if (data.syncPct !== undefined) setSyncProgress(data.syncPct);
    initMiniChart(Array.isArray(data.predictions) && data.predictions.length ? data.predictions : buildMiniSeries(getLiveDashboardState()));
    buildSparklines();
    buildPA2Bars();
  }
};
window.NexusAPI = NexusAPI;

/* ══ BOOT ══ */
document.addEventListener('DOMContentLoaded',()=>{
  NexusAPI.refresh(collectCurrentState());
  startClock();
  startAlertPulse();

  console.log('%c NEXUS AI QUANTUM %c v5 FINAL — Ready',
    'background:#4fd1c5;color:#000;font-weight:700;padding:3px 10px;border-radius:4px 0 0 4px',
    'background:#1a1a1e;color:#4fd1c5;font-weight:600;padding:3px 10px;border-radius:0 4px 4px 0');
  console.log('window.NexusAPI.refresh({ bull, neutral, bear, portfolioValue, modelAccuracy,');
  console.log('  totalPredictions, predLabels, predictions, reality, stocks, fxPairs,');
  console.log('  commodities, rates, crypto, indices })');
});


function normalizeLiveDashboardPayload(payload) {
  const source = payload && typeof payload === 'object' ? payload : {};
  const asText = (value) => {
    if (value === null || value === undefined) return '';
    return typeof value === 'string' ? value : String(value);
  };
  const asNumber = (value) => {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  };
  const normalizeIndexRow = (row) => {
    if (!row || typeof row !== 'object') return {};
    const label = asText(row.symbol ?? row.name ?? row.label ?? row.index ?? row.ticker);
    const value = asNumber(row.value ?? row.price ?? row.last ?? row.close ?? row.current ?? row.ltp ?? row.index_value);
    const change = asNumber(row.change ?? row.change_pct ?? row.changePct ?? row.percent_change ?? row.delta ?? row.move);
    return {
      ...row,
      symbol: label,
      name: label,
      label,
      value,
      price: value,
      last: value,
      close: value,
      current: value,
      ltp: value,
      change,
      change_pct: change,
      changePct: change,
      percent_change: change,
      delta: change,
      move: change,
      trend: change === null ? row.trend : (change >= 0 ? 'up' : 'down'),
    };
  };
  const normalizeGenericRow = (row) => {
    if (!row || typeof row !== 'object') return {};
    const label = asText(row.symbol ?? row.name ?? row.label ?? row.asset ?? row.pair ?? row.bank ?? row.central_bank ?? row.ticker ?? row.index);
    const value = asNumber(row.value ?? row.price ?? row.current_price ?? row.rate ?? row.last ?? row.close ?? row.current ?? row.ltp);
    const change = asNumber(row.change ?? row.change_percent ?? row.price_change_percent ?? row.change_pct ?? row.changePct ?? row.percent_change ?? row.delta ?? row.move ?? row.move_pct);
    return {
      ...row,
      symbol: label,
      name: label,
      label,
      asset: row.asset ?? label,
      pair: row.pair ?? label,
      bank: row.bank ?? label,
      central_bank: row.central_bank ?? label,
      ticker: row.ticker ?? label,
      value,
      price: value,
      rate: value,
      last: value,
      close: value,
      current: value,
      ltp: value,
      change,
      change_pct: change,
      changePct: change,
      percent_change: change,
      move: change,
      move_pct: change,
      signal: row.signal ?? row.ai_signal ?? row.direction ?? row.action ?? row.recommendation ?? row.status ?? '',
      ai_signal: row.ai_signal ?? row.signal ?? row.direction ?? row.action ?? row.recommendation ?? row.status ?? '',
      trend: row.trend ?? (change === null ? '' : (change >= 0 ? 'up' : 'down')),
    };
  };
  const normalizeRows = (rows, kind) => {
    if (!Array.isArray(rows)) return [];
    return rows.map(kind === 'indices' ? normalizeIndexRow : normalizeGenericRow);
  };
  const macro = source.macro && typeof source.macro === 'object' ? source.macro : {};
  const portfolioIntelligence = source.portfolio_intelligence
    || source.portfolioIntelligence
    || source.PORTFOLIO_STATE
    || {};
  const newsIntelligence = source.news_intelligence
    || source.newsIntelligence
    || source.market_sentiment
    || source.marketSentiment
    || {};
  const liveIndices = Array.isArray(source.live_indices)
    ? normalizeRows(source.live_indices, 'indices')
    : Array.isArray(source.liveIndices)
      ? normalizeRows(source.liveIndices, 'indices')
      : [];
  const topStocks = Array.isArray(source.top_stocks)
    ? normalizeRows(source.top_stocks)
    : Array.isArray(source.topStocks)
      ? normalizeRows(source.topStocks)
      : Array.isArray(source.stocks)
        ? normalizeRows(source.stocks)
        : [];
  const alerts = Array.isArray(source.alerts) ? source.alerts : [];
  const newsItems = Array.isArray(source.news_items)
    ? source.news_items
    : Array.isArray(source.news)
      ? source.news
      : [];

  return {
    ...source,
    live_indices: liveIndices,
    liveIndices,
    market_status: source.market_status || source.marketStatus || {},
    marketStatus: source.marketStatus || source.market_status || {},
    ai_performance: source.ai_performance || source.aiPerformance || {},
    aiPerformance: source.aiPerformance || source.ai_performance || {},
    ai_engine: source.ai_engine || source.aiEngine || {},
    aiEngine: source.aiEngine || source.ai_engine || {},
    cognitive_state: source.cognitive_state || source.cognitiveState || {},
    cognitiveState: source.cognitiveState || source.cognitive_state || {},
    news_items: newsItems,
    news: newsItems,
    news_intelligence: newsIntelligence,
    newsIntelligence,
    market_sentiment: newsIntelligence,
    marketSentiment: newsIntelligence,
    macro: {
      ...macro,
      forex: Array.isArray(macro.forex) ? normalizeRows(macro.forex) : [],
      commodities: Array.isArray(macro.commodities) ? normalizeRows(macro.commodities) : [],
      interest_rates: Array.isArray(macro.interest_rates) ? normalizeRows(macro.interest_rates) : [],
      crypto: Array.isArray(macro.crypto) ? normalizeRows(macro.crypto) : [],
    },
    top_stocks: topStocks,
    topStocks,
    stocks: Array.isArray(source.stocks) ? normalizeRows(source.stocks) : topStocks,
    alerts,
    predictions: Array.isArray(source.predictions) ? source.predictions : [],
    predLabels: Array.isArray(source.predLabels) ? source.predLabels : [],
    reality: Array.isArray(source.reality) ? source.reality : [],
    portfolio_intelligence: portfolioIntelligence,
    portfolioIntelligence,
    portfolio_metrics: source.portfolio_metrics || source.portfolioMetrics || {},
    portfolioMetrics: source.portfolioMetrics || source.portfolio_metrics || {},
    PORTFOLIO_STATE: source.PORTFOLIO_STATE || portfolioIntelligence,
  };
}

async function hydrateDashboardFromLiveApi() {
  try {
    const response = await fetch('/api/dashboard-data/live', { cache: 'no-store' });
    if (!response.ok) return;

    const livePayload = normalizeLiveDashboardPayload(await response.json());
    window.__NEXUS_LIVE_PAYLOAD__ = livePayload;

    if (window.NexusAPI && typeof window.NexusAPI.refresh === 'function' && !window.__NEXUS_REFRESH_WRAPPED__) {
      const originalRefresh = window.NexusAPI.refresh.bind(window.NexusAPI);
      window.NexusAPI.refresh = function wrappedNexusRefresh(data) {
        const merged = normalizeLiveDashboardPayload({
          ...(window.__NEXUS_LIVE_PAYLOAD__ || {}),
          ...(data || {}),
        });
        return originalRefresh(merged);
      };
      window.__NEXUS_REFRESH_WRAPPED__ = true;
    }

    if (window.NexusAPI && typeof window.NexusAPI.refresh === 'function') {
      NexusAPI.refresh(livePayload);
    }

    if (window.parent && window.parent !== window && typeof window.parent.postMessage === 'function') {
      window.parent.postMessage(
        {
          type: 'nexus-dashboard-live-echo',
          payload: {
            live_indices: livePayload.live_indices,
            news_items: livePayload.news_items,
            news_intelligence: livePayload.news_intelligence,
            macro: livePayload.macro,
            top_stocks: livePayload.top_stocks,
            alerts: livePayload.alerts,
            portfolio_intelligence: livePayload.portfolio_intelligence,
            ai_performance: livePayload.ai_performance,
          },
        },
        '*'
      );
    }
  } catch (error) {
    console.warn('[NexusDashboard] live hydration failed', error);
  }
}

if (document.readyState === 'interactive' || document.readyState === 'complete') {
  setTimeout(hydrateDashboardFromLiveApi, 0);
} else {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(hydrateDashboardFromLiveApi, 0);
  });
}

window.addEventListener('message', (event) => {
  const type = event && event.data && event.data.type;
  if (type === 'nexus-dashboard-refresh' || type === 'nexus-dashboard-sync' || type === 'nexus-dashboard-live-update') {
    hydrateDashboardFromLiveApi();
  }
});
