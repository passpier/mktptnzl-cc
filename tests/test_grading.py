import json
import os
import subprocess
import sys
from datetime import timedelta

import pytest

from mr import budget, common, ledger
from mr.report_check import check_report


@pytest.fixture
def research(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "RESEARCH", tmp_path)
    monkeypatch.setattr(ledger, "RESEARCH", tmp_path)
    return tmp_path


def _row(slug, **kw):
    base = dict(kind="rating", claim="c", value=1, tier="S", source_url="https://x", source_group="apple-itunes",
                method="test")
    base.update(kw)
    return ledger.add(slug, **base)


GOOD = """# 報告
## 結論與信心等級
- 台灣記帳 App 前段競品評分數集中在 18342 [E1, E2]，信心: Med
## 競品
| App | 評分數 |
|---|---|
| X | 18342 [E1] |
## 資料缺口
- 下載量沒有一手資料
## 下一步驗證實驗
- Landing page 轉換率 > 5% 視為通過
"""


def test_good_report_passes(research):
    _row("p")
    _row("p", kind="metadata", source_group="google-play")
    (research / "p" / "report.md").write_text(GOOD, encoding="utf-8")
    res = check_report(research / "p" / "report.md")
    assert res.ok, res.format()
    assert res.cited == {"E1", "E2"}


GOOD_EN = """# Report
> Mode: idea · Market: US
## Conclusion and confidence
- Top competitors cluster around 18342 ratings [E1, E2], Confidence: Med
## Competitor map
| App | Ratings |
|---|---|
| X | 18342 [E1] |
## Viability
- Break-even needs 111 buyers a month [threshold]
## Kill criteria check
- ≥3 large apps in the top 10 → saturated
## Data gaps
- No first-party download data
## Validation experiments
- Landing page conversion > 5% passes
"""


def test_good_english_report_passes(research):
    _row("p")
    _row("p", kind="metadata", source_group="google-play")
    (research / "p" / "report.md").write_text(GOOD_EN, encoding="utf-8")
    res = check_report(research / "p" / "report.md")
    assert res.ok, res.format()
    assert not res.warnings, res.format()
    assert res.cited == {"E1", "E2"}


def test_english_conclusion_without_confidence_blocked(research):
    _row("p")
    _row("p", source_group="google-play")
    report = GOOD_EN.replace(", Confidence: Med", "")
    (research / "p" / "report.md").write_text(report, encoding="utf-8")
    res = check_report(research / "p" / "report.md")
    assert any("missing confidence label" in e for e in res.errors)


def test_uncited_number_blocked(research):
    _row("p")
    _row("p", source_group="google-play")
    report = GOOD.replace("## 資料缺口", "市場規模約 30 億美元\n## 資料缺口")
    (research / "p" / "report.md").write_text(report, encoding="utf-8")
    res = check_report(research / "p" / "report.md")
    assert any("without [E#]" in e for e in res.errors)


def test_stale_rating_blocked(research):
    at = common.now()
    old = (at.date() - timedelta(days=40)).isoformat()  # local midnight 40 days ago: age is 40.x at any hour
    _row("p", data_as_of=old)
    _row("p", source_group="google-play")
    (research / "p" / "report.md").write_text(GOOD, encoding="utf-8")
    res = check_report(research / "p" / "report.md", at=at)
    assert any("E1 is 40d old" in e for e in res.errors)


def test_conclusion_on_single_d_source_blocked(research):
    _row("p", tier="D", source_url="memory", source_group="memory", kind="market_report")
    report = GOOD.replace("[E1, E2]", "[E1]").replace("| X | 18342 [E1] |", "| X | 有 |")
    (research / "p" / "report.md").write_text(report, encoding="utf-8")
    res = check_report(research / "p" / "report.md")
    text = "\n".join(res.errors)
    assert "tier D" in text
    assert "≥2 independent source_groups" in text
    assert "fresh S/A/B" in text


def test_missing_sections_and_unknown_id(research):
    _row("p")
    (research / "p" / "report.md").write_text("# r\n## 競品\n- 評分數 99 [E9]\n", encoding="utf-8")
    res = check_report(research / "p" / "report.md")
    text = "\n".join(res.errors)
    assert "[E9] not found" in text
    for name in ("Confidence", "Data gaps", "Validation experiments"):
        assert f"missing required section: {name}" in text


def test_exempt_tags_and_sections(research):
    _row("p")
    _row("p", source_group="google-play")
    report = GOOD + "## 放棄條件\n- top 10 中 ≥7 個評分 ≥4.5 就 no-go\n## 競品補充\n- 門檻設 3 個月 [假設]\n"
    (research / "p" / "report.md").write_text(report, encoding="utf-8")
    assert check_report(research / "p" / "report.md").ok


def test_tier_c_warns(research):
    _row("p")
    _row("p", tier="C", source_group="news")
    (research / "p" / "report.md").write_text(GOOD, encoding="utf-8")
    res = check_report(research / "p" / "report.md")
    assert res.ok and any("tier C" in w for w in res.warnings)



def test_idea_report_without_viability_warns(research):
    _row("p")
    _row("p", source_group="google-play")
    path = research / "p" / "report.md"
    path.write_text(GOOD.replace("# 報告", "# 報告\n> 模式：idea"), encoding="utf-8")
    res = check_report(path)
    assert res.ok and any("Viability" in w for w in res.warnings)
    path.write_text(GOOD.replace("# 報告", "# 報告\n> 模式：idea") + "## 可行性評估\n- 待實驗\n", encoding="utf-8")
    assert not any("Viability" in w for w in check_report(path).warnings)
    path.write_text(GOOD, encoding="utf-8")
    assert not any("Viability" in w for w in check_report(path).warnings)


