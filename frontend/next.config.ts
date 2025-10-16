import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  async rewrites() {
    console.log("Rewriting API requests");
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
