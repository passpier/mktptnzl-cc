"""Reddit via Arctic Shift (keyless archive of Reddit posts/comments), with Reddit's own RSS as an existence check.

reddit.com JSON and old.reddit return 403 to simple clients; the official API needs pre-approval. Arctic Shift
mirrors posts verbatim, so thread counts and titles count as observed (tier S) once a sample of permalinks is
confirmed on reddit.com. Scores and comment counts are frozen at archive time.
"""

from __future__ import annotations

import html
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

import httpx

ARCTIC = "https://arctic-shift.photon-reddit.com"
POST_FIELDS = "id,subreddit,created_utc,title,selftext,num_comments,score,link_flair_text,author"

_PROMO = re.compile(
    r"\b(i|we)\s+(made|built|created|developed|launched|released|wrote|coded)\b|\bmy\s+((new|free|own)\s+([\w-]+\s+){0,3})?"
    r"(app|site|website|tool|game|project|course|channel|program)\b|\bintroducing\b|\blaunch(ed|ing)?\b|\bbeta\b|"
    r"\bfeedback on (my|our)\b|\bcheck (it|this) out\b|\bshow\s*(hn|off)\b|\bwe'?re building\b",
    re.I,
)
_ASK = re.compile(
    r"\brecommend|\bsuggest|\bbest\b|\blooking for\b|\bany good\b|\b(which|what) (app|apps|site|sites|website|"
    r"resource|resources|tool|tools|program|software)\b|\b(apps?|resources?|websites?|tools?) (for|to)\b|"
    r"\balternatives?\b|\bworth (it|paying)\b|\b(apps?|websites?|sites?|resources?)\b.*\?",
    re.I,
)

# Same buckets as the review coding in E580/E593, so Reddit and review shares read side by side.
DEFAULT_TOPICS = {
    "paywall_price": r"paywall|subscri|pay(ing|ed)?\b|price|pricing|expensive|\bfree\b|premium|in-app|\$\d",
    "structure_curriculum": r"curriculum|structured?|lesson|course|progress(ion)?|step by step|path\b|levels?\b",
}


def classify_post(title: str, selftext: str = "") -> str:
    """'ask' = a request for recommendations (the unmet-demand signal); plain theory questions are 'other'.
    'promo' wins over 'ask' so "I made an app, any feedback?" is not counted as demand."""
    text = f"{title}\n{selftext or ''}"
    if _PROMO.search(text):
        return "promo"
    if _ASK.search(title) or _ASK.search((selftext or "")[:300]):
        return "ask"
    return "other"


def phrase_regex(query: str) -> re.Pattern:
    """'ear training' also matches 'ear-training' and 'eartraining'."""
    words = [re.escape(w) for w in query.split()]
    return re.compile(r"\b" + r"\W*".join(words), re.I)


class ArcticClient:
    def __init__(self, client: httpx.Client, pause: float = 1.5, retries: int = 5,
                 sleep: Callable[[float], None] = time.sleep):
        self.client, self.pause, self.retries, self.sleep = client, pause, retries, sleep

    def get(self, path: str, params: dict) -> Any:
        for attempt in range(self.retries + 1):
            try:
                r = self.client.get(f"{ARCTIC}{path}", params=params)
            except httpx.TransportError:
                if attempt == self.retries:
                    raise
                self.sleep(10 * (attempt + 1))
                continue
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            # Overload shows up as 429, 5xx, or a 200/422 with {"data": null, "error": "Timeout. Maybe slow down a bit"}.
            if r.status_code == 429 or r.status_code >= 500 or (r.status_code in (200, 422) and body.get("error")):
                if attempt == self.retries:
                    raise RuntimeError(f"Arctic Shift {path}: {r.status_code} {body.get('error')}")
                reset = r.headers.get("x-ratelimit-reset")
                self.sleep(min(float(reset) + 1, 60) if reset else 10 * (attempt + 1))
                continue
            r.raise_for_status()
            self.sleep(self.pause)
            return body.get("data")

    def search_posts(self, subreddit: str, query: str, after: datetime, before: datetime | None = None,
                     field: str = "query") -> list[dict]:
        """Newest first; pages back by created_utc until a page comes back short."""
        out: list[dict] = []
        cursor = int((before or datetime.now(timezone.utc)).timestamp())
        while True:
            page = self.get("/api/posts/search", {
                "subreddit": subreddit, field: query, "after": int(after.timestamp()), "before": cursor,
                "limit": 100, "sort": "desc", "fields": POST_FIELDS}) or []
            out.extend(page)
            if len(page) < 100:
                return out
            cursor = min(p["created_utc"] for p in page)

    def posts_by_ids(self, ids: list[str]) -> list[dict]:
        out = []
        for i in range(0, len(ids), 500):
            out.extend(self.get("/api/posts/ids", {"ids": ",".join(ids[i:i + 500]), "fields": POST_FIELDS}) or [])
        return out

    def comment_tree(self, link_id: str, limit: int = 2000) -> list[dict]:
        tree = self.get("/api/comments/tree", {"link_id": f"t3_{link_id}", "limit": limit}) or []
        return list(flatten_tree(tree))

    def subreddits(self, names: Iterable[str]) -> dict[str, dict | None]:
        out = {}
        for n in names:
            rows = self.get("/api/subreddits/search", {"subreddit": n}) or []
            out[n] = next((r for r in rows if r["display_name"].lower() == n.lower()), None)
        return out

    def rules(self, names: Iterable[str]) -> dict[str, list[dict]]:
        rows = self.get("/api/subreddits/rules", {"subreddits": ",".join(names)}) or []
        return {r["subreddit"]: r.get("rules") or [] for r in rows}


