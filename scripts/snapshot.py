"""Weekly competitor snapshots (free APIs) -> research/_tracking/<store>-<id>-<country>/<date>.json

  uv run scripts/snapshot.py take [--config config/tracking.json]
  uv run scripts/snapshot.py diff --app apple:866450515:tw [--slug <slug>]   # --slug records the velocity as evidence

A single snapshot cannot show momentum; rating-count velocity across snapshots is the cheapest
first-party proxy for download momentum. It is a proxy: report it as "評分增速", never as downloads.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from mr import ledger, stores
from mr.common import RESEARCH, ROOT, emit

TRACKING = RESEARCH / "_tracking"


def _key(store: str, app_id: str, country: str) -> Path:
    return TRACKING / f"{store}-{app_id}-{country}"


def fetch(store: str, app_id: str, country: str) -> dict:
    if store == "apple":
        return stores.apple_metrics(stores.apple_lookup(app_id, country))
    if store == "gplay":
        return stores.gplay_metrics(stores.gplay_app(app_id, country))
    raise ValueError(f"unknown store {store!r} (apple|gplay)")


def cmd_take(a):
    apps = json.loads(Path(a.config).read_text(encoding="utf-8"))["apps"]
    done, failed = [], []
    for app in apps:
        store, app_id, country = app["store"], str(app["id"]), app.get("country", "tw")
        try:
            m = fetch(store, app_id, country)
        except Exception as e:  # keep going; one delisted app must not stop the weekly run
            failed.append({"app": f"{store}:{app_id}:{country}", "error": str(e)})
            continue
        d = _key(store, app_id, country)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{date.today().isoformat()}.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
        done.append(f"{store}:{app_id}:{country}")
    emit({"snapshotted": done, "failed": failed})


def velocity(store: str, app_id: str, country: str) -> dict:
    files = sorted(_key(store, app_id, country).glob("*.json"))
    if len(files) < 2:
        raise SystemExit(f"need ≥2 snapshots for {store}:{app_id}:{country}, have {len(files)} — run `take` again later")
    points = [(date.fromisoformat(f.stem), json.loads(f.read_text(encoding="utf-8"))) for f in files]
    (d0, m0), (d1, m1) = points[0], points[-1]
    days = max((d1 - d0).days, 1)
    series = [{"date": d.isoformat(), "ratings": m.get("ratings"), "avg": m.get("avg_rating"),
               "version": m.get("version")} for d, m in points]
    out = {"name": m1.get("name"), "from": d0.isoformat(), "to": d1.isoformat(), "days": days,
           "ratings_delta": (m1.get("ratings") or 0) - (m0.get("ratings") or 0), "series": series}
    out["ratings_per_week"] = round(out["ratings_delta"] / days * 7, 1)
    if store == "gplay" and m1.get("real_installs") and m0.get("real_installs"):
        out["real_installs_per_week"] = round((m1["real_installs"] - m0["real_installs"]) / days * 7)
    return out


def cmd_diff(a):
    store, app_id, country = a.app.split(":")
    v = velocity(store, app_id, country)
    if a.slug:
        url = stores.apple_lookup_url(app_id, country) if store == "apple" else stores.gplay_url(app_id, country)
        v["evidence"] = ledger.add(
            a.slug, kind="rating", claim=f"{v['name']} {store} {country.upper()} 評分增速（{v['from']}→{v['to']}）",
            value={k: v[k] for k in v if k != "series"}, unit="ratings/week", tier="S", source_url=url,
            source_group=f"{store}-snapshots", method="scripts/snapshot.py diff (derived from dated snapshots)",
            data_as_of=v["to"], raw_path=str(_key(store, app_id, country).relative_to(ROOT)),
            note="proxy for download momentum, not downloads",
        )
    emit(v)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("take")
    t.add_argument("--config", default=str(ROOT / "config" / "tracking.json"))
    d = sub.add_parser("diff")
    d.add_argument("--app", required=True, help="store:id:country, e.g. apple:866450515:tw or gplay:cc.forestapp:tw")
    d.add_argument("--slug")
    a = ap.parse_args()
    {"take": cmd_take, "diff": cmd_diff}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
