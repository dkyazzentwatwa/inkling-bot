"""
Project Inkling - Crypto Data Watcher

Fetches live cryptocurrency prices and market data from multiple sources.
Supports CoinGecko API and major exchanges via ccxt.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

import aiohttp
from pycoingecko import CoinGeckoAPI
import ccxt.async_support as ccxt


logger = logging.getLogger(__name__)


@dataclass
class CryptoPrice:
    """Cryptocurrency price data."""
    symbol: str
    price_usd: float
    price_change_24h: float  # Percentage
    volume_24h: float
    market_cap: Optional[float] = None
    timestamp: float = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()

    @property
    def is_pumping(self) -> bool:
        """Check if coin is pumping (>5% gain)."""
        return self.price_change_24h > 5.0

    @property
    def is_dumping(self) -> bool:
        """Check if coin is dumping (>5% loss)."""
        return self.price_change_24h < -5.0

    @property
    def mood(self) -> str:
        """Get crypto bro mood based on price action."""
        if self.price_change_24h > 10:
            return "moon"
        elif self.price_change_24h > 5:
            return "bullish"
        elif self.price_change_24h > 0:
            return "hodl"
        elif self.price_change_24h > -5:
            return "dip"
        else:
            return "rekt"


@dataclass
class OHLCV:
    """OHLCV candlestick data."""
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


class CryptoWatcher:
    """
    Crypto price watcher that fetches data from CoinGecko and exchanges.

    Supports:
    - Real-time price tracking
    - Historical OHLCV data for TA analysis
    - Multiple data sources with fallback
    - Rate limiting and caching
    """

    def __init__(self, cache_ttl: int = 60):
        """
        Initialize crypto watcher.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 60s)
        """
        self.cache_ttl = cache_ttl
        self._price_cache: Dict[str, Tuple[CryptoPrice, float]] = {}
        self._coingecko: Optional[CoinGeckoAPI] = None
        self._exchange: Optional[ccxt.Exchange] = None
        self._session: Optional[aiohttp.ClientSession] = None

        # Symbol mappings (CoinGecko IDs)
        self._symbol_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "MATIC": "matic-network",
            "AVAX": "avalanche-2",
            "DOGE": "dogecoin",
            "SHIB": "shiba-inu",
            "PEPE": "pepe",
            "WIF": "dogwifhat",
            "BONK": "bonk",
        }

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession()
        self._coingecko = CoinGeckoAPI()
        # Use Binance as default exchange (no API key needed for public data)
        self._exchange = ccxt.binance({"enableRateLimit": True})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._exchange:
            await self._exchange.close()
        if self._session:
            await self._session.close()

    def _get_cached_price(self, symbol: str) -> Optional[CryptoPrice]:
        """Get price from cache if not expired."""
        if symbol in self._price_cache:
            price, cached_at = self._price_cache[symbol]
            if time.time() - cached_at < self.cache_ttl:
                return price
        return None

    def _cache_price(self, symbol: str, price: CryptoPrice):
        """Cache a price."""
        self._price_cache[symbol] = (price, time.time())

    async def get_price(self, symbol: str) -> Optional[CryptoPrice]:
        """
        Get current price for a cryptocurrency.

        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")

        Returns:
            CryptoPrice object or None if failed
        """
        # Check cache first
        cached = self._get_cached_price(symbol)
        if cached:
            logger.debug(f"Cache hit for {symbol}")
            return cached

        # Try exchange (ccxt) first - faster and more reliable for trading pairs
        try:
            price = await self._get_price_exchange(symbol)
            if price:
                self._cache_price(symbol, price)
                return price
        except Exception as e:
            logger.warning(f"Exchange (ccxt) failed for {symbol}: {e}")

        # Fallback to CoinGecko (slower but works for more coins)
        try:
            price = await self._get_price_coingecko(symbol)
            if price:
                self._cache_price(symbol, price)
                return price
        except Exception as e:
            logger.warning(f"CoinGecko fallback failed for {symbol}: {e}")

        return None

    async def _get_price_coingecko(self, symbol: str) -> Optional[CryptoPrice]:
        """Fetch price from CoinGecko."""
        coin_id = self._symbol_map.get(symbol.upper())
        if not coin_id:
            logger.warning(f"Unknown symbol: {symbol}")
            return None

        # Run sync CoinGecko API in thread pool
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: self._coingecko.get_price(
                ids=coin_id,
                vs_currencies="usd",
                include_24hr_change=True,
                include_24hr_vol=True,
                include_market_cap=True,
            )
        )

        if coin_id not in data:
            return None

        coin_data = data[coin_id]
        return CryptoPrice(
            symbol=symbol.upper(),
            price_usd=coin_data["usd"],
            price_change_24h=coin_data.get("usd_24h_change", 0),
            volume_24h=coin_data.get("usd_24h_vol", 0),
            market_cap=coin_data.get("usd_market_cap"),
        )

    async def _get_price_exchange(self, symbol: str) -> Optional[CryptoPrice]:
        """Fetch price from exchange (Binance)."""
        if not self._exchange:
            return None

        trading_pair = f"{symbol.upper()}/USDT"

        try:
            # Fetch ticker
            ticker = await self._exchange.fetch_ticker(trading_pair)

            return CryptoPrice(
                symbol=symbol.upper(),
                price_usd=ticker["last"],
                price_change_24h=ticker.get("percentage", 0),
                volume_24h=ticker.get("quoteVolume", 0),
            )
        except ccxt.BaseError as e:
            logger.warning(f"Exchange error for {trading_pair}: {e}")
            return None

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
    ) -> List[OHLCV]:
        """
        Get historical OHLCV (candlestick) data for TA analysis.

        Args:
            symbol: Crypto symbol (e.g., "BTC")
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch

        Returns:
            List of OHLCV objects
        """
        if not self._exchange:
            return []

        trading_pair = f"{symbol.upper()}/USDT"

        try:
            ohlcv_data = await self._exchange.fetch_ohlcv(
                trading_pair,
                timeframe=timeframe,
                limit=limit,
            )

            return [
                OHLCV(
                    timestamp=candle[0] / 1000,  # Convert to seconds
                    open=candle[1],
                    high=candle[2],
                    low=candle[3],
                    close=candle[4],
                    volume=candle[5],
                )
                for candle in ohlcv_data
            ]
        except ccxt.BaseError as e:
            logger.warning(f"Failed to fetch OHLCV for {trading_pair}: {e}")
            return []

    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, CryptoPrice]:
        """
        Get prices for multiple cryptocurrencies concurrently.

        Args:
            symbols: List of crypto symbols

        Returns:
            Dict mapping symbols to CryptoPrice objects
        """
        tasks = [self.get_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        prices = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, CryptoPrice):
                prices[symbol] = result
            elif isinstance(result, Exception):
                logger.warning(f"Error fetching {symbol}: {result}")

        return prices

    def format_price(self, price: CryptoPrice, use_emoji: bool = True) -> str:
        """
        Format price for display with crypto bro style.

        Args:
            price: CryptoPrice object
            use_emoji: Include emoji indicators

        Returns:
            Formatted string
        """
        change_emoji = ""
        if use_emoji:
            if price.price_change_24h > 5:
                change_emoji = "🚀"
            elif price.price_change_24h > 0:
                change_emoji = "📈"
            elif price.price_change_24h < -5:
                change_emoji = "💀"
            else:
                change_emoji = "📉"

        # Format price with appropriate decimals
        if price.price_usd >= 1:
            price_str = f"${price.price_usd:,.2f}"
        else:
            price_str = f"${price.price_usd:.6f}"

        # Format change percentage
        change_sign = "+" if price.price_change_24h >= 0 else ""
        change_str = f"{change_sign}{price.price_change_24h:.2f}%"

        return f"{price.symbol} {price_str} ({change_str}) {change_emoji}"

    def get_portfolio_value(self, holdings: Dict[str, float], prices: Dict[str, CryptoPrice]) -> float:
        """
        Calculate total portfolio value.

        Args:
            holdings: Dict mapping symbols to amounts held
            prices: Dict mapping symbols to CryptoPrice objects

        Returns:
            Total value in USD
        """
        total = 0.0
        for symbol, amount in holdings.items():
            if symbol in prices:
                total += amount * prices[symbol].price_usd
        return total
