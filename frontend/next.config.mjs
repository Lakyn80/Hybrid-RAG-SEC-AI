const backendBaseUrl =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") || "http://localhost:8021";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/ask",
        destination: `${backendBaseUrl}/api/ask`,
      },
      {
        source: "/api/stream",
        destination: `${backendBaseUrl}/api/stream`,
      },
      {
        source: "/api/health",
        destination: `${backendBaseUrl}/api/health`,
      },
    ];
  },
};

export default nextConfig;
