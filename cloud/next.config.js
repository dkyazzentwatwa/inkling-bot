/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable static optimization for API routes
  // (we only have API routes, no pages)
  experimental: {
    // API routes only, no React pages
  },
  // Output standalone for Vercel
  output: 'standalone',
}

module.exports = nextConfig
