'use strict';

const NexusCharts = {
  mini: null,
  gauge: null,
  pred: null,
  spark: null,
  p2Spark: null,
  predMode: '1D2'
};

function getLiveDashboardState() {
  try {
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

function isNonEmptyObject(value) {
  return !!value && typeof value === 'object' && Object.keys(value).length > 0;
}

function toFiniteNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function formatSignedPercent(value, digits = 2) {
  const num = Number(value);
  if (!Number.isFinite(num)) return null;
  const sign = num > 0 ? '+' : '';
  return `${sign}${num.toFixed(digits)}%`;
}

function normalizeSentimentGauge(sentiment = {}) {
  const bullishCount = toFiniteNumber(sentiment.bullish_count);
  const neutralCount = toFiniteNumber(sentiment.neutral_count);
  const bearishCount = toFiniteNumber(sentiment.bearish_count);
  const counts = [bullishCount, neutralCount, bearishCount].map((value) => (Number.isFinite(value) && value > 0 ? value : 0));
  const total = counts.reduce((sum, value) => sum + value, 0);

  if (total > 0) {
    const bull = Math.round((counts[0] / total) * 100);
    const neutral = Math.round((counts[1] / total) * 100);
    const bear = Math.max(0, 100 - bull - neutral);
    return { bull, neutral, bear };
  }

  return { bull: null, neutral: null, bear: null };
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

function buildPredictionSets(state = {}) {
  const labels = Array.isArray(state.predLabels) ? state.predLabels.filter(Boolean) : [];
  const pred = Array.isArray(state.predictions) ? state.predictions.map((value) => toFiniteNumber(value)).filter((value) => value !== null) : [];
  const real = Array.isArray(state.reality) ? state.reality.map((value) => toFiniteNumber(value)).filter((value) => value !== null) : [];
  const limit = Math.min(labels.length || pred.length || real.length, pred.length || real.length || labels.length);

  if (!limit) {
    return {
      '1D2': { labels: [], pred: [], real: [] },
      '1B': { labels: [], pred: [], real: [] }
    };
  }

  const baseLabels = labels.length ? labels.slice(-limit) : Array.from({ length: limit }, (_, idx) => `P${idx + 1}`);
  const basePred = pred.slice(-limit);
  const baseReal = real.slice(-limit);
  const weeklyLimit = Math.min(limit, 7);

  return {
    '1D2': {
      labels: baseLabels,
      pred: basePred,
      real: baseReal
    },
    '1B': {
      labels: baseLabels.slice(-weeklyLimit),
      pred: basePred.slice(-weeklyLimit),
      real: baseReal.slice(-weeklyLimit)
    }
  };
}

function registerChartDefaults() {
  if (!window.Chart) return;
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
}

function destroyChart(key) {
  if (NexusCharts[key]) {
    NexusCharts[key].destroy();
    NexusCharts[key] = null;
  }
}

function initMiniChart(series = []) {
  const el = document.getElementById('miniChart');
  if (!el || !window.Chart) return;
  if (!Array.isArray(series) || !series.length) return;
  destroyChart('mini');
  const ctx = el.getContext('2d');
  const fill = ctx.createLinearGradient(0, 0, 0, 50);
  fill.addColorStop(0, 'rgba(74,222,128,0.36)');
  fill.addColorStop(1, 'rgba(74,222,128,0)');
  NexusCharts.mini = new Chart(ctx, {
    type: 'line',
    data: {
      labels: series.map((_, idx) => idx),
      datasets: [{
        data: series,
        borderColor: '#4ade80',
        backgroundColor: fill,
        fill: true,
        pointRadius: 0,
        borderWidth: 1.6,
        tension: 0.42
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 900 },
      scales: { x: { display: false }, y: { display: false } },
      plugins: { legend: { display: false }, tooltip: { enabled: false } }
    }
  });
}

function initGauge(bull = null, neutral = null, bear = null) {
  const el = document.getElementById('gaugeCanvas');
  if (!el || !window.Chart) return;
  if (![bull, neutral, bear].every((value) => value !== null && value !== undefined && Number.isFinite(Number(value)))) return;
  destroyChart('gauge');
  NexusCharts.gauge = new Chart(el.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: ['Bull', 'Neutral', 'Bear'],
      datasets: [{
        data: [bull, neutral, bear],
        backgroundColor: ['#4ade80', '#fb923c', '#f87171'],
        borderWidth: 0,
        circumference: 180,
        rotation: 270,
        cutout: '72%',
        hoverOffset: 4
      }]
    },
    options: {
      responsive: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed}%` }
        }
      },
      animation: { duration: 1100 }
    }
  });

  const gvBull = document.getElementById('gvBull');
  const gvNeutral = document.getElementById('gvNeutral');
  const gsBull = document.getElementById('gsBull');
  const gsNeutral = document.getElementById('gsNeutral');
  const gsBear = document.getElementById('gsBear');
  if (gvBull) gvBull.textContent = bull;
  if (gvNeutral) gvNeutral.textContent = neutral;
  if (gsBull) gsBull.textContent = `${bull}%`;
  if (gsNeutral) gsNeutral.textContent = `${neutral}%`;
  if (gsBear) gsBear.textContent = `${bear}%`;
}

function buildPredChart(mode = '1D2') {
  NexusCharts.predMode = mode || '1D2';
  const el = document.getElementById('predChart');
  if (!el || !window.Chart) return;
  const liveSets = window.__NEXUS_PRED_SETS || buildPredictionSets(getLiveDashboardState());
  const dataset = liveSets[NexusCharts.predMode] || liveSets['1D2'];
  if (!dataset || !Array.isArray(dataset.labels) || !dataset.labels.length) return;
  destroyChart('pred');
  const ctx = el.getContext('2d');
  const fillPred = ctx.createLinearGradient(0, 0, 0, 220);
  fillPred.addColorStop(0, 'rgba(79,209,197,0.25)');
  fillPred.addColorStop(1, 'rgba(79,209,197,0)');
  const fillReal = ctx.createLinearGradient(0, 0, 0, 220);
  fillReal.addColorStop(0, 'rgba(167,139,250,0.18)');
  fillReal.addColorStop(1, 'rgba(167,139,250,0)');

  NexusCharts.pred = new Chart(ctx, {
    type: 'line',
    data: {
      labels: dataset.labels,
      datasets: [{
        label: 'AI Prediction',
        data: dataset.pred,
        borderColor: '#4fd1c5',
        backgroundColor: fillPred,
        borderWidth: 2.5,
        pointRadius: 6,
        pointBackgroundColor: '#4fd1c5',
        pointBorderColor: '#0d0d0f',
        pointBorderWidth: 2,
        pointHoverRadius: 9,
        tension: 0.42,
        fill: true,
        order: 1
      }, {
        label: 'Actual Outcome',
        data: dataset.real,
        borderColor: '#a78bfa',
        backgroundColor: fillReal,
        borderWidth: 2.2,
        borderDash: [6, 4],
        pointRadius: 6,
        pointBackgroundColor: '#a78bfa',
        pointBorderColor: '#0d0d0f',
        pointBorderWidth: 2,
        pointHoverRadius: 9,
        tension: 0.42,
        fill: true,
        order: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      animation: { duration: 1200, easing: 'easeInOutQuart' },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          align: 'end',
          labels: {
            color: '#888890',
            font: { size: 11, weight: '600' },
            boxWidth: 14,
            boxHeight: 5,
            padding: 16
          }
        },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}%`
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#666670', font: { size: 11 } }
        },
        y: {
          min: 91,
          max: 98,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: {
            color: '#666670',
            font: { size: 11 },
            callback: value => `${Number(value).toFixed(0)}%`
          }
        }
      }
    }
  });
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
  NexusCharts.spark = new Chart(canvas.getContext('2d'), {
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
    NexusCharts.p2Spark = new Chart(canvas.getContext('2d'), {
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

function startClock() {
  const el = document.getElementById('liveClock');
  if (!el) return;
  const tick = () => {
    const now = new Date();
    el.textContent = now.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };
  tick();
  setInterval(tick, 1000);
}

function formatInrCompact(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return '--';
  return num.toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

function renderTopStocksCard() {
  const body = document.getElementById('nexusTopStocksBody');
  if (!body) return;

  const liveState = getLiveDashboardState();
  const stocks = Array.isArray(liveState.topStocks)
    ? liveState.topStocks.slice()
    : Array.isArray(liveState.data?.top_stocks)
      ? liveState.data.top_stocks.slice()
      : Array.isArray(window.dashState?.stocks)
        ? window.dashState.stocks.slice()
        : [];
  if (!stocks.length) {
    body.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#888890;padding:10px 0;">Live stock feed is syncing...</td></tr>';
    return;
  }

  const rows = stocks
    .slice()
    .sort((a, b) => Number(b.change_percent ?? b.change_pct ?? b.change ?? 0) - Number(a.change_percent ?? a.change_pct ?? a.change ?? 0))
    .slice(0, 3)
    .map(stock => {
      const symbol = String(stock.symbol || '--').replace('.NS', '').replace('.BO', '');
      const price = Number(stock.current_price ?? stock.last_price ?? stock.price);
      const change = Number(stock.change_percent ?? stock.change_pct ?? stock.change);
      const signal = String(stock.prediction_signal ?? stock.signal ?? '').trim().toUpperCase() || '--';
      return `
        <tr>
          <td class="sym sym-t">${symbol}</td>
          <td class="price-cell">Rs ${Number.isFinite(price) ? price.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '--'}</td>
          <td><span class="${change >= 0 ? 'chg-g' : 'chg-r'}">${Number.isFinite(change) ? `${change >= 0 ? '^ +' : '^ '}${change.toFixed(2)}%` : '--'} ${signal}</span></td>
        </tr>
      `;
    })
    .join('');

  body.innerHTML = rows;
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
  const predRows = Array.isArray(window.__INTEL_PRED_ROWS) && window.__INTEL_PRED_ROWS.length
    ? window.__INTEL_PRED_ROWS
    : (Array.isArray(dashState.predRows) ? dashState.predRows : Array.isArray(dashState.predictionRows) ? dashState.predictionRows : Array.isArray(dashState.predictions) ? dashState.predictions : []);

  const predLabels = Array.isArray(dashState.predLabels) && dashState.predLabels.length
    ? dashState.predLabels.slice(0, 7)
    : predRows.slice(0, 7).map((row, idx) => String(row?.label || row?.symbol || row?.name || `P${idx + 1}`).replace(/\.NS|\.BO/g, ''));
  const predictions = Array.isArray(dashState.predictions) && dashState.predictions.length && typeof dashState.predictions[0] === 'number'
    ? dashState.predictions.slice(0, 7)
    : predRows
        .slice(0, 7)
        .map((row) => toFiniteNumber(row?.prediction ?? row?.predicted_value ?? row?.confidence ?? row?.prediction?.confidence))
        .filter((value) => value !== null);
  const reality = Array.isArray(dashState.reality) && dashState.reality.length && typeof dashState.reality[0] === 'number'
    ? dashState.reality.slice(0, 7)
    : predRows
        .slice(0, 7)
        .map((row) => toFiniteNumber(row?.actual ?? row?.actual_value ?? row?.predicted_return ?? row?.prediction?.predicted_return))
        .filter((value) => value !== null);

  return {
    bull: resolvedGauge.bull,
    neutral: resolvedGauge.neutral,
    bear: resolvedGauge.bear,
    portfolioValue,
    accuracy,
    totalPredictions,
    predLabels,
    predictions,
    reality,
    topStocks: Array.isArray(dashState.topStocks)
      ? dashState.topStocks.slice(0, 10)
      : Array.isArray(data.top_stocks)
        ? data.top_stocks.slice(0, 10)
        : [],
    newsItems: Array.isArray(dashState.newsItems)
      ? dashState.newsItems.slice(0, 6)
      : Array.isArray(dashState.news)
        ? dashState.news.slice(0, 6)
        : [],
    alerts: Array.isArray(dashState.alerts)
      ? dashState.alerts.slice(0, 6)
      : Array.isArray(dashState.portfolioNewsAlerts)
        ? dashState.portfolioNewsAlerts.slice(0, 6)
        : [],
    indices: {
      nifty50: toFiniteNumber(dashState.indices?.nifty50 ?? indexMap.nifty?.value),
      sensex: toFiniteNumber(dashState.indices?.sensex ?? indexMap.sensex?.value),
      banknifty: toFiniteNumber(dashState.indices?.banknifty ?? indexMap.bank?.value),
      nifty50Change: toFiniteNumber(dashState.indices?.nifty50Change ?? indexMap.nifty?.change_percent),
      sensexChange: toFiniteNumber(dashState.indices?.sensexChange ?? indexMap.sensex?.change_percent),
      bankniftyChange: toFiniteNumber(dashState.indices?.bankniftyChange ?? indexMap.bank?.change_percent)
    },
    portfolioPositions: Array.isArray(portfolio.positions) ? portfolio.positions.length : null,
    portfolioPnl,
    portfolioChangePercent,
    modelsActive,
    aiEngine,
    marketStatus: data.market_status?.status || dashState.marketStatus || null,
    marketSession: data.market_status?.session || dashState.marketSession || null,
    nextOpen: data.market_status?.next_open || dashState.nextOpen || null,
    marketSentiment: sentiment
  };
}

function refreshFromState(input = {}) {
  const merged = Object.keys(input || {}).length ? { ...collectCurrentState(), ...input } : collectCurrentState();
  window.__NEXUS_DASHBOARD_STATE = merged;
  window.__NEXUS_PRED_SETS = buildPredictionSets(merged);

  initGauge(merged.bull, merged.neutral, merged.bear);
  initMiniChart(buildMiniSeries(merged));
  buildPredChart(NexusCharts.predMode || '1D2');
  initSparkMini(buildMiniSeries(merged));
  initP2MiniSpark(buildMiniSeries(merged));

  const portVal = document.getElementById('portVal');
  if (portVal) portVal.textContent = Number.isFinite(Number(merged.portfolioValue)) ? `Rs ${formatInrCompact(merged.portfolioValue)}` : '--';

  const sbAccuracy = document.getElementById('sbAccuracy');
  if (sbAccuracy) sbAccuracy.textContent = Number.isFinite(Number(merged.accuracy)) ? `${Number(merged.accuracy).toFixed(2)}%` : '--';

  const sbTotalPred = document.getElementById('sbTotalPred');
  if (sbTotalPred) sbTotalPred.textContent = Number.isFinite(Number(merged.totalPredictions)) ? formatInrCompact(merged.totalPredictions) : '--';

  const dashboardGain = document.querySelector('.sb-card--dashboard .sb-stat-green');
  if (dashboardGain) {
    if (Number.isFinite(Number(merged.portfolioPnl))) {
      const pnl = Number(merged.portfolioPnl);
      dashboardGain.textContent = `${pnl >= 0 ? '+ ' : '- '}${formatInrCompact(Math.abs(pnl))}`;
    } else if (Number.isFinite(Number(merged.totalPredictions))) {
      dashboardGain.textContent = `+ ${formatInrCompact(merged.totalPredictions)}`;
    } else {
      dashboardGain.textContent = '--';
    }
  }

  const dashboardBadge = document.querySelector('.sb-card--dashboard .sb-badge-green');
  if (dashboardBadge) {
    dashboardBadge.textContent = Number.isFinite(Number(merged.modelsActive))
      ? `+${Math.round(Number(merged.modelsActive))}%`
      : (Number.isFinite(Number(merged.accuracy)) ? `${Number(merged.accuracy).toFixed(0)}%` : '--');
  }

  const dashboardReturnPct = document.querySelector('.sb-card--dashboard .sb-row-pct');
  if (dashboardReturnPct) {
    dashboardReturnPct.textContent = formatSignedPercent(merged.portfolioChangePercent) || '--';
  }

  const chartPct = document.querySelector('.sb-card--chart .sb-chart-pct');
  if (chartPct) {
    const livePct = Number.isFinite(Number(merged.marketSentiment?.confidence))
      ? Number(merged.marketSentiment.confidence) / 10
      : Number(merged.accuracy) / 10;
    chartPct.textContent = Number.isFinite(livePct) ? livePct.toFixed(1) : '--';
  }

  const chartChange = document.querySelector('.sb-card--chart .sb-chart-change-pos');
  if (chartChange) {
    chartChange.textContent = formatSignedPercent(merged.indices.nifty50Change) || '--';
  }

  const chartPrice = document.querySelector('.sb-card--chart .sb-chart-price');
  if (chartPrice) {
    chartPrice.textContent = Number.isFinite(Number(merged.indices.nifty50))
      ? Number(merged.indices.nifty50).toLocaleString('en-IN', { maximumFractionDigits: 2 })
      : '--';
  }

  const chartChangeSm = document.querySelector('.sb-card--chart .sb-stat-green-sm');
  if (chartChangeSm) {
    chartChangeSm.textContent = formatSignedPercent(merged.indices.nifty50Change) || '--';
  }

  const nifty50 = document.getElementById('nifty50');
  const sensex = document.getElementById('sensex');
  const banknifty = document.getElementById('banknifty');
  if (nifty50 && merged.indices.nifty50 != null) nifty50.textContent = formatInrCompact(merged.indices.nifty50);
  if (sensex && merged.indices.sensex != null) sensex.textContent = formatInrCompact(merged.indices.sensex);
  if (banknifty && merged.indices.banknifty != null) banknifty.textContent = formatInrCompact(merged.indices.banknifty);

  const marketStatusText = document.getElementById('marketStatusText');
  if (marketStatusText) marketStatusText.textContent = merged.marketStatus ? String(merged.marketStatus).toUpperCase() : '--';

  const marketSession = document.getElementById('marketSession');
  if (marketSession) marketSession.textContent = merged.marketSession || '--';

  const nextOpen = document.getElementById('nextOpen');
  if (nextOpen) nextOpen.textContent = merged.nextOpen || '--';

  const momentum = document.querySelector('.sb-section .sb-val-green-dot');
  if (momentum) {
    momentum.textContent = Number.isFinite(Number(merged.bull)) ? `● ${Number(merged.bull).toFixed(1)}%` : '--';
  }

  const cycleBadge = document.querySelector('.sb-section .sb-badge-cyan');
  if (cycleBadge) {
    cycleBadge.textContent = Number.isFinite(Number(merged.modelsActive))
      ? `Cycle: ${Math.max(1, Math.round(Number(merged.modelsActive))) }`
      : 'Cycle: --';
  }

  const syncFill = document.querySelector('.sb-card--sync .sb-sync-fill');
  if (syncFill) {
    const width = Number.isFinite(Number(merged.accuracy)) ? Math.max(0, Math.min(100, Number(merged.accuracy))) : 0;
    syncFill.style.width = `${width}%`;
  }

  const selfLearnFill = document.querySelector('.sb-card--selflearn .sb-selflearn-fill');
  if (selfLearnFill) {
    const width = Number.isFinite(Number(merged.modelsActive)) ? Math.max(0, Math.min(100, Number(merged.modelsActive) * 12.5)) : 0;
    selfLearnFill.style.width = `${width}%`;
  }

  renderTopStocksCard();
}

function wirePredictionTabs() {
  document.querySelectorAll('.ptab').forEach(btn => {
    if (!btn.classList.contains('ptab-dd')) {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.ptab').forEach(b => {
          if (!b.classList.contains('ptab-dd')) b.classList.remove('pred-btn--active');
        });
        btn.classList.add('pred-btn--active');
        buildPredChart(btn.dataset.mode || '1D2');
      });
    }
  });
}

window.NexusAPI = {
  refresh: refreshFromState
};

window.NexusAICharts = {
  switchTab(button, mode) {
    document.querySelectorAll('.ptab').forEach(b => {
      if (!b.classList.contains('ptab-dd')) b.classList.remove('pred-btn--active');
    });
    if (button) button.classList.add('pred-btn--active');
    NexusCharts.predMode = mode || '1D2';
    buildPredChart(mode);
  },
  refresh: refreshFromState
};

document.addEventListener('DOMContentLoaded', () => {
  registerChartDefaults();
  refreshFromState();
  startClock();
  setInterval(() => refreshFromState(), 5000);
});
