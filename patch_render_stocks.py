import pathlib

p = pathlib.Path('d:/New3_Working_V5/app.js')
text = p.read_text(encoding='utf-8')
start = text.find('function renderStocksTable()')
end = text.find('function initNeuralPredictionMatrix', start)
if start == -1 or end == -1:
    raise RuntimeError('Could not locate renderStocksTable boundaries')

new_fn = '''function renderStocksTable() {

    if (CONFIG.DEBUG_MODE) console.log('📄 Rendering stocks table with CSS classes...');


    const tbody = document.getElementById('stocksTableBody') ||
        document.querySelector('#stocksTable tbody') ||
        document.querySelector('tbody');


    if (!tbody) {
        console.error('❌ Table tbody not found');
        return;
    }


    if (!dashState.stocks || dashState.stocks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center">Live stock feed is syncing...</td></tr>';
        if (CONFIG.DEBUG_MODE) console.warn('⚠ No stocks data');
        updateStockSortIcons();
        return;
    }


    const stocks = (dashState.stocks || []).slice();
    const sortState = window.__STOCK_SORT || { key: 'symbol', direction: 'asc' };

    const sortValue = (stock, key) => {
        switch (key) {
            case 'price': return Number(stock.current_price ?? stock.last_price ?? stock.price ?? 0);
            case 'change': return Number(stock.change_percent ?? stock.change_pct ?? stock.change ?? stock.price_change ?? 0);
            case 'volume': return Number(stock.volume ?? stock.total_volume ?? stock.trading_volume ?? stock.qty ?? 0);
            case 'confidence': return Number(stock.prediction_confidence ?? stock.confidence ?? stock.confidence_percent ?? 0);
            case 'target': return Number(stock.target_price ?? stock.target ?? stock.price ?? 0);
            case 'aiSize': return Number(stock.allocation ?? stock.allocation_pct ?? stock.ai_size ?? 0);
            case 'name': return String(stock.name || stock.company_name || '').toLowerCase();
            case 'signal': return String(stock.prediction_signal || stock.signal || '').toLowerCase();
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
        const cmp = Number(aVal) - Number(bVal);
        return sortState.direction === 'asc' ? cmp : -cmp;
    });


    if (CONFIG.DEBUG_MODE) {
        console.log(`✅ Rendering ${stocks.length} stocks with CSS classes`);
        console.log('Sample stock:', stocks[0]);
    }


    tbody.innerHTML = stocks.map((stock, index) => {
        const symbol = (stock.symbol || '').replace('.NS', '').replace('.BO', '');
        const name = stock.name || stock.company_name || symbol;
        const exchange = stock.exchange || stock.market || 'NSE';
        const price = Number(stock.current_price ?? stock.last_price ?? stock.price ?? 0);
        const change = Number(stock.change_percent ?? stock.change_pct ?? stock.change ?? stock.price_change ?? 0);
        const volume = Number(stock.volume ?? stock.total_volume ?? stock.trading_volume ?? stock.qty ?? 0);
        const signal = String(stock.prediction_signal ?? stock.signal ?? 'HOLD').toUpperCase().trim();
        const confidence = Number(stock.prediction_confidence ?? stock.confidence ?? stock.confidence_percent ?? 0);
        const target = Number(stock.target_price ?? stock.target ?? price || 0);
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
'''
text = text[:start] + new_fn + text[end:]
p.write_text(text, encoding='utf-8')
print('rewrote renderStocksTable')
