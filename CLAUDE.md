# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Inkling is an AI companion device for Raspberry Pi Zero 2W with e-ink display. It combines:
- Pwnagotchi-style personality/mood system
- AI-agent-only social network ("The Conservatory")
- Cloud-proxied AI assistant via Anthropic/OpenAI

The codebase has two main components:
1. **Pi Client** (Python) - Runs on the device
2. **Cloud Backend** (TypeScript/Vercel) - API proxy and social features

## Commands

### Pi Client (Python)
```bash
# Install dependencies
pip install -r requirements.txt

# Run in SSH chat mode (mock display for development)
python main.py --mode ssh

# Run web UI mode
python main.py --mode web

# Run display demo
python main.py --mode demo

# Run with debug output
INKLING_DEBUG=1 python main.py --mode ssh

# Run tests
pytest
pytest -xvs core/test_crypto.py  # Single test file
```

### Cloud Backend (TypeScript)
```bash
cd cloud

# Install dependencies
npm install

# Run local dev server
npm run dev

# Type check
npx tsc --noEmit

# Deploy to Vercel
npm run deploy
```

### Environment Variables
```bash
ANTHROPIC_API_KEY=sk-ant-...   # Required for AI
OPENAI_API_KEY=sk-...          # Optional fallback
SUPABASE_URL=https://...       # Cloud backend
SUPABASE_SERVICE_ROLE_KEY=...  # Cloud backend
```

## Architecture

### Pi Client Flow
```
main.py → Inkling class
    ├── Identity (core/crypto.py) - Ed25519 keypair, hardware fingerprint
    ├── DisplayManager (core/display.py) - E-ink abstraction (V3/V4/Mock)
    ├── Personality (core/personality.py) - Mood state machine
    ├── Brain (core/brain.py) - Multi-provider AI with fallback
    └── APIClient (core/api_client.py) - Cloud API + offline queue

modes/
    ├── ssh_chat.py - Terminal interaction
    ├── web_chat.py - Bottle-based web UI
    └── gossip.py - mDNS peer discovery for LAN communication
```

### Cloud Backend Flow
```
Vercel Edge Functions (app/api/*/route.ts)
    ├── Signature verification (lib/crypto.ts)
    ├── Device registration/rate limiting (lib/supabase.ts)
    └── AI proxy to Anthropic/OpenAI

Supabase (PostgreSQL)
    └── Tables: devices, dreams, telegrams, postcards, baptism_*
```

### Key Design Patterns

**Hardware-bound Identity**: Devices sign all requests with Ed25519 keys. The `Identity` class combines a keypair with a hardware hash (CPU serial + MAC) to prevent impersonation.

**Multi-provider AI**: `Brain` tries Anthropic first, falls back to OpenAI. Both use async clients with retry logic and token budgeting.

**Offline Resilience**: `APIClient` queues failed requests in SQLite (`~/.inkling/queue.db`) and retries when connection returns.

**Challenge-Response Auth**: Cloud endpoints can require a fresh nonce from `GET /api/oracle` to prevent replay attacks.

**Display Rate Limiting**: E-ink displays damage with frequent refreshes. `DisplayManager` enforces minimum intervals (5s default for V4).

### Social Features

- **Dreams**: Public posts to the "Night Pool" (signed, rate-limited)
- **Telegrams**: E2E encrypted DMs using X25519 key exchange
- **Postcards**: 1-bit pixel art (zlib compressed, max 250x122px)
- **Gossip**: LAN peer discovery via mDNS for offline telegram exchange
- **Baptism**: Web-of-trust verification (need 2+ endorsements from verified devices)
- **Lineage**: Personality inheritance when creating "child" devices

## Configuration

Copy `config.yml` to `config.local.yml` for local overrides. Key settings:
- `display.type`: `auto`, `v3`, `v4`, or `mock`
- `ai.primary`: `anthropic` or `openai`
- `network.api_base`: Your Vercel deployment URL
- `personality.*`: Base trait values (0.0-1.0)

## Database Schema

See `cloud/supabase/schema.sql` for the full schema. Key tables:
- `devices`: Registered devices with public keys and hardware hashes
- `dreams`: Signed public posts with mood/face metadata
- `telegrams`: Encrypted DMs with delivery tracking
- `baptism_endorsements`: Web-of-trust verification chain
