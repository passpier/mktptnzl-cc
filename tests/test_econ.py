import pytest

from mr import econ


def test_asa_cap_fires_kill_from_budget():
    r = econ.asa_check(30, 1.5, 0.05, success_impressions=3000, kill_impressions=1000,
                       tap_install=1.0, rates={"d7": 0.15, "paywall_trial": 0.05})
    assert r.taps == 20 and r.impressions == 400
    assert r.budget_for_success == 225
    assert any("kill fires from budget" in i for i in r.issues)
    assert [x["readable"] for x in r.rates] == [False, False]


def test_asa_no_issues_when_budget_fits():
    r = econ.asa_check(300, 1.0, 0.1, success_impressions=2000, kill_impressions=1000)
    assert r.impressions == 3000 and not r.issues


def test_power_matches_two_proportion_formula():
    r = econ.power(0.08, 0.053, n=150)
    assert 0.9 < r.z < 1.0 and r.readable is False
    assert 1250 < r.n_required_per_arm < 1400
    assert econ.power(0.2, 0.1, n=500).readable is True


def test_breakeven_solves_both_directions():
    r = econ.breakeven(10, "month", 0.15, cpi=2, ratio=3, conversion=0.05)
    assert r.max_churn == pytest.approx(0.05 * 8.5 / 6)
    r = econ.breakeven(10, "month", 0.15, cpi=2, ratio=3, churn=0.1)
    assert r.min_conversion == pytest.approx(6 * 0.1 / 8.5)
    r = econ.breakeven(10, "month", 0.15, cpi=2)
    assert [g["churn"] for g in r.grid] == list(econ.CHURN_GRID["month"])


def test_lifetime_purchase_has_no_churn():
    r = econ.breakeven(20, "once", 0.15, cpi=2, ratio=3)
    assert r.min_conversion == pytest.approx(6 / 17) and not r.grid


def test_required_payers_annual_plan():
    r = econ.required_payers(1000, 30, "year", 0.15, conversion=0.02)
    assert r.net_monthly_per_payer == pytest.approx(2.125)
    assert r.required_payers == 471 and r.required_installs == 23550


def test_rejects_bad_inputs():
    with pytest.raises(ValueError):
        econ.breakeven(10, "week", 0.15, cpi=2)
    with pytest.raises(ValueError):
        econ.breakeven(10, "month", 1.0, cpi=2)
    with pytest.raises(ValueError):
        econ.power(0.1, 0.1)
