/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  // Disable telemetry
  telemetry: false,

  // Strict mode for development
  reactStrictMode: true,

  // TypeScript and ESLint
  typescript: {
    // Don't fail build on type errors in production
    ignoreBuildErrors: process.env.NODE_ENV === 'production',
  },

  eslint: {
    // Don't fail build on lint errors in production
    ignoreDuringBuilds: process.env.NODE_ENV === 'production',
  },
};

module.exports = nextConfig;
