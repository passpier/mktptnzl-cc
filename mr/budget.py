"""DataForSEO spend tracking: estimate before a call, log actual cost after, enforce a monthly cap."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from mr.common import RESEARCH, ROOT, now, now_iso

CONFIG = ROOT / "config" / "budget.json"
COSTS = RESEARCH / "_costs.jsonl"
_COST_FIELD = re.compile(r'"cost"\s*:\s*([0-9]+(?:\.[0-9]+)?)')


def load_config(path: Path = CONFIG) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(tool_input: dict[str, Any]) -> str:
    p = tool_input.get("path") or tool_input.get("url") or ""
    p = re.sub(r"^https?://[^/]+", "", p)
    if not p.startswith("/"):
        p = "/" + p
    if not p.startswith("/v3/"):
        p = "/v3" + p
    return re.sub(r"\.ai$", "", p)


def task_count(tool_input: dict[str, Any]) -> int:
    data = tool_input.get("data")
    if isinstance(data, list):
        return max(1, len(data))
    return 1


def estimate(tool_input: dict[str, Any], cfg: dict[str, Any]) -> tuple[float, str | None]:
    """Return (estimated USD, blocked reason or None)."""
    method = str(tool_input.get("method", "POST")).upper()
    path = normalize_path(tool_input)
    body = json.dumps(tool_input.get("data") or "")
    for pat in cfg["blocked_path_patterns"]:
        if re.search(pat, path):
            return 0.0, f"{path} is blocked: {cfg['blocked_reason']}"
    if re.search(r'"priority"\s*:\s*2', body):
        return 0.0, "priority queue (priority: 2) is blocked; use the standard queue"
    if method == "GET":  # task_get / tasks_ready / user_data are free; cost is charged at task_post
        return 0.0, None
    per = cfg["default_usd"]
    for rule in cfg["estimates"]:
        if re.search(rule["pattern"], path):
            per = rule["usd"]
            break
    return round(per * task_count(tool_input), 6), None


def month_key(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y-%m")


def month_spent(month: str | None = None, costs: Path = COSTS) -> float:
    month = month or month_key()
    if not costs.exists():
        return 0.0
    total = 0.0
    for line in costs.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("month") == month:
            actual = row.get("actual_usd")
            total += float(actual if actual is not None else row.get("estimated_usd", 0.0))
    return round(total, 6)


def decide(tool_input: dict[str, Any], cfg: dict[str, Any] | None = None, costs: Path = COSTS) -> tuple[str, str]:
    """Return (decision, reason) where decision is allow | ask | deny."""
    cfg = cfg or load_config()
    est, blocked = estimate(tool_input, cfg)
    if blocked:
        return "deny", blocked
    spent = month_spent(costs=costs)
    cap = cfg["monthly_cap_usd"]
    path = normalize_path(tool_input)
    if spent + est > cap:
        return "deny", f"DataForSEO monthly cap ${cap:.2f} would be exceeded: spent ${spent:.4f} + est ${est:.4f} ({path})"
    if est > cfg["ask_above_usd"]:
        return "ask", f"DataForSEO call estimated ${est:.4f} ({path}); month so far ${spent:.4f}/{cap:.2f}"
    return "allow", f"est ${est:.4f}; month ${spent:.4f}/{cap:.2f}"


def extract_cost(tool_response: Any) -> float | None:
    """Pull the top-level `cost` from a DataForSEO response (first occurrence is the request total)."""
    text = tool_response if isinstance(tool_response, str) else json.dumps(tool_response, ensure_ascii=False)
    text = text.replace('\\"', '"')
    m = _COST_FIELD.search(text)
    return float(m.group(1)) if m else None


def log_call(tool_input: dict[str, Any], tool_response: Any, cfg: dict[str, Any] | None = None,
             costs: Path = COSTS) -> dict[str, Any]:
    cfg = cfg or load_config()
    est, _ = estimate(tool_input, cfg)
    method = str(tool_input.get("method", "POST")).upper()
    # task_get responses repeat the task's cost; it was already charged (and logged) at task_post
    actual = 0.0 if method == "GET" else extract_cost(tool_response)
    row = {
        "ts": now_iso(), "month": month_key(), "path": normalize_path(tool_input),
        "method": method, "tasks": task_count(tool_input),
        "estimated_usd": est, "actual_usd": actual,
    }
    costs.parent.mkdir(parents=True, exist_ok=True)
    with costs.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row
