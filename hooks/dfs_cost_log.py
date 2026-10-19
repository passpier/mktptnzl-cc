"""PostToolUse hook (mcp__dataforseo__api_request): log actual cost to research/_costs.jsonl."""

import json
import sys

from mr.budget import log_call, month_spent


def main() -> int:
    payload = json.load(sys.stdin)
    if not payload.get("tool_name", "").endswith("api_request"):
        return 0
    row = log_call(payload.get("tool_input") or {}, payload.get("tool_response"))
    cost = row["actual_usd"] if row["actual_usd"] is not None else f"~{row['estimated_usd']} (estimated)"
    print(f"[budget] {row['path']} cost ${cost}; month total ${month_spent():.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
