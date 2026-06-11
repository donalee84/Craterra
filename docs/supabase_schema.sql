create extension if not exists "pgcrypto";

create table if not exists feedback (
  id uuid primary key default gen_random_uuid(),
  session_id text not null,
  song_name text not null,
  artist_name text not null,
  vote boolean not null,
  created_at timestamptz not null default now()
);

create index if not exists feedback_session_created_idx
  on feedback (session_id, created_at desc);

create table if not exists dig_history (
  id uuid primary key default gen_random_uuid(),
  session_id text not null,
  root_song text not null,
  params jsonb not null default '{}'::jsonb,
  model_used text,
  recommendations jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists dig_history_session_created_idx
  on dig_history (session_id, created_at desc);

create table if not exists dig_patterns (
  id uuid primary key default gen_random_uuid(),
  input_genre text,
  jump_to text,
  success_rate float not null default 0,
  sample_count integer not null default 0,
  updated_at timestamptz not null default now()
);

create table if not exists session_profile (
  session_id text primary key,
  liked_tags jsonb not null default '[]'::jsonb,
  disliked_tags jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);
