---
name: research
description: Entry point for app market & marketing research with fresh, first-party, graded evidence. Use for "/research", validating an app idea (點子驗證, 市場潛力, go/no-go), researching an existing app's marketing (行銷, ASO, 競品, 評論), finding niches or opportunities (找利基, 新機會, 市場缺口), or refreshing an earlier study ("refresh", "更新資料"). Modes - idea, app, niche, refresh. Depth - quick (default) or --deep.
metadata:
  version: 2.0.0
---

# Research — app market and marketing research

This skill runs the whole study, from intake to an audited report. Load `source-grading` first; its rules apply to every step below.

## Modes

| Command | Use for | Core skills |
|---|---|---|
| `/research idea "<one-line idea>" [--deep]` | Pre-build idea validation → go / pivot / no-go | opportunity-scan → review-mining → demand-signals → viability-check → lean-gtm (short) |
| `/research app <apple:id\|gplay:id> [--deep]` | Marketing for a live app | review-mining → demand-signals → lean-gtm (full) |
| `/research niche "<category or audience>" [--deep]` | Hunting for gaps | opportunity-scan (charts + stale incumbents) → review-mining |
| `/research refresh <slug>` | Re-fetch only stale evidence, then re-validate the report | `ledger.py stale`, then the original methods |

`niche` has no single product to market, so its report leaves out What to build and Go-to-market. Reachability is covered by the Solo-reachability score. Run `/research idea` on the chosen gap to get channels.

**Market: US by default**, both stores. Add TW (or another storefront) only when the user asks for it; then give it its own columns and never mix markets. TW-only sources (PTT, Dcard, zh-TW terms) run only when TW is in scope.

**Language**: `brief.md` and `report.md` are written in English. Talk to the user in their language.

## Depth

Default is **quick** (target: about 30 minutes, a report the user can read in 5). `--deep` runs the full procedure when the user asks for it or when a quick verdict is too close to call.

| Step | quick (default) | deep |
|---|---|---|
| Kill criteria | 3 defaults (saturation, monetization, demand), approved in one turn | 3–5, negotiated |
| Discovery sweep | 6–10 web searches (step 4a) | same |
| Store data | 3 core terms × 2 stores (search + hints), 1 top-grossing genre chart, lookups for ≤6 competitors, reviews for the top 2 | full store-collector procedure |
| Web / community | verify discovery leads, Reddit asks, pricing pages of the top 3 | + DataForSEO (if approved), HN, Reddit comment mining, competitor sites |
| Review mining | top themes with counts and quotes, no CI | codebook, shares with 95% CI |
| Audit | one evidence-auditor pass | same, plus a re-audit after fixes |
| Ledger size | soft cap of about 120 rows | no cap |

## Step 1 — Intake (≤3 questions in quick, ≤5 in deep; skip what is already known)

1. Create a `slug` (lowercase-kebab, e.g. `us-habit-tracker`). Create `research/<slug>/brief.md`.
2. Read `.agents/product-marketing.md`. If it's empty or the product differs, fill or update it (marketingskills `product-marketing`, or ask about product, audience, problem, and alternatives).
3. Ask only what changes the plan: the user's unfair advantage (skills, audience, distribution), monetization intent, and time budget. Ask about markets only if the user mentioned one other than the US.
4. In `idea` mode, record what `viability-check` needs as `[assumption]` in `brief.md`: target net revenue per month; tech stack and platforms (and whether audio or camera latency matters); where the content comes from. Reuse answers from earlier briefs when the user confirms them.

## Step 2 — Kill criteria first

Write falsifiable go/no-go thresholds into `brief.md` **before** collecting any data, and get the user's agreement. This prevents confirmation bias.

In quick mode, propose these three, filled in for the idea, and ask for a yes or edits in one turn:
- **Saturation**: ≥2 of 3 core terms have ≥3 large, active apps in the top 10 of **both** stores (large: ≥5,000 ratings on the App Store or ≥1M installs on Google Play; active: updated within 12 months) → no-go unless there's a sharp wedge.
- **Monetization**: <2 of the top 8 similar apps charge directly (paid, IAP, or subscription) **and** none is in the genre's top-grossing 100 → monetization unproven.
- **Demand**: ≥3 core terms get no App Store autocomplete **and** <3 organic community asks in 12 months → demand unproven.

Deep mode adds criteria such as "no fixable complaint cluster ≥15% in ≥2 apps with ≥100 coded reviews".

## Step 3 — Plan and budget

