import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // lean production image for the AWS deploy - see frontend/Dockerfile
};

export default nextConfig;
