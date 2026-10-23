"""Community demand signals -> raw cache + evidence ledger (tier S: posts observed directly).

  uv run scripts/community.py hn  <slug> --query "habit tracker" [--days 365]
  uv run scripts/community.py ptt <slug> --query 記帳 [--boards MobileComm,iOS,Android,Lifeismoney] [--pages 3] [--days 730]
  uv run scripts/community.py reddit <slug> --query "habit tracker" --subs productivity,getdisciplined [--days 365] [--verify 10]
  uv run scripts/community.py reddit-comments <slug> --raw raw/reddit_<...>.json --apps "Streaks,Habitica=habitica"
  uv run scripts/community.py reddit-subs <slug> --subs productivity,getdisciplined

Reddit: reddit.com JSON blocks simple clients, so `reddit` searches Reddit's own RSS feed (slow, origin data) and fills
body/score/comment counts from the Arctic Shift archive; `--backend arctic` uses the archive's full-text search instead
and confirms a sample of permalinks on reddit.com (no confirmed permalink -> tier B). Dcard blocks simple clients; use crawl4ai.
Community counts measure how loudly a topic is discussed, not market size -- label them as such.
"""

import argparse
import html
import json
import re
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone

import httpx

from mr import ledger, reddit
from mr.common import USER_AGENT, emit, http_get_json, project_dir, save_raw

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
    eid = ledger.add(a.slug, kind="community", claim=f"Hacker News '{a.query}' posts, last {a.days} days", value=value,
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
    eid = ledger.add(a.slug, kind="community", claim=f"PTT '{a.query}' posts, last {a.days} days ({a.boards})", value=value,
                     unit="posts", tier="S", source_url=f"https://www.ptt.cc/bbs/{a.boards.split(',')[0]}/search?q={a.query}",
                     source_group="ptt", method="scripts/community.py ptt", data_as_of=date.today().isoformat(),
                     raw_path=raw, note=f"capped at {a.pages} search pages per board; vocal-minority sample")
    emit({"evidence": eid, **{k: v for k, v in value.items() if k != "top"}, "top": value["top"][:5], "raw": raw})


def _reddit_url(p: dict) -> str:
    return f"https://www.reddit.com/r/{p['subreddit']}/comments/{p['id']}/"


def _arctic() -> reddit.ArcticClient:
    return reddit.ArcticClient(httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=90))


def cmd_reddit(a):
    since = datetime.now(timezone.utc) - timedelta(days=a.days)
    arctic, rx = _arctic(), reddit.phrase_regex(a.query)
    rc = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True)
    found: list[dict] = []
    for sub in a.subs.split(","):
        if a.backend == "rss":
            hits = reddit.rss_search(rc, sub, a.query, since)
            # Reddit's feed lacks body and counts; fill them from the archive (cheap id lookup, not full-text search).
            full = {p["id"]: p for p in arctic.posts_by_ids([h["id"] for h in hits])} if hits else {}
            found += [{**h, **full.get(h["id"], {})} for h in hits]
        else:
            found += arctic.search_posts(sub, a.query, since)
    posts: dict[str, dict] = {}
    for p in found:
        # Both searches are loose (any word, stemmed); keep only posts containing the phrase.
        if rx.search(f"{p.get('title')}\n{p.get('selftext') or ''}"):
            posts[p["id"]] = {**p, "class": reddit.classify_post(p.get("title") or "", p.get("selftext") or ""),
                              "date": datetime.fromtimestamp(p["created_utc"], timezone.utc).date().isoformat(),
                              "url": _reddit_url(p)}
    rows = sorted(posts.values(), key=lambda p: p["created_utc"], reverse=True)
    asks = sorted((p for p in rows if p["class"] == "ask"), key=lambda p: p.get("num_comments") or 0, reverse=True)
    if a.backend == "rss":
        verified = {"checked": 0, "exists": len(rows), "rate_limited": False, "missing": [], "origin": "reddit.com search feed"}
    else:
        order = [p["id"] for p in asks] + [p["id"] for p in rows if p["class"] != "ask"]
        verified = reddit.verify_permalinks(rc, order, n=a.verify)
    classes = Counter(p["class"] for p in rows)
    value = {
        "threads": len(rows), "asks": classes["ask"], "promos": classes["promo"], "other": classes["other"],
        "window_days": a.days, "by_sub": dict(Counter(p["subreddit"] for p in rows).most_common()),
        "asks_by_sub": dict(Counter(p["subreddit"] for p in asks).most_common()),
        "by_month": dict(sorted(Counter(p["date"][:7] for p in rows).items())),
        "top_asks": [{"title": p["title"], "sub": p["subreddit"], "date": p["date"], "num_comments": p.get("num_comments"),
                      "score": p.get("score"), "url": p["url"]} for p in asks[:10]],
        "backend": a.backend, "verified": {k: v for k, v in verified.items() if k != "missing"},
    }
    tier = "S" if a.backend == "rss" or verified["exists"] else "B"
    raw = save_raw(a.slug, f"reddit_{a.query}", {"query": a.query, "subs": a.subs, "since": since.isoformat(),
                                                 "verified": verified, "posts": rows})
    eid = ledger.add(a.slug, kind="community", claim=f"Reddit '{a.query}' threads, last {a.days} days ({a.subs})", value=value,
                     unit="threads", tier=tier, source_url=f"https://www.reddit.com/r/{a.subs.split(',')[0]}/search/?q={a.query}",
                     source_group="reddit", method=f"scripts/community.py reddit --backend {a.backend} "
                     + ("(reddit.com search feed; body/score/num_comments from Arctic Shift id lookup)" if a.backend == "rss"
                        else "(Arctic Shift full-text search + reddit.com RSS permalink check)"),
                     data_as_of=date.today().isoformat(), raw_path=raw,
                     note="vocal-minority sample; ask/promo is a title keyword classifier, review titles in raw; "
                          "score/num_comments as of archive time; posts <36h old may be missing"
                          + ("" if tier == "S" else "; no permalink confirmed on reddit.com -> tier B"))
    emit({"evidence": eid, "tier": tier, **{k: v for k, v in value.items() if k != "top_asks"},
          "top_asks": value["top_asks"][:5], "raw": raw})