- Check that the collectors can run. If the crawl4ai MCP isn't connected, say so now and what the WebFetch fallback can't do. Reddit doesn't need crawl4ai (`community.py reddit`).
- DataForSEO only where free sources can't answer: estimate the cost from [references/dataforseo.md](references/dataforseo.md), check `uv run scripts/ledger.py costs`, and show the total (typical: US$0.10–1.00; cap US$10/month, enforced by a hook).

## Step 4 — Collect

### 4a. Discovery sweep (web-collector, runs first)

6–10 web searches that store APIs miss. The iTunes Search API returns only part of the store, so new direct competitors often show up here first.
- recent direct competitors: "<idea> app", "<core term> app 2026", launch posts (Product Hunt, Reddit, X)
- adjacent business signals: funding, paid users, or ARR of the nearest larger players
- failure base rate: shutdowns, pivots, or acquisitions of similar products
- platform and policy changes: App Review guidelines, Google Play policy, and SDKs the idea depends on

Every hit is a **lead** (tier D) until verified. Store apps are verified by `apple.py lookup` / `gplay.py app`; business and policy facts by fetching the origin page (company post, official doc). Press articles are tier C: trace them. Leads that fail verification go under Data gaps.

### 4b. Store and web data (run the subagents in parallel)

- **store-collector**: core-term search and hints on both stores, top-grossing chart, lookups for search hits ∪ verified discovery leads, reviews. Pass the depth so it applies the quick caps.
- **web-collector**: verify discovery leads, Reddit asks (`community.py reddit`), pricing pages; in deep mode also DataForSEO, HN, competitor sites, and comment mining. PTT/Dcard only if TW is in scope.
- Both return short digests plus E# lists. Raw data stays on disk.

## Step 5 — Synthesize

Run the core skills for the mode (table above). Each writes its section with `[E#]` citations. In `idea` mode also write **What to build**: MVP scope, pricing tier, and which features to phase in later, tied to the evidence (competitor gaps, complaint themes, unit economics). Numbers there are cited or tagged `[assumption]` / `[threshold]`.

## Step 6 — Audit

Send the draft to **evidence-auditor**, which argues the opposite case.
- Fix every `fail` item.
- Fold each devil's-advocate point into **Risks** (or **Data gaps**) as a plain statement. Don't add a separate rebuttal section.

## Step 7 — Write the report

1. Write `research/<slug>/report.md` from [references/report-template.md](references/report-template.md), following its style guide.
2. Write the sources file (it is not pasted into the report):
   ```
   uv run scripts/ledger.py render <slug> --report research/<slug>/report.md > research/<slug>/sources.md
   ```
3. The PostToolUse hook validates the report on every save. Fix all errors until it passes, and say which warnings remain.

## Step 8 — Close the loop

The report ends with **1–3 validation experiments** (the cheapest primary data). Each one needs: hypothesis, setup, cost, duration, success threshold, and kill threshold.

Before writing the thresholds, check that the experiment can actually read them:
- Apple Search Ads tests: `uv run scripts/econ.py asa-check --budget … --cpt … --ttr … --success-impressions … --kill-impressions … --tap-install … --rate d7=… --rate paywall_trial=…`. A capped budget can trip an impression floor by itself, and a rate on a handful of installs is noise.
- A/B tests: `uv run scripts/econ.py power --p1 … --p2 … --n …`.
- If a threshold is unreadable, raise the budget or traffic, or label it "directional" and don't use it as a kill switch.
- Take the success thresholds for conversion and churn from `econ.py breakeven` (see `viability-check`), not from rules of thumb.

| Experiment | Cost | Measures |
|---|---|---|
| Landing page + waitlist, posted to Reddit / Threads / short video | US$0–10 | Problem resonance (sign-up rate) |
| Fake-door or pricing page with 2 price points | US$0 | Willingness to pay (click-through to price) |
| Apple Search Ads, exact match on 5–10 core terms, US$20–30 cap | US$20–30 | Real in-store demand (impressions), TTR, CPT |
| 5 user interviews recruited from review authors' communities | time only | Jobs-to-be-done and switching triggers |
| Technical spike (1–2 days) on the riskiest build assumption | time only | Feasibility, e.g. tap-to-sound latency on a mid-range Android phone |

When the user reports results, record them with `ledger.py add --tier S --group own-experiment --kind experiment` and re-run the verdict.

## Recurring tracking (optional)

The weekly free snapshots build first-party momentum data over time. See `config/launchd/README.md`.
