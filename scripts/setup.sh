#!/usr/bin/env bash
# One-time setup: prerequisite check, python deps, .env with a crawl4ai token, crawl4ai container. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

[ "$(uname)" = Darwin ] || echo "warning: built for macOS (BSD sed, launchd); other OSes need edits" >&2

missing=0
need() {  # need <cmd> <why> <install hint>
  command -v "$1" >/dev/null 2>&1 && return
  echo "missing: $1 — $2 (install: $3)" >&2
  missing=1
}
need uv      "python deps, scripts, hooks"  "brew install uv"
need npx     "DataForSEO MCP server"        "brew install node"
need openssl "generating CRAWL4AI_API_TOKEN" "ships with macOS"
need curl    "crawl4ai health check"         "ships with macOS"
need claude  "Claude Code CLI"               "https://docs.claude.com/en/docs/claude-code"
[ "$missing" = 0 ] || { echo "install the tools above, then re-run scripts/setup.sh" >&2; exit 1; }
[ -d "$HOME/.agents/skills/keyword-research" ] ||
  echo "note: global ASO skills missing — npx skills add eronred/aso-skills -g (see docs/operations.md › Moving to a new Mac)"
[ -d .claude/skills/product-marketing ] ||
  echo "note: marketingskills missing — run: npx skills experimental_install (restores them from skills-lock.json)"

uv sync -q
[ -f .env ] || cp .env.example .env
[ -f .agents/product-marketing.md ] || cp .agents/product-marketing.template.md .agents/product-marketing.md
[ -f config/tracking.json ] || cp config/tracking.example.json config/tracking.json

if ! grep -q '^CRAWL4AI_API_TOKEN=.\+' .env; then
  token="$(openssl rand -hex 32)"
  sed -i '' "s/^CRAWL4AI_API_TOKEN=.*/CRAWL4AI_API_TOKEN=${token}/" .env
  echo "generated CRAWL4AI_API_TOKEN in .env"
fi
set -a; source .env; set +a

# crawl4ai is optional: without Docker the free scripts and DataForSEO still work.
if ! command -v docker >/dev/null 2>&1; then
  echo "note: docker not installed — skipping crawl4ai (install OrbStack or Docker to enable it)"
elif ! docker info >/dev/null 2>&1; then
  echo "docker daemon not running — start OrbStack/Docker, then re-run scripts/setup.sh" >&2
  exit 1
else
  if docker ps -a --format '{{.Names}}' | grep -qx crawl4ai; then
    docker start crawl4ai >/dev/null
  else
    docker run -d --name crawl4ai -p 127.0.0.1:11235:11235 --shm-size=1g --restart unless-stopped \
      -e CRAWL4AI_API_TOKEN="$CRAWL4AI_API_TOKEN" unclecode/crawl4ai:0.9.2 >/dev/null
  fi
  for _ in $(seq 1 30); do
    curl -fs http://localhost:11235/health >/dev/null && break
    sleep 2
  done
  curl -fs http://localhost:11235/health && echo
fi

[ -n "${DATAFORSEO_LOGIN:-}" ] || echo "note: DATAFORSEO_LOGIN empty in .env — DataForSEO MCP will fail until you fill it"
echo "done. start Claude Code with: bin/claude-mr"
