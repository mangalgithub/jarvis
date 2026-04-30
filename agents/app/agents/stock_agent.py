import logging

from app.tools.stock_tools import (
    INDEX_MAP,
    async_fetch_history,
    async_fetch_info,
    async_fetch_mf_nav,
    async_fetch_mf_returns,
    async_fetch_quote,
    async_fetch_top_movers,
    async_search_mf,
    normalize_ticker,
    parse_stock_command,
)

logger = logging.getLogger(__name__)


def _fmt_price(val) -> str:
    if val is None:
        return "N/A"
    return f"₹{float(val):,.2f}"


def _fmt_cap(val) -> str:
    if val is None:
        return "N/A"
    val = float(val)
    if val >= 1e12:
        return f"₹{val/1e12:.2f}T"
    if val >= 1e9:
        return f"₹{val/1e9:.2f}B"
    if val >= 1e7:
        return f"₹{val/1e7:.2f}Cr"
    return f"₹{val:,.0f}"


def _chg_emoji(pct: float) -> str:
    return "🟢" if pct >= 0 else "🔴"


class StockAgent:
    name = "stock"

    async def run(self, context: dict) -> dict:
        message = context.get("message", "")
        command = await parse_stock_command(message)
        operation = command["operation"]

        try:
            if operation == "get_quote":
                return await self._get_quote(command)
            if operation == "get_info":
                return await self._get_info(command)
            if operation == "get_index":
                return await self._get_index(command)
            if operation == "compare_stocks":
                return await self._compare(command)
            if operation == "get_top_movers":
                return await self._top_movers(command)
            if operation == "get_history":
                return await self._get_history(command)
            if operation == "get_mutual_fund":
                return await self._get_mf(command)
            if operation == "get_mf_returns":
                return await self._get_mf_returns(command)
            return await self._get_quote(command)
        except Exception as exc:
            logger.error("[StockAgent] error in %s: %s", operation, exc, exc_info=True)
            return {
                "reply": f"Sorry, I couldn't fetch the stock data right now. ({exc})",
                "actions": [{"type": "stock_error", "error": str(exc)}],
            }

    # ── Quote ──────────────────────────────────────────────────────────────

    async def _get_quote(self, command: dict) -> dict:
        symbol = command["symbol"]
        if not symbol:
            return {"reply": "Which stock would you like to check?", "actions": []}

        ticker = normalize_ticker(symbol)
        data = await async_fetch_quote(ticker)

        if not data:
            return {
                "reply": f"I couldn't find data for **{symbol}**. Please check the company name.",
                "actions": [{"type": "stock_not_found", "symbol": symbol}],
            }

        emoji = _chg_emoji(data["change_pct"])
        sign = "+" if data["change"] >= 0 else ""
        vol_str = f"\nVolume: {data['volume']:,}" if data.get("volume") else ""
        mkt_note = " *(last close)*" if data["change"] == 0 else ""
        reply = (
            f"{emoji} **{data['name']}** ({ticker.replace('.NS', '').replace('.BO', '')}){mkt_note}\n"
            f"Price: {_fmt_price(data['price'])}  "
            f"Change: {sign}{_fmt_price(data['change'])} ({sign}{data['change_pct']:.2f}%)"
            f"{vol_str}"
        )
        return {
            "reply": reply.strip(),
            "actions": [{"type": "stock_quote", **data}],
        }

    # ── Detailed Info ──────────────────────────────────────────────────────

    async def _get_info(self, command: dict) -> dict:
        symbol = command["symbol"]
        if not symbol:
            return {"reply": "Which stock would you like detailed info on?", "actions": []}

        ticker = normalize_ticker(symbol)
        data = await async_fetch_info(ticker)

        if not data or not data.get("price"):
            return {"reply": f"I couldn't find info for **{symbol}**.", "actions": []}

        pe = f"{data['pe_ratio']:.2f}" if data.get("pe_ratio") else "N/A"
        pb = f"{data['pb_ratio']:.2f}" if data.get("pb_ratio") else "N/A"
        dy = f"{data['dividend_yield']*100:.2f}%" if data.get("dividend_yield") else "N/A"
        roe = f"{data['roe']*100:.2f}%" if data.get("roe") else "N/A"

        reply = (
            f"📊 **{data['name']}**\n"
            f"Sector: {data.get('sector') or 'N/A'} | Industry: {data.get('industry') or 'N/A'}\n"
            f"Price: {_fmt_price(data['price'])} | Market Cap: {_fmt_cap(data['market_cap'])}\n"
            f"P/E: {pe} | P/B: {pb} | EPS: {data.get('eps') or 'N/A'}\n"
            f"52W High: {_fmt_price(data['52w_high'])} | 52W Low: {_fmt_price(data['52w_low'])}\n"
            f"Dividend Yield: {dy} | ROE: {roe}"
        )
        return {
            "reply": reply,
            "actions": [{"type": "stock_info", **data}],
        }

    # ── Index ──────────────────────────────────────────────────────────────

    async def _get_index(self, command: dict) -> dict:
        query = command["symbol"].lower()
        # Find the index symbol
        ticker = None
        for key, val in INDEX_MAP.items():
            if key in query or query in key:
                ticker = val
                break
        if not ticker:
            ticker = "^NSEI"  # Default to Nifty

        data = await async_fetch_quote(ticker)
        if not data:
            return {"reply": "Couldn't fetch index data right now.", "actions": []}

        emoji = _chg_emoji(data["change_pct"])
        sign = "+" if data["change"] >= 0 else ""
        reply = (
            f"{emoji} **{data['name']}**\n"
            f"Level: {data['price']:,.2f}  "
            f"Change: {sign}{data['change']:,.2f} ({sign}{data['change_pct']:.2f}%)"
        )
        return {
            "reply": reply,
            "actions": [{"type": "index_quote", **data}],
        }

    # ── Compare ────────────────────────────────────────────────────────────

    async def _compare(self, command: dict) -> dict:
        sym1, sym2 = command["symbol"], command["symbol2"]
        if not sym1 or not sym2:
            return {"reply": "Please name two stocks to compare, e.g. 'Reliance vs TCS'.", "actions": []}

        t1, t2 = normalize_ticker(sym1), normalize_ticker(sym2)
        d1, d2 = await async_fetch_quote(t1), await async_fetch_quote(t2)

        if not d1 or not d2:
            return {"reply": "Couldn't fetch one or both stocks.", "actions": []}

        e1 = _chg_emoji(d1["change_pct"])
        e2 = _chg_emoji(d2["change_pct"])
        reply = (
            f"📊 **Stock Comparison**\n\n"
            f"{e1} **{d1['name']}**: {_fmt_price(d1['price'])} ({d1['change_pct']:+.2f}%)\n"
            f"{e2} **{d2['name']}**: {_fmt_price(d2['price'])} ({d2['change_pct']:+.2f}%)"
        )
        return {
            "reply": reply,
            "actions": [{"type": "stock_compare", "stock1": d1, "stock2": d2}],
        }

    # ── Top Movers ─────────────────────────────────────────────────────────

    async def _top_movers(self, command: dict) -> dict:
        mover_type = command.get("mover_type", "gainers")
        movers = await async_fetch_top_movers(mover_type)

        if not movers:
            return {"reply": "Couldn't fetch market movers right now.", "actions": []}

        label = "Top Gainers 📈" if mover_type == "gainers" else "Top Losers 📉"
        lines = [f"**{label}** (Nifty 50 sample)\n"]
        for i, m in enumerate(movers[:7], 1):
            emoji = _chg_emoji(m["change_pct"])
            lines.append(f"{i}. {emoji} **{m['symbol']}** — ₹{m['price']:,.2f} ({m['change_pct']:+.2f}%)")

        return {
            "reply": "\n".join(lines),
            "actions": [{"type": "top_movers", "mover_type": mover_type, "movers": movers}],
        }

    # ── Price History ──────────────────────────────────────────────────────

    async def _get_history(self, command: dict) -> dict:
        symbol = command["symbol"]
        period = command.get("period") or "1mo"
        ticker = normalize_ticker(symbol)

        history = await async_fetch_history(ticker, period)
        if not history:
            return {"reply": f"Couldn't fetch history for **{symbol}**.", "actions": []}

        first = history[0]["close"]
        last = history[-1]["close"]
        change_pct = ((last - first) / first) * 100 if first else 0
        emoji = _chg_emoji(change_pct)

        reply = (
            f"{emoji} **{symbol.upper()}** — {period} history\n"
            f"Start: {_fmt_price(first)} → Now: {_fmt_price(last)}\n"
            f"Return: {change_pct:+.2f}% over {len(history)} trading days"
        )
        return {
            "reply": reply,
            "actions": [{"type": "stock_history", "symbol": symbol, "period": period, "history": history[-30:]}],
        }

    # ── Mutual Fund NAV ────────────────────────────────────────────────────

    async def _get_mf(self, command: dict) -> dict:
        query = command.get("mf_query") or command.get("symbol") or ""
        if not query:
            return {"reply": "Which mutual fund would you like to check?", "actions": []}

        matches = await async_search_mf(query)
        if not matches:
            return {"reply": f"No mutual fund found matching **'{query}'**.", "actions": []}

        # Fetch NAV for top 3 matches
        results = []
        for match in matches[:3]:
            nav_data = await async_fetch_mf_nav(match["code"])
            if nav_data:
                results.append(nav_data)

        if not results:
            return {"reply": f"Couldn't fetch NAV for **'{query}'**.", "actions": []}

        lines = ["📊 **Mutual Fund NAV**\n"]
        for r in results:
            lines.append(f"• **{r['name'][:60]}**\n  NAV: ₹{r['nav']} (as of {r['date']})")

        return {
            "reply": "\n".join(lines),
            "actions": [{"type": "mf_nav", "funds": results}],
        }

    # ── Mutual Fund Returns ────────────────────────────────────────────────

    async def _get_mf_returns(self, command: dict) -> dict:
        query = command.get("mf_query") or command.get("symbol") or ""
        if not query:
            return {"reply": "Which mutual fund's returns would you like to see?", "actions": []}

        matches = await async_search_mf(query)
        if not matches:
            return {"reply": f"No mutual fund found matching **'{query}'**.", "actions": []}

        best_match = matches[0]
        data = await async_fetch_mf_returns(best_match["code"])

        if not data:
            return {"reply": f"Couldn't compute returns for **'{query}'**.", "actions": []}

        r = data["returns"]
        reply = (
            f"📈 **{data['name'][:70]}**\n"
            f"Current NAV: ₹{data['nav']:.4f}\n\n"
            f"**Returns:**\n"
            f"• 1 Month:  {r['1m']}\n"
            f"• 3 Months: {r['3m']}\n"
            f"• 6 Months: {r['6m']}\n"
            f"• 1 Year:   {r['1y']}\n"
            f"• 3 Years:  {r['3y']}"
        )
        return {
            "reply": reply,
            "actions": [{"type": "mf_returns", **data}],
        }

    # ── Dashboard helper ───────────────────────────────────────────────────

    async def get_dashboard_stocks(self) -> dict:
        """Returns a market snapshot for the dashboard sidebar."""
        try:
            nifty = await async_fetch_quote("^NSEI")
            sensex = await async_fetch_quote("^BSESN")
            bank_nifty = await async_fetch_quote("^NSEBANK")
            return {
                "indices": [
                    {"name": "Nifty 50", **nifty},
                    {"name": "Sensex", **sensex},
                    {"name": "Bank Nifty", **bank_nifty},
                ]
            }
        except Exception as exc:
            logger.error("[StockAgent] dashboard failed: %s", exc)
            return {"indices": []}
