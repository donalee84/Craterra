# Bandcamp Affiliate — Findings (2026-06-14)

## Conclusion

There is **no official public Bandcamp affiliate program with cash payouts** that
Craterra can sign up for. Re-checked on 2026-06-14.

- Affiliate-program databases list Bandcamp as **not maintaining** an official
  public cash-payout affiliate program.
- Some third-party "best music affiliate programs" listicles claim a ~10% rate,
  but none link to an official Bandcamp-run signup flow. Treat as unverified.
- `affiliatelinks.bandcamp.com` is an artist subdomain (anyone can claim
  `*.bandcamp.com`), **not** an official program.

## What Craterra does today

- Bandcamp links on recommendation cards are **search links**, not guaranteed
  exact-release matches and not affiliate-tagged.
- Outbound Bandcamp/Apple Music clicks are already tracked
  (`/outbound-click` -> Supabase `outbound_clicks`, local JSONL fallback) so the
  conversion volume is measurable the moment a partner flow appears.

## Decision

- **Do not block launch on Bandcamp affiliate wiring.** No program to wire.
- Keep click tracking running to quantify outbound intent.
- If/when Bandcamp (or a network like Impact/CJ) exposes an official flow, the
  only change needed is appending an affiliate tag/param in the link builder.
- Apple Music affiliate token support already exists via
  `APPLE_MUSIC_AFFILIATE_TOKEN` (optional env var) — that is the realistic
  first monetization channel today.

## Sources

- [Affiliate Program DB — Bandcamp](https://www.affiliateprogramdb.com/brands/bandcamp-affiliate-program/)
- [Best Music Affiliate Programs of 2026](https://walletminded.com/articles/best-music-affiliate-programs/)
- [Bandcamp x Linkfire partnership](https://www.linkfire.com/blog/bandcamp-linkfire-partnership)
