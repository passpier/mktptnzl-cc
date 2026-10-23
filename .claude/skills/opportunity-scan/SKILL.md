---
name: opportunity-scan
description: Score an app idea or niche's market potential for a solo developer across Demand, Competition, Monetization, Gap and Solo-reachability, using graded store data. Use for "market potential", "市場潛力", "值不值得做", "is this niche saturated", "find stale incumbents", "找利基", or as part of /research idea|niche.
metadata:
  version: 1.0.0
---

# Opportunity Scan — market potential score

Apply `source-grading` throughout. Every score cell cites `[E#]` and carries a confidence level. Score the US by default. If the brief adds another market, score it in its own column.

## Inputs

Collect these through store-collector / web-collector if they're missing:
- Store search results for the core terms (3 in quick mode, 3–5 in deep). Both stores: `apple.py search`, `gplay.py search`.
- Lookups for the top competitors (≤6 in quick mode, 5–8 per store in deep), including verified discovery leads.
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
| **Solo-reachability** | Market won by paid UA or brand; no communities | Niche communities exist (subreddits, Discords; PTT/Dcard when TW is in scope); long-tail keywords; SEO/ASO winnable | community counts [S], SERP [S], keyword set [B] |

## Signals worth calling out (these are often the opportunity)

- **Stale leader**: a #1–3 app with no update in ≥12 months and a 1–3★ share rising in recent reviews.
- **Localization gap** (only when a second market is in scope): a strong US app with no local listing, or poor local reviews.
- **Platform gap**: strong on one store, weak or absent on the other.
- **Price gap**: every leader asks for a subscription, and reviews complain about it. That leaves room for one-time purchase or freemium.
- **Rating velocity**: when ≥2 snapshots exist, `snapshot.py diff` shows which competitors are actually growing right now.

## Output (section of the report)

1. A score table (Dimension | Score | Evidence | Confidence), one score column per market in scope. Every cell cites `[E#]`. In quick mode, fold it into the Conclusion and Viability sections instead of a separate table if that reads better.
2. A 3-line verdict per market, checked against the kill criteria in `brief.md`.
3. "What would flip this": the single piece of evidence that would most change the score. If you don't have it yet, put it under Data gaps.

Don't average the scores into one number that hides a fatal dimension. A 1 on Monetization or Reachability is a no-go flag on its own.

These five scores only decide whether the idea is **worth validating**. Whether it's **worth building** (unit economics, retention, build and upkeep cost, defensibility, platform and licensing risk) is the `viability-check` skill's job, in its own table.

## Related skills

- `review-mining` provides the Gap evidence.
- `demand-signals` provides the Demand evidence.
- `viability-check` scores whether it's worth building, once these scores say it's worth validating.
- `lean-gtm` turns the Reachability findings into a channel plan (short form in `idea`; `niche` stops at the score).
- Global `competitor-analysis` and `keyword-research` (ASO library) go deeper on ASO once the call is GO. Their volume and difficulty fields follow "ASO library score fields" in `source-grading/references/proxies.md`.
