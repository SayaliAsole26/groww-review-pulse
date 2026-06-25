# Groww Weekly Review Pulse — Dashboard

React dashboard UI generated from the **Luminous Fintech** Stitch design system (`stitch_groww_weekly_review_pulse/`).

## Run locally

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Screens

| Route | Description |
|-------|-------------|
| `/` | Dashboard — KPIs, 3 top themes, charts, delivery shortcuts |
| `/explorer` | Review Explorer — search + rating filters |
| `/pipeline` | Pipeline Monitor — animated re-run |

Removed from nav (per bugsfile): `/reports`, `/delivery`, `/settings` (redirect to home).

Footer links open **Google Docs**, **Gmail Drafts**, and **GitHub Actions**.

## Stack

- React 19 + TypeScript + Vite
- Tailwind CSS v4 (Luminous Fintech tokens)
- React Router
- Material Symbols + Inter (matches Stitch)

Mock data lives in `src/data/mock.ts` and mirrors the pulse pipeline (2026-W25, 1,669 reviews, 5 themes, Docs + Gmail delivery).

## Build

```bash
npm run build
npm run preview
```

## Deploy on Vercel

1. Import the repo at [vercel.com/new](https://vercel.com/new) with **Root Directory** = `frontend`
2. Framework: Vite · Build: `npm run build` · Output: `dist`
3. Add environment variable (optional — defaults work):

| Variable | Value |
|----------|-------|
| `VITE_MCP_URL` | `https://mcp-server-production-725c.up.railway.app` |

4. `vercel.json` proxies `/api/mcp-health` to Railway (no API key in browser)
5. Review Explorer needs `public/data/reviews_normalized.json` — run `npm run sync-reviews` after `pulse ingest`

See [docs/deploymentplan2.md](../docs/deploymentplan2.md) for the full checklist.
