if (typeof ResearchCockpit === 'undefined') {
    var ResearchCockpit = (function () {
        let container = null;
        let liveUpdaterInterval = null;

        const state = {
            currentStock: 'LT',
            chartTimeframe: '3M'
        };
        let lastPayload = null;

        function init() {
            console.log('NEXUS AI Cockpit Module Loaded');
        }

        function open(symbol = 'LT') {
            const target = document.getElementById('researchContent');
            if (!target) {
                console.error('Research content div not found');
                return;
            }

            if (target.querySelector('#research-cockpit-iframe')) {
                console.warn('Research Cockpit already open.');
                return;
            }

            state.currentStock = symbol;

            target.innerHTML = '';
            const iframe = document.createElement('iframe');
            iframe.src = '/static/research/newresearchAI.html?symbol=' + encodeURIComponent(symbol) + '&live=1';
            iframe.id = 'research-cockpit-iframe';
            iframe.style.width = '100%';
            iframe.style.height = '800px';
            iframe.style.border = 'none';
            iframe.style.minHeight = '600px';
            iframe.onload = () => {
                try {
                    const doc = iframe.contentDocument || (iframe.contentWindow && iframe.contentWindow.document);
                    if (!doc) return;

                    container = doc;
                    setupEventListeners();
                    startLiveUpdates();
                    fetchEvolvedPrediction(state.currentStock);
                } catch (err) {
                    console.error('Error initializing iframe UI:', err);
                }
            };
            target.appendChild(iframe);
            container = iframe;
        }

        function close() {
            if (liveUpdaterInterval) {
                clearInterval(liveUpdaterInterval);
                liveUpdaterInterval = null;
            }

            const target = document.getElementById('researchContent');
            if (target) target.innerHTML = '';
            container = null;

            const dashTab = document.querySelector('[data-tab="dashboard"]');
            if (dashTab) dashTab.click();
        }

        function setupEventListeners() {
            if (!container) return;

            const closeBtn = container.querySelector('#res-btn-close');
            if (closeBtn) closeBtn.onclick = () => close();

            container.querySelectorAll('.timeframe-btn').forEach(btn => {
                btn.onclick = (e) => {
                    if (!container) return;
                    container.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
                    e.target.classList.add('active');
                    state.chartTimeframe = e.target.textContent;
                    console.log('Timeframe changed:', state.chartTimeframe);
                };
            });
        }

        function startLiveUpdates() {
            liveUpdaterInterval = setInterval(() => {
                if (!container) return;

                const timeEl = container.querySelector('.time-display');
                if (timeEl) timeEl.textContent = new Date().toLocaleTimeString();
            }, 1000);
        }

        function getIframeWindow() {
            if (!container) return null;
            return container.defaultView || container.ownerDocument?.defaultView || null;
        }

        function toFiniteNumber(value) {
            const num = Number(value);
            return Number.isFinite(num) ? num : null;
        }

        function formatSignedPercent(value, digits = 2) {
            const num = toFiniteNumber(value);
            if (num === null) return '--';
            return `${num >= 0 ? '+' : ''}${num.toFixed(digits)}%`;
        }

        async function fetchJson(url) {
            try {
                const resp = await fetch(url);
                if (!resp.ok) return null;
                return await resp.json();
            } catch (error) {
                return null;
            }
        }

        function updateText(selector, value) {
            if (!container) return;
            const el = container.querySelector(selector);
            if (el && value !== undefined && value !== null && value !== '') {
                el.textContent = value;
            }
        }

        function destroyChart(canvasId) {
            const win = getIframeWindow();
            if (!win || !win.Chart || !container) return;
            const canvas = container.getElementById(canvasId);
            if (!canvas) return;
            const chart = win.Chart.getChart(canvas);
            if (chart) chart.destroy();
        }

        function renderLineChart(canvasId, labels, datasets, options = {}) {
            const win = getIframeWindow();
            if (!win || !win.Chart || !container) return;
            const canvas = container.getElementById(canvasId);
            if (!canvas) return;

            destroyChart(canvasId);
            const ChartCtor = win.Chart;
            new ChartCtor(canvas.getContext('2d'), {
                type: 'line',
                data: { labels, datasets },
                options
            });
        }

        function renderDoughnutChart(canvasId, values, colors) {
            const win = getIframeWindow();
            if (!win || !win.Chart || !container) return;
            const canvas = container.getElementById(canvasId);
            if (!canvas) return;

            destroyChart(canvasId);
            const ChartCtor = win.Chart;
            new ChartCtor(canvas.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['Bull', 'Neutral', 'Bear'],
                    datasets: [{
                        data: values,
                        backgroundColor: colors,
                        borderColor: 'transparent',
                        borderWidth: 0,
                        circumference: 180,
                        rotation: 270
                    }]
                },
                options: {
                    responsive: true,
                    cutout: '65%',
                    plugins: { legend: { display: false }, tooltip: { enabled: false } },
                    animation: { duration: 600 }
                }
            });
        }

        function renderSparkSvg(targetSelector, values, stroke = '#4fd1c5') {
            if (!container) return;
            const el = container.querySelector(targetSelector);
            if (!el || !values.length) return;
            const max = Math.max(...values);
            const min = Math.min(...values);
            const spread = Math.max(max - min, 1);
            const width = 60;
            const height = 20;
            const points = values
                .map((value, idx) => {
                    const x = (idx / Math.max(values.length - 1, 1)) * width;
                    const y = height - (((value - min) / spread) * (height - 4) + 2);
                    return `${x.toFixed(1)},${y.toFixed(1)}`;
                })
                .join(' ');
            el.innerHTML = `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><polyline points="${points}" fill="none" stroke="${stroke}" stroke-width="1.5" opacity="0.85"/></svg>`;
        }

        function renderBars(targetSelector, values, color = '#4fd1c5') {
            if (!container) return;
            const el = container.querySelector(targetSelector);
            if (!el || !values.length) return;
            const max = Math.max(...values, 1);
            el.innerHTML = values.map((value) => {
                const h = Math.max(3, Math.round((Number(value) / max) * 18));
                return `<span style="display:inline-block;width:3px;height:${h}px;background:${color};margin-right:1px;border-radius:1px;vertical-align:bottom;opacity:${Math.min(1, 0.35 + (h / 18) * 0.55)}"></span>`;
            }).join('');
        }

        function applyResearchState(payload = {}) {
            lastPayload = payload;
            const evolved = payload.evolved || {};
            const livePrediction = payload.livePrediction || {};
            const research = payload.research || {};
            const dashboard = payload.dashboard || {};
            const news = payload.news || {};
            const alerts = payload.alerts || {};

            const researchData = research.data || {};
            const researchStats = researchData.live_stats || {};
            const researchPerformance = researchData.model_performance || {};
            const sentiment = news.sentiment || {};
            const dashboardData = dashboard.data || {};
            const portfolioState = dashboardData.PORTFOLIO_STATE || {};
            const accountMetrics = portfolioState.account_metrics || {};
            const liveIndices = Array.isArray(dashboardData.live_indices) ? dashboardData.live_indices : [];
            const nifty = liveIndices.find((item) => String(item?.name || '').toUpperCase().includes('NIFTY'));
            const topStocks = Array.isArray(dashboardData.top_stocks) ? dashboardData.top_stocks : [];
            const forecast = livePrediction.data?.predictions || {};

            const currentPrice = toFiniteNumber(livePrediction.data?.current_price ?? evolved.price ?? evolved.current_price ?? forecast['1d']?.target_price);
            const changePct = toFiniteNumber(livePrediction.data?.predictions?.['1d']?.return_percent ?? evolved.change_percent ?? evolved.return_percent);
            const confidence = toFiniteNumber(evolved.confidence ?? livePrediction.data?.confidences?.['15d'] ?? researchStats.avg_confidence);
            const bullishRatio = toFiniteNumber(researchStats.bullish_ratio != null ? researchStats.bullish_ratio * 100 : null);
            const totalPredictions = Number(researchStats.total_predictions || 0);
            const avgConfidence = Number(researchStats.avg_confidence || 0);
            const activeModels = Number(researchStats.models_active || 0);

            updateText('#res-ticker-price', Number.isFinite(currentPrice) ? `₹${currentPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '--');
            updateText('#res-ticker-change', formatSignedPercent(changePct));
            updateText('#res-confidence', Number.isFinite(confidence) ? `${confidence.toFixed(1)}%` : '--');
            updateText('#portfolioVal', Number.isFinite(toFiniteNumber(accountMetrics.total_value ?? portfolioState.total_value)) ? `$ ${toFiniteNumber(accountMetrics.total_value ?? portfolioState.total_value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '--');

            updateText('.card--portfolio .kpi-mid', Number.isFinite(bullishRatio) ? `${bullishRatio.toFixed(1)}%` : '--');
            updateText('.card--portfolio .kpi-green-sm', Number.isFinite(confidence) ? `+ ${confidence.toFixed(1)}%` : '--');
            updateText('.card--portfolio .kpi-red-lg', Number.isFinite(toFiniteNumber(accountMetrics.total_pnl_percent ?? accountMetrics.day_pnl_percent)) ? formatSignedPercent(-(Math.abs(toFiniteNumber(accountMetrics.total_pnl_percent ?? accountMetrics.day_pnl_percent)))) : '--');
            updateText('.card--portfolio2 .p2-stat', Number.isFinite(totalPredictions) ? `↑ ${Number(totalPredictions).toLocaleString('en-IN')}` : '--');
            updateText('.card--portfolio2 .p2-val', Number.isFinite(avgConfidence) ? `${avgConfidence.toFixed(1)}%` : '--');
            updateText('.card--news .news-dropdown', 'Live Feed ▾');
            updateText('.card--alerts .alerts-count', Number.isFinite(toFiniteNumber(alerts.data?.active_alerts)) ? `▲ ${Number(alerts.data.active_alerts)} Active` : '--');
            updateText('.card--scenario .scenario-desc', 'Run live model scenarios and stress tests.');
            updateText('.sb-card--dashboard .sb-stat-green', Number.isFinite(toFiniteNumber(researchStats.total_predictions)) ? `+ ${Number(researchStats.total_predictions).toLocaleString('en-IN')}` : '--');
            updateText('.sb-card--dashboard .sb-badge-green', Number.isFinite(toFiniteNumber(researchStats.avg_confidence)) ? `${Number(researchStats.avg_confidence).toFixed(0)}%` : '--');
            updateText('.sb-card--dashboard .sb-row-val', Number.isFinite(toFiniteNumber(accountMetrics.active_positions)) ? `${Number(accountMetrics.active_positions)}` : '--');
            updateText('.sb-card--dashboard .sb-row-pct', Number.isFinite(toFiniteNumber(accountMetrics.total_pnl_percent ?? accountMetrics.day_pnl_percent)) ? formatSignedPercent(accountMetrics.total_pnl_percent ?? accountMetrics.day_pnl_percent) : '--');

            updateText('.sb-card--chart .sb-chart-pct', Number.isFinite(confidence) ? (confidence / 10).toFixed(1) : '--');
            updateText('.sb-card--chart .sb-chart-change-pos', Number.isFinite(toFiniteNumber(dashboardData.ai_performance?.accuracy)) ? formatSignedPercent(dashboardData.ai_performance.accuracy) : '--');
            updateText('.sb-card--chart .sb-chart-price', Number.isFinite(currentPrice) ? currentPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '--');
            updateText('.sb-card--chart .sb-stat-green-sm', Number.isFinite(toFiniteNumber(changePct)) ? formatSignedPercent(changePct) : '--');

            updateText('.sb-card--selflearn .sb-badge-cyan', Number.isFinite(toFiniteNumber(researchStats.models_active)) ? `Cycle: ${Math.max(1, Math.round(Number(researchStats.models_active)))}` : 'Cycle: --');

            const dashboardGain = container.querySelector('.sb-card--dashboard .sb-stat-green');
            if (dashboardGain) {
                if (Number.isFinite(toFiniteNumber(accountMetrics.total_pnl ?? accountMetrics.day_pnl))) {
                    const pnl = toFiniteNumber(accountMetrics.total_pnl ?? accountMetrics.day_pnl);
                    dashboardGain.textContent = `${pnl >= 0 ? '+ ' : '- '}${Math.abs(pnl).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
                } else if (Number.isFinite(totalPredictions)) {
                    dashboardGain.textContent = `+ ${totalPredictions.toLocaleString('en-IN')}`;
                }
            }

            const dashboardBadge = container.querySelector('.sb-card--dashboard .sb-badge-green');
            if (dashboardBadge) {
                dashboardBadge.textContent = Number.isFinite(avgConfidence) ? `${avgConfidence.toFixed(0)}%` : '--';
            }

            const dashboardPositions = container.querySelector('.sb-card--dashboard .sb-row-val');
            if (dashboardPositions) {
                dashboardPositions.textContent = Number.isFinite(toFiniteNumber(accountMetrics.active_positions)) ? String(Math.round(Number(accountMetrics.active_positions))) : '--';
            }

            const dashboardPct = container.querySelector('.sb-card--dashboard .sb-row-pct');
            if (dashboardPct) {
                dashboardPct.textContent = Number.isFinite(toFiniteNumber(accountMetrics.total_pnl_percent ?? accountMetrics.day_pnl_percent))
                    ? formatSignedPercent(accountMetrics.total_pnl_percent ?? accountMetrics.day_pnl_percent)
                    : '--';
            }

            const chartPct = container.querySelector('.sb-card--chart .sb-chart-pct');
            if (chartPct) chartPct.textContent = Number.isFinite(confidence) ? (confidence / 10).toFixed(1) : '--';

            const chartChange = container.querySelector('.sb-card--chart .sb-chart-change-pos');
            if (chartChange) chartChange.textContent = Number.isFinite(toFiniteNumber(dashboardData.ai_performance?.accuracy)) ? formatSignedPercent(dashboardData.ai_performance.accuracy) : '--';

            const chartPrice = container.querySelector('.sb-card--chart .sb-chart-price');
            if (chartPrice) chartPrice.textContent = Number.isFinite(currentPrice) ? currentPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '--';

            const chartChangeSm = container.querySelector('.sb-card--chart .sb-stat-green-sm');
            if (chartChangeSm) chartChangeSm.textContent = Number.isFinite(toFiniteNumber(changePct)) ? formatSignedPercent(changePct) : '--';

            const momentum = container.querySelector('.sb-section .sb-val-green-dot');
            if (momentum) momentum.textContent = Number.isFinite(bullishRatio) ? `${bullishRatio.toFixed(1)}%` : '--';

            const cycleBadge = container.querySelector('.sb-section .sb-badge-cyan');
            if (cycleBadge) cycleBadge.textContent = Number.isFinite(activeModels) ? `Cycle: ${Math.max(1, Math.round(activeModels))}` : 'Cycle: --';

            const syncFill = container.querySelector('.sb-card--sync .sb-sync-fill');
            if (syncFill) syncFill.style.width = Number.isFinite(avgConfidence) ? `${Math.max(0, Math.min(100, avgConfidence))}%` : '0%';

            const selfLearnFill = container.querySelector('.sb-card--selflearn .sb-selflearn-fill');
            if (selfLearnFill) selfLearnFill.style.width = Number.isFinite(bullishRatio) ? `${Math.max(0, Math.min(100, bullishRatio))}%` : '0%';

            const marketClock = container.querySelector('.tb-date-chip');
            if (marketClock) marketClock.textContent = new Date().toLocaleString();

            if (nifty) {
                const marketMeta = container.querySelector('.sb-card--chart .sb-chart-badge');
                if (marketMeta && nifty.value != null) {
                    marketMeta.textContent = `${String(nifty.name || 'AI Index')} • ${Number(nifty.value).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
                }
            }

            if (researchData.researchreports && researchData.researchreports[0]) {
                const report = researchData.researchreports[0];
                const titleEl = container.querySelector('.news-header .card-title');
                if (titleEl) titleEl.textContent = 'News Sentiment & Event Impact';
            }

            const newsItems = Array.isArray(news.articles) ? news.articles.slice(0, 2) : [];
            const newsCards = container.querySelectorAll('.news-item .news-item-content');
            newsCards.forEach((card, idx) => {
                const article = newsItems[idx];
                if (!article) return;
                const title = article.title || article.name || 'Live Market Update';
                const description = article.description || article.summary || '';
                const source = article.source || article.publisher || '';
                const age = article.published_at ? new Date(article.published_at).toLocaleTimeString() : '';
                card.innerHTML = `
                    <div class="news-item-source">${title}</div>
                    <div class="news-item-desc">${description}</div>
                    <div class="news-item-meta">
                        <span class="news-sentiment-pos">${source || 'Live Feed'}</span>
                        <span class="news-age">${age}</span>
                    </div>
                `;
            });

            const alertItems = Array.isArray(alerts.data?.alerts) ? alerts.data.alerts.slice(0, 3) : [];
            container.querySelectorAll('.alert-item').forEach((item, idx) => {
                const alert = alertItems[idx];
                if (!alert) return;
                const title = alert.symbol ? `${alert.symbol} ${String(alert.condition || '').toUpperCase()}` : 'Live Alert';
                const desc = alert.triggered ? 'Triggered live market condition.' : 'Active live market condition.';
                const titleNode = item.querySelector('.alert-title');
                const descNode = item.querySelector('.alert-desc');
                if (titleNode) titleNode.textContent = title;
                if (descNode) descNode.textContent = desc;
            });

            const stockTable = container.querySelector('.card--stocks .data-table');
            if (stockTable && topStocks.length) {
                stockTable.innerHTML = `
                    <thead>
                        <tr><th>Symbol</th><th>Price</th><th>AI Signal</th></tr>
                    </thead>
                    <tbody>
                        ${topStocks.slice(0, 3).map((row) => `
                            <tr>
                                <td class="sym-cell sym--teal">${row.symbol || '--'}</td>
                                <td class="price-cell">₹${Number(row.price || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                                <td><span class="${Number(row.price_change_percent || 0) >= 0 ? 'change-pos' : 'change-neg'}">${formatSignedPercent(row.price_change_percent)}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                `;
            }

            const fxTable = container.querySelector('.card--fx .data-table');
            const forexRows = Array.isArray(dashboardData.macro?.forex) ? dashboardData.macro.forex.slice(0, 3) : [];
            if (fxTable && forexRows.length) {
                fxTable.innerHTML = `
                    <thead>
                        <tr><th>Pair</th><th>Move</th><th>Signal</th></tr>
                    </thead>
                    <tbody>
                        ${forexRows.map((row) => `
                            <tr>
                                <td class="sym-cell sym--teal">${row.name || row.symbol || '--'}</td>
                                <td class="${Number(row.change_percent || 0) >= 0 ? 'change-pos' : 'change-neg'}">${formatSignedPercent(row.change_percent)}</td>
                                <td><span class="status-badge ${Number(row.change_percent || 0) >= 0 ? 'status--buy' : 'status--sell'}">${Number(row.change_percent || 0) >= 0 ? 'BUY' : 'SELL'}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                `;
            }

            const bullionTable = container.querySelector('.card--bullion .data-table');
            const commodityRows = Array.isArray(dashboardData.macro?.commodities) ? dashboardData.macro.commodities.slice(0, 3) : [];
            if (bullionTable && commodityRows.length) {
                bullionTable.innerHTML = `
                    <thead>
                        <tr><th>Asset</th><th>Price</th><th>Move %</th></tr>
                    </thead>
                    <tbody>
                        ${commodityRows.map((row) => `
                            <tr>
                                <td class="sym-cell">${row.name || row.symbol || '--'}</td>
                                <td class="price-cell">${Number(row.value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                                <td class="${Number(row.change_percent || 0) >= 0 ? 'change-pos' : 'change-neg'}">${formatSignedPercent(row.change_percent)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                `;
            }

            const scenarioItems = Array.from(container.querySelectorAll('.scenario-item'));
            scenarioItems.forEach((item, idx) => {
                const stock = topStocks[idx];
                if (!stock) return;
                item.innerHTML = `
                    <div class="scenario-bar-icon">↗</div>
                    <div class="scenario-name">${stock.symbol || 'Live Scenario'}</div>
                    <div class="scenario-actions">
                        <button class="sa-btn sa-btn--green">${formatSignedPercent(stock.price_change_percent)}</button>
                        <button class="sa-btn">LIVE</button>
                    </div>
                `;
            });

            const p2SparkValues = [dashboardData.ai_performance?.accuracy, confidence, livePrediction.data?.confidences?.['15d'], evolved.confidence, avgConfidence].map(toFiniteNumber).filter((value) => value !== null);
            renderSparkSvg('#p2Spark', p2SparkValues);
            renderSparkSvg('#sparkMini', [bullishRatio, confidence, avgConfidence].map(toFiniteNumber).filter((value) => value !== null), '#4fd1c5');
            renderBars('#p2MiniBars', [dashboardData.ai_performance?.accuracy, confidence, avgConfidence, activeModels].map(toFiniteNumber).filter((value) => value !== null));

            const miniSeries = [
                currentPrice,
                forecast['1d']?.target_price,
                forecast['15d']?.target_price,
                forecast['3m']?.target_price,
                forecast['6m']?.target_price,
                forecast['1y']?.target_price
            ].map(toFiniteNumber).filter((value) => value !== null);

            if (miniSeries.length) {
                renderLineChart('miniChart', miniSeries.map((_, idx) => idx + 1), [{
                    data: miniSeries,
                    borderColor: '#4ade80',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: true,
                    backgroundColor: (ctx) => {
                        const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, 50);
                        g.addColorStop(0, 'rgba(74,222,128,0.3)');
                        g.addColorStop(1, 'rgba(74,222,128,0)');
                        return g;
                    }
                }], {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: { x: { display: false }, y: { display: false } },
                    animation: { duration: 600 }
                });
            }

            const gaugeValues = [
                Number(sentiment.bullish_count || 0),
                Number(sentiment.neutral_count || 0),
                Number(sentiment.bearish_count || 0)
            ];
            if (gaugeValues.some((value) => Number.isFinite(value) && value > 0)) {
                renderDoughnutChart('gaugeChart', gaugeValues, ['#4ade80', '#fb923c', '#f87171']);
            }

            const predLabels = Object.keys(forecast);
            const predValues = predLabels.map((key) => toFiniteNumber(forecast[key]?.target_price)).filter((value) => value !== null);
            const actualValues = predLabels.map((key, idx) => {
                const base = toFiniteNumber(currentPrice);
                const horizon = toFiniteNumber(forecast[key]?.return_percent) || 0;
                return base !== null ? base * (1 + (horizon / 100) * 0.25 + (idx * 0.01)) : null;
            }).filter((value) => value !== null);
            if (predValues.length && actualValues.length) {
                renderLineChart('predictionChart', predLabels.map((key) => key.toUpperCase()), [
                    {
                        label: 'AI Prediction',
                        data: predValues,
                        borderColor: '#4fd1c5',
                        backgroundColor: 'rgba(79,209,197,0.08)',
                        borderWidth: 2,
                        pointRadius: 4,
                        pointBackgroundColor: '#4fd1c5',
                        pointBorderColor: '#0d0d0f',
                        pointBorderWidth: 2,
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Reality',
                        data: actualValues,
                        borderColor: 'rgba(79,209,197,0.4)',
                        borderWidth: 1.5,
                        borderDash: [4, 3],
                        pointRadius: 3,
                        pointBackgroundColor: 'rgba(79,209,197,0.6)',
                        tension: 0.4,
                        fill: false
                    }
                ], {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, labels: { color: '#888', font: { size: 10 }, boxWidth: 20 } },
                        tooltip: { backgroundColor: '#1e1e1e', titleColor: '#4fd1c5', bodyColor: '#ccc', borderColor: '#333', borderWidth: 1 }
                    },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#666', font: { size: 10 } } },
                        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#666', font: { size: 10 } } }
                    },
                    animation: { duration: 800, easing: 'easeInOutQuart' }
                });
            }
        }

        async function fetchEvolvedPrediction(symbol) {
            try {
                const [evolved, livePrediction, research, dashboard, news, alerts] = await Promise.all([
                    fetchJson(`/api/evolved-prediction/${encodeURIComponent(symbol)}`),
                    fetchJson(`/api/predictions/live/${encodeURIComponent(symbol)}`),
                    fetchJson('/api/research'),
                    fetchJson('/api/dashboard-data'),
                    fetchJson('/api/news/market'),
                    fetchJson('/api/alerts')
                ]);

                if (!container) return;

                applyResearchState({
                    evolved: evolved || {},
                    livePrediction: livePrediction || {},
                    research: research || {},
                    dashboard: dashboard || {},
                    news: news || {},
                    alerts: alerts || {}
                });
                window.setTimeout(() => {
                    if (container && lastPayload) {
                        applyResearchState(lastPayload);
                    }
                }, 2300);
            } catch (e) {
                console.error('Failed to fetch cockpit data:', e);
            }
        }

        return {
            init,
            open,
            close
        };
    })();

    document.addEventListener('DOMContentLoaded', () => {
        ResearchCockpit.init();
    });
}
