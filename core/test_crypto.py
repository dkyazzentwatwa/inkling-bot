"""
Test script for crypto watcher and TA analysis.

Run with: pytest -xvs core/test_crypto.py
Or directly: python core/test_crypto.py
"""

import asyncio
import pytest

from crypto_watcher import CryptoWatcher, CryptoPrice
from crypto_ta import CryptoTA, Signal


@pytest.mark.asyncio
async def test_get_price():
    """Test fetching a single price."""
    async with CryptoWatcher() as watcher:
        price = await watcher.get_price("BTC")

        assert price is not None
        assert price.symbol == "BTC"
        assert price.price_usd > 0
        assert isinstance(price.price_change_24h, float)

        print(f"\nBTC Price: {watcher.format_price(price)}")


@pytest.mark.asyncio
async def test_get_multiple_prices():
    """Test fetching multiple prices concurrently."""
    async with CryptoWatcher() as watcher:
        symbols = ["BTC", "ETH", "SOL"]
        prices = await watcher.get_multiple_prices(symbols)

        assert len(prices) > 0

        print("\nMultiple prices:")
        for symbol, price in prices.items():
            print(f"  {watcher.format_price(price)}")


@pytest.mark.asyncio
async def test_get_ohlcv():
    """Test fetching OHLCV data."""
    async with CryptoWatcher() as watcher:
        ohlcv = await watcher.get_ohlcv("BTC", timeframe="1h", limit=100)

        assert len(ohlcv) > 0
        assert ohlcv[0].close > 0

        print(f"\nFetched {len(ohlcv)} candles for BTC")
        print(f"Latest close: ${ohlcv[-1].close:.2f}")


@pytest.mark.asyncio
async def test_ta_indicators():
    """Test calculating TA indicators."""
    async with CryptoWatcher() as watcher:
        ohlcv = await watcher.get_ohlcv("BTC", timeframe="1h", limit=100)

        ta = CryptoTA()
        indicators = ta.calculate_indicators(ohlcv)

        assert indicators.rsi is not None
        assert indicators.macd is not None
        assert indicators.sma_20 is not None

        print("\nTA Indicators:")
        print(ta.format_indicators(indicators, include_signal=True))


@pytest.mark.asyncio
async def test_price_mood():
    """Test crypto price mood detection."""
    async with CryptoWatcher() as watcher:
        price = await watcher.get_price("BTC")

        assert price is not None

        print(f"\nBTC Mood: {price.mood}")
        print(f"Is Pumping: {price.is_pumping}")
        print(f"Is Dumping: {price.is_dumping}")


@pytest.mark.asyncio
async def test_candlestick_patterns():
    """Test candlestick pattern detection."""
    async with CryptoWatcher() as watcher:
        ohlcv = await watcher.get_ohlcv("BTC", timeframe="1h", limit=100)

        ta = CryptoTA()
        patterns = ta.detect_patterns(ohlcv)

        print(f"\nDetected {len(patterns)} patterns:")
        for pattern in patterns:
            print(f"  {pattern}")


@pytest.mark.asyncio
async def test_support_resistance():
    """Test support/resistance calculation."""
    async with CryptoWatcher() as watcher:
        ohlcv = await watcher.get_ohlcv("BTC", timeframe="1h", limit=100)

        ta = CryptoTA()
        supports, resistances = ta.get_support_resistance(ohlcv, num_levels=3)

        print(f"\nSupport levels: {[f'${s:.2f}' for s in supports]}")
        print(f"Resistance levels: {[f'${r:.2f}' for r in resistances]}")


@pytest.mark.asyncio
async def test_portfolio_value():
    """Test portfolio valuation."""
    async with CryptoWatcher() as watcher:
        holdings = {
            "BTC": 0.5,
            "ETH": 10.0,
            "SOL": 100.0,
        }

        prices = await watcher.get_multiple_prices(list(holdings.keys()))
        total_value = watcher.get_portfolio_value(holdings, prices)

        print(f"\nPortfolio Value: ${total_value:,.2f}")
        for symbol, amount in holdings.items():
            if symbol in prices:
                value = amount * prices[symbol].price_usd
                print(f"  {symbol}: {amount} x ${prices[symbol].price_usd:.2f} = ${value:,.2f}")


if __name__ == "__main__":
    """Run tests directly without pytest."""
    async def run_all_tests():
        print("=== Crypto Watcher Tests ===\n")

        await test_get_price()
        await test_get_multiple_prices()
        await test_get_ohlcv()
        await test_ta_indicators()
        await test_price_mood()
        await test_candlestick_patterns()
        await test_support_resistance()
        await test_portfolio_value()

        print("\n=== All tests completed ===")

    asyncio.run(run_all_tests())
