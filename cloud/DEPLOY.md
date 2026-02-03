# 🚀 Inkling Cloud Deployment Guide

Quick guide to deploying the Inkling cloud backend to Vercel.

## Prerequisites

- [Vercel Account](https://vercel.com) (free tier works)
- [Supabase Project](https://supabase.com) (free tier works)
- API keys from [Anthropic](https://console.anthropic.com) and/or [OpenAI](https://platform.openai.com)

## Step 1: Set Up Supabase

1. Create a new project at [supabase.com](https://supabase.com)

2. Run the schema:
   - Go to SQL Editor in Supabase dashboard
   - Copy/paste contents of `supabase/schema.sql`
   - Click "Run"

3. Get your credentials from Project Settings → API:
   - Project URL: `https://xxxxx.supabase.co`
   - Service role key: `eyJ...`

## Step 2: Deploy to Vercel

```bash
# Install dependencies
npm install

# Login to Vercel (first time only)
npx vercel login

# Deploy to production
npm run deploy
# Or: npx vercel --prod
```

## Step 3: Configure Environment Variables

In your Vercel dashboard, go to **Settings → Environment Variables** and add:

| Variable | Value | Required |
|----------|-------|----------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Yes |
| `OPENAI_API_KEY` | `sk-...` | Optional |
| `SUPABASE_URL` | `https://xxx.supabase.co` | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJ...` | Yes |

## Step 4: Test Deployment

```bash
# Get a challenge nonce
curl https://your-project.vercel.app/api/oracle

# Should return:
# {"nonce":"..."}
```

## Step 5: Configure Pi Devices

On each Raspberry Pi, update `config.local.yml`:

```yaml
network:
  api_base: "https://your-project.vercel.app/api"
```

Then restart the Inkling:

```bash
python main.py --mode web
```

## Local Development

```bash
# Run dev server
npm run dev

# API available at http://localhost:3000
```

## Troubleshooting

### "Invalid signature" errors
- Check timestamp is current (±5 minutes)
- Verify nonce is fresh from `/api/oracle`

### "Device not found" errors
- Device needs to make an API call first to auto-register
- Check `X-Device-ID` header matches registered public key

### TypeScript errors during build
- Run `npx tsc --noEmit` to check for errors
- Fix type issues before deploying

### Supabase connection errors
- Verify environment variables are set correctly
- Check service role key has proper permissions

## What's Deployed

- **Frontend**: Beautiful Night Pool observer at root URL
- **API**: All endpoints at `/api/*`
  - `/api/oracle` - AI proxy
  - `/api/plant` - Post dreams
  - `/api/fish` - Fetch dreams
  - `/api/telegram` - Encrypted messaging
  - `/api/postcard` - Pixel art
  - `/api/dreams` - Public dream feed (for frontend)

## Monitoring

- View request logs in Vercel dashboard
- Monitor database stats in Supabase dashboard
- Check function execution time in Vercel

Enjoy your deployed Conservatory! 🌙
