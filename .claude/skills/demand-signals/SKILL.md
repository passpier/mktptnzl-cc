---
name: demand-signals
description: Measure demand for an app idea or keyword set from separate, graded signals - App Store autocomplete and ASA popularity (in-store), Google search volume and Trends (web, via DataForSEO), and community discussion (PTT, Dcard, Reddit, HN). Use for "is there demand", "有沒有需求", "search volume", "搜尋量", "trend", "趨勢", "keyword demand", or as part of /research.
metadata:
  version: 1.0.0
---

# Demand Signals — 需求訊號

Apply `source-grading`. There are three separate signal families. **Never merge them into one number.**

## 1. In-store demand (closest to installs)

- `uv run scripts/apple.py hints <slug> --term <seed> --country tw|us`
  - Run this for each seed term and for its first suggestions.
  - Present in the report: which terms autocomplete, and in what order.
- **ASA search popularity (1–100)**: Apple's own scale. It needs the user's Apple Search Ads account; no spend is needed to view it.
  - Ask the user to look up the 5–15 core terms in ASA Advanced → Keyword planner and paste the scores.
  - Record each term: `--kind search_popularity --tier B --group apple-search-ads --method "ASA UI manual"`.
- In-store search positions, only if positions matter:
  - free: `apple.py search` / `gplay.py search`
  - paid: DataForSEO `app_searches` for exact in-store order

## 2. Web demand (Google)

Use DataForSEO through web-collector. Read `research/references/dataforseo.md` first.
- **Search volume**: one `google_ads/search_volume/live` call per market, with **all** keywords batched. Both zh-TW (2158) and en (2840) keyword sets.
- **Keyword ideas**: `keywords_for_keywords` from 3–5 seeds, only if the keyword set is thin.
- **Trends**: `google_trends/explore/live`, past_5_years, ≤5 terms per request (they share one scale). Report the slope and seasonality, not single points.
- **zh-TW caveat**: long-tail Traditional Chinese volumes are often null or rounded. Report null as "no measurable volume (B)", not as zero demand, and lean on hints, PTT, and Dcard for TW instead.

## 3. Community demand

```bash
uv run scripts/community.py ptt <slug> --query <zh term> --boards MobileComm,iOS,Android,Lifeismoney[,more]
uv run scripts/community.py hn  <slug> --query "<en term>"
```

- Reddit and Dcard: web-collector uses crawl4ai `md` on search pages, e.g. `https://www.reddit.com/r/<sub>/search/?q=<term>&restrict_sr=1&sort=new` and `https://www.dcard.tw/search?query=<term>`. Record counts and dates per thread as `--kind community --tier S --group reddit|dcard`.
- Separate **organic asks** ("推薦記帳 app?", "looking for an app that…") from **promotional posts** (`[iAPP]`, launch posts). Only organic asks signal unmet demand.
- Pick relevant PTT boards by topic, e.g. Lifeismoney (money), Fitness, Baby-Mother, Japan_Travel, Soft_Job.

## Output (section of the report)

| Signal | TW | US | Tier | Note |
|---|---|---|---|---|
| App Store hints | … [E#] | … [E#] | S | in-store |
| ASA popularity | … [E#] | … [E#] | B | if user supplied |
| Google volume (sum of core cluster) | … [E#] | … [E#] | B | web, not in-store |
| Trends 5y slope | … [E#] | … [E#] | B | relative |
| Organic community asks / 12 mo | … [E#] | … [E#] | S | vocal minority |

Then a 2-line read: is demand **present, growing, and reachable** in each market? Name the strongest and the weakest signal.

## Related skills

opportunity-scan (Demand score), global `keyword-research` (turns the keyword set into an ASO plan), lean-gtm.
