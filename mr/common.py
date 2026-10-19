"""Shared paths, time helpers, raw-file caching and HTTP for the data scripts."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("MR_ROOT", Path(__file__).resolve().parent.parent))
RESEARCH = ROOT / "research"
USER_AGENT = "marketing-research/0.1 (+local research; contact: owner)"


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def project_dir(slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", slug):
        raise ValueError(f"invalid slug {slug!r}: use lowercase letters, digits, - or _")
    d = RESEARCH / slug
    (d / "raw").mkdir(parents=True, exist_ok=True)
    return d


def raw_stem(name: str) -> str:
    """Filesystem-safe stem; non-ASCII names (e.g. Chinese search terms) get a hash so terms never collide."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:80]
    return safe if safe == name else f"{safe}-{cache_key(name)}"


def save_raw(slug: str, name: str, data: Any) -> str:
    """Write a raw API response under research/<slug>/raw/ and return its path relative to the project dir."""
    d = project_dir(slug)
    stamp = now().strftime("%Y%m%dT%H%M%S")
    path = d / "raw" / f"{raw_stem(name)}_{stamp}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return str(path.relative_to(d))


def cache_key(*parts: Any) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]


def http_get_json(url: str, params: dict | None = None, timeout: float = 30.0) -> Any:
    import httpx

    r = httpx.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    r.raise_for_status()
    return r.json()


def emit(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=1))
