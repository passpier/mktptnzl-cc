---
name: opportunity-scan
description: Score an app idea or niche's market potential for a solo developer across Demand, Competition, Monetization, Gap and Solo-reachability, using graded store data. Use for "market potential", "市場潛力", "值不值得做", "is this niche saturated", "find stale incumbents", "找利基", or as part of /research idea|niche.
metadata:
  version: 1.0.0
---

# Opportunity Scan — 市場潛力評分

Apply `source-grading` throughout. Every score cell cites `[E#]` and carries a confidence level. Score TW and US separately.

## Inputs

Collect these through store-collector / web-collector if they're missing:
- Store search results for 3–5 core terms per market. Both stores: `apple.py search`, `gplay.py search`.
- Lookups for the top 5–8 apps per store/market.
- Genre charts: `apple.py chart --feed top-free|top-grossing --genre <id>`.
- Demand rows from `demand-signals`.
- Complaint clusters from `review-mining` (for the Gap score).

## The five dimensions (1–5 each)

| Dimension | 1 (bad) | 5 (good) | Evidence |
|---|---|---|---|
| **Demand** | Hints don't autocomplete the term; Google volume ~0; flat or declining Trends | Rich hints, solid volume, rising 5-year Trends, active threads | hints [S], volume [B], Trends [B], community [S] |
| **Competition** (inverted) | Top 10 all updated <3 months ago, ≥4.7★, 100k+ ratings | **Stale incumbents**: leaders not updated in 12+ months, ratings ≤4.3, or few apps with >1k ratings | lookup `current_version_date`, ratings, avg [S] |
| **Monetization** | No genre apps in top-grossing; everything free with ads | Several genre apps in top-grossing; subscription price points visible | top-grossing chart, price/IAP [S], founder revenue [A] |
| **Gap** | Complaints are scattered, or about things you can't fix (pricing power, network effects) | One complaint cluster with ≥15% share that a solo dev can fix | review-mining clusters [S] |
| **Solo-reachability** | Market won by paid UA or brand; no communities | Niche communities exist (subreddits, PTT boards, Dcard topics); long-tail keywords; SEO/ASO winnable | community counts [S], SERP [S], keyword set [B] |

## Signals worth calling out (these are often the opportunity)

- **Stale leader**: a #1–3 app with no update in ≥12 months and a 1–3★ share rising in recent reviews.
- **Localization gap**: a strong US app with no zh-TW listing, or poor zh-TW reviews. Check the TW lookup or search results.
- **Platform gap**: strong on one store, weak or absent on the other.
- **Price gap**: every leader asks for a subscription, and reviews complain about it. That leaves room for one-time purchase or freemium.
- **Rating velocity**: when ≥2 snapshots exist, `snapshot.py diff` shows which competitors are actually growing right now.

## Output (section of the report)

1. The score table from the report template (TW and US columns). Every cell cites `[E#]`.
2. A 3-line verdict per market, checked against the kill criteria in `brief.md`.
3. "What would flip this": the single piece of evidence that would most change the score. If you don't have it yet, put it in 資料缺口.

Don't average the scores into one number that hides a fatal dimension. A 1 on Monetization or Reachability is a no-go flag on its own.

## Related skills

- `review-mining` provides the Gap evidence.
- `demand-signals` provides the Demand evidence.
- `lean-gtm` turns the Reachability findings into a channel plan (short form in `idea`; `niche` stops at the score).
- Global `competitor-analysis` and `keyword-research` (ASO library) go deeper on ASO once the call is GO. Their volume and difficulty fields follow "ASO library score fields" in `source-grading/references/proxies.md`.
