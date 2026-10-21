from datetime import datetime, timezone

import httpx
import pytest

from mr import reddit


@pytest.mark.parametrize("title,expected", [
    ("Good apps/website for training my ear? Or advice in general", "ask"),
    ("Best ear training app in 2026?", "ask"),
    ("Looking for a relative pitch trainer", "ask"),
    ("I made an ear training app, any recommendations for features?", "promo"),
    ("My new bass Ear Training site", "promo"),
    ("6-7 chord enharmony", "other"),
    ("Why does a tritone sound tense?", "other"),
])
def test_classify_post(title, expected):
    assert reddit.classify_post(title) == expected


def test_phrase_regex_matches_hyphen_and_joined():
    rx = reddit.phrase_regex("ear training")
    assert rx.search("Ear-training tips") and rx.search("r/eartraining") and not rx.search("training my ear")


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_search_posts_pages_until_short_page():
    seen = []

    def handler(req):
        seen.append(int(req.url.params["before"]))
        n = 100 if len(seen) == 1 else 30
        base = 2_000_000 - len(seen) * 1000
        return httpx.Response(200, json={"data": [{"id": f"{len(seen)}-{i}", "created_utc": base - i} for i in range(n)]})

    ac = reddit.ArcticClient(_client(handler), sleep=lambda s: None)
    posts = ac.search_posts("musictheory", "ear training", datetime(2025, 1, 1, tzinfo=timezone.utc))
    assert len(posts) == 130 and len(seen) == 2
    assert seen[1] == 2_000_000 - 1000 - 99


def test_get_retries_on_429_and_soft_timeout():
    calls, waits = [], []

    def handler(req):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"x-ratelimit-reset": "3"}, json={})
        if len(calls) == 2:
            return httpx.Response(422, json={"data": None, "error": "Timeout. Maybe slow down a bit"})
        return httpx.Response(200, json={"data": [1]})

    ac = reddit.ArcticClient(_client(handler), pause=0, sleep=waits.append)
    assert ac.get("/api/posts/search", {}) == [1]
    assert waits[:2] == [4.0, 20]


def test_get_gives_up_after_retries():
    ac = reddit.ArcticClient(_client(lambda req: httpx.Response(429, json={})), retries=1, sleep=lambda s: None)
    with pytest.raises(RuntimeError):
        ac.get("/api/posts/search", {})


def test_verify_permalinks_stops_on_429_without_raising():
    def handler(req):
        pid = req.url.path.split("/")[2]
        if pid == "c":
            return httpx.Response(429)
        body = f"<feed><link href='https://www.reddit.com/r/x/comments/{pid}/t/'/></feed>" if pid == "a" else "<feed/>"
        return httpx.Response(200, text=body)

    res = reddit.verify_permalinks(_client(handler), ["a", "b", "c", "d"], n=4, sleep=lambda s: None)
    assert res == {"checked": 2, "exists": 1, "missing": ["b"], "rate_limited": True}


def test_flatten_tree_skips_more_stubs():
    tree = [{"kind": "t1", "data": {"id": "1", "replies": {"data": {"children": [
        {"kind": "t1", "data": {"id": "2", "replies": ""}}, {"kind": "more", "data": {}}]}}}}]
    assert [c["id"] for c in reddit.flatten_tree(tree)] == ["1", "2"]


def test_count_mentions_and_aliases():
    apps = reddit.parse_apps(r"FET=Functional Ear Train|\bFET\b,Perfect Ear")
    threads = {"p1": ["Functional Ear Trainer is great", "FET + Perfect Ear"], "p2": ["perfect ear!"], "p3": ["none"]}
    assert reddit.count_mentions(threads, apps) == {
        "FET": {"threads": 1, "texts": 2}, "Perfect Ear": {"threads": 2, "texts": 2}}


RSS = """<feed><entry><category term="musictheory" label="r/musictheory"/><id>t3_abc</id>
<published>2026-10-12T02:13:46+00:00</published><title>Best ear training app?</title></entry>
<entry><id>t1_zzz</id><published>2026-10-12T02:13:46+00:00</published><title>comment</title></entry></feed>"""


def test_parse_search_rss_keeps_posts_only():
    assert reddit.parse_search_rss(RSS) == [{"id": "abc", "subreddit": "musictheory", "title": "Best ear training app?",
                                             "created_utc": 1791771226}]


def test_rss_search_stops_at_short_page_and_waits_on_429():
    calls, waits = [], []

    def handler(req):
        calls.append(req)
        if len(calls) == 1:
            return httpx.Response(429, headers={"x-ratelimit-reset": "5"})
        return httpx.Response(200, text=RSS, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "9"})

    out = reddit.rss_search(_client(handler), "musictheory", "ear training",
                            datetime(2026, 1, 1, tzinfo=timezone.utc), sleep=waits.append)
    assert [p["id"] for p in out] == ["abc"] and waits == [6.0, 10.0] and len(calls) == 2


def test_rss_search_retries_connect_error():
    calls, waits = [], []

    def handler(req):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectError("No route to host")
        return httpx.Response(200, text=RSS)

    out = reddit.rss_search(_client(handler), "musictheory", "ear training",
                            datetime(2026, 1, 1, tzinfo=timezone.utc), sleep=waits.append)
    assert len(out) == 1 and waits == [30]
