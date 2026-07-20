from pathlib import Path

path = Path(__file__).resolve().parent.parent / 'app.js'
text = path.read_text(encoding='utf-8')
old = """            let elementId = null;

            if (name.includes('NIFTY 50') || name === 'NIFTY') {

                elementId = 'nifty50';

            } else if (name.includes('SENSEX')) {

                elementId = 'sensex';

            } else if (name.includes('BANK NIFTY') || name.includes('BANK')) {

                elementId = 'banknifty';

            }
"""
new = """            const mappings = [
                { test: /NIFTY\\s*50|^NIFTY$/i, id: 'nifty50' },
                { test: /BANK\\s*NIFTY|^BANK$/i, id: 'banknifty' },
                { test: /SENSEX/i, id: 'sensex' },
                { test: /S&P\\s*500|SP500/i, id: 'sp500' },
                { test: /DOW\\s*JONES|DJI|DOW/i, id: 'dowJones' },
                { test: /NASDAQ/i, id: 'nasdaq' }
            ];
            const found = mappings.find(m => m.test.test(name));
            const elementId = found ? found.id : null;
"""
if old not in text:
    raise SystemExit('Old block not found')
path.write_text(text.replace(old, new), encoding='utf-8')
print('patched')
