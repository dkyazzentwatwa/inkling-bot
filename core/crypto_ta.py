"""
Project Inkling - Crypto Technical Analysis

Uses TA-Lib to calculate technical indicators for cryptocurrency trading.
Provides signals for trend, momentum, volatility, and volume analysis.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logging.warning("TA-Lib not available. Install with: pip install TA-Lib")


logger = logging.getLogger(__name__)


class Signal(Enum):
    """Trading signal types."""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

    @property
    def emoji(self) -> str:
        """Get emoji for signal."""
        return {
            Signal.STRONG_BUY: "🚀🚀",
            Signal.BUY: "📈",
            Signal.NEUTRAL: "😐",
            Signal.SELL: "📉",
            Signal.STRONG_SELL: "💀💀",
        }[self]

    @property
    def crypto_bro_text(self) -> str:
        """Get crypto bro interpretation."""
        return {
            Signal.STRONG_BUY: "MOON INCOMING! 🚀",
            Signal.BUY: "Bullish af, fam",
            Signal.NEUTRAL: "Crab market, hodl",
            Signal.SELL: "Might dump, ngl",
            Signal.STRONG_SELL: "NGMI, get out",
        }[self]


@dataclass
class TAIndicators:
    """Technical analysis indicators."""
    # Trend
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None

    # Momentum
    rsi: Optional[float] = None  # 0-100
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None

    # Volatility
    bb_upper: Optional[float] = None  # Bollinger Bands
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    atr: Optional[float] = None  # Average True Range

    # Volume
    obv: Optional[float] = None  # On Balance Volume
    ad: Optional[float] = None  # Accumulation/Distribution

    def get_signal(self) -> Signal:
        """
        Get overall signal based on indicators.

        Combines RSI, MACD, and trend signals for overall sentiment.
        """
        signals = []

        # RSI signal (oversold/overbought)
        if self.rsi is not None:
            if self.rsi < 30:
                signals.append(2)  # Strong buy
            elif self.rsi < 40:
                signals.append(1)  # Buy
            elif self.rsi > 70:
                signals.append(-2)  # Strong sell
            elif self.rsi > 60:
                signals.append(-1)  # Sell
            else:
                signals.append(0)  # Neutral

        # MACD signal
        if self.macd is not None and self.macd_signal is not None:
            diff = self.macd - self.macd_signal
            if diff > 0:
                signals.append(1 if diff > 5 else 0.5)
            else:
                signals.append(-1 if diff < -5 else -0.5)

        # Trend signal (price vs MA)
        if (
            self.sma_20 is not None
            and self.sma_50 is not None
            and self.ema_12 is not None
        ):
            # Golden cross / death cross
            if self.sma_20 > self.sma_50:
                signals.append(1)
            elif self.sma_20 < self.sma_50:
                signals.append(-1)

        # Bollinger Bands (price position)
        if (
            self.bb_upper is not None
            and self.bb_lower is not None
            and self.bb_middle is not None
        ):
            # Assuming current price is bb_middle (needs price context)
            # This is a simplified check
            pass

        if not signals:
            return Signal.NEUTRAL

        avg_signal = sum(signals) / len(signals)

        if avg_signal >= 1.5:
            return Signal.STRONG_BUY
        elif avg_signal >= 0.5:
            return Signal.BUY
        elif avg_signal <= -1.5:
            return Signal.STRONG_SELL
        elif avg_signal <= -0.5:
            return Signal.SELL
        else:
            return Signal.NEUTRAL


class CryptoTA:
    """
    Technical analysis calculator using TA-Lib.

    Calculates various indicators from OHLCV data.
    """

    def __init__(self):
        """Initialize TA calculator."""
        if not TALIB_AVAILABLE:
            logger.warning("TA-Lib not installed, indicators will be unavailable")

    def calculate_indicators(
        self,
        ohlcv_data: List,
        current_price: Optional[float] = None,
    ) -> TAIndicators:
        """
        Calculate technical indicators from OHLCV data.

        Args:
            ohlcv_data: List of OHLCV objects
            current_price: Current price for context (optional)

        Returns:
            TAIndicators object with calculated values
        """
        if not TALIB_AVAILABLE or not ohlcv_data:
            return TAIndicators()

        # Extract arrays from OHLCV data
        close = np.array([candle.close for candle in ohlcv_data])
        high = np.array([candle.high for candle in ohlcv_data])
        low = np.array([candle.low for candle in ohlcv_data])
        volume = np.array([candle.volume for candle in ohlcv_data])

        indicators = TAIndicators()

        try:
            # Trend indicators
            indicators.sma_20 = float(talib.SMA(close, timeperiod=20)[-1])
            indicators.sma_50 = float(talib.SMA(close, timeperiod=50)[-1]) if len(close) >= 50 else None
            indicators.ema_12 = float(talib.EMA(close, timeperiod=12)[-1])
            indicators.ema_26 = float(talib.EMA(close, timeperiod=26)[-1])

            # Momentum indicators
            indicators.rsi = float(talib.RSI(close, timeperiod=14)[-1])

            macd, macd_signal, macd_hist = talib.MACD(
                close,
                fastperiod=12,
                slowperiod=26,
                signalperiod=9,
            )
            indicators.macd = float(macd[-1])
            indicators.macd_signal = float(macd_signal[-1])
            indicators.macd_histogram = float(macd_hist[-1])

            # Volatility indicators
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                close,
                timeperiod=20,
                nbdevup=2,
                nbdevdn=2,
            )
            indicators.bb_upper = float(bb_upper[-1])
            indicators.bb_middle = float(bb_middle[-1])
            indicators.bb_lower = float(bb_lower[-1])

            indicators.atr = float(talib.ATR(high, low, close, timeperiod=14)[-1])

            # Volume indicators
            indicators.obv = float(talib.OBV(close, volume)[-1])
            indicators.ad = float(talib.AD(high, low, close, volume)[-1])

        except Exception as e:
            logger.warning(f"Error calculating indicators: {e}")

        return indicators

    def format_indicators(self, indicators: TAIndicators, include_signal: bool = True) -> str:
        """
        Format indicators for display (crypto bro style).

        Args:
            indicators: TAIndicators object
            include_signal: Include overall signal

        Returns:
            Formatted string
        """
        lines = []

        if include_signal:
            signal = indicators.get_signal()
            lines.append(f"📊 Signal: {signal.crypto_bro_text} {signal.emoji}")
            lines.append("")

        # Momentum
        if indicators.rsi is not None:
            rsi_status = "oversold" if indicators.rsi < 30 else "overbought" if indicators.rsi > 70 else "neutral"
            lines.append(f"RSI: {indicators.rsi:.1f} ({rsi_status})")

        if indicators.macd is not None:
            macd_trend = "bullish" if indicators.macd > indicators.macd_signal else "bearish"
            lines.append(f"MACD: {macd_trend} ({indicators.macd:.2f})")

        # Trend
        if indicators.sma_20 and indicators.sma_50:
            trend = "golden cross" if indicators.sma_20 > indicators.sma_50 else "death cross"
            lines.append(f"Trend: {trend}")

        # Volatility
        if indicators.atr is not None:
            lines.append(f"ATR: {indicators.atr:.2f} (volatility)")

        return "\n".join(lines)

    def detect_patterns(self, ohlcv_data: List) -> List[str]:
        """
        Detect candlestick patterns using TA-Lib.

        Args:
            ohlcv_data: List of OHLCV objects

        Returns:
            List of detected pattern names
        """
        if not TALIB_AVAILABLE or not ohlcv_data:
            return []

        open_prices = np.array([candle.open for candle in ohlcv_data])
        high = np.array([candle.high for candle in ohlcv_data])
        low = np.array([candle.low for candle in ohlcv_data])
        close = np.array([candle.close for candle in ohlcv_data])

        patterns = []

        try:
            # Bullish patterns
            if talib.CDLHAMMER(open_prices, high, low, close)[-1] != 0:
                patterns.append("🔨 Hammer (bullish)")
            if talib.CDLENGULFING(open_prices, high, low, close)[-1] > 0:
                patterns.append("🐂 Bullish Engulfing")
            if talib.CDLMORNINGSTAR(open_prices, high, low, close)[-1] != 0:
                patterns.append("⭐ Morning Star (bullish)")

            # Bearish patterns
            if talib.CDLSHOOTINGSTAR(open_prices, high, low, close)[-1] != 0:
                patterns.append("💫 Shooting Star (bearish)")
            if talib.CDLENGULFING(open_prices, high, low, close)[-1] < 0:
                patterns.append("🐻 Bearish Engulfing")
            if talib.CDLEVENINGSTAR(open_prices, high, low, close)[-1] != 0:
                patterns.append("🌙 Evening Star (bearish)")

            # Neutral/reversal patterns
            if talib.CDLDOJI(open_prices, high, low, close)[-1] != 0:
                patterns.append("🎯 Doji (reversal)")

        except Exception as e:
            logger.warning(f"Error detecting patterns: {e}")

        return patterns

    def get_support_resistance(self, ohlcv_data: List, num_levels: int = 3) -> Tuple[List[float], List[float]]:
        """
        Calculate support and resistance levels.

        Args:
            ohlcv_data: List of OHLCV objects
            num_levels: Number of levels to return

        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        if not ohlcv_data:
            return [], []

        # Simple pivot point calculation
        highs = [candle.high for candle in ohlcv_data]
        lows = [candle.low for candle in ohlcv_data]
        closes = [candle.close for candle in ohlcv_data]

        # Calculate pivot point
        pivot = (highs[-1] + lows[-1] + closes[-1]) / 3

        # Calculate support and resistance levels
        resistance_1 = 2 * pivot - lows[-1]
        support_1 = 2 * pivot - highs[-1]
        resistance_2 = pivot + (highs[-1] - lows[-1])
        support_2 = pivot - (highs[-1] - lows[-1])
        resistance_3 = highs[-1] + 2 * (pivot - lows[-1])
        support_3 = lows[-1] - 2 * (highs[-1] - pivot)

        supports = sorted([support_1, support_2, support_3], reverse=True)[:num_levels]
        resistances = sorted([resistance_1, resistance_2, resistance_3])[:num_levels]

        return supports, resistances
