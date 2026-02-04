# AI Providers Guide

Configure Inkling to use Anthropic (Claude), OpenAI (GPT), Google (Gemini), or OpenAI-compatible APIs.

## Overview

Inkling's Brain module supports multiple AI providers with automatic fallback:

```
Primary Provider → Fallback Provider(s) → Error
```

If the primary provider fails (rate limit, quota, error), Inkling automatically tries the next provider.

## Supported Providers

| Provider | Models | Best For | Cost |
|----------|--------|----------|------|
| **Anthropic** | Claude Haiku, Sonnet, Opus | Best quality, safety | Medium |
| **OpenAI** | GPT-5-mini, GPT-5.2 | Fast, reliable | Medium |
| **Gemini** | Gemini 2.0 Flash, 1.5 Pro | Free tier available | Low/Free |
| **OpenAI-compatible** | Ollama, Groq, Together | Local/alternative | Varies |

## Quick Setup

### 1. Get API Keys

**Anthropic Claude**:
1. Visit [console.anthropic.com](https://console.anthropic.com)
2. Create account and add payment method
3. Generate API key in Settings

**OpenAI GPT**:
1. Visit [platform.openai.com](https://platform.openai.com)
2. Create account and add payment method
3. Generate API key in API Keys section

**Google Gemini**:
1. Visit [makersuite.google.com](https://makersuite.google.com)
2. Sign in with Google account
3. Get API key (free tier available!)

### 2. Configure Keys

Add to `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-google-api-key-here
```

Or in `config.local.yml`:

```yaml
ai:
  anthropic:
    api_key: "sk-ant-your-key-here"
  openai:
    api_key: "sk-your-key-here"
  gemini:
    api_key: "your-google-api-key-here"
```

### 3. Set Primary Provider

```yaml
ai:
  primary: "anthropic"  # or "openai" or "gemini"
```

## Provider Configuration

### Anthropic (Claude)

```yaml
ai:
  primary: "anthropic"
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: "claude-haiku-4-5"     # Fast, cheap
    # model: "claude-sonnet-4-5"  # Balanced
    # model: "claude-opus-4-5"    # Best quality
    max_tokens: 150
```

**Model Comparison**:

| Model | Speed | Quality | Cost/1M tokens |
|-------|-------|---------|----------------|
| claude-haiku-4-5 | Fastest | Good | $0.25 |
| claude-sonnet-4-5 | Medium | Great | $3.00 |
| claude-opus-4-5 | Slow | Best | $15.00 |

**Recommendation**: Use Haiku for Inkling (fast responses, low cost, sufficient for companion chat).

### OpenAI (GPT)

```yaml
ai:
  primary: "openai"
  openai:
    api_key: ${OPENAI_API_KEY}
    model: "gpt-5-mini"     # Fast, cheap
    # model: "gpt-5.2"      # Best quality
    max_tokens: 150
    # base_url: null        # Default OpenAI API
```

**Model Comparison**:

| Model | Speed | Quality | Cost/1M tokens |
|-------|-------|---------|----------------|
| gpt-5-mini | Fast | Good | $0.15 |
| gpt-5.2 | Medium | Great | $5.00 |

### Google Gemini

```yaml
ai:
  primary: "gemini"
  gemini:
    api_key: ${GOOGLE_API_KEY}
    model: "gemini-2.0-flash-exp"  # Fast, free tier
    # model: "gemini-1.5-flash"    # Stable
    # model: "gemini-1.5-pro"      # Best quality
    max_tokens: 150
```

**Model Comparison**:

| Model | Speed | Quality | Free Tier |
|-------|-------|---------|-----------|
| gemini-2.0-flash-exp | Fastest | Good | Yes (60 RPM) |
| gemini-1.5-flash | Fast | Good | Yes (15 RPM) |
| gemini-1.5-pro | Medium | Great | Yes (2 RPM) |

**Note**: Gemini's free tier is great for development and light use!

### OpenAI-Compatible APIs

Use local models (Ollama) or alternative providers:

```yaml
ai:
  primary: "openai"
  openai:
    api_key: "ollama"  # Can be anything for Ollama
    model: "llama3.2"
    max_tokens: 150
    base_url: "http://localhost:11434/v1"  # Ollama
```

**Common Base URLs**:

| Provider | Base URL |
|----------|----------|
| Ollama (local) | `http://localhost:11434/v1` |
| Together AI | `https://api.together.xyz/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |

## Token Budgeting

Control costs with token limits:

```yaml
ai:
  budget:
    daily_tokens: 10000    # Max tokens per day
    per_request_max: 500   # Max tokens per request
```

### Cost Estimation

With default settings (10,000 tokens/day, Haiku):
- **Daily cost**: ~$0.0025 ($0.075/month)
- **Per interaction**: ~$0.00025

### Viewing Usage

```bash
/stats
# Output:
# Tokens used today: 2,345 / 10,000
# Remaining: 7,655 (76.5%)
# Providers: anthropic, openai
```

## Fallback Configuration

Configure multiple providers for reliability:

```yaml
ai:
  primary: "anthropic"

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: "claude-haiku-4-5"

  openai:
    api_key: ${OPENAI_API_KEY}
    model: "gpt-5-mini"

  gemini:
    api_key: ${GOOGLE_API_KEY}
    model: "gemini-2.0-flash-exp"
```

**Fallback order**:
1. Primary provider (Anthropic)
2. OpenAI (if configured)
3. Gemini (if configured)

Each provider is tried with 3 retries (exponential backoff) before moving to next.

## Response Configuration

### Max Tokens

Controls response length:

```yaml
ai:
  anthropic:
    max_tokens: 150  # ~1-2 sentences
```

For Inkling's small display:
- **100-150**: Brief, fits display well
- **200-300**: Moderate, may need pagination
- **500+**: Long, requires pagination

### Temperature (Advanced)

Not directly configurable, but affects response creativity:
- Default is balanced for companion chat
- Model-specific defaults are used

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GOOGLE_API_KEY` | Google Gemini API key |
| `GEMINI_API_KEY` | Alternative for Google (either works) |
| `INKLING_DEBUG` | Set to `1` for debug output |

## Troubleshooting

### "No AI providers configured"

Check API keys are set:

```bash
# Verify environment
echo $ANTHROPIC_API_KEY

# Or check .env
cat .env | grep API_KEY
```

### Rate Limit Errors

- Inkling auto-retries with backoff
- If persistent, reduce daily_tokens limit
- Consider adding fallback provider

### Quota Exceeded

- Check your API provider dashboard
- Add payment method if needed
- Reduce token budget

### Slow Responses

1. Use faster model (Haiku, GPT-5-mini, Flash)
2. Reduce max_tokens
3. Check network connection
4. Consider local model (Ollama)

### Debug Mode

Enable detailed logging:

```bash
INKLING_DEBUG=1 python main.py --mode ssh
```

Shows:
- Provider selection
- Token counts
- API responses
- Error details

## Cost Optimization Tips

1. **Use Haiku/GPT-5-mini/Flash** for companion chat (sufficient quality)
2. **Set reasonable daily limit** (10,000 tokens is ~100 interactions)
3. **Use Gemini free tier** for development
4. **Local models** (Ollama) for unlimited free usage
5. **Clear conversation history** periodically (`/clear`)

## Recommended Setup

### Budget-Friendly
```yaml
ai:
  primary: "gemini"
  gemini:
    model: "gemini-2.0-flash-exp"  # Free tier
  budget:
    daily_tokens: 20000
```

### Balanced
```yaml
ai:
  primary: "anthropic"
  anthropic:
    model: "claude-haiku-4-5"
  openai:
    model: "gpt-5-mini"
  gemini:
    model: "gemini-2.0-flash-exp"
  budget:
    daily_tokens: 10000
```

### Quality-Focused
```yaml
ai:
  primary: "anthropic"
  anthropic:
    model: "claude-sonnet-4-5"
  budget:
    daily_tokens: 5000  # Higher cost per token
```

### Fully Local
```yaml
ai:
  primary: "openai"
  openai:
    model: "llama3.2"
    base_url: "http://localhost:11434/v1"
  budget:
    daily_tokens: 100000  # No cost limit needed
```

## Next Steps

- [Customize Themes](themes-appearance.md)
- [Set Up Task Management](../features/task-management.md)
- [Configure MCP Tools](../features/mcp-integration.md)