def test_population_and_policy_ttl(research):
    at = common.now()
    three_years = (at.date() - timedelta(days=3 * 365)).isoformat()
    pop = _row("p", kind="population", tier="A", data_as_of=three_years)
    pol = _row("p", kind="policy", tier="A", data_as_of=(at.date() - timedelta(days=200)).isoformat())
    stale = {s.id: s for s in ledger.stale_rows("p")}
    assert pop not in stale  # a 3-year-old census survey is still usable
    assert stale[pol].severity == "warn"
    year_only = _row("p", kind="population", tier="A", data_as_of=str(at.year - 6))  # docs allow `--as-of 2025`
    assert {s.id: s for s in ledger.stale_rows("p")}[year_only].severity == "warn"


CFG = {
    "monthly_cap_usd": 10.0, "ask_above_usd": 0.5, "blocked_path_patterns": ["^/v3/backlinks/"],
    "blocked_reason": "subscription", "estimates": [{"pattern": "app_listings", "usd": 0.5}], "default_usd": 0.05,
}


def _cost(tmp_path, usd):
    p = tmp_path / "_costs.jsonl"
    p.write_text(json.dumps({"month": budget.month_key(), "estimated_usd": 0.1, "actual_usd": usd}) + "\n")
    return p


def test_budget_denies_over_cap(tmp_path):
    costs = _cost(tmp_path, 9.8)
    d, reason = budget.decide({"method": "POST", "path": "/v3/app_data/apple/app_listings/search/live"}, CFG, costs)
    assert d == "deny" and "cap" in reason


def test_budget_allows_and_asks(tmp_path):
    costs = _cost(tmp_path, 1.0)
    assert budget.decide({"method": "POST", "path": "serp/google/organic/live/regular"}, CFG, costs)[0] == "allow"
    many = {"method": "POST", "path": "/v3/x", "data": [{}] * 20}  # 20 tasks * 0.05 = 1.0 > ask threshold
    assert budget.decide(many, CFG, costs)[0] == "ask"


def test_budget_blocks_backlinks_priority_and_frees_get(tmp_path):
    costs = _cost(tmp_path, 0)
    assert budget.decide({"method": "POST", "path": "/v3/backlinks/summary/live"}, CFG, costs)[0] == "deny"
    assert budget.decide({"method": "POST", "path": "/v3/x/task_post", "data": [{"priority": 2}]}, CFG, costs)[0] == "deny"
    assert budget.estimate({"method": "GET", "path": "/v3/app_data/apple/app_info/task_get/advanced/1"}, CFG) == (0.0, None)


def test_extract_cost_and_log(tmp_path):
    resp = {"content": [{"type": "text", "text": json.dumps({"status_code": 20000, "cost": 0.0012, "tasks": [{"cost": 0.0012}]})}]}
    assert budget.extract_cost(resp) == 0.0012
    costs = tmp_path / "c.jsonl"
    budget.log_call({"method": "POST", "path": "/v3/serp/google/organic/live/regular"}, resp, CFG, costs)
    budget.log_call({"method": "GET", "path": "/v3/serp/google/organic/task_get/regular/1"}, resp, CFG, costs)
    assert budget.month_spent(costs=costs) == pytest.approx(0.0012)


def _run_hook(name, root, stdin="", args=()):
    env = {**os.environ, "MR_ROOT": str(root), "PYTHONPATH": str(common.ROOT)}
    return subprocess.run([sys.executable, str(common.ROOT / "hooks" / name), *args], input=stdin,
                          capture_output=True, text=True, env=env)


def test_budget_guard_fails_closed(tmp_path):
    # MR_ROOT without config/budget.json: the guard must deny, not crash (a crash exits 1 and lets the call run)
    payload = json.dumps({"tool_name": "mcp__dataforseo__api_request", "tool_input": {"method": "POST", "path": "/v3/x"}})
    r = _run_hook("dfs_budget_guard.py", tmp_path, stdin=payload)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny" and "guard error" in out["permissionDecisionReason"]


def test_check_report_hook_blocks_on_error(tmp_path):
    d = tmp_path / "research" / "p"
    d.mkdir(parents=True)
    (d / "evidence.jsonl").write_text("{not json\n", encoding="utf-8")
    (d / "report.md").write_text(GOOD, encoding="utf-8")
    r = _run_hook("check_report.py", tmp_path, args=[str(d / "report.md")])
    assert r.returncode == 2 and "crashed" in r.stderr


def test_snapshot_velocity(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("snapshot", common.ROOT / "scripts" / "snapshot.py")
    snap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(snap)
    monkeypatch.setattr(snap, "TRACKING", tmp_path)
    d = tmp_path / "gplay-x-tw"
    d.mkdir()
    (d / "2026-10-01.json").write_text(json.dumps({"name": "X", "ratings": 1000, "real_installs": 50000}))
    (d / "2026-10-15.json").write_text(json.dumps({"name": "X", "ratings": 1280, "real_installs": 57000}))
    v = snap.velocity("gplay", "x", "tw")
    assert v["ratings_per_week"] == 140.0 and v["real_installs_per_week"] == 3500
