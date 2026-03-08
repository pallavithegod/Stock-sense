if (typeof ResearchCockpit === 'undefined') {
    var ResearchCockpit = (function () {
        let container = null;
        let liveUpdaterInterval = null;

        const state = {
            currentStock: 'LT',
            isLive: true,
            chartTimeframe: '3M',
            dataCache: {}
        };

        function init() {
            console.log('🚀 NEXUS AI Cockpit Module Loaded');
        }

        function open(symbol = 'LT') {
            const target = document.getElementById('researchContent');
            if (!target) {
                console.error('Research content div not found');
                return;
            }

            // If the cockpit is already rendered in the target, warn and return
            if (target.querySelector('#research-ui-container')) {
                console.warn('Research Cockpit already open.');
                return;
            }

            state.currentStock = symbol;

            target.innerHTML = `
                <div id="research-ui-container">
                    <!-- HEADER -->
                    <div class="header">
                        <div class="header-left">
                            <div class="logo-section">
                                <i class="fas fa-brain logo-icon"></i>
                                <span class="logo-text">NEXUS AI QUANTUM</span>
                            </div>
                            
                            <div class="stock-ticker">
                                <div class="ticker-symbol">${state.currentStock} (${state.currentStock})</div>
                                <span style="color: rgba(255, 255, 255, 0.2);">|</span>
                                <div class="ticker-details">
                                    <div class="ticker-detail-item">
                                        <span class="ticker-detail-label">Price</span>
                                        <span class="ticker-detail-value" id="res-ticker-price">₹3856.40</span>
                                    </div>
                                    <div class="ticker-detail-item">
                                        <span class="ticker-detail-label">Change</span>
                                        <span class="ticker-detail-value" style="color: var(--accent-red);" id="res-ticker-change">-0.24%</span>
                                    </div>
                                </div>
                                <span class="exchange-badge">NSE • LT:10T</span>
                                <span style="color: rgba(255, 255, 255, 0.2);">|</span>
                                <span class="exchange-badge" style="background: rgba(255, 200, 50, 0.1); border-color: var(--accent-yellow); color: var(--accent-yellow);">AM 2</span>
                                <div class="time-display">10:35 AM</div>
                            </div>
                        </div>

                        <div class="header-right">
                            <div class="live-indicator">
                                <div class="pulse-dot"></div>
                                <span class="live-text">LIVE</span>
                            </div>
                            <button id="res-btn-close" style="background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 14px;">
                                <i class="fas fa-times"></i>
                            </button>
                            <button style="background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 14px;">
                                <i class="fas fa-microphone"></i>
                            </button>
                            <button style="background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 14px;">
                                <i class="fas fa-search"></i>
                            </button>
                            <button style="background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 14px;">
                                <i class="fas fa-plus"></i>
                            </button>
                            <button style="background: none; border: none; color: var(--accent-red); cursor: pointer; font-size: 14px;">
                                <i class="fas fa-star"></i>
                            </button>
                        </div>
                    </div>
                    
                    <!-- MAIN CONTAINER -->
                    <div class="main-container">
                        
                        <!-- LEFT PANEL: MARKET RADAR -->
                        <div class="left-panel">
                            
                            <!-- Sector Trends -->
                            <div class="panel-section">
                                <div class="panel-title">
                                    <i class="fas fa-chart-bar"></i> Market Radar
                                </div>
                                <div class="panel-title" style="font-size: 10px; margin-bottom: 8px; border: none; margin-top: -8px;">
                                    Sector Trends
                                </div>
                                <div class="sector-trends">
                                    <div class="sector-item">
                                        <span class="sector-name">Tech</span>
                                        <div class="sector-bar-container">
                                            <div class="sector-bar" style="width: 52%;"></div>
                                        </div>
                                        <span class="sector-percent">52%</span>
                                    </div>
                                    <div class="sector-item">
                                        <span class="sector-name">Finance</span>
                                        <div class="sector-bar-container">
                                            <div class="sector-bar" style="width: 38%;"></div>
                                        </div>
                                        <span class="sector-percent">38%</span>
                                    </div>
                                    <div class="sector-item">
                                        <span class="sector-name">Energy</span>
                                        <div class="sector-bar-container">
                                            <div class="sector-bar negative" style="width: 25%;"></div>
                                        </div>
                                        <span class="sector-percent">25%</span>
                                    </div>
                                    <div class="sector-item">
                                        <span class="sector-name">Industrial</span>
                                        <div class="sector-bar-container">
                                            <div class="sector-bar negative" style="width: 15%;"></div>
                                        </div>
                                        <span class="sector-percent">15%</span>
                                    </div>
                                </div>
                            </div>

                            <!-- AI Signals -->
                            <div class="panel-section">
                                <div class="panel-title">
                                    <i class="fas fa-flask"></i> AI Signals
                                </div>
                                <div class="ai-signals">
                                    <div class="signal-item">
                                        <div class="signal-label">
                                            <i class="fas fa-arrow-up"></i> BUY
                                        </div>
                                        <div class="signal-bar">
                                            <div class="signal-fill" style="width: 52%;"></div>
                                        </div>
                                        <div class="signal-count">19</div>
                                        <div class="signal-percent">52%</div>
                                    </div>
                                    <div class="signal-item">
                                        <div class="signal-label">
                                            <i class="fas fa-pause"></i> HOLD
                                        </div>
                                        <div class="signal-bar">
                                            <div class="signal-fill" style="width: 33%; background: var(--accent-blue);"></div>
                                        </div>
                                        <div class="signal-count">8</div>
                                        <div class="signal-percent">33%</div>
                                    </div>
                                    <div class="signal-item">
                                        <div class="signal-label">
                                            <i class="fas fa-arrow-down"></i> SELL
                                        </div>
                                        <div class="signal-bar">
                                            <div class="signal-fill" style="width: 15%; background: var(--accent-red);"></div>
                                        </div>
                                        <div class="signal-count">3</div>
                                        <div class="signal-percent">15%</div>
                                    </div>
                                </div>
                            </div>

                            <!-- Live Alerts -->
                            <div class="panel-section">
                                <div class="panel-title">
                                    <i class="fas fa-bell"></i> Live Alerts
                                </div>
                                <div class="live-alerts">
                                    <div class="alert-item warning">
                                        <strong>Energy sector breakout</strong>
                                        <div class="alert-time">8h ago</div>
                                    </div>
                                    <div class="alert-item warning">
                                        <strong>High volatility detected</strong>
                                        <div class="alert-time">13m ago</div>
                                    </div>
                                    <div class="alert-item warning">
                                        <strong>Confidence drop in INFY</strong>
                                        <div class="alert-time">38m ago</div>
                                    </div>
                                </div>
                            </div>

                            <!-- Correlated Assets -->
                            <div class="panel-section">
                                <div class="panel-title">
                                    <i class="fas fa-link"></i> Correlated Assets
                                </div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; justify-items: center;">
                                    <div class="correlation-widget">
                                        <div class="correlation-circle">36%</div>
                                        <div class="correlation-text">TECH</div>
                                    </div>
                                    <div class="correlation-widget">
                                        <div class="correlation-circle" style="border-color: var(--accent-orange); background: radial-gradient(circle, rgba(255, 153, 51, 0.2), transparent);">
                                            <span style="color: var(--accent-orange);">29%</span>
                                        </div>
                                        <div class="correlation-text">ENERGY</div>
                                    </div>
                                    <div class="correlation-widget">
                                        <div class="correlation-circle" style="border-color: var(--accent-red); background: radial-gradient(circle, rgba(255, 68, 68, 0.2), transparent);">
                                            <span style="color: var(--accent-red);">18%</span>
                                        </div>
                                        <div class="correlation-text">VOLATILITY</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- CENTER PANEL: MAIN CHART & TIMELINE -->
                        <div class="center-panel">
                            <div class="chart-area">
                                
                                <!-- Chart Header -->
                                <div class="chart-header">
                                    <div class="chart-title">
                                        <i class="fas fa-chart-line" style="color: var(--accent-cyan);"></i>
                                        <span class="chart-title-text">${state.currentStock} (${state.currentStock})</span>
                                        <span style="color: var(--accent-red); font-size: 12px; font-weight: 700;">↑</span>
                                    </div>
                                    <div class="chart-timeframe">
                                        <button class="timeframe-btn">1D</button>
                                        <button class="timeframe-btn">1W</button>
                                        <button class="timeframe-btn">1M</button>
                                        <button class="timeframe-btn active">3M</button>
                                        <button class="timeframe-btn">1Y</button>
                                    </div>
                                </div>

                                <!-- Main Chart Canvas -->
                                <div class="chart-container">
                                    <div class="chart-canvas" id="mainChart">
                                        <svg style="width: 100%; height: 100%; position: absolute;" viewBox="0 0 800 300">
                                            <!-- Grid -->
                                            <defs>
                                                <pattern id="grid" width="40" height="20" patternUnits="userSpaceOnUse">
                                                    <path d="M 40 0 L 0 0 0 20" fill="none" stroke="rgba(0,255,255,0.1)" stroke-width="0.5"/>
                                                </pattern>
                                            </defs>
                                            <rect width="800" height="300" fill="url(#grid)" />
                                            
                                            <!-- Candlestick chart approximation with lines -->
                                            <polyline points="20,150 60,120 100,130 140,100 180,110 220,90 260,80 300,70 340,75 380,60 420,50 460,45 500,40 540,50 580,45 620,55 660,50 700,60 740,65 780,70" 
                                                    stroke="#00ff00" stroke-width="1.5" fill="none" opacity="0.7"/>
                                            
                                            <!-- Upper band (P95) -->
                                            <polyline points="20,130 60,100 100,110 140,80 180,90 220,70 260,60 300,50 340,55 380,40 420,30 460,25 500,20 540,30 580,25 620,35 660,30 700,40 740,45 780,50" 
                                                    stroke="#39ff14" stroke-width="1" fill="none" opacity="0.4" stroke-dasharray="5,5"/>
                                            
                                            <!-- Lower band (P5) -->
                                            <polyline points="20,170 60,140 100,150 140,120 180,130 220,110 260,100 300,90 340,95 380,80 420,70 460,65 500,60 540,70 580,65 620,75 660,70 700,80 740,85 780,90" 
                                                    stroke="#ff4444" stroke-width="1" fill="none" opacity="0.4" stroke-dasharray="5,5"/>
                                        </svg>
                                    </div>
                                </div>

                                <!-- Regime Shift Timeline -->
                                <div class="regime-timeline">
                                    <div class="regime-title">
                                        <i class="fas fa-wave-square"></i> Regime Shift Timeline
                                    </div>
                                    <div class="regime-bar">
                                        <div class="regime-segment ranging" style="width: 15%;">
                                            <span>RANGING</span>
                                        </div>
                                        <div class="regime-segment trending" style="width: 45%;">
                                            <span>TRENDING</span>
                                        </div>
                                        <div class="regime-segment volatility" style="width: 25%;">
                                            <span>HIGH VOL</span>
                                        </div>
                                        <div class="regime-segment trending" style="width: 15%;">
                                            <span>TRENDING</span>
                                        </div>
                                    </div>
                                </div>

                                <!-- AI Market Memory -->
                                <div class="ai-market-memory">
                                    <div class="memory-title">
                                        <i class="fas fa-brain"></i> AI Market Memory
                                    </div>
                                    <div class="memory-stat">
                                        <div class="memory-icon"><i class="fas fa-history"></i></div>
                                        <div class="memory-content">
                                            <div class="memory-label">Recall Rate</div>
                                            <div class="memory-value">38%</div>
                                        </div>
                                    </div>
                                    <div class="memory-stat">
                                        <div class="memory-icon"><i class="fas fa-network-wired"></i></div>
                                        <div class="memory-content">
                                            <div class="memory-label">Success Rate</div>
                                            <div class="memory-value">4/5</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- RIGHT PANEL: STRATEGY & INTELLIGENCE -->
                        <div class="right-panel">
                            
                            <!-- Strategy Actions Header -->
                            <div class="strategy-section">
                                <div class="strategy-header">
                                    <div class="strategy-title">
                                        <i class="fas fa-shield-alt"></i> RL Strategy Actions
                                    </div>
                                </div>
                                <div class="confidence-display">
                                    <span class="confidence-level">CONFIDENT</span>
                                    <div class="confidence-value" id="res-confidence">46.8%</div>
                                </div>
                            </div>

                            <!-- 28 Neural Layers -->
                            <div class="strategy-section">
                                <div class="strategy-title">
                                    <i class="fas fa-microchip"></i> NEXUS NEURAL LAYERS (28 ENGINES ACTIVE)
                                </div>
                                <div class="neural-layers">
                                    <div class="neural-card active">
                                        <div class="neural-label">Emotional</div>
                                        <div class="neural-value">GREED</div>
                                    </div>
                                    <div class="neural-card active">
                                        <div class="neural-label">Confidence</div>
                                        <div class="neural-value">78.5%</div>
                                    </div>
                                    <div class="neural-card active">
                                        <div class="neural-label">Futures</div>
                                        <div class="neural-value">MULTIWORLD</div>
                                    </div>
                                </div>
                            </div>

                            <!-- AI Console -->
                            <div class="strategy-section">
                                <div class="console-title">
                                    <i class="fas fa-terminal"></i> AI Console
                                </div>
                                <div class="console-input">
                                    <span class="console-text">Analyse ${state.currentStock} volatility...</span>
                                    <button class="console-btn">
                                        <i class="fas fa-paper-plane"></i>
                                    </button>
                                </div>
                                <div style="margin-top: 8px;">
                                    <button class="console-btn" style="width: 100%; padding: 6px 10px; background: rgba(0, 255, 255, 0.2); border-color: var(--accent-cyan); color: var(--accent-cyan);">
                                        + Submit
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Set the global 'container' variable to the newly injected UI root
            container = target.querySelector('#research-ui-container');

            setupEventListeners();
            startLiveUpdates();

            // Trigger data load
            fetchEvolvedPrediction(symbol);
        }

        function close() {
            if (liveUpdaterInterval) {
                clearInterval(liveUpdaterInterval);
                liveUpdaterInterval = null;
            }

            const target = document.getElementById('researchContent');
            if (target) {
                target.innerHTML = ''; // Clear the content of the target div
            }
            container = null; // Reset container reference

            // Restore dashboard view logic
            const dashTab = document.querySelector('[data-tab="dashboard"]');
            if (dashTab) dashTab.click();
        }

        function setupEventListeners() {
            if (!container) return;

            const closeBtn = container.querySelector('#res-btn-close');
            if (closeBtn) {
                closeBtn.onclick = () => close();
            }

            container.querySelectorAll('.timeframe-btn').forEach(btn => {
                btn.onclick = (e) => {
                    if (!container) return;
                    container.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
                    e.target.classList.add('active');
                    state.chartTimeframe = e.target.textContent;
                    console.log('📊 Timeframe changed:', state.chartTimeframe);
                };
            });
        }

        function startLiveUpdates() {
            liveUpdaterInterval = setInterval(() => {
                if (!container) return;

                const timeEl = container.querySelector('.time-display');
                if (timeEl) {
                    timeEl.textContent = new Date().toLocaleTimeString();
                }

                // Pulsing confidence
                const confEl = container.querySelector('#res-confidence');
                if (confEl) {
                    const val = 40 + Math.random() * 20;
                    confEl.textContent = val.toFixed(1) + '%';
                }
            }, 1000);
        }

        async function fetchEvolvedPrediction(symbol) {
            console.log('🔬 Fetching evolved prediction for:', symbol);
            try {
                const resp = await fetch(`/api/evolved-prediction/${symbol}`);
                const data = await resp.json();

                if (!container) return;

                if (data.prediction) {
                    const priceEl = container.querySelector('#res-ticker-price');
                    if (priceEl && data.prediction.price) {
                        priceEl.textContent = '₹' + data.prediction.price;
                    }
                }
            } catch (e) {
                console.error('Failed to fetch cockpit data:', e);
            }
        }

        return {
            init: init,
            open: open,
            close: close
        };
    })();

    document.addEventListener('DOMContentLoaded', () => {
        ResearchCockpit.init();
    });
}
