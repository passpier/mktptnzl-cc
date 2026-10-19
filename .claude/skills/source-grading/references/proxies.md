# Proxies for missing data

Downloads, revenue, and in-store search volume have **no free first-party source**. These proxies are the honest alternative.

How to use them in a report:
- Name the metric as the proxy it is, e.g. "評分增速（下載動能代理指標）" (rating velocity, a download-momentum proxy).
- Never relabel a proxy as the underlying metric.
- Never convert a proxy into a point estimate of downloads or revenue with a made-up ratio.

## Download momentum

| Proxy | How | Tier | Failure modes |
|---|---|---|---|
| **iOS rating velocity** | `snapshot.py diff --app apple:<id>:<cc> --slug <slug>` → ratings/week | S (derived) | Apps that prompt for ratings aggressively inflate it. Compare apps against each other, never in absolute terms. Needs ≥2 snapshots, ideally ≥4 weeks apart |
| **Google Play realInstalls delta** | `snapshot.py diff --app gplay:<id>:<cc>` → real_installs_per_week | S (derived) | Global, not per country. Rounded. The best free Android momentum signal |
| Install bracket | `gplay.py app` → `installs` | S | Coarse (100K+ → 500K+); cumulative, not current |
| Chart presence over time | repeated `apple.py chart` (genre-filtered) | S | Charts weigh download velocity; absent ≠ dead in niche categories |
| Review volume in last 90d | `apple.py reviews` / `gplay.py reviews` → count by date | S | RSS caps at about 500 recent reviews |

## Monetization

| Proxy | How | Tier | Failure modes |
|---|---|---|---|
| **Top-grossing presence** | `apple.py chart --feed top-grossing --genre <id> --country tw` | S | Proves someone pays; says nothing about margins |
| Price points / IAP range | `apple.py lookup` (price), `gplay.py app` (iap_range), competitor paywall screenshots via crawl4ai | S | Listed range ≠ what most users pay |
| Founder-published revenue | crawl the public post or dashboard | A (自述) | Survivorship: only winners publish |

## Demand / search

| Proxy | How | Tier | Failure modes |
|---|---|---|---|
| **App Store search popularity** | Apple Search Ads → Keyword planner; type the 1–100 score in manually (`--kind search_popularity --tier B --group apple-search-ads`) | B | Needs an ASA account (no spend). The scale is opaque; 5 is the floor |
| App Store autocomplete | `apple.py hints` | S | Order hints at popularity; carries no volume |
| Google search volume | DataForSEO `keywords_data/google_ads/search_volume/live` | B | **Web** demand, not in-store. zh-TW long-tail is often null or rounded |
| Google Trends | DataForSEO `keywords_data/google_trends/explore/live`, past_5_years | B | Relative index; compare terms within one request only |
| Community discussion | `community.py hn/ptt`; Reddit/Dcard via crawl4ai | S | Vocal minority; promotional posts inflate counts (check titles) |

## ASO library score fields

The ASO skills (global aso-skills, marketingskills `aso`) ask for fields that have no first-party source. Fill each one only from the source given here.

| Field the skill asks for | Allowed source | If missing |
|---|---|---|
| App Store keyword volume / popularity | `search_popularity` row only (ASA Keyword planner, B). **Never** a Google `keyword_volume` row: that's web demand | Leave the cell blank, put the term in 資料缺口 |
| Keyword difficulty | No first-party score. Describe competition instead: rating counts and last-update dates of the top search results (`apple.py search` / `gplay.py search`), each `[E#]` | No 1–100 number |
| "Estimated monthly search volume" (App Store) | None. It's a point estimate built from a proxy | Never output it |
| Opportunity score (volume × difficulty × relevance) | Only when every input is a ledger row. Call it a derived ranking, not a measurement | Rank by popularity and autocomplete order instead |
| Appeeky or other paid ASO API data | Not configured; use `scripts/` | — |
| Listing fields for an `aso` audit | `apple.py lookup` / `gplay.py app` rows (S), not the skill's WebFetch of the listing page | — |
| Apple keyword field limit | **100 bytes, not characters** ([Apple](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information), S, checked 2026-10-19). zh-Hant is about 3 bytes per character in UTF-8, so roughly 33 characters. Add a `--kind metadata --tier S --group apple-docs` row when a report proposes keyword-field contents | Apple doesn't name the encoding; confirm in the App Store Connect field before submitting |

## Market size

- Prefer a bottom-up estimate: (competitor count with real momentum) × (observed price points). Mark every input with its own E#.
- Top-down market-size reports must be traced to the original publisher (A/B) and be ≤ 24 months old. Otherwise they go in 資料缺口.

## When nothing works

Write it in 資料缺口 as:

> "X 未知；最便宜的取得方式：<experiment>，成本 <US$/hours>，成功門檻 <threshold>"

("X unknown; cheapest way to get it: <experiment>, cost <US$/hours>, success threshold <threshold>")
