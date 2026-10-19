"""Free first-party store data: Apple iTunes/RSS endpoints and Google Play (google-play-scraper).

Everything here is a direct observation of the store (tier S) at fetch time.
"""

from __future__ import annotations

import plistlib
from datetime import datetime, timezone
from typing import Any

from mr.common import USER_AGENT, http_get_json

STOREFRONTS = {"tw": "143470", "us": "143441", "jp": "143462", "hk": "143463", "gb": "143444"}
GPLAY_LANG = {"tw": "zh-TW", "us": "en", "jp": "ja", "hk": "zh-HK", "gb": "en"}
APPLE_FEEDS = {"top-free", "top-paid"}
LEGACY_FEEDS = {"top-free": "topfreeapplications", "top-paid": "toppaidapplications",
                "top-grossing": "topgrossingapplications"}


# ---------- Apple ----------

def apple_lookup_url(app_id: str, country: str) -> str:
    return f"https://itunes.apple.com/lookup?id={app_id}&country={country}"


def apple_lookup(app_id: str, country: str) -> dict[str, Any]:
    data = http_get_json("https://itunes.apple.com/lookup", {"id": app_id, "country": country})
    if not data.get("results"):
        raise LookupError(f"apple app {app_id} not found in {country} store")
    return data["results"][0]


def apple_metrics(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": r.get("trackName"), "id": str(r.get("trackId")), "seller": r.get("sellerName"),
        "ratings": r.get("userRatingCount"), "avg_rating": round(r.get("averageUserRating") or 0, 3),
        "price": r.get("price"), "currency": r.get("currency"), "formatted_price": r.get("formattedPrice"),
        "genre": r.get("primaryGenreName"), "genre_id": r.get("primaryGenreId"), "version": r.get("version"),
        "current_version_date": (r.get("currentVersionReleaseDate") or "")[:10],
        "first_release": (r.get("releaseDate") or "")[:10], "url": r.get("trackViewUrl"),
    }


def apple_search(term: str, country: str, limit: int = 25) -> list[dict[str, Any]]:
    data = http_get_json("https://itunes.apple.com/search",
                         {"term": term, "country": country, "entity": "software", "limit": limit})
    return data.get("results", [])


def apple_chart_url(feed: str, country: str, limit: int, genre: int | None) -> str:
    if feed in APPLE_FEEDS and genre is None:
        return f"https://rss.marketingtools.apple.com/api/v2/{country}/apps/{feed}/{limit}/apps.json"
    g = f"/genre={genre}" if genre else ""
    return f"https://itunes.apple.com/{country}/rss/{LEGACY_FEEDS[feed]}/limit={limit}{g}/json"


def apple_chart(feed: str, country: str, limit: int = 100, genre: int | None = None) -> tuple[str, list[dict]]:
    """Return (url, [{rank, id, name, artist}]). Genre filter and top-grossing use the legacy iTunes RSS feed."""
    url = apple_chart_url(feed, country, limit, genre)
    data = http_get_json(url)
    rows = []
    if "results" in data.get("feed", {}):
        for i, a in enumerate(data["feed"]["results"], 1):
            rows.append({"rank": i, "id": a["id"], "name": a["name"], "artist": a.get("artistName")})
    else:
        for i, e in enumerate(data.get("feed", {}).get("entry", []), 1):
            rows.append({"rank": i, "id": e["id"]["attributes"]["im:id"], "name": e["im:name"]["label"],
                         "artist": e.get("im:artist", {}).get("label")})
    return url, rows


