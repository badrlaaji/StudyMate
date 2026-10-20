import type { NextConfig } from "next";

// "standalone" = minimal server bundle for the Docker image (step 10).
const nextConfig: NextConfig = { output: "standalone" };

export default nextConfig;
