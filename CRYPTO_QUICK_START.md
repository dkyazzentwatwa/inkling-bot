# 🚀 Crypto Watcher Bot - Quick Start

**5-minute setup guide for the crypto watcher bot**

---

## 📦 Prerequisites

1. **Python 3.11+** installed
2. **Virtual environment** activated
3. **TA-lib system library** installed

---

## ⚡ Quick Install

### 1. Install TA-lib (One-time)

**Raspberry Pi / Debian / Ubuntu:**
```bash
sudo apt-get update && sudo apt-get install -y build-essential wget
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/ && ./configure --prefix=/usr && make && sudo make install
cd .. && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
```

**macOS:**
```bash
brew install ta-lib
```

### 2. Install Python Dependencies

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Test Installation

```bash
python core/test_crypto.py
```

You should see:
```
=== Crypto Watcher Tests ===

BTC Price: BTC $65,300.00 (+5.20%) 🚀
...
=== All tests completed ===
```

---

## 🎮 Basic Usage

### Start the Bot

**SSH Mode (Terminal):**
```bash
python main.py --mode ssh
```

**Web Mode (Browser):**
```bash
python main.py --mode web
# Visit http://localhost:8081
```

### Try These Commands

```bash
gm                      # Say good morning
/price BTC              # Check Bitcoin price
/chart BTC              # Show TA indicators
/watch                  # Show watchlist
/portfolio              # Show portfolio value
/alert BTC 70000 above  # Set price alert
```

---

## 💎 Set Up Your Portfolio

```bash
/add BTC 0.5        # Add 0.5 BTC
/add ETH 10.0       # Add 10 ETH
/add SOL 100.0      # Add 100 SOL
/portfolio          # Check total value
```

---

## 🔔 Set Price Alerts

```bash
/alert BTC 70000 above   # Alert when BTC > $70k
/alert ETH 3000 below    # Alert when ETH < $3k
/alerts                  # List all alerts
```

---

## 📊 Customize Watchlist

Edit `config.yml`:
```yaml
crypto:
  watchlist:
    - "BTC"
    - "ETH"
    - "SOL"
    - "YOUR_COIN_HERE"
```

Or use commands:
```bash
/add DOGE       # Add to watchlist
/remove SHIB    # Remove from watchlist
```

---

## 🎨 Example Interactions

**Check BTC:**
```
You: How's BTC?
Bot: BTC pumping to $65.3k! 🚀 Up 5.2% today.
     RSI at 68, not overbought yet. WAGMI!
```

**Portfolio:**
```
You: /portfolio
Bot: 💎 Portfolio: $67,150 (+4.5% today)

     BTC: $32,650 (+5.2%) 🚀
     ETH: $34,500 (+3.8%) 📈

     Green day! WAGMI! 🔥
```

**TA Analysis:**
```
You: /chart BTC
Bot: 📊 Signal: Bullish af fren 📈

     RSI: 68.2 (neutral)
     MACD: bullish (125.45)
     Trend: golden cross

     Support: $62.1k, $59.8k
     Resistance: $67.2k, $70.5k
```

---

## 📺 Display Preview

When running on e-ink (250x122):

```
┌─────────────────────────────────────────────────────┐
│ BTC $65.3k +5.2% 🚀              ▂▄▆ BAT85% UP 2:15 │
├─────────────────────────────────────────────────────┤
│  BTC pumping to $65k! 🚀 RSI at 72, overbought    │
│  but bullish af fren. WAGMI!                       │
├─────────────────────────────────────────────────────┤
│        💎 $12.5k   |   BTC +5% ETH -2%   |   SSH   │
│          54%m 1%c 43°   |   CH3   |   14:23         │
└─────────────────────────────────────────────────────┘
```

---

## 🐛 Troubleshooting

**"No module named 'talib'"**
```bash
# Install TA-lib system library (see step 1)
# Then reinstall Python package
pip install --upgrade TA-Lib
```

**"Exchange (ccxt) failed"**
```bash
# Normal! Falls back to CoinGecko automatically
# Check internet connection
ping api.binance.com
```

**"Failed to fetch price"**
```bash
# Enable debug mode
INKLING_DEBUG=1 python main.py --mode ssh
```

**Price not showing on display**
```bash
# Crypto data loads on first price check
# Try: /price BTC
# Display will update with BTC price in header
```

---

## 📚 Full Documentation

For complete details, see:
- **[CRYPTO_BOT.md](CRYPTO_BOT.md)** - Full transformation guide
- **[CLAUDE.md](CLAUDE.md)** - Development guide

---

## 🎯 Quick Reference

### Commands
- `/price <symbol>` - Check price
- `/chart <symbol>` - TA indicators
- `/watch` - Show watchlist
- `/portfolio` - Portfolio value
- `/add <symbol> <amount>` - Add holding
- `/alert <symbol> <price> <above|below>` - Set alert
- `/alerts` - List alerts

### Files
- `core/crypto_watcher.py` - Price fetching
- `core/crypto_ta.py` - TA analysis
- `mcp_servers/crypto.py` - MCP tools
- `config.yml` - Configuration
- `~/.inkling/crypto_watchlist.json` - Watchlist
- `~/.inkling/crypto_portfolio.json` - Portfolio
- `~/.inkling/crypto_alerts.json` - Alerts

### Config
```yaml
crypto:
  watchlist: ["BTC", "ETH", "SOL"]
  update_interval: 60
  cache_ttl: 30
```

---

**WAGMI! 🚀💎🙌**

Need help? Check logs with `INKLING_DEBUG=1` or review test output.
