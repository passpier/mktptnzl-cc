# Report template (`research/<slug>/report.md`)

What `hooks/check_report.py` enforces on this file:
- Every line that contains a number needs an `[E#]` citation.
- Numbers are allowed without citations under the Kill criteria / Validation experiments / Sources headings, and on lines tagged `[assumption]` or `[threshold]`.
- Every bullet under Conclusion needs ≥2 source_groups and a `Confidence:` label.
- Tier D is allowed only under Data gaps.

## Style guide

The reader is a solo developer deciding whether to spend the next two months on this. Write for them, not for the checker.
- **Answer first.** The verdict and its main reason come in the first bullet. Each section opens with its takeaway in one sentence, and the table or detail follows.
- **Plain, short sentences.** One idea per sentence. Prefer verbs to nouns ("banix added 500K installs in three weeks", not "banix demonstrates significant install momentum").
- **One citation group per sentence, at the end.** `… in three weeks [E236, E237].` Don't cite each clause.
- **Name a proxy once.** Say "install brackets are global and a proxy for momentum" once per report, then use the number plainly. No stacks of hedges.
- **Say what it means.** After a number, say why it matters for the decision, or drop the number.
- **Don't restate the rules** (tier definitions, how a criterion was read) inside the report. Put the reading of a borderline criterion in one short note under the kill-criteria table.
- **Length**: about 120–150 lines in quick mode. Tables ≤8 rows. Long evidence lives in `sources.md` and `evidence.jsonl`.

```markdown
# <App / idea>: market and marketing research — <YYYY-MM-DD>

> Mode: idea | app | niche · Depth: quick | deep · Market: US · Stores: App Store, Google Play · Sources: [sources.md](sources.md)

## Conclusion and confidence
- **Verdict: GO / PIVOT / NO-GO.** <one-sentence reason> [E3, E12]. Confidence: Med
- <finding 2: demand> [E5, E9]. Confidence: High
- <finding 3: competition / wedge> [E7, E14]. Confidence: Med
- <finding 4: money> [E8, E15]. Confidence: Low — flips if <evidence>

## Competitor map
<one-sentence takeaway>
| App | Store | Ratings / installs | Last update | Price | <wedge 1> | <wedge 2> |
|---|---|---|---|---|---|---|

## Demand
<one-sentence takeaway>
- In-store (App Store hints, search results) [E#]
- Web search (Google volume, Trends) [E#], or "not collected" with the reason
- Community (Reddit asks vs. self-promotion) [E#]

## What users complain about
<!-- review-mining; quick: top themes with counts and 1 quote each; deep: shares with CI -->

## Viability
<!-- idea: viability-check; app/niche: may be omitted -->
- **Unit economics**: <price> after <fee> needs <N> buyers a month for <target> [threshold]
- **Retention / frequency**: …
- **Buildability**: …
- **Moat**: new-entrant rate [E#], free alternatives [E#]

## What to build
<!-- idea mode only -->
- **MVP**: <scope, and what is deliberately left out>
- **Pricing**: <model and price point, anchored on competitor prices [E#]>
- **Later**: <features to phase in, and what evidence would justify each>

## Go-to-market
<!-- idea: lean-gtm short; app: lean-gtm full; niche: delete -->
1. **<Channel>**: why it fits [E#]; cost; first experiment; threshold [threshold]

## Risks
| Risk | Evidence | Impact | Mitigation |
|---|---|---|---|
<!-- include the auditor's strongest counterpoints here -->

## Kill criteria check
| Criterion (set before research) | Result | Triggered? |
|---|---|---|

## Data gaps
- <unknown>: cheapest way to get it, cost (tier D leads may appear only here [E#])

## Validation experiments
| # | Hypothesis | Setup | Cost | Duration | Success | Kill |
|---|---|---|---|---|---|---|
```
