"""Google Play free first-party data -> raw cache + evidence ledger (tier S).

  uv run scripts/gplay.py app     <slug> --id cc.forestapp [--country us]
  uv run scripts/gplay.py search  <slug> --term "habit tracker" [--country us] [--n 30]
  uv run scripts/gplay.py reviews <slug> --id cc.forestapp [--country us] [--n 300] [--max-stars 3]

Language follows country (tw -> zh-TW, us -> en). Google Play has no public chart feed;
use DataForSEO app_data/google/app_list for charts if needed.
"""

import argparse
import sys
from datetime import date

from mr import ledger, stores
from mr.common import emit, save_raw

GROUP = "google-play"


def cmd_app(a):
    r = stores.gplay_app(a.id, a.country)
    raw_obj = {k: v for k, v in r.items() if k not in ("comments", "screenshots", "descriptionHTML")}
    raw = save_raw(a.slug, f"gplay_app_{a.id}_{a.country}", raw_obj)
    m = stores.gplay_metrics(r)
    common = dict(tier="S", source_url=stores.gplay_url(a.id, a.country), source_group=GROUP,
                  method="scripts/gplay.py app", data_as_of=date.today().isoformat(), raw_path=raw)
    cc = a.country.upper()
    ids = {
        "rating": ledger.add(a.slug, kind="rating", claim=f"{m['name']} Google Play {cc} rating count / average",
                             value={"ratings": m["ratings"], "reviews": m["reviews"], "avg": m["avg_rating"]},
                             unit="ratings", **common),
        "installs": ledger.add(a.slug, kind="installs", claim=f"{m['name']} Google Play installs (global)",
                               value={"bracket": m["installs"], "real_installs": m["real_installs"]}, unit="installs",
                               note="real_installs is Google's own rounded figure exposed in page data; global, not per-country",
                               **common),
        "metadata": ledger.add(a.slug, kind="metadata", claim=f"{m['name']} Google Play {cc} version and release info",
                               value={k: m[k] for k in ("version", "updated", "released", "genre", "developer", "contains_ads")},
                               **common),
        "price": ledger.add(a.slug, kind="price", claim=f"{m['name']} Google Play {cc} price and IAP range",
                            value={k: m[k] for k in ("price", "currency", "free", "offers_iap", "iap_range")}, **common),
    }
    emit({"evidence": ids, "metrics": m, "raw": raw})


def cmd_search(a):
    res = stores.gplay_search(a.term, a.country, a.n)
    slim = [{"pos": i, "id": x["appId"], "name": x["title"], "avg": x.get("score"), "installs": x.get("installs"),
             "free": x.get("free"), "developer": x.get("developer")} for i, x in enumerate(res, 1)]
    raw = save_raw(a.slug, f"gplay_search_{a.country}_{a.term}", slim)
    eid = ledger.add(a.slug, kind="serp", claim=f"Google Play search '{a.term}' {a.country.upper()} results", value=slim,
                     tier="S", source_url=f"https://play.google.com/store/search?q={a.term}&c=apps&gl={a.country}",
                     source_group=GROUP, method="scripts/gplay.py search", data_as_of=date.today().isoformat(),
                     raw_path=raw, note="scraped search order; may be personalised/unstable")
    emit({"evidence": eid, "results": slim, "raw": raw})


def cmd_reviews(a):
    rows = stores.gplay_reviews(a.id, a.country, a.n, a.max_stars)
    raw = save_raw(a.slug, f"gplay_reviews_{a.id}_{a.country}", rows)
    s = stores.review_summary(rows)
    s["filter"] = f"1-{a.max_stars} stars" if a.max_stars else "all stars"
    eid = ledger.add(a.slug, kind="review", claim=f"Google Play {a.country.upper()} {a.id} latest review sample ({s['filter']})",
                     value=s, unit="reviews", tier="S", source_url=stores.gplay_url(a.id, a.country),
                     source_group=GROUP, method="scripts/gplay.py reviews", data_as_of=s["to"], raw_path=raw,
                     note="star-filtered samples are not representative of overall sentiment")
    emit({"evidence": eid, "summary": s, "raw": raw})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("app", "search", "reviews"):
        p = sub.add_parser(name)
        p.add_argument("slug")
        p.add_argument("--country", default="us", choices=sorted(stores.GPLAY_LANG))
        if name in ("app", "reviews"):
            p.add_argument("--id", required=True)
    sub.choices["search"].add_argument("--term", required=True)
    sub.choices["search"].add_argument("--n", type=int, default=30)
    sub.choices["reviews"].add_argument("--n", type=int, default=300)
    sub.choices["reviews"].add_argument("--max-stars", type=int, choices=range(1, 6))
    a = ap.parse_args()
    {"app": cmd_app, "search": cmd_search, "reviews": cmd_reviews}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
