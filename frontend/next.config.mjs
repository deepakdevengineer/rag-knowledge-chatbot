/** @type {import('next').NextConfig} */
const nextConfig = {
    // Backend API handles CORS, but sometimes you need rewrites in dev
    /*
    async rewrites() {
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/api/:path*',
        },
      ]
    },
    */
};

export default nextConfig;
