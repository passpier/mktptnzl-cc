"""Evidence ledger CLI.

  uv run scripts/ledger.py add <slug> --kind rating --claim "..." --value 123 --tier S \
      --url https://... --group apple-itunes --method "manual: pricing page" [--unit ratings]
      [--published 2026-09-01] [--as-of 2026-10] [--raw raw/x.json] [--cost 0.002] [--note ...]
  uv run scripts/ledger.py list <slug> [--tier D]
  uv run scripts/ledger.py stale <slug>          # rows past TTL -> re-fetch these (refresh mode)
  uv run scripts/ledger.py render <slug> [--report research/<slug>/report.md]   # sources appendix
  uv run scripts/ledger.py costs                  # DataForSEO spend this month
"""

import argparse
import json
import sys
from pathlib import Path

from mr import ledger
from mr.budget import COSTS, month_spent
from mr.report_check import cited_ids


def _value(s: str):
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return s


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add")
    a.add_argument("slug")
    a.add_argument("--kind", required=True, choices=sorted(ledger.TTL_POLICY))
    a.add_argument("--claim", required=True)
    a.add_argument("--value", required=True, type=_value)
    a.add_argument("--tier", required=True, choices=ledger.TIERS)
    a.add_argument("--url", required=True, help="source URL; use 'memory' for model knowledge (tier D)")
    a.add_argument("--group", required=True, help="independence group, e.g. apple-itunes, dataforseo, ptt")
    a.add_argument("--method", required=True)
    a.add_argument("--unit")
    a.add_argument("--published")
    a.add_argument("--as-of", dest="as_of")
    a.add_argument("--raw")
    a.add_argument("--cost", type=float, default=0.0)
    a.add_argument("--note")

    ls = sub.add_parser("list")
    ls.add_argument("slug")
    ls.add_argument("--tier", choices=ledger.TIERS)

    st = sub.add_parser("stale")
    st.add_argument("slug")

    r = sub.add_parser("render")
    r.add_argument("slug")
    r.add_argument("--report", type=Path, help="only include rows cited in this report")

    sub.add_parser("costs")

    args = ap.parse_args()
    if args.cmd == "add":
        if args.tier == "D" and args.url != "memory" and not args.note:
            print("hint: tier D rows should carry --note explaining why they cannot be verified", file=sys.stderr)
        eid = ledger.add(
            args.slug, kind=args.kind, claim=args.claim, value=args.value, tier=args.tier,
            source_url=args.url, source_group=args.group, method=args.method, unit=args.unit,
            published_at=args.published, data_as_of=args.as_of, raw_path=args.raw,
            cost_usd=args.cost, note=args.note,
        )
        print(eid)
    elif args.cmd == "list":
        for row in ledger.load(args.slug):
            if not args.tier or row["tier"] == args.tier:
                print(json.dumps(row, ensure_ascii=False))
    elif args.cmd == "stale":
        rows = ledger.load_index(args.slug)
        stale = ledger.stale_rows(args.slug)
        for s in stale:
            r_ = rows[s.id]
            print(f"{s.describe()} | {r_['kind']} | {r_['claim']} | {r_['method']}")
        if not stale:
            print("no stale evidence")
    elif args.cmd == "render":
        cited = set(cited_ids(args.report.read_text(encoding="utf-8"))) if args.report else None
        print(ledger.render_appendix(args.slug, cited))
    elif args.cmd == "costs":
        print(f"DataForSEO spend this month: ${month_spent():.4f} (log: {COSTS})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
