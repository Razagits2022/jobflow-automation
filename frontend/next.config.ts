import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/pricing",
        destination: "/subscribe",
        permanent: false,
      },
      {
        source: "/contact",
        destination: "/#contact",
        permanent: false,
      },
      {
        source: "/login",
        destination: "/dashboard",
        permanent: false,
      },
      {
        source: "/signup",
        destination: "/subscribe",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
