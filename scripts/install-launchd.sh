#!/usr/bin/env bash
# Weekly snapshot LaunchAgent: renders config/launchd/snapshot.plist.template with this machine's uv and repo path.
# Re-run `install` after moving the repo, reinstalling uv, or switching Macs.
#   scripts/install-launchd.sh install | uninstall | run-now | render
set -euo pipefail
cd "$(dirname "$0")/.."

label=com.marketing-research.snapshot
root="$(pwd)"
dest="$HOME/Library/LaunchAgents/$label.plist"

render() {
  local uv
  uv="$(command -v uv)" || { echo "uv not found on PATH" >&2; exit 1; }
  sed -e "s|__UV__|$uv|g" -e "s|__ROOT__|$root|g" config/launchd/snapshot.plist.template
}

case "${1:-}" in
  render)  render ;;
  install)
    mkdir -p research/_tracking "$(dirname "$dest")"
    launchctl unload "$dest" 2>/dev/null || true
    render >"$dest"
    plutil -lint "$dest" >/dev/null
    launchctl load "$dest"
    echo "installed $dest (uv: $(command -v uv), repo: $root)"
    ;;
  uninstall)
    launchctl unload "$dest" 2>/dev/null || true
    rm -f "$dest"
    echo "removed $dest"
    ;;
  run-now)
    launchctl start "$label"
    sleep 5
    tail -n 20 research/_tracking/snapshot.log
    ;;
  *) echo "usage: $0 install | uninstall | run-now | render" >&2; exit 2 ;;
esac
