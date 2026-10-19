"""PreToolUse hook (mcp__dataforseo__api_request): enforce the monthly DataForSEO budget.

deny  -> blocked endpoint, priority queue, or monthly cap would be exceeded
ask   -> single call estimated above ask_above_usd
allow -> stays silent so normal permission rules apply

Fails closed: any error (bad config, corrupt _costs.jsonl) denies the call. A non-2 exit would let it through.
"""

import json
import sys

from mr.budget import decide


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not payload.get("tool_name", "").endswith("api_request"):
            return 0
        decision, reason = decide(payload.get("tool_input") or {})
    except Exception as e:
        decision = "deny"
        reason = f"guard error: {type(e).__name__}: {e} — fix config/budget.json or research/_costs.jsonl first"
    if decision == "allow":
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": f"[budget] {reason}",
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
