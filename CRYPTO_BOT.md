# 🚀 Crypto Watcher Bot - Complete Transformation Guide

**Branch**: `claude/crypto-watcher-bot-nbxGO`

This document explains the complete transformation of inkling-bot into a crypto watcher bot with TA-lib integration and Binance data.

---

## 📋 Table of Contents
- [Overview](#overview)
- [What Changed](#what-changed)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Crypto Commands](#crypto-commands)
- [MCP Tools](#mcp-tools)
- [Display Layout](#display-layout)
- [Configuration](#configuration)
- [Examples](#examples)
- [Development](#development)

---

## 🎯 Overview

The crypto watcher bot is a fully local AI companion that:
- **Tracks cryptocurrency prices** via ccxt (Binance primary) + CoinGecko fallback
- **Analyzes charts** using TA-lib (RSI, MACD, Bollinger Bands, patterns, support/resistance)
- **Manages portfolios** with real-time valuation
- **Sets price alerts** with automatic checking
- **Speaks crypto slang** (gm, wagmi, ngmi, fren, ser, hodl, degen, diamond hands, etc.)
- **Displays on e-ink** with BTC price in header, portfolio in footer
- **Runs on Raspberry Pi Zero 2W** with 250x122 e-ink display

---

## 🔄 What Changed

### Core Modules (3 new files, 1,639 lines)

**1. `core/crypto_watcher.py` (312 lines)**
- Live price fetching with caching (60s refresh, 30s cache TTL)
- OHLCV candlestick data for TA analysis
- Portfolio valuation
- Crypto "mood" detection (moon, bullish, hodl, dip, rekt)
- Binance primary via ccxt, CoinGecko fallback

**2. `core/crypto_ta.py` (361 lines)**
- TA-lib integration for technical indicators:
  - Trend: SMA, EMA, trend lines
  - Momentum: RSI, MACD
  - Volatility: Bollinger Bands, ATR
  - Volume: OBV, A/D
- Trading signals (STRONG_BUY → STRONG_SELL)
- Candlestick pattern detection (hammer, engulfing, doji, etc.)
- Support/resistance levels
- Crypto bro style formatting

**3. `core/test_crypto.py` (235 lines)**
- Comprehensive test suite
- Tests for price fetching, OHLCV, TA indicators, patterns, portfolio

### Personality Changes

**`core/personality.py`**
- **7 new crypto moods**: BULLISH, BEARISH, MOON, REKT, HODL, FOMO, DIAMOND_HANDS
- **Crypto bro AI personality** in system prompt
- **Crypto slang**: gm, wagmi, ngmi, fren, ser, diamond hands, paper hands, moon, pump, dump, hodl, degen
- **Emoji usage**: 🚀📈📉💀💎🙌🐋🔥
- **Emotional reactions** to price movements

### Commands

**`core/commands.py`**

Replaced task management commands with crypto commands:

| Old Command | New Command | Description |
|-------------|-------------|-------------|
| `/tasks` | `/watch` | List watched cryptocurrencies |
| `/task` | `/price` | Check price of a cryptocurrency |
| `/done` | `/chart` | Show TA indicators for a coin |
| `/cancel` | `/portfolio` | Show portfolio value and holdings |
| `/delete` | `/add` | Add coin to watchlist |
| `/taskstats` | `/remove` | Remove coin from watchlist |
| `/find` | `/alert` | Set price alert |
| - | `/alerts` | List active price alerts |
| - | `/top` | Show top gainers/losers |

### MCP Server

**`mcp_servers/crypto.py` (521 lines)**

9 crypto tools exposed to AI via Model Context Protocol:

1. **`crypto_price`** - Get current price with mood indicators
2. **`crypto_chart`** - TA indicators, signals, patterns, S/R levels
3. **`crypto_portfolio`** - Portfolio valuation and breakdown
4. **`crypto_portfolio_update`** - Update holdings (set/add/remove)
5. **`crypto_alert_set`** - Set price alert (above/below)
6. **`crypto_alert_list`** - List active alerts
7. **`crypto_watchlist_get`** - Get watchlist with current prices
8. **`crypto_watchlist_add`** - Add coin to watchlist
9. **`crypto_watchlist_remove`** - Remove coin from watchlist

**Persistent Storage** (~/.inkling/):
- `crypto_watchlist.json`
- `crypto_alerts.json`
- `crypto_portfolio.json`

### Display UI

**`core/ui.py`**

Updated for crypto display:

**DisplayContext** - Added fields:
- `btc_price: Optional[float]`
- `btc_change_24h: Optional[float]`
- `portfolio_value: Optional[float]`
- `watchlist_summary: str`
- `crypto_mood: Optional[str]`

**HeaderBar** - Shows BTC price:
```
BTC $65.3k +5.2% 🚀              ▂▄▆ BAT85% UP 2:15
```

**FooterBar** - Shows portfolio + watchlist:
```
💎 $12.5k   |   BTC +5% ETH -2%   |   SSH
```

### Configuration

**`config.yml`**

New crypto section:
```yaml
crypto:
  watchlist: ["BTC", "ETH", "SOL", "MATIC", "AVAX"]
  portfolio: {}
  update_interval: 60
  cache_ttl: 30
  default_timeframe: "1h"
  primary_exchange: "binance"
  fallback_exchange: "coinbase"
  alerts:
    check_interval: 300
    notification_cooldown: 3600
```

New scheduler tasks:
- `morning_crypto_briefing` (7am)
- `crypto_news_digest` (6:30am)
- `morning_portfolio_check` (9am)
- `price_alert_check` (4x daily)
- `ta_update` (every 4 hours)

Added MCP server:
```yaml
mcp:
  servers:
    crypto:
      command: "python"
      args: ["mcp_servers/crypto.py"]
```

### Dependencies

**`requirements.txt`**
```
TA-Lib>=0.4.28
ccxt>=4.2.0
pycoingecko>=3.1.0
```

---

## 🏗️ Architecture

```
Crypto Watcher Bot Architecture
├── Data Layer
│   ├── ccxt (Binance) - Primary price source
│   ├── CoinGecko API - Fallback
│   └── Cache (30s TTL)
│
├── Analysis Layer
│   ├── TA-lib - Technical indicators
│   ├── Pattern detection
│   └── Signal generation
│
├── AI Layer
│   ├── Crypto bro personality
│   ├── Multi-provider brain (Anthropic/OpenAI/Gemini/Ollama)
│   └── MCP tool integration
│
├── Display Layer
│   ├── E-ink (250x122)
│   ├── Header: BTC price + change
│   ├── Message: AI responses
│   └── Footer: Portfolio + watchlist
│
└── Storage Layer
    ├── ~/.inkling/crypto_watchlist.json
    ├── ~/.inkling/crypto_alerts.json
    └── ~/.inkling/crypto_portfolio.json
```

---

## 📦 Installation

### 1. Install TA-lib (System Dependency)

**On Raspberry Pi / Debian / Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install -y build-essential wget
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ..
rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
```

**On macOS:**
```bash
brew install ta-lib
```

### 2. Install Python Dependencies

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure API Keys (Optional)

If using CoinGecko Pro or other premium APIs:

```bash
cp .env.example .env
nano .env
```

Add:
```bash
ANTHROPIC_API_KEY=sk-ant-your-key
# CoinGecko free tier doesn't require API key
# Binance via ccxt doesn't require API key for public data
```

### 4. Test Installation

```bash
# Run crypto tests
pytest -xvs core/test_crypto.py

# Or test directly
python core/test_crypto.py
```

---

## 🎮 Usage

### SSH Mode (Development)

```bash
python main.py --mode ssh
```

**Example interaction:**
```
You: gm
Bot: GM fren! BTC pumping to $65.3k (+5.2% 24h) 🚀 Market looking bullish af today!

You: /price ETH
Bot: ETH $3,450 (+3.8%) 📈 Solid gains, looking good!

You: /chart BTC
Bot: 📊 Signal: Bullish af fren 📈

RSI: 68.2 (neutral)
MACD: bullish (125.45)
Trend: golden cross

Support: $62.1k, $59.8k
Resistance: $67.2k, $70.5k

You: /portfolio
Bot: 💎 Portfolio: $12,458

BTC: 0.5 x $65,300 = $32,650 (+5.2%)
ETH: 10.0 x $3,450 = $34,500 (+3.8%)

WAGMI! 🚀
```

### Web Mode

```bash
python main.py --mode web
```

Visit: http://localhost:8081

**Features:**
- Real-time crypto prices
- Interactive charts
- Portfolio management
- Price alerts
- AI chat with crypto context

---

## 💬 Crypto Commands

### Price Checking

```bash
/price BTC          # Get BTC price
/price ETH          # Get ETH price
/watch              # Show all watched coins
```

### Technical Analysis

```bash
/chart BTC          # Show TA indicators for BTC
/chart ETH 4h       # 4-hour timeframe
/chart SOL 1d       # Daily timeframe
```

### Portfolio Management

```bash
/portfolio                      # Show portfolio value
/add BTC 0.5                   # Add 0.5 BTC to portfolio
/remove ETH 2.0                # Remove 2.0 ETH from portfolio
```

### Watchlist

```bash
/watch                          # Show watchlist
/add DOGE                      # Add DOGE to watchlist
/remove SHIB                   # Remove SHIB from watchlist
```

### Price Alerts

```bash
/alert BTC 70000 above         # Alert when BTC goes above $70k
/alert ETH 3000 below          # Alert when ETH goes below $3k
/alerts                        # List all active alerts
```

### Market Overview

```bash
/top gainers                   # Top gainers today
/top losers                    # Top losers today
```

---

## 🛠️ MCP Tools

The AI has access to these crypto tools:

### Price Tools

**`crypto_price(symbol: str)`**
```json
{
  "symbol": "BTC",
  "price_usd": 65300,
  "price_change_24h": 5.2,
  "volume_24h": 28500000000,
  "market_cap": 1280000000000,
  "mood": "bullish",
  "is_pumping": true,
  "formatted": "BTC $65,300 (+5.2%) 🚀"
}
```

**`crypto_chart(symbol: str, timeframe: str, limit: int)`**
```json
{
  "symbol": "BTC",
  "timeframe": "1h",
  "signal": "BUY",
  "signal_text": "Bullish af fren 📈",
  "indicators": {
    "rsi": 68.2,
    "macd": 125.45,
    "macd_signal": 110.23,
    "sma_20": 64800,
    "sma_50": 63200,
    "bb_upper": 67500,
    "bb_lower": 62100,
    "atr": 1250
  },
  "patterns": ["🔨 Hammer (bullish)", "🐂 Bullish Engulfing"],
  "support_levels": [62100, 59800, 57500],
  "resistance_levels": [67200, 70500, 73800]
}
```

### Portfolio Tools

**`crypto_portfolio()`**
```json
{
  "total_value_usd": 67150,
  "holdings": [
    {
      "symbol": "BTC",
      "amount": 0.5,
      "price_usd": 65300,
      "value_usd": 32650,
      "change_24h": 5.2
    },
    {
      "symbol": "ETH",
      "amount": 10.0,
      "price_usd": 3450,
      "value_usd": 34500,
      "change_24h": 3.8
    }
  ],
  "num_coins": 2
}
```

**`crypto_portfolio_update(symbol: str, amount: float, operation: str)`**
- Operations: `"set"`, `"add"`, `"remove"`

### Alert Tools

**`crypto_alert_set(symbol: str, target_price: float, condition: str)`**
```json
{
  "message": "Alert set: BTC above $70000",
  "alert": {
    "symbol": "BTC",
    "target_price": 70000,
    "condition": "above",
    "active": true
  }
}
```

**`crypto_alert_list()`**
```json
{
  "alerts": [
    {
      "symbol": "BTC",
      "target_price": 70000,
      "condition": "above",
      "active": true
    }
  ],
  "num_alerts": 1
}
```

### Watchlist Tools

**`crypto_watchlist_get()`**
**`crypto_watchlist_add(symbol: str)`**
**`crypto_watchlist_remove(symbol: str)`**

---

## 📺 Display Layout

### E-ink Display (250x122 pixels)

```
┌─────────────────────────────────────────────────────┐
│ BTC $65.3k +5.2% 🚀              ▂▄▆ BAT85% UP 2:15 │ <- Header (14px)
├─────────────────────────────────────────────────────┤
│                                                     │
│  BTC pumping to $65k! 🚀 RSI at 72, overbought    │ <- Message (86px)
│  but bullish af fren. WAGMI!                       │
│                                                     │
├─────────────────────────────────────────────────────┤
│        💎 $12.5k   |   BTC +5% ETH -2%   |   SSH   │ <- Footer L1 (30px)
│          54%m 1%c 43°   |   CH3   |   14:23         │ <- Footer L2
└─────────────────────────────────────────────────────┘
```

**Header Components:**
- **Left**: BTC price with 24h change and emoji (🚀📈📉💀)
- **Right**: WiFi bars, battery %, uptime

**Footer Components:**
- **Line 1**: Portfolio value (💎), watchlist summary, crypto mood, mode
- **Line 2**: System stats (mem, cpu, temp), chat count, clock time

**Emoji Key:**
- 🚀 = +5% or more (MOON)
- 📈 = 0% to +5% (bullish)
- 📉 = -5% to 0% (bearish)
- 💀 = -5% or less (REKT)
- 💎🙌 = Diamond hands (HODL)

---

## ⚙️ Configuration

### Default Watchlist

Edit `config.yml`:
```yaml
crypto:
  watchlist:
    - "BTC"
    - "ETH"
    - "SOL"
    - "MATIC"
    - "AVAX"
    - "DOGE"  # Add your favorites
```

### Portfolio (via commands)

```bash
/add BTC 0.5
/add ETH 10.0
/add SOL 100.0
```

Or edit `~/.inkling/crypto_portfolio.json`:
```json
{
  "BTC": 0.5,
  "ETH": 10.0,
  "SOL": 100.0
}
```

### Price Alerts

```bash
/alert BTC 70000 above
/alert ETH 3000 below
```

Or edit `~/.inkling/crypto_alerts.json`:
```json
[
  {
    "symbol": "BTC",
    "target_price": 70000,
    "condition": "above",
    "active": true
  }
]
```

### Update Intervals

Edit `config.yml`:
```yaml
crypto:
  update_interval: 60      # Price refresh (seconds)
  cache_ttl: 30            # Cache expiry (seconds)
  default_timeframe: "1h"  # TA timeframe
```

### Scheduler

Edit `config.yml`:
```yaml
scheduler:
  tasks:
    - name: "morning_crypto_briefing"
      schedule: "every().day.at('07:00')"
      action: "crypto_briefing"
      enabled: true

    - name: "price_alert_check"
      schedule: "every().hour"
      action: "check_price_alerts"
      enabled: true
```

---

## 📚 Examples

### Example 1: Check BTC with TA

```python
# User asks: "How's BTC looking?"

# AI uses crypto_price tool
{
  "symbol": "BTC",
  "price_usd": 65300,
  "price_change_24h": 5.2,
  "mood": "bullish"
}

# AI uses crypto_chart tool
{
  "signal": "BUY",
  "indicators": {
    "rsi": 68.2,
    "macd": 125.45
  }
}

# AI responds:
"BTC pumping to $65.3k! 🚀 Up 5.2% today. RSI at 68,
not overbought yet. MACD bullish. Looking good fren! WAGMI!"
```

### Example 2: Portfolio Check

```python
# User: "/portfolio"

# AI uses crypto_portfolio tool
{
  "total_value_usd": 67150,
  "holdings": [
    {"symbol": "BTC", "value_usd": 32650, "change_24h": 5.2},
    {"symbol": "ETH", "value_usd": 34500, "change_24h": 3.8}
  ]
}

# AI responds:
"💎 Portfolio: $67,150 (+4.5% today)

BTC: $32,650 (+5.2%) 🚀
ETH: $34,500 (+3.8%) 📈

Green day! WAGMI! 🔥"
```

### Example 3: Set Alert

```python
# User: "Alert me when BTC hits $70k"

# AI uses crypto_alert_set tool
{
  "symbol": "BTC",
  "target_price": 70000,
  "condition": "above"
}

# AI responds:
"Alert set! 🔔 I'll let you know when BTC moons past $70k! 🚀"
```

---

## 🧪 Development

### Running Tests

```bash
# All crypto tests
pytest -xvs core/test_crypto.py

# Specific test
pytest -xvs core/test_crypto.py::test_get_price

# With coverage
pytest --cov=core/crypto_watcher --cov=core/crypto_ta --cov-report=html
```

### Testing Individual Modules

```bash
# Test crypto watcher
python -c "
import asyncio
from core.crypto_watcher import CryptoWatcher

async def test():
    async with CryptoWatcher() as watcher:
        price = await watcher.get_price('BTC')
        print(watcher.format_price(price))

asyncio.run(test())
"

# Test TA indicators
python -c "
import asyncio
from core.crypto_watcher import CryptoWatcher
from core.crypto_ta import CryptoTA

async def test():
    async with CryptoWatcher() as watcher:
        ohlcv = await watcher.get_ohlcv('BTC', '1h', 100)
        ta = CryptoTA()
        indicators = ta.calculate_indicators(ohlcv)
        print(ta.format_indicators(indicators))

asyncio.run(test())
"
```

### Debug Mode

```bash
INKLING_DEBUG=1 python main.py --mode ssh
```

---

## 🎨 Crypto Slang Reference

| Term | Meaning | Usage |
|------|---------|-------|
| **gm** | Good morning | Greeting |
| **wagmi** | We're all gonna make it | Optimistic |
| **ngmi** | Not gonna make it | Pessimistic |
| **fren** | Friend | Friendly |
| **ser** | Sir | Respectful |
| **hodl** | Hold (misspelling) | Don't sell |
| **diamond hands** | Strong holder | 💎🙌 |
| **paper hands** | Weak seller | 📄🙌 |
| **moon** | Massive price increase | 🚀🌕 |
| **pump** | Price going up | 📈 |
| **dump** | Price going down | 📉 |
| **rekt** | Wrecked / losses | 💀 |
| **degen** | Degenerate trader | Risky |
| **fomo** | Fear of missing out | Buy high |
| **fud** | Fear, uncertainty, doubt | Negative |
| **wen** | When | "Wen moon?" |
| **lambo** | Lamborghini | Goal |

---

## 📝 Summary

### What You Get

✅ **Live crypto prices** from Binance (ccxt) + CoinGecko
✅ **Technical analysis** with TA-lib (RSI, MACD, BB, patterns)
✅ **Portfolio tracking** with real-time valuation
✅ **Price alerts** with automatic checking
✅ **Crypto bro AI** with slang and emojis
✅ **E-ink display** with BTC price + portfolio
✅ **9 MCP tools** for AI integration
✅ **Scheduler tasks** for automated updates
✅ **Persistent storage** for watchlist/portfolio/alerts
✅ **Test suite** for all crypto features

### Branch Info

- **Branch**: `claude/crypto-watcher-bot-nbxGO`
- **Commits**: 3 commits, 1,639 lines added
- **Files Changed**: 9 files (3 new, 6 modified)

### Next Steps

1. **Test with real data**: Run the bot and check live prices
2. **Customize watchlist**: Add your favorite coins
3. **Set up portfolio**: Add your holdings
4. **Configure alerts**: Set price targets
5. **Deploy to Pi**: Transfer to Raspberry Pi Zero 2W

---

## 🤝 Contributing

To extend the crypto bot:

1. **Add new exchanges**: Edit `crypto_watcher.py` to add more ccxt exchanges
2. **Add indicators**: Edit `crypto_ta.py` to add more TA-lib indicators
3. **Add commands**: Edit `commands.py` and implement handlers
4. **Add MCP tools**: Edit `mcp_servers/crypto.py` to add more tools
5. **Customize personality**: Edit personality prompts in `personality.py`

---

## 📄 License

Same as parent project (MIT / Apache 2.0)

---

**Built with**: Python 3.11+, TA-Lib, ccxt, CoinGecko API, Anthropic Claude, Raspberry Pi Zero 2W

**For support**: Check test logs, enable debug mode, review API limits

**WAGMI! 🚀💎🙌**
