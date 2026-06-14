# Craterra — Launch-Ready Promotion Pack (2026-06-14)

Copy-paste ready. **You post these yourself** (they need your accounts; posting
as you to public forums is a reputation action, so it is intentionally manual).
Order and rationale live in `craterra_promotion_plan.md` — this file is the
final go-copy plus a status-checked pre-flight list.

Production: https://craterra-production.up.railway.app/

---

## Pre-flight (status as of 2026-06-14)

- [x] Production `/health` returns 200 (verified)
- [x] `/` returns 200 text/html (verified)
- [x] `/validate?query=Radiohead Creep` returns 200 (verified)
- [x] `/dig` works on a common seed (verified in release smoke test)
- [ ] Apply `outbound_clicks` table in Supabase — paste `docs/outbound_clicks_schema.sql`
      into the Supabase SQL editor (clicks fall back to local JSONL until then)
- [ ] Eyeball the site on a real phone once (mobile CSS was just simplified)
- [ ] Keep the OpenRouter usage/cost log open during the first traffic wave

---

## 1. Hacker News — Show HN (post first)

Title:

    Show HN: Craterra – dig for less obvious music recommendations from one song

First comment:

    I built Craterra, a music digging tool. You give it one song and it tries to
    return 3-5 less obvious tracks — not a same-vibe playlist, but a digging path
    with a stated bridge and difference for each pick.

    How it works: it builds a candidate pool from public metadata (Last.fm
    similar tracks + ListenBrainz artist top recordings), scores relative rarity
    within that pool, has an LLM curate 3-5 picks with reasons, then validates
    each pick through Deezer -> MusicBrainz -> iTunes before showing it, so the
    AI can't hallucinate a track that doesn't exist.

    No signup. Anonymous sessions. Like/Skip feedback nudges the next dig.

    It's an MVP and recommendations can still be uneven on sparse metadata. I'd
    love feedback, especially on which seed songs produce weak paths.

    https://craterra-production.up.railway.app/

## 2. Reddit r/ifyoulikeblank and r/musicsuggestions (after HN)

Title:

    I made a tool that turns one song into a digging path of less obvious tracks

Body:

    Not a same-vibe playlist generator — it tries to justify why each pick is a
    defensible jump (bridge + difference), using Last.fm/ListenBrainz/MusicBrainz/
    Deezer plus AI curation. No signup, anonymous.

    It's an MVP, so feedback welcome — especially seeds where the path falls flat.

    https://craterra-production.up.railway.app/

Reddit rules reminder: don't ask for upvotes; ask for feedback. Read each sub's
self-promo rules before posting.

## 3. Korean communities (optional, same wave)

    Craterra라는 음악 디깅 도구를 만들었습니다. 곡 하나를 넣으면 비슷한 분위기의 뻔한
    플레이리스트가 아니라 "왜 이 곡으로 넘어갈 수 있는지" 설명 가능한 덜 뻔한 추천 3-5개를
    찾아줍니다. Last.fm, ListenBrainz, MusicBrainz, Deezer 공개 메타데이터 + AI 큐레이션.
    로그인 없이 동작합니다. 피드백 환영합니다.

    https://craterra-production.up.railway.app/

## 4. Product Hunt (after the first feedback wave, not day one)

- Name: Craterra
- Tagline: Turn one song into a defensible digging path.
- Need before launch: 3-5 screenshots, maker first comment (reuse HN comment),
  short description. Don't ask for upvotes; asking people to visit/comment is ok.

---

## Demo format that converts

> Give me one song. I'll run it through Craterra and post the digging path.

Good in music Discords, RYM-adjacent threads, and X/Twitter.

## Be honest about (don't hide these)

- It's an MVP; sparse-metadata seeds can produce uneven paths.
- Bandcamp links are search links, not affiliate-tagged exact matches
  (see `docs/bandcamp_affiliate.md`).
