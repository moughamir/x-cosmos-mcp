import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  serverExternalPackages: [],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://mcp-api:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
