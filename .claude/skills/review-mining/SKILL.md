---
name: review-mining
description: Mine recent competitor App Store and Google Play reviews (US by default) into complaint clusters, switching triggers, wished-for features and verbatim voice-of-customer phrases. Use for "review mining", "評論分析", "使用者痛點", "what do users hate about X", "voice of customer", "feature gaps", or as part of /research.
metadata:
  version: 1.0.0
---

# Review Mining

Apply `source-grading`. Reviews are tier S, but they're a **biased sample**. Say so in the report.

## Collect (store-collector)

For the top competitors (quick: 2; deep: 3–5) × both stores, in each market in scope (US by default):

```bash
uv run scripts/apple.py reviews <slug> --id <apple_id> --country us --pages 10       # most recent ≤500
uv run scripts/gplay.py reviews <slug> --id <package> --country us --n 300 --max-stars 3
uv run scripts/gplay.py reviews <slug> --id <package> --country us --n 200            # unfiltered baseline
```

Each command writes one ledger row (the sample summary) and saves the full text in `raw/`. Analyse from the raw files; don't paste them into the conversation. If you need more than these free caps, DataForSEO `app_reviews` is cheap (see `research/references/dataforseo.md`).

## Analyse

1. **Weight recency.** Primary window is the last 90 days. Older reviews only show whether an issue persists; it may already be fixed. Check `version` against the current version.
2. **Cluster** every 1–3★ review into one primary code:
   - **Complaint**: bug/crash, missing feature, UX friction, pricing/paywall, ads, sync/data loss, support, privacy.
   - **Switching trigger**: "I moved from X because…" / "looking for alternative to…".
   - **Wished-for feature**: "I wish it could…".
   - **Job-to-be-done**: what the user was trying to accomplish when it failed.
   - Also tag these secondary codes, on **all** star levels, because they feed `viability-check`:
     - `tenure`: how long or how often the reviewer has used it ("used it for 2 years", "every day"). This is a retention proxy.
     - `quit`: why they stopped or plan to stop. Use plateau, boredom, goal reached, or exam over. Goal-reached and seasonal quits cap subscription lifetime.
     - `price`: explicit price or value statements ("worth every penny", "$X is too much", "would pay for…"). Record the amount when one is stated. This is a willingness-to-pay proxy.
3. **Quantify**: each cluster's share of coded reviews, per app and per market.
   - Record each cluster table as a ledger row: `--kind review --tier S --group apple|google-play --method "review-mining coding of raw/<file>"`, with value = {cluster: share, n: total}.
   - Keep Apple and Google Play as separate rows so they can corroborate each other as independent groups.
4. **Verbatims**: collect 2–3 short quotes per cluster in the original language (never translate quotes). These feed copywriting and ASO later.
5. **Check 4–5★ reviews too**: they tell you which value must be preserved, and they make good positioning copy.

## Output (section of the report)

- Quick mode: the top 3–5 themes with count out of n, one quote each, and whether a solo dev can fix it. No CI.
- Deep mode: table with columns cluster | share (95% CI) | example quote | fixable by solo dev? | [E#], one share column per market in scope.
- Secondary-code shares (`tenure`, `quit` by reason, `price`) per app, with 1–2 verbatims each, as their own ledger row. `viability-check` cites them.
- Top 3 gaps, ranked by (share × fixability × how often it shows up as a switching trigger).
- Bias note: what the review sample over- and under-represents. Example: "1–3★ filtered; RSS caps 500; vocal users".
- Hand-offs:
  - verbatims → marketingskills `copywriting` / `customer-research`
  - complaint keywords → global `keyword-research`
  - reply strategy (live apps) → global `review-management`

## Related skills

opportunity-scan (Gap score), viability-check (retention and willingness-to-pay proxies), lean-gtm (messaging), demand-signals (do the complaint terms also show up in search?).
