"""PostToolUse hook (Write|Edit): validate research/<slug>/report.md against source-grading rules.

Also usable by hand: uv run hooks/check_report.py research/<slug>/report.md
Exit 2 feeds the violations back to Claude so it must fix them.
"""

import json
import re
import sys
from pathlib import Path

from mr.report_check import check_report

REPORT = re.compile(r"(^|/)research/[^/]+/report\.md$")


def main() -> int:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        payload = json.load(sys.stdin)
        fp = (payload.get("tool_input") or {}).get("file_path", "")
        if not REPORT.search(fp):
            return 0
        path = Path(fp)
    if not path.exists():
        return 0
    try:
        res = check_report(path.resolve())
    except Exception as e:  # exit 1 would let the report through unchecked; fail closed
        print(f"source-grading check crashed for {path}: {type(e).__name__}: {e}\n"
              "Fix the evidence.jsonl row or report that caused it, then save the report again.", file=sys.stderr)
        return 2
    msg = res.format()
    if res.ok:
        print(msg)
        return 0
    print(f"source-grading check failed for {path}:\n{msg}\n"
          "Fix: cite each number as [E#] from evidence.jsonl, refresh stale rows, "
          "or move unverifiable items to 資料缺口.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
