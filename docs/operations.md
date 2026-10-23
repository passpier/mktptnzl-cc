# Operations

Running and maintaining the agent. For what the project is and why it's built this way, see the [README](../README.md).

## Monthly check (5 minutes)

Most failures here are silent: the snapshot job stops, the crawl4ai container dies or its token drifts, evidence expires. Nothing errors until a study comes out thin. This checklist catches that.

```bash
uv run scripts/ledger.py costs                 # DataForSEO spend this month (resets each calendar month)
uv run scripts/ledger.py stale <slug>          # evidence past its TTL; refresh with /research refresh <slug>
curl -fs http://localhost:11235/health         # crawl4ai alive?
tail research/_tracking/snapshot.log           # weekly snapshot job ran?
launchctl list | grep marketing-research       # snapshot job loaded? (2nd column = last exit code)
uv run pytest
```

## Weekly snapshots

See [`config/launchd/README.md`](../config/launchd/README.md). In short: `scripts/install-launchd.sh install`. The plist is rendered from a template with this machine's `uv` path and repo path, so **re-run install after moving the repo or reinstalling uv**.

## Pinned versions

Upgrade on purpose, one at a time, then run `uv run pytest` and one small `/research`.

| What | Pinned in | How to upgrade |
|---|---|---|
| crawl4ai image (`unclecode/crawl4ai:0.9.2`) | `scripts/setup.sh` | Edit the tag, run `docker rm -f crawl4ai`, re-run `scripts/setup.sh`. Check that the MCP tool names (`md`, `html`, `crawl`, `screenshot`) still match `.claude/agents/web-collector.md` |
| DataForSEO MCP (`dataforseo-mcp-server@3.1.3`) | `.mcp.json` | Edit the version, restart `bin/claude-mr`. Check that the tool is still named `api_request`, because the hooks match on it in `.claude/settings.json` |
| DataForSEO unit prices | `config/budget.json` `estimates` | Compare with <https://dataforseo.com/pricing>. Actual costs from responses are logged anyway, but estimates gate calls *before* they run |
| marketingskills subset | `skills-lock.json` | `npx skills update -p`, or edit and run `npx skills experimental_install` |
| Global ASO library | `~/.agents/.skill-lock.json` (outside the repo) | `npx skills update -g` |
| Python deps | `pyproject.toml` / `uv.lock` | `uv lock --upgrade && uv run pytest` |

## Updating skills or swapping components

Principle: **swap tools, keep the rules.** `source-grading`, the ledger format, and `hooks/check_report.py` are the contract. Every new tool has to write ledger rows with a tier, URL, group, and method.

