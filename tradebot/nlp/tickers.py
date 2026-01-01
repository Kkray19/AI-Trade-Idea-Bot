import re

CASHTAG = re.compile(r"\$([A-Z]{1,6})\b")
UPPER_TICKER = re.compile(r"\b([A-Z]{2,5})\b")

COMMON_FALSES = {"I", "A", "YOLO", "DD", "CEO", "ETF", "IMO", "USA", "GDP", "CPI", "FOMC"}
FUTURES = {"ES","NQ","YM","RTY","CL","GC","SI","NG","ZB","ZN","ZF","ZT","6E","6J","6B"}

def extract_symbols(text: str):
    if not text:
        return []

    found = set()

    for m in CASHTAG.finditer(text):
        sym = m.group(1)
        if sym not in COMMON_FALSES:
            found.add(sym)

    for m in UPPER_TICKER.finditer(text):
        sym = m.group(1)
        if sym in COMMON_FALSES:
            continue
        if sym in FUTURES:
            found.add(sym)
        elif 2 <= len(sym) <= 5:
            found.add(sym)

    return sorted(found)

def classify_asset_type(symbol: str):
    return "future" if symbol in FUTURES else "stock"
