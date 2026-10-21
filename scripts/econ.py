"""Break-even thresholds and experiment readability (viability-check). Pure arithmetic: writes no ledger rows.

  uv run scripts/econ.py breakeven --price 29.99 --period year --commission 0.15 --cpi 3 [--ratio 3]
      [--conversion 0.03 | --churn 0.5]          # -> max churn / min conversion for LTV:CPI >= ratio
  uv run scripts/econ.py payers --target 1000 --price 29.99 --period year --commission 0.15 [--conversion 0.03]
  uv run scripts/econ.py power --p1 0.08 --p2 0.053 [--n 150]
  uv run scripts/econ.py asa-check --budget 30 --cpt 1.5 --ttr 0.05 [--success-impressions 3000]
      [--kill-impressions 1000] [--tap-install 0.5 --rate d7=0.15 --rate paywall_trial=0.05]

Inputs are cited ledger rows (price, commission) or founder assumptions. Outputs go into the report as
[門檻] lines or experiment thresholds, never as an LTV or revenue estimate. --rate expected events assume
every install reaches that step, so they are an upper bound.
"""

import argparse
import json
import sys

from mr import econ


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.2%}"


def _rate(s: str) -> tuple[str, float]:
    name, _, v = s.partition("=")
    return name, float(v)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("breakeven")
    p = sub.add_parser("payers")
    for s in (b, p):
        s.add_argument("--price", type=float, required=True)
        s.add_argument("--period", choices=econ.PERIODS, required=True)
        s.add_argument("--commission", type=float, required=True, help="cite Apple/Google docs, e.g. 0.15")
        s.add_argument("--conversion", type=float, help="install -> paying share")
    b.add_argument("--cpi", type=float, required=True, help="cost per install (US$); for organic, your time cost")
    b.add_argument("--ratio", type=float, default=3.0, help="target LTV:CPI [門檻]")
    b.add_argument("--churn", type=float, help="churn per billing period")
    p.add_argument("--target", type=float, required=True, help="target net revenue per month (US$) [假設]")

    w = sub.add_parser("power")
    w.add_argument("--p1", type=float, required=True)
    w.add_argument("--p2", type=float, required=True)
    w.add_argument("--n", type=int, help="planned sample per arm")
    w.add_argument("--alpha", type=float, default=0.05)
    w.add_argument("--power", type=float, default=0.8)

    a = sub.add_parser("asa-check")
    a.add_argument("--budget", type=float, required=True)
    a.add_argument("--cpt", type=float, required=True)
    a.add_argument("--ttr", type=float, required=True)
    a.add_argument("--success-impressions", type=float)
    a.add_argument("--kill-impressions", type=float)
    a.add_argument("--tap-install", type=float, help="tap -> install share [假設]")
    a.add_argument("--rate", type=_rate, action="append", default=[], help="name=threshold on installs, repeatable")

    args = ap.parse_args()
    if args.cmd == "breakeven":
        r = econ.breakeven(args.price, args.period, args.commission, args.cpi, args.ratio, args.conversion, args.churn)
        lines = [f"net per {r.period}: US${r.net_per_period}; LTV per install needed: US${r.required_ltv_per_install} "
                 f"(= {r.ratio} x CPI US${r.cpi})"]
        if r.max_churn is not None:
            lines.append(f"max churn per {r.period} at conversion {_pct(args.conversion)}: {_pct(r.max_churn)}")
        if r.min_conversion is not None:
            lines.append(f"min install->paid conversion: {_pct(r.min_conversion)}")
        lines += [f"  churn {_pct(g['churn'])}/{r.period} -> min conversion {_pct(g['min_conversion'])}" for g in r.grid]
    elif args.cmd == "payers":
        r = econ.required_payers(args.target, args.price, args.period, args.commission, args.conversion)
        unit = "new buyers per month" if args.period == "once" else "paying subscribers"
        lines = [f"net per payer per month: US${r.net_monthly_per_payer}; {unit} needed: {r.required_payers}"]
        if r.required_installs:
            lines.append(f"installs needed at conversion {_pct(args.conversion)}: {r.required_installs}")
    elif args.cmd == "power":
        r = econ.power(args.p1, args.p2, args.n, args.alpha, args.power)
        lines = [f"n per arm for {r.power:.0%} power at alpha {r.alpha}: {r.n_required_per_arm}"]
        if r.n:
            lines.append(f"at n={r.n} per arm: z={r.z} -> {'readable' if r.readable else 'NOT readable (noise)'}")
    else:
        r = econ.asa_check(args.budget, args.cpt, args.ttr, args.success_impressions, args.kill_impressions,
                           args.tap_install, dict(args.rate))
        lines = [f"cap buys ~{r.taps} taps, ~{r.impressions} impressions"
                 + (f", ~{r.installs} installs" if r.installs is not None else "")]
        lines += [f"ISSUE: {i}" for i in r.issues] or ["no issues"]
    print(json.dumps(econ.as_dict(r), ensure_ascii=False) if args.json else "\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
