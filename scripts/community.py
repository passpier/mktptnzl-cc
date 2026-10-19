"""Community demand signals -> raw cache + evidence ledger (tier S: posts observed directly).

  uv run scripts/community.py hn  <slug> --query "habit tracker" [--days 365]
  uv run scripts/community.py ptt <slug> --query 記帳 [--boards MobileComm,iOS,Android,Lifeismoney] [--pages 3] [--days 730]

Reddit and Dcard block simple clients; collect them with the crawl4ai MCP (web-collector agent).
Community counts measure how loudly a topic is discussed, not market size -- label them as such.
"""

import argparse
import html
import re
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone

import httpx

from mr import ledger
from mr.common import USER_AGENT, emit, http_get_json, save_raw

HN = "https://hn.algolia.com/api/v1/search_by_date"
PTT_BOARDS = "MobileComm,iOS,Android,Lifeismoney"


def cmd_hn(a):
    since = int((datetime.now(timezone.utc) - timedelta(days=a.days)).timestamp())
    params = {"query": a.query, "tags": "story", "numericFilters": f"created_at_i>{since}", "hitsPerPage": 1000}
    stories = http_get_json(HN, params)
    comments = http_get_json(HN, {**params, "tags": "comment", "hitsPerPage": 0})
    hits = stories.get("hits", [])
    by_month = Counter(h["created_at"][:7] for h in hits)
    top = sorted(hits, key=lambda h: h.get("points") or 0, reverse=True)[:10]
    value = {
        "stories": stories.get("nbHits", len(hits)), "comments": comments.get("nbHits"), "window_days": a.days,
        "by_month": dict(sorted(by_month.items())),
        "top": [{"title": h.get("title"), "points": h.get("points"), "date": h["created_at"][:10],
                 "url": f"https://news.ycombinator.com/item?id={h['objectID']}"} for h in top],
    }
    raw = save_raw(a.slug, f"hn_{a.query}", {"params": params, "stories": hits, "comments_nbHits": comments.get("nbHits")})
    eid = ledger.add(a.slug, kind="community", claim=f"Hacker News「{a.query}」近 {a.days} 天討論量", value=value,
                     unit="posts", tier="S", source_url=f"{HN}?query={a.query}&tags=story", source_group="hackernews",
                     method="scripts/community.py hn", data_as_of=date.today().isoformat(), raw_path=raw,
                     note="HN skews to developers/early adopters; measures discussion volume, not demand")
    emit({"evidence": eid, **value, "raw": raw})


_ENTRY = re.compile(
    r'<div class="nrec">(?:<span[^>]*>)?(?P<nrec>[^<]*)(?:</span>)?</div>.*?'
    r'<a href="/bbs/(?P<board>[^/]+)/M\.(?P<ts>\d+)\.A\.(?P<aid>\w+)\.html">(?P<title>[^<]*)</a>',
    re.S,
)


def _nrec(s: str) -> int:
    s = s.strip()
    if s == "爆":
        return 100
    if s.startswith("X"):
        return -10
    return int(s) if s.isdigit() else 0


def cmd_ptt(a):
    cutoff = datetime.now(timezone.utc) - timedelta(days=a.days)
    posts = []
    client = httpx.Client(headers={"User-Agent": USER_AGENT}, cookies={"over18": "1"}, timeout=20)
    for board in a.boards.split(","):
        for page in range(1, a.pages + 1):
            r = client.get(f"https://www.ptt.cc/bbs/{board}/search", params={"q": a.query, "page": page})
            if r.status_code == 404:
                break
            r.raise_for_status()
            found = list(_ENTRY.finditer(r.text))
            for m in found:
                when = datetime.fromtimestamp(int(m["ts"]), timezone.utc)
                if when < cutoff:
                    continue
                posts.append({"board": board, "date": when.date().isoformat(), "title": html.unescape(m["title"]).strip(),
                              "push": _nrec(m["nrec"]),
                              "url": f"https://www.ptt.cc/bbs/{board}/M.{m['ts']}.A.{m['aid']}.html"})
            if len(found) < 20:
                break
            time.sleep(0.5)
    by_board = Counter(p["board"] for p in posts)
    by_month = Counter(p["date"][:7] for p in posts)
    value = {
        "posts": len(posts), "window_days": a.days, "by_board": dict(by_board), "by_month": dict(sorted(by_month.items())),
        "top": sorted(posts, key=lambda p: p["push"], reverse=True)[:10],
    }
    raw = save_raw(a.slug, f"ptt_{a.query}", posts)
    eid = ledger.add(a.slug, kind="community", claim=f"PTT「{a.query}」近 {a.days} 天討論量（{a.boards}）", value=value,
                     unit="posts", tier="S", source_url=f"https://www.ptt.cc/bbs/{a.boards.split(',')[0]}/search?q={a.query}",
                     source_group="ptt", method="scripts/community.py ptt", data_as_of=date.today().isoformat(),
                     raw_path=raw, note=f"capped at {a.pages} search pages per board; vocal-minority sample")
    emit({"evidence": eid, **{k: v for k, v in value.items() if k != "top"}, "top": value["top"][:5], "raw": raw})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hn")
    h.add_argument("slug")
    h.add_argument("--query", required=True)
    h.add_argument("--days", type=int, default=365)
    p = sub.add_parser("ptt")
    p.add_argument("slug")
    p.add_argument("--query", required=True)
    p.add_argument("--boards", default=PTT_BOARDS)
    p.add_argument("--pages", type=int, default=3)
    p.add_argument("--days", type=int, default=730)
    a = ap.parse_args()
    {"hn": cmd_hn, "ptt": cmd_ptt}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
