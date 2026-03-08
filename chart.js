// ============================================================================
// NEXUS QUANTUM AI - COMPLETE PRODUCTION chart.js
// ============================================================================
// Version: 3.0 FINAL - 100% Dynamic Charts
// November 19, 2025, 10:06 PM IST
// Pure API Integration | Auto-Updating | No Hard coding
// ============================================================================

'use strict';

// ============================================================================
// CHART CONFIGURATION
// ============================================================================
const CHART_CONFIG = {
    THEME: {
        background: 'transparent',
        gridColor: 'rgba(255, 255, 255, 0.1)',
        textColor: '#ffffff',
        colors: {
            primary: '#39FF14',
            secondary: '#00D9FF',
            danger: '#ef4444',
            warning: '#f59e0b',
            success: '#22c55e',
            gradient: ['#39FF14', '#00D9FF', '#8B5CF6', '#f59e0b', '#22c55e']
        }
    },
    ANIMATION: {
        duration: 750,
        easing: 'easeInOutQuart'
    },
    UPDATE_INTERVAL: 60000, // 1 minute
    RESPONSIVE: true,
    MAINTAIN_ASPECT_RATIO: false
};

// ============================================================================
// CHART MANAGER
// ============================================================================
class ChartManager {
    constructor() {
        this.charts = {};
        this.updateTimers = {};
    }

    /**
     * Create or update a chart with live data
     */
    async createChart(chartId, type, options = {}) {
        const canvas = document.getElementById(chartId);
        if (!canvas) {
            console.error(`Canvas not found: ${chartId}`);
            return null;
        }

        const ctx = canvas.getContext('2d');

        // Destroy existing chart
        if (this.charts[chartId]) {
            this.charts[chartId].destroy();
        }

        // Get live data
        const data = await this.fetchChartData(options.dataEndpoint || `/api/chart/${type}`);
        
        if (!data) {
            console.error(`No data for chart: ${chartId}`);
            return null;
        }

        // Create chart config
        const config = this.buildChartConfig(type, data, options);

        // Create chart
        this.charts[chartId] = new Chart(ctx, config);

        // Setup auto-update
        if (options.autoUpdate !== false) {
            this.setupAutoUpdate(chartId, type, options);
        }

        console.log(`✅ Chart created: ${chartId}`);
        return this.charts[chartId];
    }

