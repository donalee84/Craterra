# Craterra Deployment

## Railway Backend + Frontend

For the first demo, FastAPI serves both the API and the static frontend.

### 1. Create Railway service

1. Create a new Railway project.
2. Connect this repository.
3. Keep the default Nixpacks builder.
4. Railway should use `railway.json` or `Procfile` to start the app.

Start command:

```sh
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

Health check:

```text
/health
```

### 2. Set Railway environment variables

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
VALIDATE_RATE_LIMIT_PER_MINUTE=60
FEEDBACK_RATE_LIMIT_PER_MINUTE=60
DIG_RATE_LIMIT_PER_MINUTE=12
```

Optional:

```env
OPENROUTER_MODEL=deepseek/deepseek-v4-flash
OPENROUTER_FALLBACK_MODEL=qwen/qwen3-30b-a3b-instruct-2507
APPLE_MUSIC_AFFILIATE_TOKEN=
```

### 3. Prepare Supabase

Run `docs/supabase_schema.sql` in the Supabase SQL editor before routing public traffic to the app.

### 4. Verify deployment

After Railway deploys:

```text
https://your-railway-domain/health
https://your-railway-domain/
```

Expected health response:

```json
{"status":"ok","environment":"production"}
```

### Notes

- Keep `SUPABASE_SERVICE_ROLE_KEY` only in backend server environment variables.
- Do not expose secret keys in frontend files.
- Vercel is optional for the first demo because FastAPI already serves `frontend/index.html` and `/static/*`.