def cmd_reddit_comments(a):
    src = json.loads((project_dir(a.slug) / a.raw).read_text(encoding="utf-8"))
    ids = set(a.ids.split(",")) if a.ids else None
    posts = [p for p in src["posts"] if (p["id"] in ids if ids else p["class"] in a.classes.split(","))]
    arctic, apps = _arctic(), reddit.parse_apps(a.apps)
    threads, missing = {}, 0
    for p in posts:
        comments = arctic.comment_tree(p["id"], limit=a.limit)
        missing += max((p.get("num_comments") or 0) - len(comments), 0)
        threads[p["id"]] = {"title": p["title"], "url": p["url"], "date": p["date"],
                            "comments": [{"id": c["id"], "body": c.get("body"), "score": c.get("score"),
                                          "date": datetime.fromtimestamp(c["created_utc"], timezone.utc).date().isoformat()}
                                         for c in comments if c.get("body") not in (None, "[deleted]", "[removed]")]}
    bodies = {pid: [c["body"] for c in t["comments"]] for pid, t in threads.items()}
    value = {
        "threads": len(threads), "comments": sum(map(len, bodies.values())), "comments_not_retrieved": missing,
        "app_mentions": dict(sorted(reddit.count_mentions(bodies, apps).items(), key=lambda kv: -kv[1]["threads"])),
        "topic_mentions": reddit.count_mentions(bodies, reddit.DEFAULT_TOPICS),
    }
    raw = save_raw(a.slug, f"reddit_comments_{src['query']}", threads)
    scope = f"{len(ids)} selected" if ids else a.classes
    eid = ledger.add(a.slug, kind="community", claim=f"Reddit '{src['query']}' app and topic mentions in comments ({scope} threads)",
                     value=value, unit="threads", tier="S", source_url=posts[0]["url"] if posts else "https://www.reddit.com",
                     source_group="reddit", method="scripts/community.py reddit-comments (Arctic Shift comment trees, regex)",
                     data_as_of=date.today().isoformat(), raw_path=raw,
                     note=f"threads from {a.raw}; regex mentions (a mention is not an endorsement); vocal minority")
    emit({"evidence": eid, **value, "raw": raw})


_PROMO_RULE = re.compile(r"self[\s-]*promo|promot|advertis|spam|9:1|90/10|10%|links? to your", re.I)


def cmd_reddit_subs(a):
    arctic = _arctic()
    names = a.subs.split(",")
    info, rules = arctic.subreddits(names), arctic.rules(names)
    value = {}
    for n in names:
        s = info.get(n)
        r = next((v for k, v in rules.items() if k.lower() == n.lower()), [])
        value[n] = None if s is None else {
            "subscribers": s.get("subscribers"), "posts_total": (s.get("_meta") or {}).get("num_posts"),
            "promo_rules": [{"rule": x.get("short_name"), "text": (x.get("description") or "")[:400]}
                            for x in r if _PROMO_RULE.search(f"{x.get('short_name')} {x.get('description')}")]}
    raw = save_raw(a.slug, "reddit_subs", {"subreddits": info, "rules": rules})
    eid = ledger.add(a.slug, kind="community", claim=f"Reddit subreddit size and self-promotion rules ({a.subs})", value=value,
                     unit="subscribers", tier="S", source_url=f"https://www.reddit.com/r/{names[0]}/about/rules",
                     source_group="reddit", method="scripts/community.py reddit-subs (Arctic Shift subreddits + rules)",
                     data_as_of=date.today().isoformat(), raw_path=raw,
                     note="subscriber counts are Arctic Shift's infrequently refreshed copy; null = subreddit not found; "
                          "rules filtered by promo keywords, read the raw before posting")
    emit({"evidence": eid, **value, "raw": raw})


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
    r = sub.add_parser("reddit")
    r.add_argument("slug")
    r.add_argument("--query", required=True)
    r.add_argument("--subs", required=True, help="comma-separated subreddit names")
    r.add_argument("--days", type=int, default=365)
    r.add_argument("--backend", choices=["rss", "arctic"], default="rss",
                   help="rss: Reddit's own search feed (origin; ~1 request per 30s). arctic: archive full-text search")
    r.add_argument("--verify", type=int, default=10, help="arctic backend: permalinks to confirm on reddit.com (~7s each)")
    rc = sub.add_parser("reddit-comments")
    rc.add_argument("slug")
    rc.add_argument("--raw", required=True, help="raw/reddit_*.json from the reddit command")
    rc.add_argument("--apps", required=True, help='"Name=regex,Name2" (bare name = literal match)')
    rc.add_argument("--classes", default="ask")
    rc.add_argument("--ids", help="comma-separated post ids (e.g. a hand-reviewed ask list); overrides --classes")
    rc.add_argument("--limit", type=int, default=2000)
    rs = sub.add_parser("reddit-subs")
    rs.add_argument("slug")
    rs.add_argument("--subs", required=True)
    a = ap.parse_args()
    {"hn": cmd_hn, "ptt": cmd_ptt, "reddit": cmd_reddit, "reddit-comments": cmd_reddit_comments,
     "reddit-subs": cmd_reddit_subs}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
