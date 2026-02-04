# Fix: Gemini Rate Limiting

## The Problem

You're seeing:
```
[Brain] GeminiProvider rate limited, retrying in 1.0s...
[Brain] GeminiProvider rate limited, retrying in 2.1s...
[Brain] GeminiProvider rate limited, retrying in 4.2s...
```

## Why This Happens

**Gemini Free Tier Limits:**
- 15 requests per minute
- 1 request per second
- Smaller request size limits

When MCP tools are enabled (even 20-50 tools), the request can hit these limits.

## Solutions (Try in Order)

### 1. Reduce Tool Count (Quickest Fix)

Edit `config.local.yml`:

```yaml
mcp:
  enabled: true
  max_tools: 10  # Lower limit = less rate limiting
```

Or even lower:
```yaml
mcp:
  max_tools: 5  # Just essentials
```

### 2. Disable MCP for Simple Chat

Edit `config.local.yml`:

```yaml
mcp:
  enabled: false  # Disable tools entirely
```

You can enable it only when you need tools.

### 3. Use OpenAI Instead

OpenAI has much higher rate limits. Edit `config.local.yml`:

```yaml
ai:
  primary: "openai"  # Switch to OpenAI
```

### 4. Upgrade to Gemini Paid Tier

Get higher limits:
- Go to https://aistudio.google.com/
- Upgrade to paid tier
- Much higher rate limits (1000+ requests/min)

### 5. Use Anthropic

Anthropic (Claude) has generous limits even on free tier:

```yaml
ai:
  primary: "anthropic"
```

Set `ANTHROPIC_API_KEY` in `.env`

## Recommended Setup

**For casual chat** (no tools needed):
```yaml
ai:
  primary: "gemini"

mcp:
  enabled: false
```

**For tool usage** (tasks, email, etc.):
```yaml
ai:
  primary: "anthropic"  # or "openai"

mcp:
  enabled: true
  max_tools: 20
```

**For Gemini with tools** (if you must):
```yaml
ai:
  primary: "gemini"

mcp:
  enabled: true
  max_tools: 5  # Keep it very low
```

## Current Status

Your current system prompt now tells the AI:
> "Only use tools when the user explicitly asks for something that requires them - simple greetings and chat don't need tools."

This should help reduce unnecessary tool use.

## Testing

After changing config:

```bash
cd ~/cypher/inkling-bot
git pull
python main.py --mode web
```

Try: `hello` - Should respond immediately without rate limiting.

Try: `show me my tasks` - Will use tools if needed.
