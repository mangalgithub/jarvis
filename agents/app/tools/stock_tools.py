import asyncio
import json
import re

from app.core.llm import LLMUnavailableError, generate_response

STOCK_OPERATIONS = {
    "get_quote",         # current price of a stock
    "get_info",          # detailed info (P/E, 52w high/low, market cap)
    "get_index",         # market indices (Nifty, Sensex)
    "get_mutual_fund",   # MF NAV by name/code
    "get_mf_returns",    # historical MF returns
    "compare_stocks",    # compare two stocks side by side
    "get_top_movers",    # top gainers / losers from Nifty 50
    "get_history",       # price history for a period
}

# Common Indian company name → NSE ticker symbol
COMPANY_ALIASES: dict[str, str] = {
    "reliance": "RELIANCE", "ril": "RELIANCE",
    "tcs": "TCS", "tata consultancy": "TCS",
    "infosys": "INFY", "infy": "INFY",
    "wipro": "WIPRO",
    "hdfc bank": "HDFCBANK", "hdfc": "HDFCBANK",
    "icici bank": "ICICIBANK", "icici": "ICICIBANK",
    "sbi": "SBIN", "state bank": "SBIN",
    "bajaj finance": "BAJFINANCE",
    "tata motors": "TATAMOTORS",
    "asian paints": "ASIANPAINT",
    "itc": "ITC",
    "bharti airtel": "BHARTIARTL", "airtel": "BHARTIARTL",
    "axis bank": "AXISBANK",
    "kotak bank": "KOTAKBANK", "kotak": "KOTAKBANK",
    "l&t": "LT", "larsen": "LT",
    "maruti": "MARUTI", "maruti suzuki": "MARUTI",
    "sun pharma": "SUNPHARMA",
    "hul": "HINDUNILVR", "hindustan unilever": "HINDUNILVR",
    "adani ports": "ADANIPORTS",
    "adani enterprises": "ADANIENT",
    "power grid": "POWERGRID",
    "ntpc": "NTPC",
    "ongc": "ONGC",
    "titan": "TITAN",
    "nestle": "NESTLEIND",
    "dr reddy": "DRREDDY",
    "cipla": "CIPLA",
    "hcl tech": "HCLTECH", "hcl": "HCLTECH",
    "ultratech cement": "ULTRACEMCO",
    "jsw steel": "JSWSTEEL",
    "tata steel": "TATASTEEL",
    "hindalco": "HINDALCO",
    "bajaj auto": "BAJAJ-AUTO",
    "hero motocorp": "HEROMOTOCO",
    "m&m": "M&M", "mahindra": "M&M",
    "divis lab": "DIVISLAB",
    "britannia": "BRITANNIA",
    "eicher motors": "EICHERMOT",
    "shree cement": "SHREECEM",
    "grasim": "GRASIM",
    "upl": "UPL",
    "tech mahindra": "TECHM",
    "indusind bank": "INDUSINDBK",
    "sbilife": "SBILIFE",
    "hdfc life": "HDFCLIFE",
    "apollo hospitals": "APOLLOHOSP",
}

# Index name → yfinance symbol
INDEX_MAP: dict[str, str] = {
    "nifty": "^NSEI", "nifty 50": "^NSEI", "nifty50": "^NSEI",
    "sensex": "^BSESN", "bse": "^BSESN",
    "bank nifty": "^NSEBANK", "banknifty": "^NSEBANK", "nifty bank": "^NSEBANK",
    "midcap": "^CNXMIDCAP", "nifty midcap": "^CNXMIDCAP",
    "smallcap": "^CNXSMALLCAP",
    "it index": "^CNXIT", "nifty it": "^CNXIT",
}

# A representative Nifty 50 subset for top-movers calculation
NIFTY50_SAMPLE = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY",
    "HINDUNILVR", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT",
    "BAJFINANCE", "HCLTECH", "ASIANPAINT", "AXISBANK", "MARUTI",
    "TITAN", "SUNPHARMA", "TATAMOTORS", "WIPRO", "NESTLEIND",
]


