# DataForSEO via MCP — cheat sheet

The MCP server (`dataforseo-mcp-server@3.1.3`) exposes four tools:
- **`api_request`** `{method, path, data, noAiMode}`: the only paid tool.
- `docs_index`, `docs_list_sections`, `docs_search`: free.

**Before you use an endpoint for the first time in a session, read its docs with `docs_search <path>`.** It's free, and parameters change. Don't rely on this sheet or on memory for parameter names.

## Budget rules (enforced by hooks/dfs_budget_guard.py)

- Monthly cap is **US$10**. Calls over US$0.50 trigger an approval prompt. Estimates live in `config/budget.json`; actual cost goes to `research/_costs.jsonl`.
- Use the **standard queue** (`task_post`, then `tasks_ready`, then `task_get`). It's the cheapest option, and GET requests are free. `priority: 2` is blocked.
- Use `live` only where it's the only mode (Google Ads volume, Trends, SERP live are cheap enough).
- Blocked: `backlinks/*` (needs a US$100/mo subscription), `on_page/lighthouse`. App listings `live` costs about US$0.20, so avoid it.
- **Batch**: one `search_volume` task takes up to 1000 keywords for the price of one task. Send every keyword in a single call.
- **Cache**: check `uv run scripts/ledger.py list <slug>` before buying. If a matching row is still fresh, reuse it.
- Default `noAiMode: false`. The `.ai` paths return a trimmed response, which saves context. If the response has no `cost` field, the hook logs the estimate instead.

## Codes

| Market | location_code | language_code |
|---|---|---|
| United States (default) | 2840 | en |
| Taiwan (only when TW is in scope) | 2158 | zh-TW |

## Endpoints that matter for app research (all verified with docs_search before use)

| Need | Path | Approx. cost | Ledger kind / tier |
|---|---|---|---|
| Google search volume for many keywords | `POST /v3/keywords_data/google_ads/search_volume/live` | ~$0.075 / task (≤1000 kw) | keyword_volume / B |
| Keyword ideas from seeds | `POST /v3/keywords_data/google_ads/keywords_for_keywords/live` | ~$0.075 / task | keyword_volume / B |
| Google Trends, 5-year shape | `POST /v3/keywords_data/google_trends/explore/live` (`time_range: past_5_years`) | ~$0.01–0.02 | trends / B |
| Google SERP (who ranks for "best X app") | `POST /v3/serp/google/organic/live/regular` | ~$0.002 | serp / S |
| Google Play top charts (no free feed) | `POST /v3/app_data/google/app_list/task_post` (`app_collection` e.g. `topselling_free`, `topgrossing`) → `task_get` | ~$0.001–0.005 | ranking / S |
| App Store / Play app search in-store | `POST /v3/app_data/{apple,google}/app_searches/task_post` | ~$0.001–0.005 | serp / S |
| Bulk reviews beyond the free RSS cap | `POST /v3/app_data/{apple,google}/app_reviews/task_post` | ~$0.00075 / 50–150 reviews | review / S |

Free scripts already cover App Store lookup, search, charts (including top-grossing by genre), reviews, and hints, plus Google Play app details, search, and reviews. Use DataForSEO only for: **Google search volume, Trends, SERP, Google Play charts, and in-store search positions**.

## Recording results

After each paid call, record what you will cite:

```bash
uv run scripts/ledger.py add <slug> --kind keyword_volume --claim "'habit tracker app' Google monthly searches US" \
  --value 1900 --unit searches/mo --tier B --group dataforseo \
  --url "dataforseo:/v3/keywords_data/google_ads/search_volume/live" \
  --method "DataForSEO google_ads search_volume (location 2840, en)" --as-of 2026-09 --cost 0.075
```

Save large responses to `research/<slug>/raw/` by writing the JSON yourself, then pass `--raw`. For many keywords, store one ledger row per keyword *cluster* (value = {keyword: volume}), not one row per keyword.
