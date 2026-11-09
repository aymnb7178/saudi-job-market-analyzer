"""Loader, analytics, skills gap, report and CLI."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from saudi_jobs import analytics as an
from saudi_jobs.charts import save_all
from saudi_jobs.cli import main
from saudi_jobs.datagen import generate_postings
from saudi_jobs.gap import skill_gap
from saudi_jobs.loader import load_postings
from saudi_jobs.report import SYNTHETIC_NOTICE, build_report


def test_generator_is_deterministic_and_flagged():
    a, b = generate_postings(50, seed=3), generate_postings(50, seed=3)
    pd.testing.assert_frame_equal(a, b)
    assert (a["source"] == "synthetic").all()


def test_loader_csv_json_rejects_and_dedupes(tmp_path):
    base = {"title": "Data Analyst", "company": "X", "city": "Riyadh", "sector": "Telecom",
            "posted_date": "2026-01-05", "description": "SQL"}
    rows = [base, dict(base), {**base, "title": " "}, {**base, "posted_date": "not a date"}]
    p = tmp_path / "in.json"
    p.write_text(json.dumps({"postings": rows}), encoding="utf-8")
    res = load_postings(p)
    assert len(res.frame) == 1 and res.duplicates_removed == 1 and len(res.rejected) == 2
    pd.DataFrame(rows[:1]).to_csv(tmp_path / "in.csv", index=False)
    assert len(load_postings(tmp_path / "in.csv").frame) == 1


def test_loader_errors(tmp_path):
    (tmp_path / "bad.csv").write_text("title,company\na,b\n")
    with pytest.raises(ValueError, match="missing required"):
        load_postings(tmp_path / "bad.csv")
    (tmp_path / "x.txt").write_text("hi")
    with pytest.raises(ValueError, match="unsupported"):
        load_postings(tmp_path / "x.txt")


def test_enrich_columns_and_roles(frame):
    for c in ["role", "city_norm", "sector_norm", "seniority_norm", "month", "salary_monthly_mid", "skills"]:
        assert c in frame
    assert set(frame["role"]) >= {"Data Analyst", "IT Support Specialist", "Python Developer",
                                  "AI/Automation Engineer"}
    assert frame["salary_monthly_mid"].dropna().between(2000, 60000).all()


def test_top_skills_shares_are_consistent(frame, taxonomy):
    t = an.top_skills(frame, taxonomy, n=5)
    assert t["postings"].is_monotonic_decreasing
    top = t.iloc[0]
    assert top["share_pct"] == round(100 * top["postings"] / len(frame), 1)
    py = an.top_skills(frame, taxonomy, n=1, role="Python Developer").iloc[0]
    assert py["skill"] == "Python" and py["share_pct"] >= 95


def test_cooccurrence_symmetric_with_counts_on_diagonal(frame, taxonomy):
    skills = list(an.top_skills(frame, taxonomy, n=6)["skill"])
    c = an.cooccurrence(frame, skills)
    assert (c.values == c.values.T).all()
    s = skills[0]
    assert c.loc[s, s] == sum(s in sk for sk in frame["skills"])


def test_monthly_trend_and_breakdowns(frame):
    t = an.monthly_trend(frame, ["Python", "SQL"])
    assert t.index.is_monotonic_increasing and ((t >= 0) & (t <= 100)).all().all()
    assert an.breakdown(frame, "city_norm")["postings"].sum() == len(frame)
    assert an.seniority_split(frame).values.sum() <= len(frame)


def test_trend_detects_planted_rise(frame):
    big = generate_postings(1500, seed=42)
    from saudi_jobs.enrich import enrich
    m = an.trend_movers(enrich(big), n=5)
    assert m.loc[m["skill"] == "LLMs", "change_pp"].iloc[0] > 0


def test_gap_ranks_missing_by_demand(frame, extractor):
    g = skill_gap(frame, ["Python", "بايثون", "Excel", "Klingon"], "Data Analyst", extractor)
    assert g.unrecognised == ["Klingon"]
    assert "Python" not in set(g.missing["skill"]) and "Excel" not in set(g.missing["skill"])
    assert g.missing["share_pct"].is_monotonic_decreasing
    assert list(g.missing["priority"]) == list(range(1, len(g.missing) + 1))
    assert "Soft Skills" not in set(g.missing["category"])
    assert 0 <= g.coverage_top10_pct <= 100


def test_gap_accepts_arabic_role_and_rejects_unknown(frame, extractor):
    assert skill_gap(frame, ["SQL"], "محلل بيانات", extractor).role == "Data Analyst"
    with pytest.raises(ValueError, match="unknown role"):
        skill_gap(frame, ["SQL"], "Astronaut", extractor)


def test_report_has_synthetic_notice_first_and_inline_images(frame, taxonomy, tmp_path):
    pngs = save_all(frame, taxonomy, tmp_path)
    assert len(list(tmp_path.glob("*.png"))) == 5
    html = build_report(frame, taxonomy, pngs)
    assert html.index(SYNTHETIC_NOTICE[:30]) < html.index("<h1>")
    assert html.count("data:image/png;base64,") == 5 and "<script" not in html and "http" not in html.lower()


def test_cli_end_to_end(tmp_path, capsys):
    csv = tmp_path / "p.csv"
    assert main(["generate", "--out", str(csv), "--n", "200", "--seed", "1"]) == 0
    assert main(["analyze", str(csv), "--out", str(tmp_path / "r.html")]) == 0
    out = capsys.readouterr().out
    assert "SYNTHETIC" in out and (tmp_path / "r.html").exists()
    assert main(["gap", str(csv), "--skills", "Python,Excel", "--role", "Data Analyst", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["role"] == "Data Analyst" and payload["synthetic_data"] is True
    assert main(["skills", "--text", "نحتاج مطور بايثون مع SQL"]) == 0
    assert json.loads(capsys.readouterr().out) == ["Python", "SQL"]
    assert main(["gap", str(csv), "--skills", "x", "--role", "Nope"]) == 2
