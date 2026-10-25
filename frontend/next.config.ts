import type { NextConfig } from "next";

// The browser may only fetch from this site and from the official MediaPipe model host.
// This also blocks the usage statistics MediaPipe sends to Google (odml.pa.googleapis.com):
// in the camera mode, nothing leaves the browser but the one-time model download.
const CONNECT_SRC = "connect-src 'self' https://storage.googleapis.com";

// "standalone" = minimal server bundle for the Docker image (step 10).
const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    return [{ source: "/:path*", headers: [{ key: "Content-Security-Policy", value: CONNECT_SRC }] }];
  },
};

export default nextConfig;
