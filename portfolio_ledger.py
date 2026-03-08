
class PortfolioLedger:
    """
    STRICT LEDGER LAYER
    Stores recognized AI symbols only.
    """
    def __init__(self):
        self.positions = {}

    def add(self, symbol, qty, price, date=None):
        self.positions[symbol] = {
            "symbol": symbol,
            "quantity": float(qty),
            "avg_price": float(price),
            "purchase_date": date
        }

    def remove(self, symbol):
        self.positions.pop(symbol, None)

    def all(self):
        return list(self.positions.values())

portfolio_ledger = PortfolioLedger()
