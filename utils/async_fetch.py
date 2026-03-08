import asyncio
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

TIMEOUT = 10  # seconds

def _fetch_sync(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5d")
        if df.empty:
            return None

        price = float(df["Close"].iloc[-1])
        change = float(df["Close"].pct_change().iloc[-1] * 100)

        return {
            "symbol": symbol,
            "price": price,
            "change": change
        }
    except Exception:
        return None

async def fetch_bulk(symbols):
    loop = asyncio.get_running_loop()

    with ThreadPoolExecutor(max_workers=8) as executor:
        tasks = [
            loop.run_in_executor(executor, _fetch_sync, sym)
            for sym in symbols
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Remove None/failed results
    return [r for r in results if isinstance(r, dict)]
