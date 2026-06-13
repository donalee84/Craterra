# Craterra Release Summary
> Updated: 2026-06-12

## Status

Craterra MVP is deployed and working in production.

Production:

```text
https://craterra-production.up.railway.app/
```

Health:

```text
https://craterra-production.up.railway.app/health
```

Expected health response:

```json
{"status":"ok","environment":"production"}
```

## What Works

- Song input from browser UI
- Deezer seed normalization
- Last.fm similar-track candidate pool
- ListenBrainz artist top-recording candidate pool
- Relative rarity labels
- OpenRouter / DeepSeek curation
- Deezer -> MusicBrainz -> iTunes validation fallback
- Recommendation cards with artwork and preview audio
- Bandcamp and Apple Music outbound search links
- Recommendation share actions
- Like / Skip feedback
- Continue digging from a recommendation
- Session dig-chain display
- Supabase feedback persistence
- Supabase dig-history persistence
- Local JSONL fallback when Supabase is unavailable
- In-memory rate limits for `/validate`, `/feedback`, and `/dig`
- Structured JSON request logs with request ids
- Stable 500 error payloads for unexpected backend failures
- External API retry/backoff logging for transient 429/5xx and network failures
- OpenRouter token and cost tracking in `/dig` responses, dig history, and logs
- Mobile and desktop viewport QA screenshots
- Railway deployment from GitHub

## Final Production Smoke Test

Confirmed:

```text
GET /health -> 200
GET / -> 200 text/html
GET /validate?query=Radiohead%20Creep -> found=true, source=deezer
POST /feedback -> saved=true, storage_backend=supabase
POST /dig -> status=200, model=deepseek/deepseek-v4-flash
```

Latest `/dig` production check:

```text
query: Radiohead Creep
distance_level: 4
recommendations: 3
next_step: Tune dig-pattern learning and share cards next.
```

Example recommendations after stronger digging rules:

```text
Jeff Buckley - Grace
My Chemical Romance - Disenchanted
bôa - Twilight
```

## Latest Git / Railway State

GitHub repository:

```text
https://github.com/donalee84/Craterra
```

Latest pushed commits:

```text
708a704 Trigger Railway redeploy
4c7945d Add recommendation share actions
e99a81e Add external API retry logging
bacb112 Add structured request logging
8f2bcaf Trigger Railway redeploy
```

Railway active deployment:

```text
Trigger Railway redeploy
Deployment successful
```

## Important Environment Variables

Production variables are configured in Railway, not committed to Git.

Required:

```env
APP_NAME=Craterra API
APP_ENV=production
OPENROUTER_API_KEY=
LASTFM_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
HTTP_TIMEOUT_SECONDS=10
LOCAL_DATA_DIR=data
DIG_RATE_LIMIT_PER_MINUTE=12
FEEDBACK_RATE_LIMIT_PER_MINUTE=60
VALIDATE_RATE_LIMIT_PER_MINUTE=60
OPENROUTER_MODEL=deepseek/deepseek-v4-flash
OPENROUTER_FALLBACK_MODEL=qwen/qwen3-30b-a3b-instruct-2507
```

Optional:

```env
APPLE_MUSIC_AFFILIATE_TOKEN=
```

## Remaining Work

- Test mobile layout on a real phone browser
- Add MusicBrainz relationship enrichment
- Wire real Bandcamp affiliate flow
