"""Evidence ledger: every number in a report is a row in research/<slug>/evidence.jsonl.

Source tiers (see .claude/skills/source-grading):
  S  direct observation fetched from the origin in this run
  A  dated first-party statement (official docs, filings, founder-published numbers)
  B  measured third-party estimate with public method (keyword volume, Trends index)
  C  secondhand reporting -- must be traced to origin, otherwise downgrade to D
  D  unverifiable, including the model's own memory -- leads only, never conclusions
"""

from __future__ import annotations

import fcntl
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from mr.common import RESEARCH, now, now_iso, project_dir

TIERS = ("S", "A", "B", "C", "D")
DECISION_TIERS = ("S", "A", "B")

# kind -> (ttl_days, severity when stale). Age is measured from data_as_of, else published_at, else retrieved_at.
TTL_POLICY: dict[str, tuple[int, str]] = {
    "ranking": (7, "block"),
    "price": (7, "block"),
    "rating": (30, "block"),
    "metadata": (30, "block"),
    "installs": (30, "block"),
    "review": (365, "warn"),
    "keyword_volume": (90, "block"),
    "search_popularity": (90, "block"),
    "trends": (30, "warn"),
    "serp": (30, "warn"),
    "community": (90, "warn"),
    "market_report": (730, "block"),
    "population": (1825, "warn"),
    "policy": (180, "warn"),
    "experiment": (180, "warn"),
    "other": (30, "warn"),
}

FIELDS = (
    "id", "kind", "claim", "value", "unit", "tier", "source_url", "source_group", "method",
    "retrieved_at", "published_at", "data_as_of", "ttl_days", "severity", "raw_path", "cost_usd", "note",
)


def ledger_path(slug: str) -> Path:
    return RESEARCH / slug / "evidence.jsonl"


def load(slug: str) -> list[dict[str, Any]]:
    p = ledger_path(slug)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_index(slug: str) -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in load(slug)}


def _next_id(rows: list[dict[str, Any]]) -> str:
    nums = [int(r["id"][1:]) for r in rows if str(r.get("id", "")).startswith("E") and r["id"][1:].isdigit()]
    return f"E{max(nums, default=0) + 1}"


def add(slug: str, *, kind: str, claim: str, value: Any, tier: str, source_url: str, source_group: str,
        method: str, unit: str | None = None, published_at: str | None = None, data_as_of: str | None = None,
        retrieved_at: str | None = None, raw_path: str | None = None, cost_usd: float = 0.0,
        note: str | None = None, ttl_days: int | None = None) -> str:
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {TIERS}, got {tier!r}")
    if kind not in TTL_POLICY:
        raise ValueError(f"kind must be one of {sorted(TTL_POLICY)}, got {kind!r}")
    if not source_url:
        raise ValueError("source_url is required; model memory is tier D and still needs source_url='memory'")
    default_ttl, severity = TTL_POLICY[kind]
    project_dir(slug)
    # Lock across read-max-id and append so parallel collectors never mint the same E#.
    with ledger_path(slug).open("a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        rec = {
            "id": _next_id(load(slug)), "kind": kind, "claim": claim, "value": value, "unit": unit, "tier": tier,
            "source_url": source_url, "source_group": source_group, "method": method,
            "retrieved_at": retrieved_at or now_iso(), "published_at": published_at, "data_as_of": data_as_of,
            "ttl_days": ttl_days or default_ttl, "severity": severity, "raw_path": raw_path,
            "cost_usd": cost_usd, "note": note,
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec["id"]


def _parse_when(s: str) -> datetime:
    s = s.strip()
    if len(s) == 4:  # YYYY (e.g. a survey year) -> Jan 1, strict like YYYY-MM below
        s += "-01"
    if len(s) == 7:  # YYYY-MM -> end of that month is generous; use the 1st to stay strict
        s += "-01"
    if len(s) == 10:
        d = date.fromisoformat(s)
        return datetime(d.year, d.month, d.day).astimezone()
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.astimezone()


def reference_time(rec: dict[str, Any]) -> datetime:
    for key in ("data_as_of", "published_at", "retrieved_at"):
        if rec.get(key):
            return _parse_when(str(rec[key]))
    raise ValueError(f"{rec.get('id')}: no date field")


def age_days(rec: dict[str, Any], at: datetime | None = None) -> float:
    return ((at or now()) - reference_time(rec)).total_seconds() / 86400


@dataclass
class Staleness:
    id: str
    age_days: float
    ttl_days: int
    severity: str

    def describe(self) -> str:
        return f"{self.id} is {int(self.age_days)}d old (TTL {self.ttl_days}d, {self.severity})"


def staleness(rec: dict[str, Any], at: datetime | None = None) -> Staleness | None:
    age = age_days(rec, at)
    ttl = int(rec.get("ttl_days") or TTL_POLICY.get(rec.get("kind", "other"), TTL_POLICY["other"])[0])
    if age > ttl:
        sev = rec.get("severity") or TTL_POLICY.get(rec.get("kind", "other"), TTL_POLICY["other"])[1]
        return Staleness(rec["id"], age, ttl, sev)
    return None


def stale_rows(slug: str, at: datetime | None = None) -> list[Staleness]:
    return [s for r in load(slug) if (s := staleness(r, at))]


def render_appendix(slug: str, cited: set[str] | None = None) -> str:
    rows = load(slug)
    if cited is not None:
        rows = [r for r in rows if r["id"] in cited]
    out = ["| ID | Tier | Claim | Value | Data as of | Retrieved | Source |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        v = r["value"] if isinstance(r["value"], str) else json.dumps(r["value"], ensure_ascii=False)
        v = v if len(v) <= 100 else v[:100] + "… (full value in evidence.jsonl)"
        val = f"{v}{(' ' + r['unit']) if r.get('unit') else ''}".replace("|", "\\|")
        as_of = r.get("data_as_of") or r.get("published_at") or "—"
        out.append(
            f"| {r['id']} | {r['tier']} | {r['claim']} | {val} | {as_of} | {r['retrieved_at'][:10]} | {r['source_url']} |"
        )
    return "\n".join(out)
