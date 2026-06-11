# Craterra Progress
> Updated: 2026-06-11

## Current Status

Craterra now has a working local MVP.

The app can:

1. Accept a seed song from the frontend
2. Normalize the seed song through Deezer
3. Build a candidate pool from Last.fm similar tracks
4. Compute relative rarity labels from Last.fm playcount/listener data
5. Curate 3-5 recommendations through OpenRouter
6. Validate recommendations through Deezer -> MusicBrainz -> iTunes fallback
7. Render recommendation cards in the browser
8. Play Deezer previews when available
9. Save Like / Skip feedback through Supabase with local fallback
10. Feed session taste history into the next recommendation request
11. Continue digging from a recommended track
12. Save dig history through Supabase with local fallback
13. Add ListenBrainz artist top recordings as a second candidate source
14. Add Bandcamp and Apple Music outbound search links to recommendation cards

Local app URL:

```text
http://127.0.0.1:8002
```

## Implemented Backend

FastAPI app:

- `backend/app/main.py`
- Serves API routes
- Serves frontend at `/`
- Serves static assets from `/static`

Implemented routes:

| Method | Path | Status |
|---|---|---|
| GET | `/health` | Done |
| GET | `/validate` | Done |
| POST | `/dig` | Done for local MVP |
| POST | `/feedback` | Done with local JSONL storage |

### `/validate`

Validation fallback order:

```text
Deezer -> MusicBrainz -> iTunes
```

Returns:

- source
- title
- artist
- album
- artwork URL
- preview URL
- external URL
- confidence
- checked sources

### `/dig`

Current flow:

```text
Seed song
  -> Deezer normalization
  -> Last.fm similar tracks
  -> relative rarity scoring
  -> OpenRouter curation
  -> Deezer / MusicBrainz / iTunes validation
  -> recommendation cards
  -> local dig history save
```

OpenRouter models:

```env
OPENROUTER_MODEL=deepseek/deepseek-v4-flash
OPENROUTER_FALLBACK_MODEL=qwen/qwen3-30b-a3b-instruct-2507
```

Candidate handling:

- Last.fm fetches up to 25 candidates
- ListenBrainz adds up to 10 artist top-recording candidates after MusicBrainz artist MBID lookup
- The first 18 are sent to OpenRouter for curation
- OpenRouter returns structured JSON picks
- Each pick is validated before being returned to the frontend

### `/feedback`

Current storage:

```text
data/feedback.jsonl
```

Saved fields:

- session_id
- song_name
- artist_name
- vote
- created_at

Feedback is used to build a session taste profile:

- liked tracks
- disliked tracks
- liked artists
- disliked artists

That profile is injected into later `/dig` prompts.

## Implemented Frontend

Files:

- `frontend/index.html`
- `frontend/styles.css`
- `frontend/app.js`

Current UI:

- Song input
- Jump strength slider
- Region input
- Era input
- Mood tags input
- Challenge mode toggle
- Recommendation cards
- Rarity badge
- Confidence badge
- Album artwork
- Deezer preview audio
- External link
- Bandcamp link
- Apple Music link
- Like button
- Skip button
- Continue digging button

Session ID is stored in `localStorage` as:

```text
craterra_session_id
```

## Local Data

Default local fallback:

```text
data/
```

Current local files:

```text
data/feedback.jsonl
data/dig_history.jsonl
```

`dig_history.jsonl` stores:

- session_id
- root_song
- params
- model_used
- recommendations
- created_at

## Supabase Persistence

Added a Supabase persistence layer with local JSONL fallback.

Files:

- `backend/app/clients/supabase.py`
- `backend/app/services/persistence.py`
- `docs/supabase_schema.sql`

Environment variables:

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

Current behavior:

- `/feedback` writes to Supabase when configured
- `/dig` history writes to Supabase when configured
- Session taste profile reads feedback from Supabase when configured
- If Supabase is missing or a persistence request fails, the app keeps using local JSONL

## Rarity Scoring

Current rarity is relative to the candidate pool, not global popularity.

Labels:

```text
Deepest here
Less played
Mid-known
Obvious
```

Reason:

- Popular seed songs like `Radiohead - Creep` produce generally popular Last.fm candidates
- Absolute thresholds made every result look `Popular`
- Relative rarity makes the badge useful within each dig session

## Verified

Confirmed working:

- Python compile check
- Static frontend serving
- `/health`
- `/validate`
- `/feedback`
- `/dig`
- Last.fm API key
- OpenRouter model config
- Deezer validation
- MusicBrainz fallback when Deezer is forced to fail
- ListenBrainz candidate source integration
- Basic pytest coverage for `/validate`, `/feedback`, and `/dig`
- Desktop/mobile visual QA screenshots generated in `artifacts/visual-qa/`
- Railway deployment config added
- In-memory rate limiting added for `/validate`, `/feedback`, and `/dig`
- Local feedback storage
- Local dig history storage

Example verified `/dig` behavior:

```text
status: 200
model: deepseek/deepseek-v4-flash
candidates: 25
recommendations: 3
```

## Known Limitations

This is a local MVP, not a launch-ready service.

Still missing:

- Railway / Vercel deployment
- MusicBrainz relationship enrichment
- Bandcamp affiliate program wiring
- Mobile layout QA in a real browser
- Production error handling
- Cost tracking
- Share cards
- Dig chain visualization

## Recommended Next Steps

1. Test mobile layout in a real handheld browser
2. Connect Railway project and deploy backend/frontend together
3. Add production error handling and structured logging
4. Decide whether Vercel split deploy is needed after first demo

## Important Notes

Last.fm:

- API key is enough for current public read endpoints
- Shared secret is not needed for MVP
- Before public launch or monetization, review Last.fm commercial-use terms or contact `partners@last.fm`

OpenRouter:

- Current default model is `deepseek/deepseek-v4-flash`
- Current fallback model is `qwen/qwen3-30b-a3b-instruct-2507`
- Both were verified against the OpenRouter model API during development
