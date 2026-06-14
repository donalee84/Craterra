# Vercel Split-Deploy Decision (2026-06-14)

## Question

Should Craterra split the frontend onto Vercel while the API stays on Railway?

## Decision

**No — not for the feedback-first launch.** Keep the single Railway deploy where
FastAPI serves both the API and the static frontend (`/`, `/static/*`).

## Why

- The frontend is 3 static files (`index.html`, `styles.css`, `app.js`) served
  by FastAPI today. There is no build step and no SSR to gain from Vercel.
- A single origin means **no CORS layer** to configure or break, and one URL to
  share during the launch.
- One deploy target = one place to watch logs, health, and OpenRouter cost
  during the launch window. Splitting doubles the moving parts at the worst time.
- Railway already passes the full production smoke test (health / `/` /
  `/validate` / `/feedback` / `/dig`).

## When to revisit (triggers)

Move the frontend to Vercel only if one of these becomes true:

1. The frontend grows a real build step (React/Vite/bundler) or many assets.
2. Static asset latency is measurably hurting non-US users (add a CDN/edge).
3. The API needs to scale or restart independently of static serving.
4. A custom marketing domain wants edge caching separate from the API.

## If/when splitting (checklist for later)

- Deploy `frontend/` to Vercel as a static project.
- Point `app.js` `fetch` base URL at the Railway API origin.
- Add CORS allow-list on FastAPI for the Vercel domain(s).
- Keep `/health` on Railway as the API source of truth.
