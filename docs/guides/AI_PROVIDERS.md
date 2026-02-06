# AI Provider Configuration

This guide covers how to configure AI providers for your Inkling device.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Supported Providers](#supported-providers)
3. [Getting API Keys](#getting-api-keys)
4. [Configuration Methods](#configuration-methods)
5. [Provider-Specific Setup](#provider-specific-setup)
6. [Using Ollama Cloud](#using-ollama-cloud)
7. [Groq (OpenAI-Compatible)](#groq-openai-compatible)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

The fastest way to get started:

```bash
# Set your API key as an environment variable
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Run Inkling
python main.py --mode ssh
```

That's it! Inkling will use Claude by default.

---

## Supported Providers

| Provider | Type | Cost | Best For |
|----------|------|------|----------|
| **Anthropic (Claude)** | Cloud | Pay-per-token | Primary use, best quality |
| **OpenAI (GPT)** | Cloud | Pay-per-token | Fallback option |
| **Google (Gemini)** | Cloud | Free tier available | Budget-conscious |
| **Ollama** | Cloud | API key required | Hosted models via Ollama Cloud |
| **Groq** | Cloud | Free tier | Fast inference |
| **Together AI** | Cloud | Pay-per-token | Open-source models |
| **OpenRouter** | Cloud | Pay-per-token | Model variety |

---

## Getting API Keys

### Anthropic (Claude)

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to **API Keys**
4. Click **Create Key**
5. Copy the key (starts with `sk-ant-`)

**Pricing**: ~$0.25/million input tokens, ~$1.25/million output tokens (Haiku)

### OpenAI (GPT)

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Navigate to **API Keys**
4. Click **Create new secret key**
5. Copy the key (starts with `sk-`)

**Pricing**: ~$0.15/million input tokens, ~$0.60/million output tokens (GPT-4o-mini)

### Google (Gemini)

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Sign in with Google account
3. Click **Get API Key**
4. Create a key for a new or existing project
5. Copy the key

**Pricing**: Free tier available (60 requests/minute)

### Groq

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Navigate to **API Keys**
4. Click **Create API Key**
5. Copy the key (starts with `gsk_`)

**Pricing**: Free tier (30 requests/minute), then pay-per-token

### Together AI

1. Go to [api.together.xyz](https://api.together.xyz)
2. Sign up or log in
3. Navigate to **Settings** > **API Keys**
4. Copy your key

**Pricing**: Pay-per-token, varies by model

### OpenRouter

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up or log in
3. Navigate to **Keys**
4. Create a new key
5. Copy the key (starts with `sk-or-`)

**Pricing**: Pay-per-token, varies by model

---

## Configuration Methods

### Method 1: Environment Variables (Recommended)

Set variables in your shell or `.bashrc`/`.zshrc`:

```bash
# Primary provider
export ANTHROPIC_API_KEY="sk-ant-..."

# Fallback providers (optional)
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="AIza..."

# For Groq via OpenAI-compatible endpoint
export GROQ_API_KEY="gsk_..."
```

For the Pi, add to `~/.bashrc`:
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
source ~/.bashrc
```

### Method 2: Config File

Create `config.local.yml` in the project root:

```yaml
ai:
  primary: "anthropic"

  anthropic:
    api_key: "sk-ant-your-key-here"
    model: "claude-3-haiku-20240307"
    max_tokens: 150

  openai:
    api_key: "sk-your-key-here"
    model: "gpt-4o-mini"
    max_tokens: 150
```

**Note**: Don't commit `config.local.yml` to git! It's in `.gitignore` by default.

### Method 3: Mixed (Best Practice)

Use environment variables for secrets, config file for settings:

```yaml
# config.local.yml
ai:
  primary: "anthropic"

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}  # Reads from environment
    model: "claude-3-haiku-20240307"
    max_tokens: 150
```

---

## Provider-Specific Setup

### Anthropic (Default)

```yaml
ai:
  primary: "anthropic"

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: "claude-3-haiku-20240307"  # Fast and cheap
    # model: "claude-sonnet-4-20250514"  # Smarter, costs more
    max_tokens: 150
```

### OpenAI

```yaml
ai:
  primary: "openai"

  openai:
    api_key: ${OPENAI_API_KEY}
    model: "gpt-4o-mini"  # Fast and cheap
    # model: "gpt-4o"  # Smarter, costs more
    max_tokens: 150
```

### Google Gemini

```yaml
ai:
  primary: "gemini"

  gemini:
    api_key: ${GOOGLE_API_KEY}
    model: "gemini-2.0-flash"
    max_tokens: 150
```

**Note**: Requires `google-genai` package:
```bash
pip install google-genai
```

### Groq (OpenAI-Compatible)

Groq provides extremely fast inference using their custom LPU hardware.
Set `GROQ_API_KEY` and use the OpenAI-compatible base URL.

```yaml
ai:
  primary: "openai"

  openai:
    api_key: ${GROQ_API_KEY}
    base_url: "https://api.groq.com/openai/v1"
    model: "llama-3.3-70b-versatile"
    # model: "mixtral-8x7b-32768"
    max_tokens: 150
```

### Together AI (OpenAI-Compatible)

Access to many open-source models.

```yaml
ai:
  primary: "openai"

  openai:
    api_key: ${TOGETHER_API_KEY}
    base_url: "https://api.together.xyz/v1"
    model: "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    max_tokens: 150
```

### OpenRouter (OpenAI-Compatible)

Access many providers through one API.

```yaml
ai:
  primary: "openai"

  openai:
    api_key: ${OPENROUTER_API_KEY}
    base_url: "https://openrouter.ai/api/v1"
    model: "anthropic/claude-3-haiku"  # Use any model
    max_tokens: 150
```

---

## Using Ollama Cloud

### Ollama Cloud (Recommended)

[Ollama Cloud](https://ollama.com) provides hosted models behind an OpenAI-compatible API.
It requires an API key and a cloud base URL.

#### 1. Create an API Key

1. Go to [ollama.com](https://ollama.com)
2. Create an API key
3. Set it as an environment variable:

```bash
export OLLAMA_API_KEY="your_ollama_cloud_key"
```

#### 2. Configure Inkling

```yaml
ai:
  primary: "openai"

  openai:
    api_key: ${OLLAMA_API_KEY}
    base_url: "https://ollama.com/v1"
    model: "gpt-oss:20b"
    max_tokens: 150
```

---

## Provider Fallback

Inkling automatically tries providers in order if one fails:

```yaml
ai:
  primary: "anthropic"  # Try first

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: "claude-3-haiku-20240307"

  openai:  # Fallback
    api_key: ${OPENAI_API_KEY}
    model: "gpt-4o-mini"

  gemini:  # Second fallback
    api_key: ${GOOGLE_API_KEY}
    model: "gemini-2.0-flash"
```

Fallback triggers on:
- Rate limit errors (429)
- Quota exceeded
- Provider outages

---

## Token Budgets

Control costs with daily limits:

```yaml
ai:
  budget:
    daily_tokens: 10000   # ~$0.03/day with Haiku
    per_request_max: 500  # Max tokens per response
```

Check usage in SSH mode:
```
/stats
```

---

## Troubleshooting

### "No AI providers configured"

At least one provider needs a valid API key:
```bash
# Check if key is set
echo $ANTHROPIC_API_KEY

# Should print your key, not empty
```

### "Rate limit exceeded"

You've hit the provider's rate limit. Options:
1. Wait a few seconds (automatic retry)
2. Configure a fallback provider
3. Upgrade your API plan

### "Quota exceeded"

Daily token budget exhausted. Options:
1. Wait until tomorrow (resets at midnight)
2. Increase `daily_tokens` in config
3. Use a cheaper model (Haiku vs Sonnet)

### Gemini Import Error

```
ModuleNotFoundError: No module named 'google'
```

Install the Gemini SDK:
```bash
pip install google-genai
```

### Ollama Cloud Auth Error

If you see authentication errors, verify:
1. `OLLAMA_API_KEY` is set in your environment
2. `openai.base_url` is `https://ollama.com/v1`
3. Your key is active on ollama.com

### OpenAI-Compatible Provider Errors

Some providers need specific headers. Check their documentation for requirements beyond `base_url` and `api_key`.

---

## Model Recommendations

| Use Case | Recommended | Why |
|----------|-------------|-----|
| **Daily use** | Claude Haiku | Best quality/cost ratio |
| **Hosted open models** | Ollama Cloud | OpenAI-compatible hosted models |
| **Free tier** | Groq + Llama 3.3 | Generous free tier |
| **Fastest** | Groq | Custom LPU hardware |
| **Budget** | Gemini Flash | Free tier available |
| **Best quality** | Claude Sonnet | Most capable |
