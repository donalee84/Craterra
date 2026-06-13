# Craterra Promotion Plan
> Updated: 2026-06-14

## Current Launch Readiness

Craterra is ready for a small public MVP/demo push.

Production:

```text
https://craterra-production.up.railway.app/
```

Best framing:

```text
Craterra is a music digging tool. Give it one song and it recommends 3-5 less obvious tracks with a clear bridge and difference, using public music metadata plus AI curation.
```

Avoid framing it as:

- A Spotify replacement
- A fully finished commercial launch
- A perfect recommender
- A generic same-vibe playlist generator

## Recommended Promotion Order

### 1. Feedback-First Soft Launch

Goal:

- Get honest feedback from music diggers and technical early adopters
- Find obvious UX bugs before a bigger launch
- Observe what kinds of seed songs produce strong or weak results

Best places:

- Hacker News `Show HN`
- Reddit `r/ifyoulikeblank`
- Reddit `r/musicsuggestions`
- Small Discord music communities

Tone:

- Ask for feedback
- Say it is an MVP
- Emphasize that it works without signup
- Do not ask for upvotes

HN reference:

```text
Show HN is for something personally made that others can try, preferably without signup barriers.
```

Source:

```text
https://news.ycombinator.com/showhn.html
```

### 2. Product Hunt Launch

Goal:

- Broader startup/product audience
- Collect product comments
- Test positioning outside music-only communities

Do this after the first feedback wave.

Prepare before launch:

- Product name: Craterra
- Tagline
- Short description
- Maker comment
- Screenshots
- First comment explaining why it exists

Product Hunt notes:

- Makers can hunt their own product
- Product Hunt says launch success depends on preparation
- Do not directly ask people to upvote
- Asking people to visit/comment is acceptable

Source:

```text
https://www.producthunt.com/launch
```

### 3. Music Community Expansion

Goal:

- Reach people who already dig through Bandcamp, Last.fm, Rate Your Music, and recommendation threads
- Find the strongest audience segment

Potential places:

- Rate Your Music communities
- Bandcamp-focused communities
- Indieheads-adjacent spaces
- Music discovery Discord servers
- X/Twitter demo threads

Good demo format:

```text
Give me one song. I will run it through Craterra and post the digging path.
```

## Draft Copy

### English Short Version

```text
I built Craterra, a music digging tool.

Give it one song and it tries to recommend 3-5 less obvious tracks using public music metadata, MusicBrainz/Deezer validation, and AI curation.

It is not trying to make a same-vibe playlist. It tries to make a defensible digging path: bridge + difference.

Would love feedback, especially from people who already dig through Bandcamp, Last.fm, RYM, or obscure recommendation threads.

https://craterra-production.up.railway.app/
```

### Korean Short Version

```text
Craterra라는 음악 디깅 도구를 만들었습니다.

곡 하나를 넣으면 비슷한 분위기의 뻔한 플레이리스트가 아니라, "왜 이 곡으로 넘어갈 수 있는지" 설명 가능한 덜 뻔한 추천 3-5개를 찾아줍니다.

Last.fm, ListenBrainz, MusicBrainz, Deezer 같은 공개 음악 메타데이터와 AI 큐레이션을 섞어 만들었습니다.

음악 많이 파는 분들 피드백 받고 싶습니다.

https://craterra-production.up.railway.app/
```

### Hacker News Title

```text
Show HN: Craterra - dig for less obvious music recommendations from one song
```

### Product Hunt Tagline Drafts

```text
Find less obvious music paths from one song.
```

```text
A music digging tool for finding the next deeper cut.
```

```text
Turn one song into a defensible digging path.
```

## Pre-Promotion Checklist

- Confirm production `/health` returns 200
- Confirm `/dig` works with a common seed such as `Radiohead Creep`
- Confirm one obscure or regional seed works well enough
- Run one mobile browser check on a real phone
- Apply `outbound_clicks` table in Supabase production
- Keep an eye on OpenRouter usage/cost logs during launch
- Be ready to answer what public metadata sources are used

## Current Caveats To Be Honest About

- It is an MVP
- Recommendations can still be uneven for sparse metadata
- Bandcamp links are search links, not guaranteed exact matches
- Bandcamp affiliate wiring is not active because no public official affiliate-link flow was confirmed
- Real phone QA is still pending

