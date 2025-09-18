Kyle Holthaus – Portfolio (Next.js 14)

Overview
- Next.js 14 + TypeScript + Tailwind CSS
- App Router, dark finance theme, responsive
- Pages: Home, About, Projects, Blog, Contact
- Admin-authenticated projects area backed by Auth.js credentials
- Demo page at /demo showing live KPIs and candidates via your VCP API

Getting Started
1) Copy .env.example to .env and set NEXT_PUBLIC_SITE_URL, NEXT_PUBLIC_VCP_API_BASE, NEXT_PUBLIC_SANITY_PROJECT_ID, NEXT_PUBLIC_SANITY_DATASET, AUTH_ADMIN_EMAIL, AUTH_ADMIN_PASSWORD, AUTH_SECRET, NEXTAUTH_URL
2) Install deps: npm install
3) Ensure your FastAPI backend is running on http://127.0.0.1:8000 (see repo root README for make api)
4) Run the site: npm run dev (http://localhost:3000) or npm run demo (pre-sets API base)

Deploy
- Optimized for Vercel: import repo folder `kyle-portfolio`.
- Set env vars in Vercel: NEXT_PUBLIC_SITE_URL, NEXT_PUBLIC_VCP_API_BASE, NEXT_PUBLIC_SANITY_PROJECT_ID, NEXT_PUBLIC_SANITY_DATASET, SANITY_API_VERSION (optional), SANITY_USE_CDN, STUDIO_USERNAME, STUDIO_PASSWORD, SANITY_READ_TOKEN (optional for server-side previews), AUTH_SECRET, AUTH_ADMIN_EMAIL, AUTH_ADMIN_PASSWORD, NEXTAUTH_URL

Blog (Sanity CMS)
- Studio mounted at `/studio` and protected with basic auth via `STUDIO_USERNAME`/`STUDIO_PASSWORD` (leave unset to disable gate; Sanity auth still applies).
- `.env.example` lists required keys. Add your Sanity project ID and dataset, then restart `npm run dev`.
- Schemas support rich text, inline charts/attachments, cover images, tags, and SEO overrides.
- Posts published in Sanity appear on `/blog`; the site revalidates every 60s.

Authentication
- Credentials-based admin login provided by Auth.js/NextAuth (see `/login`).
- Set `AUTH_ADMIN_EMAIL`, `AUTH_ADMIN_PASSWORD`, and `AUTH_SECRET` (or `NEXTAUTH_SECRET`) in your environment.
- Protected routes (e.g., `/projects`) use SSR checks; unauthenticated visitors are redirected to `/login`.

Notes
- Client-side password gating is for demo UX, not security. Use real auth for production.

Frontend Quickstart
```bash
cd kyle-portfolio
cp .env.example .env
npm install
npm run demo
# Open http://localhost:3000/demo
```

Legend Room Demo Page
- URL: http://localhost:3000/demo
- Requires backend API at NEXT_PUBLIC_VCP_API_BASE (default http://127.0.0.1:8000)
- Calls:
  - GET /api/v1/vcp/today → candidates table
  - GET /api/v1/vcp/metrics?start=YYYY-MM-DD&end=YYYY-MM-DD → KPI header
- Includes:
  - Rescan button that invokes /api/v1/vcp/today and refreshes
  - Per-row sparkline (Yahoo chart API if available; deterministic fallback otherwise)
