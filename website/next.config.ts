import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: '/:path*',
        has: [
          {
            type: 'host',
            value: 'digital-wellbeing.vercel.app',
          },
        ],
        destination: 'https://not-your-wellbeing.vercel.app/:path*',
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
