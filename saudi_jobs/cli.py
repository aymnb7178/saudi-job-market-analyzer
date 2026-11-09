"""Command line interface: analyze, gap, skills, generate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from saudi_jobs import analytics as an
from saudi_jobs.charts import save_all
from saudi_jobs.datagen import generate_postings
from saudi_jobs.enrich import enrich
from saudi_jobs.gap import skill_gap
from saudi_jobs.loader import load_postings
from saudi_jobs.report import SYNTHETIC_NOTICE, build_report
from saudi_jobs.skills import SkillExtractor, Taxonomy

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 20)


def prepare(path: str, taxonomy_path: str | None = None):
    """Load, validate and enrich a file. Returns (frame, taxonomy, extractor, quality)."""
    tax = Taxonomy.from_json(taxonomy_path)
    ext = SkillExtractor(tax)
    res = load_postings(path)
    df = enrich(res.frame, ext)
    return df, tax, ext, an.data_quality(df, len(res.rejected), res.duplicates_removed)


def _banner(df: pd.DataFrame) -> None:
    if an.is_synthetic(df):
        print(f"!! {SYNTHETIC_NOTICE}\n")


def cmd_analyze(a: argparse.Namespace) -> int:
    df, tax, _, q = prepare(a.input, a.taxonomy)
    _banner(df)
    print(f"Postings analysed: {q['postings']:,}  (rejected {q['rejected_rows']}, duplicates removed "
          f"{q['duplicates_removed']}, with salary {q['with_salary_pct']}%)\n")
    print("Top skills:\n" + an.top_skills(df, tax, n=a.top).to_string(index=False))
    print("\nRising / falling skills (share change, first vs last third of months):\n"
          + an.trend_movers(df, n=3).to_string(index=False))
    print("\nBy city:\n" + an.breakdown(df, "city_norm").head(6).to_string(index=False))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pngs = save_all(df, tax, a.charts_dir) if a.charts_dir else save_all(df, tax, out.parent / (out.stem + "_charts"))
    out.write_text(build_report(df, tax, pngs, q), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


def cmd_gap(a: argparse.Namespace) -> int:
    df, tax, ext, _ = prepare(a.input, a.taxonomy)
    skills = [s for s in a.skills.replace("،", ",").split(",") if s.strip()]
    try:
        g = skill_gap(df, skills, a.role, ext, top=a.top, include_soft=a.include_soft)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"role": g.role, "postings": g.n_postings, "have": g.have.to_dict("records"),
                          "missing": g.missing.to_dict("records"), "unrecognised": g.unrecognised,
                          "coverage_top10_pct": g.coverage_top10_pct,
                          "synthetic_data": an.is_synthetic(df)}, ensure_ascii=False, indent=2))
        return 0
    _banner(df)
    print(f"Target role: {g.role} ({g.n_postings:,} postings)")
    print(f"You cover {g.coverage_top10_pct}% of the role's top-10 skills; "
          f"{g.postings_half_matched_pct}% of postings list skills you half-match or better.")
    if g.unrecognised:
        print("Not in taxonomy (ignored): " + ", ".join(g.unrecognised))
    print("\nSkills you have that this role asks for:\n" + (g.have.to_string(index=False) if len(g.have) else "  none"))
    print("\nLearning priority (missing skills, most demanded first):\n" + g.missing.to_string(index=False))
    return 0


def cmd_skills(a: argparse.Namespace) -> int:
    tax = Taxonomy.from_json(a.taxonomy)
    if a.text is not None:
        print(json.dumps(SkillExtractor(tax).extract(a.text), ensure_ascii=False))
        return 0
    if not a.input:
        print("error: give an input file or --text", file=sys.stderr)
        return 2
    df, tax, _, _ = prepare(a.input, a.taxonomy)
    _banner(df)
    from saudi_jobs.gap import resolve_role
    role = resolve_role(a.role) if a.role else None
    t = an.top_skills(df, tax, n=a.top, role=role)
    if a.category:
        t = t[t["category"].str.lower() == a.category.lower()]
    print(t.to_string(index=False))
    return 0


def cmd_generate(a: argparse.Namespace) -> int:
    df = generate_postings(a.n, a.seed)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False, encoding="utf-8")
    print(f"Wrote {len(df):,} SYNTHETIC postings to {a.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="saudi-jobs", description="Job-posting analytics (CSV/JSON in).")
    sub = p.add_subparsers(dest="cmd", required=True)
    tx = argparse.ArgumentParser(add_help=False)
    tx.add_argument("--taxonomy", help="path to a custom skills_taxonomy.json")

    s = sub.add_parser("analyze", parents=[tx], help="full analysis + HTML report")
    s.add_argument("input")
    s.add_argument("--out", default="output/report.html")
    s.add_argument("--charts-dir", help="where to write PNG charts (default: next to the report)")
    s.add_argument("--top", type=int, default=15)
    s.set_defaults(func=cmd_analyze)

    s = sub.add_parser("gap", parents=[tx], help="skills gap for a target role")
    s.add_argument("input")
    s.add_argument("--skills", required=True, help="comma-separated, English or Arabic")
    s.add_argument("--role", required=True)
    s.add_argument("--top", type=int, default=10)
    s.add_argument("--include-soft", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_gap)

    s = sub.add_parser("skills", parents=[tx], help="top skills in a file, or extract from --text")
    s.add_argument("input", nargs="?")
    s.add_argument("--text")
    s.add_argument("--role")
    s.add_argument("--category")
    s.add_argument("--top", type=int, default=15)
    s.set_defaults(func=cmd_skills)

    s = sub.add_parser("generate", help="write a SYNTHETIC demo dataset")
    s.add_argument("--out", default="data/sample_postings.csv")
    s.add_argument("--n", type=int, default=1500)
    s.add_argument("--seed", type=int, default=42)
    s.set_defaults(func=cmd_generate)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
