# Freshness TTL policy

The source of truth is `TTL_POLICY` in `mr/ledger.py`. If you change this table, update that dict too.

| kind | TTL | severity | Reasoning |
|---|---|---|---|
| ranking | 7d | block | Chart positions move daily; a week-old rank is history, not state |
| price | 7d | block | Paywalls and IAP prices are A/B tested and change without notice |
| rating | 30d | block | Rating counts drift steadily; snapshot velocity needs dated points |
| metadata | 30d | block | Titles/subtitles/versions change with ASO iterations |
| installs | 30d | block | Brackets and realInstalls move monthly |
| keyword_volume | 90d | block | Google Ads volumes are monthly averages; a quarter is the usable window |
| search_popularity | 90d | block | ASA popularity updates periodically |
| review | 365d | warn | Theme analysis can use a year of reviews, but weight the last 90d. Pre-redesign complaints may be fixed already |
| trends | 30d | warn | Fetch a 5-year window for shape; refresh monthly for the latest point |
| serp | 30d | warn | Search results and autocomplete shift, but slowly for most niches |
| community | 90d | warn | Discussion counts are directional |
| market_report | 730d | block | Over 2 years old misses the AI-era shifts in most categories; over 1 year old should be flagged in prose |
| experiment | 180d | warn | Your own test results age as the product and market change |
| other | 30d | warn | Default: be conservative |

## Refresh workflow (`/research refresh <slug>`)

1. `uv run scripts/ledger.py stale <slug>`. Each line names the `method` that produced the row.
2. Re-run exactly those methods: free scripts first. Re-run DataForSEO calls only for stale paid rows.
3. Point report citations at the new E# rows. Keep the old rows: they become the time series.
4. Re-save the report. The hook re-validates it.
