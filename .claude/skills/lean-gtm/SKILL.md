---
name: lean-gtm
description: Budget-constrained go-to-market plan for a solo developer's app - pick the top 3 channels from the evidence ledger, with cost, first experiment and success threshold per channel, delegating execution details to marketingskills and the ASO skill library. Use for "marketing plan", "行銷計畫", "how do I market my app with no budget", "低預算行銷", "launch plan", "GTM", or as part of /research idea|app.
metadata:
  version: 1.0.0
---

# Lean GTM — 低預算行銷計畫

Apply `source-grading`. Every channel recommendation must cite the evidence that makes the channel fit, e.g. "PTT Lifeismoney had 14 organic asks in the last 12 months [E9]". Generic advice ("do TikTok") without ledger support is not allowed.

## Constraints to assume unless told otherwise

- Solo developer, ≤10 hours per week of marketing, ≤US$100 per month cash.
- Markets: TW and US. Channels differ per market, so plan each market separately.

## Channel candidates → evidence that qualifies them

| Channel | Qualifies when the ledger shows | Execution skill |
|---|---|---|
| **ASO** (both stores) | In-store hints or popularity exist for terms leaders under-use; competitor metadata gaps | marketingskills `aso` (listing audit); global `keyword-research`, `metadata-optimization`, `screenshot-optimization`, `android-aso`, `localization`. Fill their score fields per "ASO library score fields" in `source-grading/references/proxies.md` |
| **Apple Search Ads (exact, small cap)** | ASA popularity ≥ ~20 on core terms, or an in-store demand test is needed anyway | global `apple-search-ads` |
| **Community-led** (PTT, Dcard, Reddit, Threads) | Organic asks exist [community rows]; boards allow self-posts | marketingskills `community-marketing` |
| **Directories & launch sites** (Product Hunt, etc.) | Audience is early-adopter or tech (HN/Reddit signal) | marketingskills `directory-submissions`, `launch` |
| **SEO / free tool** | Google volume exists for problem terms [B] and the SERP shows weak pages [S] | marketingskills `free-tools`, `programmatic-seo` (if installed) |
| **Review-driven positioning** | A clear complaint cluster against leaders [review rows] | marketingskills `copywriting`, `marketing-psychology` |
| **Pricing / paywall** | Competitor price points and complaints about subscriptions | marketingskills `pricing`, `paywalls` |

When a needed marketingskills skill isn't installed, say so and give the short version inline. Don't block on it.

## Depth by mode

| Mode | Output |
|---|---|
| `/research idea` (short) | Top 3 channels per market, each with Why / Cost / First experiment / thresholds. No messaging angle, 30-day sequence, or execution-skill handoff: there's no product to market yet. A channel with a strong signal can become one of the report's validation experiments |
| `/research app` (full) | Everything in the plan format below |
| `/research niche` | Not run. Reachability is covered by the opportunity-scan Solo-reachability score |

## Plan format (section of the report)

For each of the **top 3 channels per market**:
- **Why this channel**: the evidence, with `[E#]`.
- **Cost**: cash and hours per week. Mark these as `[假設]` (assumption) if they're estimates.
- **First experiment** (≤2 weeks): concrete steps.
- **Success threshold / kill threshold**: numbers decided now, marked `[門檻]` (threshold).
- **Messaging angle**: taken from review-mining verbatims and gaps.

Then add a **30-day sequence**: week 1 ASO and listing, week 2 community seeding, weeks 3–4 a paid test only if the free channels gave a signal.

Also list what **not** to do, and why, with evidence. Example: "Skip Meta ads: no monetization proof yet [E5]".

## After launch

When the user brings results (installs, conversion, ASA metrics), record them as tier S `own-experiment` rows. Re-rank the channels at the next `/research app` run.
