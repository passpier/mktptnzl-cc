---
name: demand-signals
description: Measure demand for an app idea or keyword set from separate, graded signals - App Store autocomplete and ASA popularity (in-store), Google search volume and Trends (web, via DataForSEO), and community discussion (Reddit, HN; PTT and Dcard when TW is in scope). Use for "is there demand", "有沒有需求", "search volume", "搜尋量", "trend", "趨勢", "keyword demand", or as part of /research.
metadata:
  version: 1.0.0
---

# Demand Signals

Apply `source-grading`. There are three separate signal families. **Never merge them into one number.**

## 1. In-store demand (closest to installs)

- `uv run scripts/apple.py hints <slug> --term <seed>` (default `--country us`)
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
- **Search volume**: one `google_ads/search_volume/live` call per market, with **all** keywords batched. US is location 2840 (en); add zh-TW (2158) only when TW is in scope.
- **Keyword ideas**: `keywords_for_keywords` from 3–5 seeds, only if the keyword set is thin.
- **Trends**: `google_trends/explore/live`, past_5_years, ≤5 terms per request (they share one scale). Report the slope and seasonality, not single points.
- **zh-TW caveat** (TW only): long-tail Traditional Chinese volumes are often null or rounded. Report null as "no measurable volume (B)", not as zero demand, and lean on hints, PTT, and Dcard for TW instead.

## 3. Community demand

```bash
uv run scripts/community.py hn  <slug> --query "<en term>"          # deep mode
uv run scripts/community.py ptt <slug> --query <zh term> --boards MobileComm,iOS,Android,Lifeismoney[,more]   # TW only
```

- Reddit: `uv run scripts/community.py reddit-subs <slug> --subs a,b` (size, self-promo rules), then `reddit <slug> --query "<en term>" --subs a,b` (thread counts with ask/promo split), then `reddit-comments <slug> --raw <reddit raw> --apps "Name=regex,..."` (which apps get recommended in ask threads). Review the ask titles in raw; the classifier is keyword-based. The default backend obeys Reddit's feed limit (~1 request per 30s), so run it in the background; `--backend arctic` is faster when the archive's full-text search is up.
- Dcard (TW only): web-collector uses crawl4ai `md` on `https://www.dcard.tw/search?query=<term>`. Record counts and dates per thread as `--kind community --tier S --group dcard`.
- Separate **organic asks** ("looking for an app that…", "any app that can…") from **promotional posts** (`[iAPP]`, launch posts). Only organic asks signal unmet demand.
- TW only: pick relevant PTT boards by topic, e.g. Lifeismoney (money), Fitness, Baby-Mother, Japan_Travel, Soft_Job.

## Output (section of the report)

| Signal | US | Tier | Note |
|---|---|---|---|
| App Store hints | … [E#] | S | in-store |
| ASA popularity | … [E#] | B | if user supplied |
| Google volume (sum of core cluster) | … [E#] | B | web, not in-store |
| Trends 5y slope | … [E#] | B | relative |
| Organic community asks / 12 mo | … [E#] | S | vocal minority |

Add a column per extra market only when the brief includes one. In quick mode, a few bullets under **Demand** can replace the table.

Then a 2-line read: is demand **present, growing, and reachable**? Name the strongest and the weakest signal.

## Related skills

opportunity-scan (Demand score), global `keyword-research` (turns the keyword set into an ASO plan), lean-gtm.
