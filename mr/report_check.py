"""Validate a research report against the source-grading rules.

Rules enforced:
  1. Every line carrying a number cites evidence as [E#] (exempt: kill criteria, experiments, appendix,
     lines tagged [假設]/[門檻]/[assumption]/[threshold]).
  2. Every cited E# exists in research/<slug>/evidence.jsonl.
  3. Cited evidence past its TTL: severity=block -> error, severity=warn -> warning.
  4. Conclusion bullets (list items under a 結論 heading): >=1 citation, a confidence label, no tier D, >=2 independent source_groups,
     and >=1 fresh S/A/B row.
  5. Tier D cited outside the data-gap section -> error. Tier C cited anywhere -> warning (trace it).
  6. Required sections: 信心 (confidence), 資料缺口 (data gaps), 驗證實驗 (validation experiments).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from mr.ledger import DECISION_TIERS, load_index, staleness

CITE = re.compile(r"\[(E\d+)\]")
CITE_GROUP = re.compile(r"\[(E\d+(?:\s*,\s*E\d+)*)\]")
EXEMPT_TAG = re.compile(r"\[(假設|門檻|assumption|threshold)\]", re.I)
CONFIDENCE = re.compile(r"(信心|confidence)\s*[:：]?\s*\**\s*(high|medium|med|low|高|中|低)", re.I)
STRIP = [
    re.compile(r"\[E\d+(?:\s*,\s*E\d+)*\]"),
    re.compile(r"\]\([^)]*\)"),                       # markdown link targets
    re.compile(r"https?://\S+"),
    re.compile(r"\b\d{4}-\d{2}(-\d{2})?([T ][\d:+.-]+)?\b"),  # ISO dates
    re.compile(r"^\s*(\d+[.)]|[-*+>])\s+"),            # list markers
    re.compile(r"(?i)\btop\s?\d+\b|前\s?\d+\s?[名大]"),
    re.compile(r"(?i)\d\s?([-–~]\s?\d\s?)?(星|★|stars?)"),
    re.compile(r"(?i)\b(iOS|Android|v)\s?\d+(\.\d+)*\b"),
]
SECTION_KEYS = {
    "conclusion": ("結論", "conclusion"),
    "exempt": ("放棄條件", "kill criteria", "驗證實驗", "experiment", "來源附錄", "appendix", "sources"),
    "gaps": ("資料缺口", "data gap"),
}
REQUIRED = {
    "信心等級": ("信心", "confidence"),
    "資料缺口": ("資料缺口", "data gap"),
    "驗證實驗": ("驗證實驗", "experiment"),
}


@dataclass
class CheckResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cited: set[str] = field(default_factory=set)

    @property
    def ok(self) -> bool:
        return not self.errors

    def format(self) -> str:
        out = []
        if self.errors:
            out.append(f"❌ {len(self.errors)} error(s):")
            out += [f"  - {e}" for e in self.errors]
        if self.warnings:
            out.append(f"⚠️  {len(self.warnings)} warning(s):")
            out += [f"  - {w}" for w in self.warnings]
        if not out:
            out.append(f"✅ report passes source-grading checks ({len(self.cited)} evidence rows cited)")
        return "\n".join(out)


def _classify(heading: str) -> set[str]:
    h = heading.lower()
    return {name for name, keys in SECTION_KEYS.items() if any(k.lower() in h for k in keys)}


def cited_ids(line: str) -> list[str]:
    ids: list[str] = []
    for grp in CITE_GROUP.findall(line):
        ids += [x.strip() for x in grp.split(",")]
    return ids


def _has_claim_number(line: str) -> bool:
    s = line
    for pat in STRIP:
        s = pat.sub(" ", s)
    return bool(re.search(r"\d", s))


def check_report(path: Path, at: datetime | None = None) -> CheckResult:
    res = CheckResult()
    slug = path.parent.name
    index = load_index(slug)
    text = path.read_text(encoding="utf-8")

    headings: list[str] = []
    sections: set[str] = set()
    in_code = False
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line.strip() or line.strip().startswith("<!--"):
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            headings.append(m.group(2))
            # top-level (#) title resets; sub-headings inherit parent section classification
            level = len(m.group(1))
            cls = _classify(m.group(2))
            if level <= 2:
                sections = cls
            else:
                sections = sections | cls
            continue
        if re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", line):  # table separator
            continue

        ids = cited_ids(line)
        res.cited.update(ids)
        where = f"L{n}"
        snippet = line.strip()[:70]

        for eid in ids:
            rec = index.get(eid)
            if rec is None:
                res.errors.append(f"{where}: [{eid}] not found in evidence.jsonl — {snippet}")
                continue
            st = staleness(rec, at)
            if st:
                (res.errors if st.severity == "block" else res.warnings).append(f"{where}: {st.describe()} — refresh it")
            if rec["tier"] == "D" and "gaps" not in sections:
                res.errors.append(f"{where}: [{eid}] is tier D (unverifiable) — only allowed in 資料缺口 as a lead")
            if rec["tier"] == "C":
                res.warnings.append(f"{where}: [{eid}] is tier C (secondhand) — trace to the original source")

        exempt = "exempt" in sections or EXEMPT_TAG.search(line)
        if not exempt and not ids and _has_claim_number(line):
            res.errors.append(f"{where}: number without [E#] citation — {snippet}")

        is_bullet = re.match(r"^\s*([-*+]|\d+[.)])\s+", line)
        if "conclusion" in sections and "exempt" not in sections and is_bullet:
            if not ids:
                res.errors.append(f"{where}: conclusion without evidence — {snippet}")
                continue
            if not CONFIDENCE.search(line):
                res.errors.append(f"{where}: conclusion missing confidence label (信心: High/Med/Low) — {snippet}")
            recs = [index[i] for i in ids if i in index]
            groups = {r["source_group"] for r in recs}
            if len(groups) < 2:
                res.errors.append(f"{where}: conclusion needs ≥2 independent source_groups, has {sorted(groups)}")
            if not any(r["tier"] in DECISION_TIERS and not staleness(r, at) for r in recs):
                res.errors.append(f"{where}: conclusion needs ≥1 fresh S/A/B evidence row")

    joined = " ".join(h.lower() for h in headings)
    for name, keys in REQUIRED.items():
        if not any(k.lower() in joined for k in keys):
            res.errors.append(f"missing required section: {name}")
    return res
