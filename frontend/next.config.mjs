/** @type {import('next').NextConfig} */
const nextConfig = {
  // Hides the dev-only route indicator badge (the bottom-left "N" circle) — dev-only UI, has no
  // effect on production builds.
  devIndicators: false,
  // Static export for Render's free Static Site tier — safe here since the whole app is one route
  // (app/page.js, no app/api/, no middleware, no next/image) and everything client-side already
  // talks to the FastAPI backend over plain fetch(), never a Next.js server route. `next build`
  // emits static HTML/JS/CSS to `out/` instead of requiring a Node server to run.
  output: "export",
};

export default nextConfig;