def apple_reviews(app_id: str, country: str, pages: int = 3) -> tuple[str, list[dict]]:
    """Most recent reviews via the public RSS feed (max 10 pages x 50)."""
    out: list[dict] = []
    base = f"https://itunes.apple.com/{country}/rss/customerreviews/page={{p}}/id={app_id}/sortby=mostrecent/json"
    for p in range(1, min(pages, 10) + 1):
        entries = http_get_json(base.format(p=p)).get("feed", {}).get("entry", [])
        if isinstance(entries, dict):
            entries = [entries]
        if not entries:
            break
        for e in entries:
            if "im:rating" not in e:
                continue
            out.append({
                "date": e["updated"]["label"][:10], "rating": int(e["im:rating"]["label"]),
                "title": e["title"]["label"], "text": e["content"]["label"],
                "version": e.get("im:version", {}).get("label"), "votes": int(e.get("im:voteCount", {}).get("label", 0)),
            })
    return base.format(p=1), out


def apple_hints(term: str, country: str) -> tuple[str, list[str]]:
    """App Store search autocomplete. Unofficial endpoint, but a direct observation of Apple's own suggestions."""
    import httpx

    url = "https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints"
    r = httpx.get(url, params={"clientApplication": "Software", "term": term}, timeout=20,
                  headers={"X-Apple-Store-Front": f"{STOREFRONTS[country]}-1,29", "User-Agent": USER_AGENT})
    r.raise_for_status()
    hints = [h["term"] for h in plistlib.loads(r.content).get("hints", [])]
    return f"{url}?clientApplication=Software&term={term} (storefront {country})", hints


# ---------- Google Play ----------

def gplay_url(app_id: str, country: str) -> str:
    return f"https://play.google.com/store/apps/details?id={app_id}&gl={country}&hl={GPLAY_LANG.get(country, 'en')}"


def gplay_app(app_id: str, country: str) -> dict[str, Any]:
    from google_play_scraper import app

    return app(app_id, lang=GPLAY_LANG.get(country, "en"), country=country)


def gplay_metrics(a: dict[str, Any]) -> dict[str, Any]:
    updated = a.get("updated")
    return {
        "name": a.get("title"), "id": a.get("appId"), "developer": a.get("developer"),
        "ratings": a.get("ratings"), "reviews": a.get("reviews"), "avg_rating": round(a.get("score") or 0, 3),
        "installs": a.get("installs"), "min_installs": a.get("minInstalls"), "real_installs": a.get("realInstalls"),
        "price": a.get("price"), "currency": a.get("currency"), "free": a.get("free"),
        "offers_iap": a.get("offersIAP"), "iap_range": a.get("inAppProductPrice"), "contains_ads": a.get("containsAds"),
        "genre": a.get("genre"), "version": a.get("version"), "released": a.get("released"),
        "updated": datetime.fromtimestamp(updated, timezone.utc).date().isoformat() if updated else None,
    }


def gplay_search(term: str, country: str, n: int = 30) -> list[dict[str, Any]]:
    from google_play_scraper import search

    return search(term, lang=GPLAY_LANG.get(country, "en"), country=country, n_hits=n)


def gplay_reviews(app_id: str, country: str, count: int = 300, max_stars: int | None = None) -> list[dict]:
    from google_play_scraper import Sort, reviews

    rows: list[dict] = []
    stars = range(1, max_stars + 1) if max_stars else [None]
    per = max(1, count // len(stars))
    for s in stars:
        res, _ = reviews(app_id, lang=GPLAY_LANG.get(country, "en"), country=country, sort=Sort.NEWEST,
                         count=per, filter_score_with=s)
        for r in res:
            rows.append({"date": r["at"].date().isoformat(), "rating": r["score"], "title": "",
                         "text": r["content"], "version": r.get("reviewCreatedVersion"),
                         "votes": r.get("thumbsUpCount", 0)})
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def review_summary(rows: list[dict]) -> dict[str, Any]:
    dist = {str(i): 0 for i in range(1, 6)}
    for r in rows:
        dist[str(r["rating"])] += 1
    dates = sorted(r["date"] for r in rows)
    return {"n": len(rows), "stars": dist, "from": dates[0] if dates else None, "to": dates[-1] if dates else None}