def flatten_tree(nodes: list[dict]) -> Iterable[dict]:
    for n in nodes:
        if n.get("kind") != "t1":
            continue  # "more" stubs: counted as missing, not fetched
        yield n["data"]
        replies = n["data"].get("replies")
        if isinstance(replies, dict):
            yield from flatten_tree(replies.get("data", {}).get("children", []))


_ENTRY = re.compile(r"<entry>(.*?)</entry>", re.S)


def _tag(xml: str, name: str) -> str | None:
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", xml, re.S)
    return html.unescape(m.group(1)) if m else None


def parse_search_rss(xml: str) -> list[dict]:
    """Reddit search Atom feed -> [{id, subreddit, title, created_utc}] (posts only)."""
    out = []
    for e in _ENTRY.findall(xml):
        fullname, published = _tag(e, "id") or "", _tag(e, "published")
        sub = re.search(r'<category term="([^"]+)"', e)
        if not fullname.startswith("t3_") or not published:
            continue
        out.append({"id": fullname[3:], "subreddit": sub.group(1) if sub else None, "title": _tag(e, "title"),
                    "created_utc": int(datetime.fromisoformat(published).timestamp())})
    return out


def rss_search(client: httpx.Client, subreddit: str, query: str, after: datetime, max_pages: int = 10,
               sleep: Callable[[float], None] = time.sleep) -> list[dict]:
    """Reddit's own search feed (origin data), newest first, paged with `after=t3_<id>` until past the window.
    Unauthenticated feeds allow about one request per reset window; waits on x-ratelimit-reset."""
    out: list[dict] = []
    cursor = None
    for _ in range(max_pages):
        params = {"q": query, "restrict_sr": 1, "sort": "new", "t": "year", "limit": 100, **({"after": cursor} if cursor else {})}
        for attempt in range(4):
            try:
                r = client.get(f"https://www.reddit.com/r/{subreddit}/search.rss", params=params)
            except httpx.TransportError:  # flaky network: back off and retry, re-raise on the last try
                if attempt == 3:
                    raise
                sleep(30 * (attempt + 1))
                continue
            if r.status_code != 429:
                break
            sleep(min(float(r.headers.get("x-ratelimit-reset") or 30) + 1, 120))
        r.raise_for_status()
        page = parse_search_rss(r.text)
        out.extend(p for p in page if p["created_utc"] >= after.timestamp())
        if float(r.headers.get("x-ratelimit-remaining") or 1) < 1:
            sleep(min(float(r.headers.get("x-ratelimit-reset") or 30) + 1, 120))
        if len(page) < 100 or page[-1]["created_utc"] < after.timestamp():
            return out
        cursor = f"t3_{page[-1]['id']}"
    return out


def verify_permalinks(client: httpx.Client, ids: list[str], n: int = 10, pause: float = 7.0,
                      sleep: Callable[[float], None] = time.sleep) -> dict:
    """Confirm posts exist on reddit.com via the per-post RSS. Unauthenticated RSS allows ~10 req/min; a 429 stops
    the check and is recorded, it never raises."""
    res = {"checked": 0, "exists": 0, "missing": [], "rate_limited": False}
    for i, pid in enumerate(ids[:n]):
        if i:
            sleep(pause)
        r = client.get(f"https://www.reddit.com/comments/{pid}/.rss")
        if r.status_code == 429:
            res["rate_limited"] = True
            break
        res["checked"] += 1
        if r.status_code == 200 and f"/comments/{pid}/" in r.text:
            res["exists"] += 1
        else:
            res["missing"].append(pid)
    return res


def count_mentions(threads: dict[str, list[str]], patterns: dict[str, str]) -> dict[str, dict]:
    """threads: {post_id: [texts]}. Returns per pattern how many threads and texts mention it."""
    out = {}
    for name, pat in patterns.items():
        rx = re.compile(pat, re.I)
        hits = {pid: sum(1 for t in texts if rx.search(t or "")) for pid, texts in threads.items()}
        out[name] = {"threads": sum(1 for v in hits.values() if v), "texts": sum(hits.values())}
    return out


def parse_apps(spec: str) -> dict[str, str]:
    """'FET=Functional Ear Train|\\bFET\\b,Perfect Ear' -> {name: regex}; a bare name is its own literal pattern."""
    out = {}
    for item in filter(None, (s.strip() for s in spec.split(","))):
        name, _, pat = item.partition("=")
        out[name.strip()] = pat.strip() or re.escape(name.strip())
    return out
