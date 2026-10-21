"""Break-even and experiment-readability arithmetic for the viability check.

Nothing here estimates downloads or revenue. Every function turns inputs the caller already has
(observed price points, Apple's commission, a CPI budget, a founder target) into *required* thresholds,
or checks whether an experiment's thresholds can be read at all with its budget and traffic.

LTV per install = conversion x net price per period / churn per period
  - net price = price x (1 - commission)
  - churn is per billing period: monthly churn for monthly plans, annual non-renewal for annual plans
  - period "once" (lifetime purchase) has no churn: LTV per install = conversion x net price
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from statistics import NormalDist

PERIODS = ("month", "year", "once")
MIN_COUNT = 5  # expected events below this make a rate unreadable
# Scenario rows only, not benchmarks: churn per billing period to tabulate when neither churn nor conversion is known.
CHURN_GRID = {"month": (0.05, 0.1, 0.15, 0.2, 0.3), "year": (0.3, 0.5, 0.7, 0.9)}


def _net(price: float, commission: float) -> float:
    if not 0 <= commission < 1:
        raise ValueError(f"commission must be in [0, 1), got {commission}")
    return price * (1 - commission)


def _check_period(period: str) -> None:
    if period not in PERIODS:
        raise ValueError(f"period must be one of {PERIODS}, got {period!r}")


@dataclass
class Breakeven:
    price: float
    period: str
    commission: float
    cpi: float
    ratio: float
    net_per_period: float
    required_ltv_per_install: float
    max_churn: float | None = None          # given conversion: churn above this breaks the ratio
    min_conversion: float | None = None     # given churn (or a lifetime purchase): conversion below this breaks it
    grid: list[dict] = field(default_factory=list)  # churn -> min conversion, when neither is given


def breakeven(price: float, period: str, commission: float, cpi: float, ratio: float = 3.0,
              conversion: float | None = None, churn: float | None = None,
              churn_grid: tuple[float, ...] | None = None) -> Breakeven:
    """Thresholds at which LTV per install / CPI reaches `ratio`."""
    _check_period(period)
    if cpi <= 0 or ratio <= 0:
        raise ValueError("cpi and ratio must be positive")
    net = _net(price, commission)
    need = ratio * cpi
    out = Breakeven(price, period, commission, cpi, ratio, round(net, 4), round(need, 4))
    if period == "once":
        out.min_conversion = need / net
        return out
    if conversion is not None:
        out.max_churn = conversion * net / need
    if churn is not None:
        out.min_conversion = need * churn / net
    if conversion is None and churn is None:
        grid = churn_grid or CHURN_GRID[period]
        out.grid = [{"churn": c, "min_conversion": need * c / net} for c in grid]
    return out


@dataclass
class Payers:
    target_net_monthly: float
    net_monthly_per_payer: float
    required_payers: int
    required_installs: int | None = None


def required_payers(target_net_monthly: float, price: float, period: str, commission: float,
                    conversion: float | None = None) -> Payers:
    """Reverse market check: paying users (and installs, given a conversion) needed for a monthly net target.

    Lifetime purchases are not recurring, so `required_payers` means new buyers per month in that case.
    """
    _check_period(period)
    net = _net(price, commission)
    per_month = net / 12 if period == "year" else net
    payers = math.ceil(target_net_monthly / per_month)
    installs = math.ceil(payers / conversion) if conversion else None
    return Payers(target_net_monthly, round(per_month, 4), payers, installs)


@dataclass
class Power:
    p1: float
    p2: float
    alpha: float
    power: float
    n_required_per_arm: int
    n: int | None = None
    z: float | None = None
    readable: bool | None = None


def power(p1: float, p2: float, n: int | None = None, alpha: float = 0.05, power_: float = 0.8) -> Power:
    """Two-proportion z test (two-sided): z at n per arm, and n per arm needed for the given power."""
    if p1 == p2:
        raise ValueError("p1 and p2 must differ")
    nd = NormalDist()
    za, zb = nd.inv_cdf(1 - alpha / 2), nd.inv_cdf(power_)
    var = p1 * (1 - p1) + p2 * (1 - p2)
    need = math.ceil((za + zb) ** 2 * var / (p1 - p2) ** 2)
    out = Power(p1, p2, alpha, power_, need)
    if n:
        out.n = n
        out.z = round(abs(p1 - p2) / math.sqrt(var / n), 3)
        out.readable = out.z >= za
    return out


@dataclass
class AsaCheck:
    budget: float
    cpt: float
    ttr: float
    taps: float
    impressions: float
    installs: float | None = None
    budget_for_success: float | None = None
    issues: list[str] = field(default_factory=list)
    rates: list[dict] = field(default_factory=list)


def asa_check(budget: float, cpt: float, ttr: float, success_impressions: float | None = None,
              kill_impressions: float | None = None, tap_install: float | None = None,
              rates: dict[str, float] | None = None) -> AsaCheck:
    """What a capped Apple Search Ads test can buy, and whether its thresholds are reachable and readable.

    Impressions stop when the budget runs out, so an impression floor can fire because of the cap, not demand.
    """
    if min(budget, cpt, ttr) <= 0:
        raise ValueError("budget, cpt and ttr must be positive")
    taps = budget / cpt
    imps = taps / ttr
    out = AsaCheck(budget, cpt, ttr, round(taps, 1), round(imps))
    if success_impressions:
        out.budget_for_success = round(success_impressions * ttr * cpt, 2)
        if out.budget_for_success > budget:
            out.issues.append(f"success needs {success_impressions:.0f} impressions = US${out.budget_for_success} "
                              f"at this TTR and CPT, above the US${budget} cap")
    if kill_impressions and imps < kill_impressions:
        out.issues.append(f"the cap buys only ~{imps:.0f} impressions at TTR {ttr:.0%}, below the kill floor "
                          f"{kill_impressions:.0f}: the kill fires from budget, not demand")
    if tap_install:
        out.installs = round(taps * tap_install, 1)
        for name, rate in (rates or {}).items():
            exp = out.installs * rate
            ok = exp >= MIN_COUNT
            out.rates.append({"rate": name, "threshold": rate, "expected_events": round(exp, 2), "readable": ok})
            if not ok:
                out.issues.append(f"{name} ≥{rate:.0%} on ~{out.installs:.0f} installs is ~{exp:.2f} events "
                                  f"(<{MIN_COUNT}): unreadable, treat as directional")
    return out


def as_dict(obj) -> dict:
    return asdict(obj)
