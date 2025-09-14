Kyle Holthaus – Portfolio (Next.js 14)

Overview
- Next.js 14 + TypeScript + Tailwind CSS
- App Router, dark finance theme, responsive
- Pages: Home, About, Projects, Blog, Contact
- Protected demo section on Projects via NEXT_PUBLIC_LEGEND_ROOM_DEMO_PASSWORD (client-side gate for demos only)
- Demo page at /demo showing live KPIs and candidates via your VCP API

Getting Started
1) Copy .env.example to .env and set NEXT_PUBLIC_LEGEND_ROOM_DEMO_PASSWORD
2) Install deps: npm install
3) Ensure your FastAPI backend is running on http://127.0.0.1:8000 (see repo root README for make api)
4) Run the site: npm run dev (http://localhost:3000) or npm run demo (pre-sets API base)

Deploy
- Optimized for Vercel: import repo folder `kyle-portfolio`.
- Set env vars in Vercel: NEXT_PUBLIC_LEGEND_ROOM_DEMO_PASSWORD, NEXT_PUBLIC_SITE_URL, NEXT_PUBLIC_VCP_API_BASE

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
