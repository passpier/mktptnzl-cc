"""Apple App Store free first-party data -> raw cache + evidence ledger (tier S).

  uv run scripts/apple.py lookup  <slug> --id 866450515 [--country tw]
  uv run scripts/apple.py search  <slug> --term 記帳 [--country tw] [--limit 25]
  uv run scripts/apple.py chart   <slug> --feed top-free|top-paid|top-grossing [--genre 6015] [--country tw] [--limit 100]
  uv run scripts/apple.py reviews <slug> --id 866450515 [--country tw] [--pages 3]
  uv run scripts/apple.py hints   <slug> --term 記帳 [--country tw]

Genre ids: 6015 Finance, 6007 Productivity, 6013 Health & Fitness, 6017 Education, 6012 Lifestyle,
6002 Utilities, 6005 Social Networking, 6023 Food & Drink, 6020 Medical, 6014 Games.
"""

import argparse
import sys
from datetime import date

from mr import ledger, stores
from mr.common import emit, save_raw

GROUP = "apple"


def cmd_lookup(a):
    r = stores.apple_lookup(a.id, a.country)
    raw = save_raw(a.slug, f"apple_lookup_{a.id}_{a.country}", r)
    m = stores.apple_metrics(r)
    url = stores.apple_lookup_url(a.id, a.country)
    today = date.today().isoformat()
    common = dict(tier="S", source_url=url, source_group=GROUP, method="scripts/apple.py lookup",
                  data_as_of=today, raw_path=raw)
    ids = {
        "rating": ledger.add(a.slug, kind="rating", claim=f"{m['name']} App Store {a.country.upper()} 評分數/平均評分",
                             value={"ratings": m["ratings"], "avg": m["avg_rating"]}, unit="ratings", **common),
        "metadata": ledger.add(a.slug, kind="metadata", claim=f"{m['name']} App Store {a.country.upper()} 版本與上架資訊",
                               value={k: m[k] for k in ("version", "current_version_date", "first_release", "genre", "seller")},
                               **common),
        "price": ledger.add(a.slug, kind="price", claim=f"{m['name']} App Store {a.country.upper()} 售價",
                            value={"price": m["price"], "currency": m["currency"], "formatted": m["formatted_price"]},
                            **common),
    }
    emit({"evidence": ids, "metrics": m, "raw": raw})


def cmd_search(a):
    results = stores.apple_search(a.term, a.country, a.limit)
    raw = save_raw(a.slug, f"apple_search_{a.country}_{a.term}", results)
    top = [stores.apple_metrics(r) for r in results]
    slim = [{"pos": i, "id": t["id"], "name": t["name"], "ratings": t["ratings"], "avg": t["avg_rating"],
             "updated": t["current_version_date"], "price": t["price"]} for i, t in enumerate(top, 1)]
    eid = ledger.add(a.slug, kind="serp", claim=f"iTunes Search「{a.term}」{a.country.upper()} 結果", value=slim,
                     tier="S", source_url=f"https://itunes.apple.com/search?term={a.term}&country={a.country}&entity=software",
                     source_group=GROUP, method="scripts/apple.py search", data_as_of=date.today().isoformat(),
                     raw_path=raw, note="iTunes Search API order approximates but is not identical to in-app App Store search ranking")
    emit({"evidence": eid, "results": slim, "raw": raw})


def cmd_chart(a):
    url, rows = stores.apple_chart(a.feed, a.country, a.limit, a.genre)
    raw = save_raw(a.slug, f"apple_chart_{a.feed}_{a.genre or 'all'}_{a.country}", rows)
    label = f"{a.feed}{' genre ' + str(a.genre) if a.genre else ''}"
    eid = ledger.add(a.slug, kind="ranking", claim=f"App Store {a.country.upper()} {label} 榜單", value=rows,
                     tier="S", source_url=url, source_group=GROUP, method="scripts/apple.py chart",
                     data_as_of=date.today().isoformat(), raw_path=raw)
    emit({"evidence": eid, "chart": rows[:25], "total": len(rows), "raw": raw})


def cmd_reviews(a):
    url, rows = stores.apple_reviews(a.id, a.country, a.pages)
    raw = save_raw(a.slug, f"apple_reviews_{a.id}_{a.country}", rows)
    s = stores.review_summary(rows)
    eid = ledger.add(a.slug, kind="review", claim=f"App Store {a.country.upper()} app {a.id} 最新評論樣本", value=s,
                     unit="reviews", tier="S", source_url=url, source_group=GROUP, method="scripts/apple.py reviews",
                     data_as_of=s["to"], raw_path=raw,
                     note="RSS returns only the most recent ≤500 reviews; review samples skew negative")
    emit({"evidence": eid, "summary": s, "raw": raw})


def cmd_hints(a):
    url, hints = stores.apple_hints(a.term, a.country)
    raw = save_raw(a.slug, f"apple_hints_{a.country}_{a.term}", hints)
    eid = ledger.add(a.slug, kind="serp", claim=f"App Store {a.country.upper()} 搜尋提示「{a.term}」", value=hints,
                     tier="S", source_url=url, source_group="apple-hints", method="scripts/apple.py hints",
                     data_as_of=date.today().isoformat(), raw_path=raw,
                     note="unofficial endpoint; order hints at popularity but carries no volume")
    emit({"evidence": eid, "hints": hints, "raw": raw})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("lookup", "search", "chart", "reviews", "hints"):
        p = sub.add_parser(name)
        p.add_argument("slug")
        p.add_argument("--country", default="tw", choices=sorted(stores.STOREFRONTS))
        if name in ("lookup", "reviews"):
            p.add_argument("--id", required=True)
        if name in ("search", "hints"):
            p.add_argument("--term", required=True)
    sub.choices["search"].add_argument("--limit", type=int, default=25)
    sub.choices["chart"].add_argument("--feed", required=True, choices=sorted(stores.LEGACY_FEEDS))
    sub.choices["chart"].add_argument("--genre", type=int)
    sub.choices["chart"].add_argument("--limit", type=int, default=100)
    sub.choices["reviews"].add_argument("--pages", type=int, default=3)
    a = ap.parse_args()
    {"lookup": cmd_lookup, "search": cmd_search, "chart": cmd_chart, "reviews": cmd_reviews, "hints": cmd_hints}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
