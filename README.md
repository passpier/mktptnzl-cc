# marketing-research

A local Claude Code agent for researching an app's market potential and low-budget marketing (TW and US, App Store and Google Play).

Its main rule is that every number must come from a fresh, graded, first-party source. A hook blocks any report that breaks it.

## What problem this solves

A solo developer needs go/no-go and marketing answers for an app on less than US$10 a month. Desk research for that usually fails in four ways, and the project is built around blocking each one:

1. **Stale or secondhand numbers.** An LLM's memory, listicles, and news articles all count here.
2. **Confirmation bias.** You only find evidence for the idea you already like.
3. **No real download or revenue data.** That data is behind paid tools (Sensor Tower, data.ai) or not public at all.
4. **Research that never meets reality.** A report that stops at desk research.

## How it works

Each method answers one question. Its rule stays even if the skill or tool behind it is replaced. The full workflow (intake → kill criteria → plan → collect → synthesize → audit → report → experiments) lives in the `research` skill.

| Question | Method | Built here |
|---|---|---|
| Can I trust this number? | Every number is a ledger row with source tier S–D, a TTL, and an independence group, cited as `[E#]`. Tier-D and expired rows can't support a conclusion | `source-grading`, evidence ledger, report-checker hook |
| Am I fooling myself? | Kill criteria are written **before** collecting, so they can't move. A separate agent then argues the opposite case | `research`, `evidence-auditor` |
| Is the market worth it? | 5-axis score (Demand, Competition, Monetization, Gap, Solo-reachability) from live store data, not market-size reports. TW and US are scored separately | `opportunity-scan`, `store-collector` |
| What do users hate? | Complaint clusters, switching triggers, and verbatims from recent 1–3★ competitor reviews, labeled as a biased sample | `review-mining` |
| Is there demand? | In-store, web, and community signals are kept **separate** and never merged into one number | `demand-signals`, `web-collector` |
| How fast are competitors growing? | Proxies only, from [weekly snapshots](#optional-weekly-snapshots): rating and realInstalls velocity. Never a download or revenue estimate | `snapshot.py`, `source-grading` |
| How do I market it? | Top 3 channels, each backed by ledger evidence, with a cost, a first experiment, and a threshold | `lean-gtm` |
| What next? | Every report ends with 1–3 cheap experiments with success and kill thresholds | `research` |

## Upstream skills and tools

Only the evidence rules and workflow above are built here. Everything below comes from upstream projects, and any number it suggests still has to pass the ledger rules. When an upstream skill is updated, nothing here needs to change.

Project skills point to an upstream skill as the next step, and Claude loads it when that step runs. "When it runs" lists the `/research` modes that reach it (with the project skill in brackets). Every skill can also be used on its own, e.g. `/aso`.

| Source | Skill / component | When it runs | Used for |
|---|---|---|---|
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | `product-marketing` | Every mode, step 1 | Fill `.agents/product-marketing.md` |
| | `customer-research` | `idea`, `app`, `niche` (review-mining) | Turn review verbatims into voice-of-customer |
| | `aso` | `app` (lean-gtm) | App Store and Google Play listing audits. Chosen over aso-skills' `aso-audit` because it treats fetched listings as untrusted, reads `product-marketing.md`, and adjusts scoring for brand maturity |
| | `community-marketing` | `app` (lean-gtm) | PTT, Dcard, Reddit, Threads channel |
| | `directory-submissions`, `launch` | `app` (lean-gtm) | Directories and launch sites |
| | `pricing`, `paywalls` | `app` (lean-gtm) | Pricing and paywall channel |
| | `competitor-profiling`, `marketing-ideas`, `marketing-council` | Direct use only | Installed, but no project skill points to them |
| | `copywriting`, `marketing-psychology`, `free-tools`, `programmatic-seo` | — | **Referenced but not installed.** lean-gtm and review-mining give a short inline version instead |
| [eronred/aso-skills](https://github.com/eronred/aso-skills) | `keyword-research` | `idea`, `app`, `niche` (opportunity-scan, demand-signals, review-mining, lean-gtm) | Turn a keyword set into an ASO plan |
| | `competitor-analysis` | `idea`, `niche` (opportunity-scan, after a GO) | Deeper ASO competitor work |
| | `review-management` | `idea`, `app`, `niche` (review-mining) | Reply strategy for live apps |
| | `metadata-optimization`, `screenshot-optimization`, `android-aso`, `localization` | `app` (lean-gtm) | ASO channel |
| | `apple-search-ads` | `app` (lean-gtm) | Apple Search Ads channel |
| | `app-icon-optimization`, `app-launch`, `app-preview-video`, `in-app-events`, `seasonal-aso`, `ua-campaign` | Direct use only | Installed, but no project skill points to them |
| [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) | MCP server in local Docker | Every mode, step 4 (web-collector) | JS pages that WebFetch returns empty (Reddit and Dcard search, SPA pricing pages). **Optional**: falls back to WebSearch and WebFetch |
| [dataforseo/mcp-server-typescript](https://github.com/dataforseo/mcp-server-typescript) | DataForSEO MCP | Every mode, step 4 (web-collector, for demand-signals) | Google volume, Trends, SERP. The only paid source, capped at US$10 a month by hooks |
| [JoMingyu/google-play-scraper](https://github.com/JoMingyu/google-play-scraper) | Python library | Every mode, step 4 (store-collector → `scripts/gplay.py`) | Free Google Play search, details, reviews (there's no public Play API) |
| Apple iTunes Search API and RSS feeds | HTTP, no wrapper | Every mode, step 4 (store-collector → `scripts/apple.py`) | Free App Store search, lookups, charts, reviews, autocomplete hints |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | `npx skills` CLI | Setup | Installs and pins both skill libraries |

Where each library lives and how it's pinned: [operations](docs/operations.md#pinned-versions).

aso-skills caveats: volume and difficulty fields come only from the ledger ("ASO library score fields" in `source-grading/references/proxies.md`). The Apple keyword field is 100 **bytes**, not the 100 characters these skills say. `aso-router` and `aso-audit` are left out on purpose ([operations](docs/operations.md#moving-to-a-new-mac)).

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
> /research idea "台灣記帳 App"
```

**Always start with `bin/claude-mr`, not plain `claude`.** `.mcp.json` reads `${CRAWL4AI_API_TOKEN}` and `${DATAFORSEO_*}` from the environment, and only `bin/claude-mr` loads `.env`. With plain `claude`, those variables are empty: crawl4ai returns 401 and DataForSEO fails to authenticate, even though the container is healthy.

## Usage

| Command | Use for | Runs |
|---|---|---|
| `/research idea "<one-line idea>"` | Pre-build go / pivot / no-go | opportunity-scan → review-mining → demand-signals → lean-gtm (short: top 3 channels, no execution handoff) |
| `/research app <apple:id\|gplay:id>` | Marketing for a live app, including ASO | review-mining → demand-signals → lean-gtm (full) |
| `/research niche "<category or audience>"` | Hunting for gaps | opportunity-scan → review-mining |
| `/research refresh <slug>` | Re-fetch stale evidence and re-check the report | `ledger.py stale`, then the original methods |

For ASO or other execution work without a full study, call the upstream skill directly: `/aso` (listing audit), `/keyword-research`, `/metadata-optimization`, `/android-aso`, `/apple-search-ads`, or describe the task in plain words. Their volume and difficulty fields still come only from the ledger, so run `/research app <id>` first to fill it.

## Architecture at a glance

```
data sources, in order of preference (free first, paid second)
  1. scripts/*.py         free Apple / Google Play / PTT / HN  → research/<slug>/raw + evidence.jsonl
  2. DataForSEO MCP       npx, paid; PreToolUse hook enforces config/budget.json, PostToolUse logs cost
  3. crawl4ai MCP         Docker container on localhost:11235

credentials
  .env ──(bin/claude-mr exports)──▶ environment ──▶ .mcp.json ${VARS} ──▶ MCP servers
                                                  └▶ crawl4ai container (token set at docker run)
```

## Optional: weekly snapshots

App stores only show a competitor's *current* rating count and install bracket, and you can't backfill history. A weekly launchd job (Mondays 09:00) saves those values for the apps in `config/tracking.json`. After two or more weeks, the diff gives rating velocity (iOS) and realInstalls velocity (Android): the best free first-party proxy for a competitor's momentum. It costs US$0. Setup: [`config/launchd/README.md`](config/launchd/README.md).

## Example output

Each study writes `research/<slug>/report.md` with its evidence ledger. The author's test run (`tw-expense-tracker`: 17 evidence rows, free sources only, US$0, passes the checker) isn't in this repo.

`research/` is gitignored (raw scrapes contain third-party content), so studies exist only on the machine that ran them. Back them up yourself. `.agents/product-marketing.md` and `config/tracking.json` are also local: `scripts/setup.sh` creates them from the committed templates.

## Operations

Monthly check, pinned versions, swapping components, backups, moving to a new Mac, and troubleshooting: [`docs/operations.md`](docs/operations.md).
