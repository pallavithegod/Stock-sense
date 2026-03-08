from rapidfuzz import process, fuzz

def fuzzy_filter(query, items, limit=30):
    # Only keep valid dicts with a 'symbol' key
    valid_items = [item for item in items if isinstance(item, dict) and "symbol" in item]

    # Create choices dict
    choices = {item["symbol"]: item for item in valid_items}

    # Perform fuzzy matching
    matches = process.extract(query, choices.keys(), scorer=fuzz.WRatio, limit=limit)

    results = []
    for symbol, score, _ in matches:
        if score > 40:  
            results.append(choices[symbol])

    return results
