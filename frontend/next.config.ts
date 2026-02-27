import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // output: 'standalone', // Not needed for Cloudflare; handled by @opennextjs/cloudflare
};

export default nextConfig;