    /**
     * Fetch chart data from API
     */
    async fetchChartData(endpoint) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            return data.success ? data.data : null;
        } catch (error) {
            console.error('Chart data fetch error:', error);
            return null;
        }
    }

    /**
     * Build chart configuration
     */
    buildChartConfig(type, data, options) {
        const baseConfig = {
            type,
            data: this.formatChartData(type, data, options),
            options: {
                responsive: CHART_CONFIG.RESPONSIVE,
                maintainAspectRatio: CHART_CONFIG.MAINTAIN_ASPECT_RATIO,
                animation: CHART_CONFIG.ANIMATION,
                plugins: {
                    legend: {
                        labels: {
                            color: CHART_CONFIG.THEME.textColor,
                            font: { size: 12, family: 'Inter, sans-serif' }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: CHART_CONFIG.THEME.colors.primary,
                        borderWidth: 1,
                        callbacks: options.tooltipCallbacks || {}
                    }
                },
                scales: this.buildScales(type, options)
            }
        };

        return baseConfig;
    }

    /**
     * Format data for different chart types
     */
    formatChartData(type, data, options) {
        if (!data) return { labels: [], datasets: [] };

        switch (type) {
            case 'line':
                return this.formatLineData(data, options);
            case 'bar':
                return this.formatBarData(data, options);
            case 'pie':
            case 'doughnut':
                return this.formatPieData(data, options);
            case 'scatter':
                return this.formatScatterData(data, options);
            default:
                return data;
        }
    }

    /**
     * Format line chart data
     */
    formatLineData(data, options) {
        return {
            labels: data.labels || data.map((_, i) => `Point ${i + 1}`),
            datasets: [{
                label: options.label || 'Data',
                data: data.values || data,
                borderColor: options.color || CHART_CONFIG.THEME.colors.primary,
                backgroundColor: options.backgroundColor || 'rgba(57, 255, 20, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: options.fill !== false,
                pointRadius: 3,
                pointHoverRadius: 6
            }]
        };
    }

    /**
     * Format bar chart data
     */
    formatBarData(data, options) {
        const labels = data.labels || Object.keys(data);
        const values = data.values || Object.values(data);

        return {
            labels,
            datasets: [{
                label: options.label || 'Values',
                data: values,
                backgroundColor: this.generateColors(values.length),
                borderColor: CHART_CONFIG.THEME.colors.primary,
                borderWidth: 1
            }]
        };
    }

    /**
     * Format pie/doughnut chart data
     */
    formatPieData(data, options) {
        const labels = data.labels || Object.keys(data);
        const values = data.values || Object.values(data);

        return {
            labels,
            datasets: [{
                data: values,
                backgroundColor: this.generateColors(labels.length),
                borderColor: '#1a1a1a',
                borderWidth: 2
            }]
        };
    }

    /**
     * Format scatter chart data
     */
    formatScatterData(data, options) {
        return {
            datasets: [{
                label: options.label || 'Data Points',
                data: data.points || data,
                backgroundColor: options.color || CHART_CONFIG.THEME.colors.primary,
                pointRadius: 5,
                pointHoverRadius: 8
            }]
        };
    }

    /**
     * Build scales configuration
     */
    buildScales(type, options) {
        if (type === 'pie' || type === 'doughnut') return {};

        return {
            x: {
                grid: {
                    color: CHART_CONFIG.THEME.gridColor,
                    borderColor: CHART_CONFIG.THEME.gridColor
                },
                ticks: {
                    color: CHART_CONFIG.THEME.textColor,
                    font: { size: 10 }
                }
            },
            y: {
                grid: {
                    color: CHART_CONFIG.THEME.gridColor,
                    borderColor: CHART_CONFIG.THEME.gridColor
                },
                ticks: {
                    color: CHART_CONFIG.THEME.textColor,
                    font: { size: 10 },
                    callback: options.yAxisFormatter || ((value) => value)
                }
            }
        };
    }

    /**
     * Generate gradient colors
     */
    generateColors(count) {
        const colors = CHART_CONFIG.THEME.colors.gradient;
        const result = [];
        for (let i = 0; i < count; i++) {
            result.push(colors[i % colors.length]);
        }
        return result;
    }

    /**
     * Update existing chart with new data
     */
    async updateChart(chartId, newData) {
        const chart = this.charts[chartId];
        if (!chart) {
            console.error(`Chart not found: ${chartId}`);
            return;
        }

        if (newData.labels) chart.data.labels = newData.labels;
        if (newData.datasets) chart.data.datasets = newData.datasets;

        chart.update('active');
        console.log(`✓ Chart updated: ${chartId}`);
    }

    /**
     * Setup auto-update for chart
     */
    setupAutoUpdate(chartId, type, options) {
        // Clear existing timer
        if (this.updateTimers[chartId]) {
            clearInterval(this.updateTimers[chartId]);
        }

        // Set new timer
        this.updateTimers[chartId] = setInterval(async () => {
            const data = await this.fetchChartData(options.dataEndpoint || `/api/chart/${type}`);
            if (data) {
                const formatted = this.formatChartData(type, data, options);
                await this.updateChart(chartId, formatted);
            }
        }, options.updateInterval || CHART_CONFIG.UPDATE_INTERVAL);
    }

    /**
     * Destroy chart and cleanup
     */
    destroyChart(chartId) {
        if (this.charts[chartId]) {
            this.charts[chartId].destroy();
            delete this.charts[chartId];
        }

        if (this.updateTimers[chartId]) {
            clearInterval(this.updateTimers[chartId]);
            delete this.updateTimers[chartId];
        }

        console.log(`✓ Chart destroyed: ${chartId}`);
    }

    /**
     * Destroy all charts
     */
    destroyAll() {
        Object.keys(this.charts).forEach(chartId => this.destroyChart(chartId));
    }
}

// Initialize global chart manager
const chartManager = new ChartManager();

// ============================================================================
// PRE-DEFINED CHART CREATORS
// ============================================================================

/**
 * Portfolio Allocation Chart (Doughnut)
 */