def normalize_ticker(raw: str) -> str:
    """Convert company name or partial symbol to .NS yfinance ticker."""
    lower = raw.lower().strip()
    # Already has exchange suffix
    if lower.endswith(".ns") or lower.endswith(".bo"):
        return raw.upper()
    # Check index
    if lower in INDEX_MAP:
        return INDEX_MAP[lower]
    # Check alias map
    for alias, symbol in COMPANY_ALIASES.items():
        if alias in lower or lower in alias:
            return f"{symbol}.NS"
    # Default: treat as NSE symbol
    return f"{raw.upper().strip()}.NS"


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def normalize_stock_command(payload: dict) -> dict:
    operation = payload.get("operation", "get_quote")
    if operation not in STOCK_OPERATIONS:
        operation = "get_quote"
    return {
        "operation": operation,
        "symbol": str(payload.get("symbol") or "").strip().upper(),
        "symbol2": str(payload.get("symbol2") or "").strip().upper(),
        "period": str(payload.get("period") or "1d").strip(),
        "mf_query": str(payload.get("mf_query") or "").strip(),
        "mf_amount": float(payload.get("mf_amount") or 0),
        "mover_type": str(payload.get("mover_type") or "gainers").strip().lower(),
    }


async def parse_stock_command(message: str) -> dict:
    prompt = f"""Parse this stock/market/mutual fund request into strict JSON.

Allowed operations: {", ".join(sorted(STOCK_OPERATIONS))}

JSON shape:
{{
  "operation": "get_quote",
  "symbol": "RELIANCE",
  "symbol2": "",
  "period": "1d",
  "mf_query": "",
  "mf_amount": 0,
  "mover_type": "gainers"
}}

Rules:
- "Reliance stock price / how is TCS doing" → get_quote, symbol = company name
- "Reliance vs TCS" → compare_stocks, symbol + symbol2
- "Nifty / Sensex / Bank Nifty" → get_index, symbol = index name
- "top gainers / top losers today" → get_top_movers, mover_type = gainers/losers
- "Reliance last month / 1 year chart" → get_history, period = 1mo/1y/6mo/3mo
- "Reliance full info / fundamentals" → get_info
- "Axis Bluechip fund NAV / SBI mutual fund" → get_mutual_fund, mf_query = fund name
- "HDFC Top 100 returns / 1 year returns on Mirae" → get_mf_returns, mf_query = fund name
- period values: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y
- Return ONLY JSON. No markdown.

User message: {message}
"""
    try:
        response_text = await generate_response(
            prompt,
            system_prompt="You parse stock/market/mutual-fund commands for Jarvis. Return strict JSON only.",
            temperature=0,
        )
        return normalize_stock_command(_parse_json(response_text))
    except LLMUnavailableError:
        # Regex fallback
        msg = message.lower()
        if any(w in msg for w in ["nifty", "sensex", "bank nifty"]):
            return normalize_stock_command({"operation": "get_index", "symbol": msg})
        if "mutual fund" in msg or " mf " in msg or "nav" in msg:
            return normalize_stock_command({"operation": "get_mutual_fund", "mf_query": message})
        return normalize_stock_command({"operation": "get_quote", "symbol": message})


# ── yfinance helpers (blocking → run in executor) ─────────────────────────────

