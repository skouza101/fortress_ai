import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
        pathname: "**",
      },
    ],
  },
  async rewrites() {
    // If running in Docker, 'backend' resolves. If running locally, use localhost.
    // We can check an environment variable or try to be smart.
    const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8080";
    console.log(`[NextConfig] Proxying /api to ${backendUrl}`);
    return [
      {
        // Capture everything under /api/ EXCEPT for /api/auth
        source: "/api/:path((?!auth(?:/|$)).*)",
        destination: `${backendUrl}/api/:path`,
      },
    ];
  },
};

export default nextConfig;
