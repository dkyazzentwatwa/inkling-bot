#!/usr/bin/env python3
"""
MCP Server for Crypto Tools

Exposes cryptocurrency price tracking, portfolio management, and alert tools
to the AI via Model Context Protocol.

Tools:
- crypto_price: Get current price for a cryptocurrency
- crypto_chart: Get TA indicators and chart analysis
- crypto_portfolio: Get portfolio value and breakdown
- crypto_alert_set: Set a price alert
- crypto_alert_list: List active alerts
- crypto_watchlist: Get/manage watchlist
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.crypto_watcher import CryptoWatcher, CryptoPrice
from core.crypto_ta import CryptoTA, Signal


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CryptoMCPServer:
    """MCP Server for cryptocurrency tools."""

    def __init__(self, data_dir: str = "~/.inkling"):
        """Initialize crypto MCP server."""
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.watchlist_file = self.data_dir / "crypto_watchlist.json"
        self.alerts_file = self.data_dir / "crypto_alerts.json"
        self.portfolio_file = self.data_dir / "crypto_portfolio.json"

        self.watchlist = self._load_watchlist()
        self.alerts = self._load_alerts()
        self.portfolio = self._load_portfolio()

    def _load_watchlist(self) -> List[str]:
        """Load watchlist from JSON."""
        if self.watchlist_file.exists():
            try:
                with open(self.watchlist_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load watchlist: {e}")
        return ["BTC", "ETH", "SOL"]  # Default watchlist

    def _save_watchlist(self):
        """Save watchlist to JSON."""
        with open(self.watchlist_file, 'w') as f:
            json.dump(self.watchlist, f, indent=2)

    def _load_alerts(self) -> List[Dict]:
        """Load price alerts from JSON."""
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load alerts: {e}")
        return []

    def _save_alerts(self):
        """Save price alerts to JSON."""
        with open(self.alerts_file, 'w') as f:
            json.dump(self.alerts, f, indent=2)

    def _load_portfolio(self) -> Dict[str, float]:
        """Load portfolio holdings from JSON."""
        if self.portfolio_file.exists():
            try:
                with open(self.portfolio_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load portfolio: {e}")
        return {}  # Empty portfolio by default

    def _save_portfolio(self):
        """Save portfolio holdings to JSON."""
        with open(self.portfolio_file, 'w') as f:
            json.dump(self.portfolio, f, indent=2)

    async def crypto_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get current price for a cryptocurrency.

        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH", "SOL")

        Returns:
            Price data with change percentage and mood
        """
        async with CryptoWatcher() as watcher:
            price = await watcher.get_price(symbol.upper())

            if not price:
                return {"error": f"Failed to fetch price for {symbol}"}

            return {
                "symbol": price.symbol,
                "price_usd": price.price_usd,
                "price_change_24h": price.price_change_24h,
                "volume_24h": price.volume_24h,
                "market_cap": price.market_cap,
                "mood": price.mood,
                "is_pumping": price.is_pumping,
                "is_dumping": price.is_dumping,
                "formatted": watcher.format_price(price),
            }

    async def crypto_chart(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get TA indicators and chart analysis for a cryptocurrency.

        Args:
            symbol: Crypto symbol (e.g., "BTC")
            timeframe: Candlestick timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to analyze

        Returns:
            TA indicators, signal, and detected patterns
        """
        async with CryptoWatcher() as watcher:
            ohlcv = await watcher.get_ohlcv(symbol.upper(), timeframe, limit)

            if not ohlcv:
                return {"error": f"Failed to fetch chart data for {symbol}"}

            ta = CryptoTA()
            indicators = ta.calculate_indicators(ohlcv)
            patterns = ta.detect_patterns(ohlcv)
            supports, resistances = ta.get_support_resistance(ohlcv)

            signal = indicators.get_signal()

            return {
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "signal": signal.value,
                "signal_text": signal.crypto_bro_text,
                "indicators": {
                    "rsi": indicators.rsi,
                    "macd": indicators.macd,
                    "macd_signal": indicators.macd_signal,
                    "sma_20": indicators.sma_20,
                    "sma_50": indicators.sma_50,
                    "bb_upper": indicators.bb_upper,
                    "bb_lower": indicators.bb_lower,
                    "atr": indicators.atr,
                },
                "patterns": patterns,
                "support_levels": supports,
                "resistance_levels": resistances,
                "formatted": ta.format_indicators(indicators, include_signal=True),
            }

    async def crypto_portfolio(self) -> Dict[str, Any]:
        """
        Get portfolio value and breakdown.

        Returns:
            Total value, holdings, and individual coin values
        """
        if not self.portfolio:
            return {
                "total_value_usd": 0,
                "holdings": {},
                "message": "Portfolio is empty. Use crypto_portfolio_update to add holdings."
            }

        async with CryptoWatcher() as watcher:
            symbols = list(self.portfolio.keys())
            prices = await watcher.get_multiple_prices(symbols)

            total_value = watcher.get_portfolio_value(self.portfolio, prices)

            breakdown = []
            for symbol, amount in self.portfolio.items():
                if symbol in prices:
                    price = prices[symbol]
                    value = amount * price.price_usd
                    breakdown.append({
                        "symbol": symbol,
                        "amount": amount,
                        "price_usd": price.price_usd,
                        "value_usd": value,
                        "change_24h": price.price_change_24h,
                    })

            return {
                "total_value_usd": total_value,
                "holdings": breakdown,
                "num_coins": len(breakdown),
            }

    async def crypto_portfolio_update(
        self,
        symbol: str,
        amount: float,
        operation: str = "set"
    ) -> Dict[str, Any]:
        """
        Update portfolio holdings.

        Args:
            symbol: Crypto symbol
            amount: Amount to set/add/remove
            operation: "set", "add", or "remove"

        Returns:
            Updated portfolio
        """
        symbol = symbol.upper()

        if operation == "set":
            self.portfolio[symbol] = amount
        elif operation == "add":
            self.portfolio[symbol] = self.portfolio.get(symbol, 0) + amount
        elif operation == "remove":
            current = self.portfolio.get(symbol, 0)
            new_amount = max(0, current - amount)
            if new_amount == 0:
                self.portfolio.pop(symbol, None)
            else:
                self.portfolio[symbol] = new_amount
        else:
            return {"error": f"Invalid operation: {operation}"}

        self._save_portfolio()

        return {
            "symbol": symbol,
            "new_amount": self.portfolio.get(symbol, 0),
            "operation": operation,
            "message": f"Updated {symbol} holdings"
        }

    async def crypto_alert_set(
        self,
        symbol: str,
        target_price: float,
        condition: str = "above"
    ) -> Dict[str, Any]:
        """
        Set a price alert.

        Args:
            symbol: Crypto symbol
            target_price: Price to trigger alert
            condition: "above" or "below"

        Returns:
            Alert confirmation
        """
        alert = {
            "symbol": symbol.upper(),
            "target_price": target_price,
            "condition": condition,
            "active": True,
        }

        self.alerts.append(alert)
        self._save_alerts()

        return {
            "message": f"Alert set: {symbol} {condition} ${target_price}",
            "alert": alert,
        }

    async def crypto_alert_list(self) -> Dict[str, Any]:
        """
        List all active price alerts.

        Returns:
            List of active alerts
        """
        return {
            "alerts": self.alerts,
            "num_alerts": len(self.alerts),
        }

    async def crypto_alert_check(self) -> List[Dict[str, Any]]:
        """
        Check alerts and return triggered ones.

        Returns:
            List of triggered alerts
        """
        if not self.alerts:
            return []

        triggered = []

        async with CryptoWatcher() as watcher:
            symbols = list(set(alert["symbol"] for alert in self.alerts))
            prices = await watcher.get_multiple_prices(symbols)

            for alert in self.alerts[:]:
                if not alert.get("active"):
                    continue

                symbol = alert["symbol"]
                if symbol not in prices:
                    continue

                price = prices[symbol]
                target = alert["target_price"]
                condition = alert["condition"]

                if (condition == "above" and price.price_usd >= target) or \
                   (condition == "below" and price.price_usd <= target):
                    triggered.append({
                        "alert": alert,
                        "current_price": price.price_usd,
                        "formatted": watcher.format_price(price),
                    })
                    alert["active"] = False

            self._save_alerts()

        return triggered

    async def crypto_watchlist_get(self) -> Dict[str, Any]:
        """
        Get watchlist with current prices.

        Returns:
            Watchlist coins with prices and changes
        """
        async with CryptoWatcher() as watcher:
            prices = await watcher.get_multiple_prices(self.watchlist)

            coins = []
            for symbol in self.watchlist:
                if symbol in prices:
                    price = prices[symbol]
                    coins.append({
                        "symbol": symbol,
                        "price_usd": price.price_usd,
                        "change_24h": price.price_change_24h,
                        "formatted": watcher.format_price(price),
                    })

            return {
                "watchlist": coins,
                "num_coins": len(coins),
            }

    async def crypto_watchlist_add(self, symbol: str) -> Dict[str, Any]:
        """Add coin to watchlist."""
        symbol = symbol.upper()
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            self._save_watchlist()
            return {"message": f"Added {symbol} to watchlist", "watchlist": self.watchlist}
        return {"message": f"{symbol} already in watchlist", "watchlist": self.watchlist}

    async def crypto_watchlist_remove(self, symbol: str) -> Dict[str, Any]:
        """Remove coin from watchlist."""
        symbol = symbol.upper()
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            self._save_watchlist()
            return {"message": f"Removed {symbol} from watchlist", "watchlist": self.watchlist}
        return {"message": f"{symbol} not in watchlist", "watchlist": self.watchlist}


# MCP Protocol Implementation
async def handle_request(request: Dict) -> Dict:
    """Handle MCP request."""
    method = request.get("method")
    params = request.get("params", {})

    server = CryptoMCPServer()

    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "crypto_price",
                    "description": "Get current price for a cryptocurrency (BTC, ETH, SOL, etc.)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Crypto symbol (e.g., BTC, ETH)"}
                        },
                        "required": ["symbol"]
                    }
                },
                {
                    "name": "crypto_chart",
                    "description": "Get TA indicators and chart analysis for a cryptocurrency",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Crypto symbol"},
                            "timeframe": {"type": "string", "description": "Timeframe (1h, 4h, 1d)", "default": "1h"},
                            "limit": {"type": "integer", "description": "Number of candles", "default": 100}
                        },
                        "required": ["symbol"]
                    }
                },
                {
                    "name": "crypto_portfolio",
                    "description": "Get portfolio value and breakdown",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "crypto_portfolio_update",
                    "description": "Update portfolio holdings (set/add/remove amount)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Crypto symbol"},
                            "amount": {"type": "number", "description": "Amount to set/add/remove"},
                            "operation": {"type": "string", "description": "set/add/remove", "default": "set"}
                        },
                        "required": ["symbol", "amount"]
                    }
                },
                {
                    "name": "crypto_alert_set",
                    "description": "Set a price alert for a cryptocurrency",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Crypto symbol"},
                            "target_price": {"type": "number", "description": "Price to trigger alert"},
                            "condition": {"type": "string", "description": "above or below", "default": "above"}
                        },
                        "required": ["symbol", "target_price"]
                    }
                },
                {
                    "name": "crypto_alert_list",
                    "description": "List all active price alerts",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "crypto_watchlist_get",
                    "description": "Get watchlist with current prices",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "crypto_watchlist_add",
                    "description": "Add coin to watchlist",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Crypto symbol"}
                        },
                        "required": ["symbol"]
                    }
                },
                {
                    "name": "crypto_watchlist_remove",
                    "description": "Remove coin from watchlist",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Crypto symbol"}
                        },
                        "required": ["symbol"]
                    }
                },
            ]
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        handler = getattr(server, tool_name, None)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        result = await handler(**tool_args)
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    return {"error": "Unknown method"}


async def main():
    """Run MCP server on stdio."""
    logger.info("Starting Crypto MCP Server")

    while True:
        line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        if not line:
            break

        try:
            request = json.loads(line)
            response = await handle_request(request)
            print(json.dumps(response), flush=True)
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            print(json.dumps({"error": str(e)}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
