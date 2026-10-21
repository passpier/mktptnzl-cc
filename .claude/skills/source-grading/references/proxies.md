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
| Community discussion | `community.py hn/ptt/reddit`; Dcard via crawl4ai | S | Vocal minority; promotional posts inflate counts (check titles) |

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
- **Population funnel** (who could use it): start from a government or association survey of the activity (people who play an instrument, exam takers), then narrow step by step to the reachable segment.
  - Each step is its own row: `--kind population --tier A` for survey figures; a step with no source is a `[假設]` line.
  - Show the funnel as a range, with every step visible. Never collapse it into one "TAM = X" number.
- **Reverse check** (how big it must be): `uv run scripts/econ.py payers --target <net/month> --price <E#> --period year --commission <E#> --conversion <[假設]>` gives the paying users and installs needed for the founder's target.
  - Compare those numbers with observed scale proxies, such as install brackets and rating counts.
  - Read the result as "needs N payers; the leaders show scale proxies of M". It's a plausibility check, not an estimate.

## Retention and use frequency

No free source shows another app's retention. Use these proxies to judge whether the category **tends** to keep users, then measure your own app in an experiment.

| Proxy | How | Tier | Failure modes |
|---|---|---|---|
| Tenure statements in reviews | review-mining `tenure` code ("used it for 2 years", "every day") | S | Long-time users write more reviews; the share is not a retention rate |
| Quit reasons in reviews | review-mining `quit` code: plateau, boredom, goal reached, exam over | S | 1–3★ samples overstate quitting |
| Natural frequency of the job | Is the job daily (habit), seasonal (exam, back-to-school), or one-off (goal reached, then leave)? Cite the event, e.g. exam date [A] | A/S | Says nothing about any particular app |
| Category benchmark report | Trace a subscription-platform or analytics-vendor report to the publisher's own page. `--kind market_report --tier A`, labeled 自述 | A | Covers only the vendor's customers, who skew to subscription apps that use that SDK. The category may be defined differently |
| Own experiment (D1/D7/D30, weekly active days) | `--kind experiment --tier S --group own-experiment` | S | Needs enough installs to read; check with `econ.py asa-check --rate` |

## Unit economics

Before launch there is no churn, conversion, or CAC data, so **never write an LTV, LTV:CAC, or revenue figure**. Reverse it instead:
- `uv run scripts/econ.py breakeven --price <E#> --period month|year|once --commission <E#> --cpi <US$> --ratio <[門檻]>` returns the max churn or min conversion that keeps LTV per install / CPI at or above the ratio.
- Inputs:
  - price points: S rows from lookups or IAP lists;
  - commission: A rows from Apple or Google docs (`--kind policy`);
  - CPI: a planned ad cost, or for organic channels your hourly time cost [假設];
  - ratio: your own `[門檻]`. Rules of thumb like "LTV:CAC ≥ 3" are secondhand (C/D), so they're thresholds you choose, not evidence.
- Write the outputs as `[門檻]` lines or as experiment success thresholds. The experiment then measures whether reality clears them.
- Model annual plans with annual churn and monthly plans with monthly churn. Freemium needs the install → paid conversion term. Lifetime purchases have no churn.

## Defensibility

| Proxy | How | Tier | Failure modes |
|---|---|---|---|
| New-entrant rate | Share of the top 25 search results first released in the last 12 months (`released` in `apple.py search` rows; older rows only have it in the raw file) | S | Survivors only: entrants that vanished from search don't show |
| Free substitutes | Count of free, no-IAP apps and free websites covering the core job (lookups, crawled pages) | S | A free substitute that is hard to find is a weaker threat |
| Copyable vs. not | Classify the features: content generated by code (copyable in days) vs. curriculum, content assets, community, distribution (slow to copy) | [假設] + S | Judgment call: state it as such |

## When nothing works

Write it in 資料缺口 as:

> "X 未知；最便宜的取得方式：<experiment>，成本 <US$/hours>，成功門檻 <threshold>"

("X unknown; cheapest way to get it: <experiment>, cost <US$/hours>, success threshold <threshold>")
