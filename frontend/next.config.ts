import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Fix "multiple lockfiles" turbopack warning
  turbopack: {
    root: path.resolve(__dirname),
  },

  // Proxy /api/* → backend so there are no CORS issues
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
