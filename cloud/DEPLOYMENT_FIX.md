# 🚀 Vercel Deployment Fix

## The Problem

```
Error: The pattern "app/api/**/*.ts" defined in `functions`
doesn't match any Serverless Functions inside the `api` directory.
```

This error occurred because the cloud backend was using **Next.js App Router** patterns (`app/api/*/route.ts`) but didn't have Next.js installed.

## The Solution

We've added Next.js as a dependency and configured the project properly for Vercel deployment.

## Changes Made

### 1. Updated `package.json`

Added Next.js and React dependencies:

```json
{
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  }
}
```

### 2. Created `next.config.js`

Minimal Next.js configuration:

```javascript
const nextConfig = {
  output: 'standalone',
}
module.exports = nextConfig
```

### 3. Simplified `vercel.json`

Let Vercel auto-detect Next.js:

```json
{
  "framework": "nextjs",
  "buildCommand": "next build",
  "devCommand": "next dev"
}
```

### 4. Added Required Next.js Files

- `app/layout.tsx` - Root layout (required by Next.js)
- `app/page.tsx` - Home page with API documentation
- `.gitignore` - Ignore Next.js build files

## Fresh Deployment Steps

### 1. Install Dependencies

```bash
cd cloud
npm install
```

This will install Next.js and all dependencies.

### 2. Test Locally (Optional)

```bash
npm run dev
```

Visit http://localhost:3000 to see:
- Home page with API documentation
- API routes at `/api/*`

### 3. Deploy to Vercel

```bash
npm run deploy
```

Or manually:

```bash
npx vercel --prod
```

### 4. Set Environment Variables

In your Vercel dashboard (Settings → Environment Variables):

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

### 5. Redeploy (if needed)

After setting environment variables:

```bash
npx vercel --prod
```

## Verification

After deployment:

```bash
# Get challenge nonce
curl https://your-project.vercel.app/api/oracle

# Should return:
# {"nonce":"..."}
```

Visit `https://your-project.vercel.app` to see the API documentation page.

## How It Works Now

### File Structure

```
cloud/
├── app/
│   ├── layout.tsx          # Next.js root layout
│   ├── page.tsx            # Home page (API docs)
│   └── api/                # API routes
│       ├── oracle/route.ts
│       ├── plant/route.ts
│       ├── fish/route.ts
│       ├── telegram/route.ts
│       ├── postcard/route.ts
│       ├── baptism/route.ts
│       └── lineage/route.ts
├── lib/                    # Shared utilities
├── next.config.js          # Next.js config
├── package.json            # Dependencies (includes Next.js)
└── vercel.json            # Vercel config
```

### Build Process

1. **Install**: `npm install` installs Next.js and dependencies
2. **Build**: `next build` compiles TypeScript and bundles
3. **Deploy**: Vercel deploys as Next.js app with edge functions

### Why Next.js?

The API routes (`app/api/*/route.ts`) use Next.js 13+ App Router patterns:

- `export async function GET(request: Request)`
- `export async function POST(request: Request)`
- `Response.json(...)` helpers

These patterns require Next.js to work. Vercel detects Next.js and automatically configures:
- Serverless functions for each route
- Optimized edge deployment
- Automatic TypeScript compilation

## Troubleshooting

### Build fails with TypeScript errors

```bash
# Check types locally
cd cloud
npx tsc --noEmit
```

Fix any type errors before deploying.

### Environment variables not working

Make sure to:
1. Set them in Vercel dashboard (Settings → Environment Variables)
2. Redeploy after adding variables

### API routes return 404

Check that:
1. Files are in `app/api/*/route.ts`
2. Each file exports `GET` or `POST` functions
3. Functions use correct signature: `async function POST(request: Request): Promise<Response>`

### Functions timeout

Increase timeout in `vercel.json`:

```json
{
  "functions": {
    "app/api/**/*.ts": {
      "maxDuration": 60
    }
  }
}
```

But note: This is auto-configured by Next.js now.

## Next Steps

1. ✅ Deploy to Vercel
2. ✅ Configure environment variables
3. ✅ Test all API endpoints
4. ✅ Update your Inkling device config with the API URL

## Additional Resources

- [Next.js App Router Docs](https://nextjs.org/docs/app)
- [Vercel Next.js Deployment](https://vercel.com/docs/frameworks/nextjs)
- [Next.js API Routes](https://nextjs.org/docs/app/building-your-application/routing/route-handlers)

---

**Fixed**: February 2, 2026
**Status**: ✅ Ready to deploy
