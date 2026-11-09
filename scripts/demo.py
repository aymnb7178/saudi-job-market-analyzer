"""End-to-end demo on SYNTHETIC data: generate -> analyse -> charts -> report -> skills gap."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from saudi_jobs import analytics as an  # noqa: E402
from saudi_jobs.charts import save_all  # noqa: E402
from saudi_jobs.cli import prepare  # noqa: E402
from saudi_jobs.datagen import generate_postings  # noqa: E402
from saudi_jobs.gap import skill_gap  # noqa: E402
from saudi_jobs.report import SYNTHETIC_NOTICE, build_report  # noqa: E402


def main() -> int:
    data = ROOT / "data" / "sample_postings.csv"
    data.parent.mkdir(exist_ok=True)
    generate_postings(1500, seed=42).to_csv(data, index=False, encoding="utf-8")
    df, tax, ext, q = prepare(str(data))
    print("!! " + SYNTHETIC_NOTICE + "\n")
    print(f"Postings: {q['postings']:,} | with salary: {q['with_salary_pct']}% | "
          f"unclassified role: {q['role_other_pct']}% | no skill found: {q['no_skill_found_pct']}%\n")
    print("Top 10 skills:\n" + an.top_skills(df, tax, n=10).to_string(index=False))
    print("\nRising / falling skills:\n" + an.trend_movers(df, n=3).to_string(index=False))
    print("\nTop pairs:\n" + an.top_pairs(df, n=5).to_string(index=False))
    g = skill_gap(df, ["Python", "إكسل", "Git"], "Data Analyst", ext, top=6)
    print(f"\nGap for {g.role} with Python, Excel, Git: covers {g.coverage_top10_pct}% of top-10 skills\n"
          + g.missing.to_string(index=False))
    docs = ROOT / "docs"
    pngs = save_all(df, tax, docs)
    (docs / "sample_report.html").write_text(build_report(df, tax, pngs, q, g), encoding="utf-8")
    print(f"\nWrote {data.relative_to(ROOT)}, docs/*.png, docs/sample_report.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
