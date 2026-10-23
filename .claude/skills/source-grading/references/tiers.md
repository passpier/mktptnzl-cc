# Tier edge cases

## Assigning the tier

Ask: "Did I see this number at its origin, in this run?"

| Situation | Tier | Why |
|---|---|---|
| `scripts/apple.py lookup` → userRatingCount | S | Apple's own number, fetched now |
| Google Play `realInstalls` via scraper | S | Google's own figure, exposed in page data. Note: global and rounded |
| Competitor pricing page crawled with crawl4ai | S | Origin page, fetched now. Save the `raw` path |
| Review text quoted from the RSS/scraper output | S | Origin content. The bias still needs a label |
| Reddit/HN/PTT post counts from `community.py` | S | Direct observation. It measures discussion, not demand |
| Reddit thread counts/titles from `community.py reddit` | S (default backend: Reddit's own search feed). `--backend arctic`: S if ≥1 permalink confirmed on reddit.com, else B | Body, score and comment counts come from the Arctic Shift archive and are as of archive time; say so |
| Your own landing-page / ASA test results | S | Your own measurement. It's the strongest evidence you can get |
| Founder tweet: "we hit $20k MRR" | A | First-party statement, but self-reported and unaudited. Label it self-reported |
| Apple developer docs on ranking factors | A | Official, dated |
| Company press release with user counts | A | Self-reported |
| DataForSEO / Google Ads search volume | B | Modeled. Low-volume terms are bucketed or rounded |
| Google Trends index | B | Relative index (0–100), not volume |
| ASA search popularity (1–100), typed in from the ASA UI | B | Apple's own scale, but opaque. Record method "ASA UI manual" |
| Sensor Tower / Appfigures estimate from their own public page | B | Modeled estimate, stated methodology |
| News article quoting a Sensor Tower estimate | C → trace | Find the original Sensor Tower page. If you can't, it's D |
| "Top 10 budgeting apps 2026" listicle | D | No primary data. Use it only to discover app names, then look those apps up (S) |
| WebSearch result snippet with a number | C/D | Snippets are not sources. Open the page and find the origin |
| Anything you "know" from training | D | Use `--url memory`. Leads only: verify it or move it to Data gaps |

## Independence (`source_group`)

Two rows are independent only if one did not derive from the other.
- `apple`, `google-play`, `apple-hints`, `apple-snapshots`, `gplay-snapshots`, `dataforseo`, `google-trends`, `ptt`, `dcard`, `reddit`, `hackernews`, `crawl:<domain>`, `own-experiment` are separate groups.
- Several articles that all cite one report belong to **one** group: the report's group.
- DataForSEO SERP and DataForSEO keyword volume both come from DataForSEO. They count as independent only for different claim types (rank vs. volume), never as double confirmation of one number.

## Dates

- `retrieved_at`: when you fetched it. Set automatically.
- `published_at`: when the source was published, for articles, reports, and posts.
- `data_as_of`: the period the number describes. Examples: keyword volume `2026-09`, a 2025 market report `2025`, a review sample's newest date.
- Staleness uses `data_as_of`. If that's missing, `published_at`; if that's missing too, `retrieved_at`.