def _fetch_quote(ticker_symbol: str) -> dict:
    """Blocking call — fetch current quote."""
    import yfinance as yf
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    # Use 5d so we always have data even when market is closed
    hist = ticker.history(period="5d", auto_adjust=True)
    if hist.empty:
        return {}
    # Drop NaN rows to get the last valid price
    close_series = hist["Close"].dropna()
    if close_series.empty:
        return {}
    current = float(close_series.iloc[-1])
    prev = float(close_series.iloc[-2]) if len(close_series) > 1 else current
    change = current - prev
    change_pct = (change / prev) * 100 if prev else 0
    return {
        "symbol": ticker_symbol,
        "name": info.get("longName") or info.get("shortName") or ticker_symbol,
        "price": round(current, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "volume": info.get("volume"),
        "market_cap": info.get("marketCap"),
        "currency": info.get("currency", "INR"),
    }


def _fetch_info(ticker_symbol: str) -> dict:
    """Blocking call — detailed fundamentals."""
    import yfinance as yf
    info = yf.Ticker(ticker_symbol).info
    return {
        "symbol": ticker_symbol,
        "name": info.get("longName") or ticker_symbol,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "pe_ratio": info.get("trailingPE"),
        "pb_ratio": info.get("priceToBook"),
        "market_cap": info.get("marketCap"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "dividend_yield": info.get("dividendYield"),
        "eps": info.get("trailingEps"),
        "book_value": info.get("bookValue"),
        "roe": info.get("returnOnEquity"),
    }


def _fetch_history(ticker_symbol: str, period: str) -> list[dict]:
    """Blocking call — price history."""
    import yfinance as yf
    hist = yf.Ticker(ticker_symbol).history(period=period)
    if hist.empty:
        return []
    result = []
    for date, row in hist.iterrows():
        result.append({
            "date": str(date.date()),
            "open": round(float(row["Open"]), 2),
            "close": round(float(row["Close"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "volume": int(row["Volume"]),
        })
    return result


def _fetch_top_movers(mover_type: str) -> list[dict]:
    """Blocking call — top gainers/losers from Nifty 50 sample."""
    import yfinance as yf
    symbols = [f"{s}.NS" for s in NIFTY50_SAMPLE]
    data = yf.download(symbols, period="2d", auto_adjust=True, progress=False)
    results = []
    if "Close" not in data.columns:
        return results
    close = data["Close"]
    for sym in symbols:
        if sym not in close.columns:
            continue
        prices = close[sym].dropna()
        if len(prices) < 2:
            continue
        curr = float(prices.iloc[-1])
        prev = float(prices.iloc[-2])
        chg_pct = ((curr - prev) / prev) * 100 if prev else 0
        results.append({"symbol": sym.replace(".NS", ""), "price": round(curr, 2), "change_pct": round(chg_pct, 2)})

    reverse = mover_type == "gainers"
    results.sort(key=lambda x: x["change_pct"], reverse=reverse)
    return results[:10]


# ── mftool helpers ─────────────────────────────────────────────────────────────

def _search_mf(query: str) -> list[dict]:
    """Blocking — search mutual fund schemes by name keyword."""
    from mftool import Mftool
    mf = Mftool()
    schemes = mf.get_scheme_codes(as_json=False)  # {code: name}
    query_lower = query.lower()
    matches = []
    for code, name in schemes.items():
        if query_lower in name.lower():
            matches.append({"code": code, "name": name})
        if len(matches) >= 10:
            break
    return matches


def _fetch_mf_nav(scheme_code: str) -> dict:
    """Blocking — fetch current NAV for a scheme code."""
    from mftool import Mftool
    mf = Mftool()
    data = mf.get_scheme_quote(scheme_code, as_json=False)
    if not data:
        return {}
    return {
        "scheme_code": scheme_code,
        "name": data.get("scheme_name", ""),
        "nav": data.get("net_asset_value", "N/A"),
        "date": data.get("date", ""),
    }


def _fetch_mf_returns(scheme_code: str) -> dict:
    """Blocking — fetch historical NAV and compute returns."""
    from mftool import Mftool
    mf = Mftool()
    history = mf.get_scheme_historical_nav(scheme_code, as_json=False)
    if not history or "data" not in history:
        return {}
    nav_data = history["data"]  # list of {date, nav}
    if len(nav_data) < 2:
        return {}
    # nav_data is newest first
    current_nav = float(nav_data[0]["nav"])
    name = history.get("scheme_name", "")

    def nav_n_days_ago(days: int) -> float | None:
        target = len(nav_data) - 1
        if days <= len(nav_data):
            return float(nav_data[min(days, len(nav_data) - 1)]["nav"])
        return None

    def ret(old: float | None) -> str:
        if old is None or old == 0:
            return "N/A"
        return f"{((current_nav - old) / old * 100):.2f}%"

    return {
        "name": name,
        "nav": current_nav,
        "returns": {
            "1m": ret(nav_n_days_ago(30)),
            "3m": ret(nav_n_days_ago(90)),
            "6m": ret(nav_n_days_ago(180)),
            "1y": ret(nav_n_days_ago(365)),
            "3y": ret(nav_n_days_ago(1095)),
        },
    }


# ── Async wrappers ─────────────────────────────────────────────────────────────

async def async_fetch_quote(ticker_symbol: str) -> dict:
    return await asyncio.get_event_loop().run_in_executor(None, _fetch_quote, ticker_symbol)

async def async_fetch_info(ticker_symbol: str) -> dict:
    return await asyncio.get_event_loop().run_in_executor(None, _fetch_info, ticker_symbol)

async def async_fetch_history(ticker_symbol: str, period: str) -> list[dict]:
    return await asyncio.get_event_loop().run_in_executor(None, _fetch_history, ticker_symbol, period)

async def async_fetch_top_movers(mover_type: str) -> list[dict]:
    return await asyncio.get_event_loop().run_in_executor(None, _fetch_top_movers, mover_type)

async def async_search_mf(query: str) -> list[dict]:
    return await asyncio.get_event_loop().run_in_executor(None, _search_mf, query)

async def async_fetch_mf_nav(code: str) -> dict:
    return await asyncio.get_event_loop().run_in_executor(None, _fetch_mf_nav, code)

async def async_fetch_mf_returns(code: str) -> dict:
    return await asyncio.get_event_loop().run_in_executor(None, _fetch_mf_returns, code)
