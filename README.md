# marketing-research

A local Claude Code agent for researching an app's market potential and low-budget marketing (US by default, TW optional; App Store and Google Play). Reports are written in English.

Its main rule is that every number must come from a fresh, graded, first-party source. A hook blocks any report that breaks it.

## What problem this solves

A solo developer needs go/no-go and marketing answers for an app. Desk research for that usually fails in four ways, and the project is built around blocking each one:

1. **Stale or secondhand numbers.** An LLM's memory, listicles, and news articles all count here.
2. **Confirmation bias.** You only find evidence for the idea you already like.
3. **No real download or revenue data.** That data is behind paid tools (Sensor Tower, data.ai) or not public at all.
4. **Research that never meets reality.** A report that stops at desk research.

## How it works

Each method answers one question. Its rule stays even if the skill or tool behind it is replaced. The full workflow (intake, including founder assumptions → kill criteria → plan, collector check, and cost estimate → discovery sweep → collect → synthesize → audit → report → experiments) lives in the `research` skill. Studies run in **quick** depth by default (about 30 minutes); add `--deep` for the full procedure.

| Question | Method | Built here |
|---|---|---|
| Can I trust this number? | Every number is a ledger row with source tier S–D, a TTL, and an independence group, cited as `[E#]`. Tier-D and expired rows can't support a conclusion | `source-grading`, evidence ledger, report-checker hook |
| Am I fooling myself? | Kill criteria are written **before** collecting, so they can't move. A separate agent then argues the opposite case | `research`, `evidence-auditor` |
| Is the market worth it? | 5-axis score (Demand, Competition, Monetization, Gap, Solo-reachability) from live store data, not market-size reports. Each market in scope is scored separately | `opportunity-scan`, `store-collector` |
| Is it worth building? | Break-even thresholds instead of LTV or revenue guesses: price, commission, and CPI turn into a max churn or min conversion. Also covers retention and use frequency from review codes, build risk, new-entrant rate, and a platform and licensing risk register. A cell with no data names the experiment that will fill it | `viability-check`, `scripts/econ.py` |
| What do users hate? | Complaint clusters, switching triggers, and verbatims from recent 1–3★ competitor reviews, labeled as a biased sample. `tenure`, `quit`, and `price` codes feed the viability check | `review-mining` |
| Is there demand? | In-store, web, and community signals (Reddit, HN; PTT and Dcard for TW; organic asks split from promo posts) are kept **separate** and never merged into one number | `demand-signals`, `web-collector`, `community.py` |
| How fast are competitors growing? | Proxies only, from [weekly snapshots](#optional-weekly-snapshots): rating and realInstalls velocity. Never a download or revenue estimate | `snapshot.py`, `source-grading` |
| How do I market it? | Top 3 channels, each backed by ledger evidence, with a cost, a first experiment, and a threshold | `lean-gtm` |
| What next? | Every report ends with 1–3 cheap experiments with success and kill thresholds. Thresholds come from `econ.py breakeven`, and `econ.py power` / `asa-check` confirm the budget and sample can actually read them | `research`, `scripts/econ.py` |

## Upstream skills and tools

Only the evidence rules and workflow above are built here. Everything below comes from upstream projects, and any number it suggests still has to pass the ledger rules. When an upstream skill is updated, nothing here needs to change.

Project skills point to an upstream skill as the next step, and Claude loads it when that step runs. "When it runs" lists the `/research` modes that reach it (with the project skill in brackets). Every skill can also be used on its own, e.g. `/aso`.

| Source | Skill / component | When it runs | Used for |
|---|---|---|---|
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | `product-marketing` | Every mode, step 1 | Fill `.agents/product-marketing.md` |
| | `customer-research` | `idea`, `app`, `niche` (review-mining) | Turn review verbatims into voice-of-customer |
| | `aso` | `app` (lean-gtm) | App Store and Google Play listing audits. Chosen over aso-skills' `aso-audit` because it treats fetched listings as untrusted, reads `product-marketing.md`, and adjusts scoring for brand maturity |
| | `community-marketing` | `app` (lean-gtm) | Reddit, Threads (PTT, Dcard for TW) channel |
| | `directory-submissions`, `launch` | `app` (lean-gtm) | Directories and launch sites |
| | `pricing`, `paywalls` | `idea` (viability-check), `app` (lean-gtm) | Willingness-to-pay interview questions and paywall placement; pricing and paywall channel |
| | `competitor-profiling`, `marketing-ideas`, `marketing-council` | Direct use only | Installed, but no project skill points to them |
| | `copywriting`, `marketing-psychology`, `free-tools`, `programmatic-seo` | — | **Referenced but not installed.** lean-gtm and review-mining give a short inline version instead |
| [eronred/aso-skills](https://github.com/eronred/aso-skills) | `keyword-research` | `idea`, `app`, `niche` (opportunity-scan, demand-signals, review-mining, lean-gtm) | Turn a keyword set into an ASO plan |
| | `competitor-analysis` | `idea`, `niche` (opportunity-scan, after a GO) | Deeper ASO competitor work |
| | `review-management` | `idea`, `app`, `niche` (review-mining) | Reply strategy for live apps |
| | `metadata-optimization`, `screenshot-optimization`, `android-aso`, `localization` | `app` (lean-gtm) | ASO channel |
| | `apple-search-ads` | `app` (lean-gtm) | Apple Search Ads channel |
| | `app-icon-optimization`, `app-launch`, `app-preview-video`, `in-app-events`, `seasonal-aso`, `ua-campaign` | Direct use only | Installed, but no project skill points to them |
| [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) | MCP server in local Docker | Every mode, step 4 (web-collector) | JS pages that WebFetch returns empty (Dcard search, SPA pricing pages). **Optional**: falls back to WebSearch and WebFetch |
| [dataforseo/mcp-server-typescript](https://github.com/dataforseo/mcp-server-typescript) | DataForSEO MCP | Every mode, step 4 (web-collector, for demand-signals) | Google volume, Trends, SERP. The only paid source, capped at US$10 a month by hooks |
| [JoMingyu/google-play-scraper](https://github.com/JoMingyu/google-play-scraper) | Python library | Every mode, step 4 (store-collector → `scripts/gplay.py`) | Free Google Play search, details, reviews (there's no public Play API) |
| Apple iTunes Search API and RSS feeds | HTTP, no wrapper | Every mode, step 4 (store-collector → `scripts/apple.py`) | Free App Store search, lookups, charts, reviews, autocomplete hints |
| Reddit search RSS feed and [Arctic Shift](https://arctic-shift.photon-reddit.com) archive | HTTP, no wrapper | Every mode, step 4 (web-collector → `scripts/community.py reddit*`) | Free thread counts with an ask/promo split, which apps get recommended, subreddit size and self-promo rules. reddit.com JSON blocks simple clients. Arctic rows are tier S only after a permalink check on reddit.com |
| PTT web and HN Algolia API | HTTP, no wrapper | Every mode, step 4 (web-collector → `scripts/community.py ptt\|hn`) | Free community thread counts |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | `npx skills` CLI | Setup | Installs and pins both skill libraries |

Where each library lives and how it's pinned: [operations](docs/operations.md#pinned-versions).

## Prerequisites

macOS only (setup uses BSD `sed`; the optional weekly job uses launchd).

| Tool | Required? |
|---|---|
| [Claude Code](https://docs.claude.com/en/docs/claude-code) | Yes |
| [uv](https://docs.astral.sh/uv/) (runs the scripts and **every hook**; hooks fail if uv isn't on PATH) | Yes |
| Node.js (`npx`), for the DataForSEO MCP server and the skills CLI | Yes for skills; DataForSEO is optional |
| OrbStack or Docker, for crawl4ai | Optional |
| DataForSEO API login (<https://app.dataforseo.com/api-access>) | Optional |
| aso-skills in `~/.agents/skills` | Recommended |

`scripts/setup.sh` checks all of these and tells you what's missing.

## Quickstart

```bash
npx skills experimental_install  # restores the marketingskills subset pinned in skills-lock.json (not committed)
scripts/setup.sh           # checks prerequisites, uv sync, creates .env + token and local config from templates, starts crawl4ai if Docker is present
$EDITOR .env               # optional: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD (API credentials, not your site login)
bin/claude-mr              # start Claude Code with .env loaded
> /research idea "habit tracker with streak sharing"
```

**Always start with `bin/claude-mr`, not plain `claude`.** `.mcp.json` reads `${CRAWL4AI_API_TOKEN}` and `${DATAFORSEO_*}` from the environment, and only `bin/claude-mr` loads `.env`. With plain `claude`, those variables are empty: crawl4ai returns 401 and DataForSEO fails to authenticate, even though the container is healthy.

## Usage

| Command | Use for | Runs |
|---|---|---|
| `/research idea "<one-line idea>" [--deep]` | Pre-build go / pivot / no-go | opportunity-scan → review-mining → demand-signals → viability-check → lean-gtm (short: top 3 channels, no execution handoff) |
| `/research app <apple:id\|gplay:id> [--deep]` | Marketing for a live app, including ASO | review-mining → demand-signals → lean-gtm (full) |
| `/research niche "<category or audience>" [--deep]` | Hunting for gaps | opportunity-scan → review-mining |
| `/research refresh <slug>` | Re-fetch stale evidence and re-check the report | `ledger.py stale`, then the original methods |

### Examples

```
> /research niche "music apps for practicing musicians"                 # find gaps in the US
> /research idea "ear training app, US first, subscription"             # go / pivot / no-go on the gap you picked
> /research idea "expense tracker app for Taiwan, TW market" --deep    # TW only when you ask for it
> /research app apple:<your app id>                                     # marketing and ASO for a live app
> /research refresh us-ear-training                                     # re-fetch expired rows, re-check the report
```

The argument can be English or Chinese. The report is always in English. When TW is in scope, its search terms are agreed at intake and searched in zh-TW.

A typical session goes like this:

1. **Intake.** Up to 3 questions (5 in deep): your unfair advantage, monetization, and time budget. In `idea` mode it also asks for your revenue target, what an hour of your time is worth, your tech stack, and where the content comes from. Answers are recorded in `brief.md` as `[assumption]`.
2. **Kill criteria.** Three default go/no-go thresholds (saturation, monetization, demand), filled in for the idea, are written to `brief.md`; deep mode negotiates 3–5. You confirm them before any data is fetched.
3. **Plan.** A list of fetches, a collector health check (e.g. crawl4ai down), and a DataForSEO cost estimate. Answering "free only" is fine; the gaps go under Data gaps.
4. **Collect.** `web-collector` first runs a discovery web sweep (new competitors, shutdowns, business and policy signals; every lead is verified at its origin). Then `store-collector` and `web-collector` run in parallel and write `raw/` and `evidence.jsonl`.
5. **Audit.** `evidence-auditor` argues the opposite case once; its points are fixed or folded into Risks.
6. **Report.** `report.md` (answer first, about 150 lines in quick mode, with a What to build section) is saved only once the checker hook passes it. Cited sources go to `sources.md`.
7. **Experiments.** 1–3, each with success and kill thresholds you can actually read on your budget.

Useful outside a study:

```bash
uv run scripts/ledger.py stale <slug>   # rows past their TTL
uv run scripts/ledger.py costs          # DataForSEO spend this month
uv run scripts/econ.py breakeven --price 4.99 --period month --commission 0.15 --cpi 2   # max churn / min conversion
```

For ASO or other execution work without a full study, call the upstream skill directly: `/aso` (listing audit), `/keyword-research`, `/metadata-optimization`, `/android-aso`, `/apple-search-ads`, or describe the task in plain words. Their volume and difficulty fields still come only from the ledger, so run `/research app <id>` first to fill it.

## Architecture at a glance

```
data sources, in order of preference (free first, paid second)
  1. scripts/*.py         free Apple / Google Play / Reddit (RSS + Arctic Shift) / HN / PTT
                          → research/<slug>/raw + evidence.jsonl
  2. DataForSEO MCP       npx, paid; PreToolUse hook enforces config/budget.json, PostToolUse logs cost
  3. crawl4ai MCP         Docker container on localhost:11235

local only (no fetch, no ledger rows)
  scripts/econ.py         break-even thresholds, A/B power, Apple Search Ads readability

guardrails (hooks in .claude/settings.json)
  check_report.py         PostToolUse Write|Edit on research/*/report.md: blocks uncited, stale, or tier-D claims;
                          warns when an idea report has no Viability section
  dfs_budget_guard.py     PreToolUse on DataForSEO: blocks calls over the monthly cap or on blocked endpoints
  dfs_cost_log.py         PostToolUse on DataForSEO: logs actual cost

credentials
  .env ──(bin/claude-mr exports)──▶ environment ──▶ .mcp.json ${VARS} ──▶ MCP servers
                                                  └▶ crawl4ai container (token set at docker run)
```

## Optional: weekly snapshots

App stores only show a competitor's *current* rating count and install bracket, and you can't backfill history. A weekly launchd job (Mondays 09:00) saves those values for the apps in `config/tracking.json`. After two or more weeks, the diff gives rating velocity (iOS) and realInstalls velocity (Android): the best free first-party proxy for a competitor's momentum. It costs US$0. Setup: [`config/launchd/README.md`](config/launchd/README.md).

## Example output

Each study writes `research/<slug>/report.md` with its evidence ledger. The author's runs aren't in this repo. One example is a `niche` scan (`music-app-niche`, about 570 evidence rows) that picked a gap, followed by an `idea` study on that gap (`us-ear-training`, about 610 rows, including the Viability section). Both used free sources only, cost US$0, and pass the checker.

`research/` is gitignored (raw scrapes contain third-party content), so studies exist only on the machine that ran them. Back them up yourself. `.agents/product-marketing.md` and `config/tracking.json` are also local: `scripts/setup.sh` creates them from the committed templates.

## Operations

Monthly check, pinned versions, swapping components, backups, moving to a new Mac, and troubleshooting: [`docs/operations.md`](docs/operations.md).
