# Weekly competitor snapshots (optional)

The snapshots use free Apple and Google Play data, so they cost US$0. After ≥2 weekly points, `scripts/snapshot.py diff` gives rating velocity (iOS) and realInstalls velocity (Android). These are the best free first-party proxies for download momentum.

`snapshot.plist.template` has no machine-specific paths. `scripts/install-launchd.sh` fills in this machine's `uv` and repo path, so re-run `install` after moving the repo, reinstalling uv, or switching Macs.

```bash
scripts/install-launchd.sh install     # runs Mondays 09:00 while the Mac is awake; missed runs fire on wake
scripts/install-launchd.sh run-now     # run once now and tail research/_tracking/snapshot.log
scripts/install-launchd.sh render      # print the rendered plist without installing
scripts/install-launchd.sh uninstall
launchctl list | grep marketing-research   # is it loaded? (2nd column = last exit code)
```

The tracked apps are listed in `config/tracking.json` (gitignored; `scripts/setup.sh` creates it from `config/tracking.example.json`). The store-collector agent appends competitors to it during `/research`.
