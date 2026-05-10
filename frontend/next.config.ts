import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Production-ready config for Vercel
  // We'll use the full backend URL in frontend/src/lib/api.ts instead of rewrites
  // for more reliable cross-origin communication in serverless environments.
};

export default nextConfig;