async function createPortfolioChart() {
    return await chartManager.createChart('portfolio-chart', 'doughnut', {
        dataEndpoint: '/api/portfolio/allocation',
        label: 'Portfolio Allocation',
        autoUpdate: true,
        updateInterval: 60000,
        tooltipCallbacks: {
            label: function(context) {
                const label = context.label || '';
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ₹${value.toLocaleString()} (${percentage}%)`;
            }
        }
    });
}

/**
 * AI Performance Chart (Line)
 */
async function createPerformanceChart() {
    return await chartManager.createChart('performance-chart', 'line', {
        dataEndpoint: '/api/analytics/performance',
        label: 'AI Prediction Accuracy',
        color: CHART_CONFIG.THEME.colors.success,
        fill: true,
        autoUpdate: true,
        updateInterval: 120000,
        yAxisFormatter: (value) => `${value}%`
    });
}

/**
 * Sector Analysis Chart (Bar)
 */
async function createSectorChart() {
    return await chartManager.createChart('sector-chart', 'bar', {
        dataEndpoint: '/api/analytics/sectors',
        label: 'Sector Performance',
        autoUpdate: true,
        updateInterval: 180000,
        yAxisFormatter: (value) => `${value}%`
    });
}

/**
 * Stock Price History (Line)
 */
async function createStockPriceChart(symbol) {
    return await chartManager.createChart(`stock-${symbol}-chart`, 'line', {
        dataEndpoint: `/api/stock/${symbol}/history`,
        label: `${symbol} Price`,
        color: CHART_CONFIG.THEME.colors.secondary,
        autoUpdate: true,
        updateInterval: 60000,
        yAxisFormatter: (value) => `₹${value.toFixed(2)}`
    });
}

/**
 * Prediction Confidence Distribution (Bar)
 */
async function createConfidenceChart() {
    return await chartManager.createChart('confidence-chart', 'bar', {
        dataEndpoint: '/api/predictions/confidence-distribution',
        label: 'Confidence Distribution',
        autoUpdate: true,
        updateInterval: 120000
    });
}

/**
 * Risk vs Return Scatter
 */
async function createRiskReturnChart() {
    return await chartManager.createChart('risk-return-chart', 'scatter', {
        dataEndpoint: '/api/analytics/risk-return',
        label: 'Risk vs Expected Return',
        color: CHART_CONFIG.THEME.colors.warning,
        autoUpdate: true,
        updateInterval: 180000
    });
}

/**
 * Market Trend Chart (Multi-Line)
 */
async function createMarketTrendChart() {
    const data = await chartManager.fetchChartData('/api/analytics/market-trends');
    if (!data) return null;

    const canvas = document.getElementById('market-trend-chart');
    if (!canvas) return null;

    const ctx = canvas.getContext('2d');

    const config = {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'NIFTY 50',
                    data: data.nifty,
                    borderColor: CHART_CONFIG.THEME.colors.primary,
                    backgroundColor: 'rgba(57, 255, 20, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'SENSEX',
                    data: data.sensex,
                    borderColor: CHART_CONFIG.THEME.colors.secondary,
                    backgroundColor: 'rgba(0, 217, 255, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'BANK NIFTY',
                    data: data.banknifty,
                    borderColor: CHART_CONFIG.THEME.colors.warning,
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    labels: { color: CHART_CONFIG.THEME.textColor }
                }
            },
            scales: {
                x: {
                    grid: { color: CHART_CONFIG.THEME.gridColor },
                    ticks: { color: CHART_CONFIG.THEME.textColor }
                },
                y: {
                    grid: { color: CHART_CONFIG.THEME.gridColor },
                    ticks: {
                        color: CHART_CONFIG.THEME.textColor,
                        callback: (value) => `₹${value.toLocaleString()}`
                    }
                }
            }
        }
    };

    chartManager.charts['market-trend-chart'] = new Chart(ctx, config);
    return chartManager.charts['market-trend-chart'];
}

// ============================================================================
// CHART UTILITIES
// ============================================================================

/**
 * Format currency for charts
 */
function formatChartCurrency(value) {
    if (value >= 1e9) return `₹${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `₹${(value / 1e6).toFixed(2)}M`;
    if (value >= 1e3) return `₹${(value / 1e3).toFixed(2)}K`;
    return `₹${value.toFixed(2)}`;
}

/**
 * Initialize all dashboard charts
 */
async function initializeAllCharts() {
    console.log('📊 Initializing all charts...');
    
    const charts = [
        createPortfolioChart(),
        createPerformanceChart(),
        createSectorChart(),
        createConfidenceChart(),
        createMarketTrendChart()
    ];

    await Promise.allSettled(charts);
    console.log('✅ All charts initialized');
}

/**
 * Cleanup all charts on page unload
 */
window.addEventListener('beforeunload', () => {
    chartManager.destroyAll();
});

/**
 * Handle window resize
 */
let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        Object.values(chartManager.charts).forEach(chart => chart.resize());
    }, 250);
});

// ============================================================================
console.log('✅ chart.js v3.0 LOADED - 100% Dynamic');
// ============================================================================

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        chartManager,
        createPortfolioChart,
        createPerformanceChart,
        createSectorChart,
        createStockPriceChart,
        createConfidenceChart,
        createRiskReturnChart,
        createMarketTrendChart,
        initializeAllCharts
    };
}
