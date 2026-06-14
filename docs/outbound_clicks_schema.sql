-- Apply this in the Supabase SQL editor to enable production outbound-click
-- persistence. It is idempotent and only adds the missing outbound_clicks table.
-- Until this runs, /outbound-click keeps writing to data/outbound_clicks.jsonl.

create extension if not exists "pgcrypto";

create table if not exists outbound_clicks (
  id uuid primary key default gen_random_uuid(),
  session_id text not null,
  service text not null,
  song_name text not null,
  artist_name text not null,
  url text not null,
  created_at timestamptz not null default now()
);

create index if not exists outbound_clicks_session_created_idx
  on outbound_clicks (session_id, created_at desc);

create index if not exists outbound_clicks_service_created_idx
  on outbound_clicks (service, created_at desc);