| Change | Files to touch |
|---|---|
| A marketingskills or ASO skill updated | Run the update (see [Pinned versions](#pinned-versions)). If it now suggests numbers, the ledger rules still apply. Nothing else changes, because project skills only *delegate* to them by name (`lean-gtm`, the agent instructions' skill ecosystem list) |
| Replace crawl4ai with another crawler | `.mcp.json` (server), `.claude/settings.json` (`enabledMcpjsonServers`, permissions), `.claude/agents/web-collector.md` (`tools:` line, `--method` examples), `.claude/skills/source-grading/references/{tiers,proxies}.md` and `demand-signals/SKILL.md` (method names), `scripts/setup.sh` (container) |
| Replace or add a paid API | `config/budget.json` (estimates, blocked endpoints), `.claude/settings.json` (hook `matcher` on the new tool name), `hooks/dfs_budget_guard.py` / `dfs_cost_log.py` (cost parsing), `.claude/skills/research/references/dataforseo.md` |
| Add a free data source | New `scripts/<name>.py` that writes ledger rows through `mr/ledger.py`, like `scripts/community.py`. Add it to the permissions in `.claude/settings.json`, to `store-collector` or `web-collector`, and to `source-grading/references/proxies.md` if it's a proxy |
| Change a freshness or tier rule | `mr/ledger.py` (TTL policy), `.claude/skills/source-grading/`, and `tests/test_grading.py` |
| Add a market beyond US (and optional TW) | The agent instructions (`CLAUDE.md`), `research` skill (defaults), and `mr/stores.py` (`STOREFRONTS`, `GPLAY_LANG`), which limit the scripts' `--country` choices |

## What enforces the rules

| Mechanism | File |
|---|---|
| Source tiers S/A/B/C/D, TTL by data kind, independence | `.claude/skills/source-grading/` and `mr/ledger.py` |
| Report validator (PostToolUse hook) | `hooks/check_report.py` → `mr/report_check.py` |
| DataForSEO monthly cap US$10, blocked endpoints | `hooks/dfs_budget_guard.py` and `config/budget.json` |
| Cost log | `hooks/dfs_cost_log.py` → `research/_costs.jsonl` |

Run the tests with `uv run pytest`.

## Backups

`research/` is gitignored. Back it up yourself (Time Machine, or `rsync` to a cloud folder), especially:
- `research/_costs.jsonl`: the budget guard's memory. Losing it resets this month's spend to US$0 as far as the guard knows.
- `research/<slug>/evidence.jsonl` and `raw/`: you can't re-fetch past snapshots of store data.
- `research/_tracking/`: weekly snapshots. Velocity needs history.

## Moving to a new Mac

1. Install the [prerequisites](../README.md#prerequisites).
2. `git clone` the repo. The path can be anything; nothing in the repo hardcodes it.
3. Copy from the old Mac:
   - `.env`. Or skip it: setup generates a new crawl4ai token, but you re-enter the DataForSEO credentials.
   - the whole `research/` folder, including `_costs.jsonl`.
   - `.agents/product-marketing.md` and `config/tracking.json` (gitignored; otherwise setup recreates them as empty templates).
4. Restore skills:
   ```bash
   npx skills experimental_install              # project marketingskills, from skills-lock.json
   npx skills add eronred/aso-skills -g          # global ASO library (pick the skills; -l lists them).
                                                 # Leave out aso-router and aso-audit (see CLAUDE.md)
   ```
5. `scripts/setup.sh`
6. `scripts/install-launchd.sh install` (only if you want the weekly snapshots)
7. `bin/claude-mr`, then `uv run pytest`, then `/research refresh <slug>` on one study as a smoke test.

## Troubleshooting

| Symptom | Cause → fix |
|---|---|
| crawl4ai MCP `401` | Started with plain `claude` → quit and use `bin/claude-mr`. Or `.env` token changed after the container was created (the token is set at `docker run`) → `docker rm -f crawl4ai && scripts/setup.sh` |
| crawl4ai MCP can't connect | OrbStack/Docker not running. The container has `--restart unless-stopped`, so it comes back once Docker starts. Check with `docker ps --filter name=crawl4ai` |
| DataForSEO auth error | `.env` empty, or holds the website login instead of the API login from api-access. Restart `bin/claude-mr` after editing |
| DataForSEO call denied or asks for approval | The budget hook is working as intended (cap, per-call threshold, or blocked endpoint in `config/budget.json`). Don't route around it |
| `apple.py reviews` returns 0 reviews for every app | The Apple reviews RSS feed sometimes answers 200 with no entries for all apps. The script still writes an n=0 row, which looks fresh, so a refresh skips it. Check one well-known app first; if it's empty too, ignore n=0 rows when deciding what to refetch, use Google Play reviews, and note the gap under 資料缺口 |
| Reddit returns 403 or 429 | reddit.com JSON and old.reddit block simple clients (403): use `community.py reddit*`, never a crawl. The default `--backend rss` allows about 1 search per 30s (429 if faster), so run it in the background. If Arctic Shift full-text search keeps returning "Timeout. Maybe slow down a bit", stay on the RSS backend. PullPush refuses agents (429) |
| Hook errors mentioning `uv` | `uv` not on the PATH that Claude Code inherits. Fix your shell profile |
| `report.md` save blocked | `hooks/check_report.py` found uncited, stale, or tier-D-supported claims. Fix the claims, or move them to Data gaps |
| Weekly snapshot not running | `launchctl list \| grep marketing-research`. Re-run `scripts/install-launchd.sh install` if uv or the repo moved. Read `research/_tracking/snapshot.log` |
