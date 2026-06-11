# Craterra

Craterra is a music digging tool: enter one song, then discover related hidden tracks through public music metadata, AI curation, and external platform links.

## Local Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open:

- API health: `http://127.0.0.1:8000/health`
- Song validation: `http://127.0.0.1:8000/validate?query=artist%20song`

Create `.env` from `.env.example`, then add your keys:

```env
LASTFM_API_KEY=your_lastfm_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=deepseek/deepseek-v4-flash
OPENROUTER_FALLBACK_MODEL=qwen/qwen3-30b-a3b-instruct-2507
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

## First Milestone

- `/validate`: Deezer -> MusicBrainz -> iTunes validation fallback
- `/dig`: Last.fm + ListenBrainz candidate pool -> DeepSeek curation -> Deezer verification
- `/feedback`: anonymous session feedback storage, currently local JSONL in `data/`
- Frontend: song input, jump level, region, era, challenge mode, recommendation cards, previews, Bandcamp / Apple Music outbound links, feedback, and continue-dig controls
- Local history: `data/dig_history.jsonl` stores anonymous dig chains for later visualization

## Persistence

By default, feedback and dig history are stored locally in `data/`.

To use Supabase instead:

1. Run `docs/supabase_schema.sql` in your Supabase SQL editor.
2. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`.
3. Restart the FastAPI server.

If Supabase is not configured or a write fails, the app falls back to local JSONL storage.

## API Notes

- Last.fm API key issuance is free for MVP development.
- Last.fm Pro is separate and is not required for Craterra.
- Before public launch or monetization, review Last.fm commercial-use terms or contact `partners@last.fm`.

## Deployment

For the first demo, deploy the FastAPI app to Railway and let it serve the frontend too.

See `docs/deployment.md`.

## Rate Limits

Local in-memory limits protect the highest-risk endpoints:

- `/dig`: `DIG_RATE_LIMIT_PER_MINUTE`, default `12`
- `/feedback`: `FEEDBACK_RATE_LIMIT_PER_MINUTE`, default `60`
- `/validate`: `VALIDATE_RATE_LIMIT_PER_MINUTE`, default `60`
