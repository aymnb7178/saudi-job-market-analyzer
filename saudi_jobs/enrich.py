"""Turn raw validated postings into an analysis-ready frame."""
from __future__ import annotations

import pandas as pd

from saudi_jobs.normalize import normalize_city, normalize_sector, normalize_seniority, normalize_title
from saudi_jobs.salary import parse_salary, salary_from_numbers
from saudi_jobs.skills import SkillExtractor


def enrich(df: pd.DataFrame, extractor: SkillExtractor | None = None) -> pd.DataFrame:
    """Add role, city_norm, sector_norm, seniority_norm, month, salary_* and skills columns."""
    ext = extractor or SkillExtractor()
    out = df.copy().reset_index(drop=True)
    out["role"] = out["title"].map(normalize_title)
    out["city_norm"] = out["city"].map(normalize_city)
    out["sector_norm"] = out["sector"].map(normalize_sector)
    seniority = out["seniority"] if "seniority" in out else pd.Series([None] * len(out))
    out["seniority_norm"] = [normalize_seniority(s, t) for s, t in zip(seniority, out["title"])]
    out["month"] = pd.to_datetime(out["posted_date"]).dt.strftime("%Y-%m")

    def _sal(row):
        s = parse_salary(row.get("salary")) if row.get("salary") else None
        return s or salary_from_numbers(row.get("salary_min"), row.get("salary_max"), row.get("salary_period"))

    sal = [_sal(r) for r in out.to_dict("records")]
    out["salary_monthly_min"] = [s.min_monthly if s else float("nan") for s in sal]
    out["salary_monthly_max"] = [s.max_monthly if s else float("nan") for s in sal]
    out["salary_monthly_mid"] = [s.mid_monthly if s else float("nan") for s in sal]
    out["salary_period_inferred"] = [bool(s.period_inferred) if s else False for s in sal]
    out["skills"] = [tuple(ext.extract(f"{t}\n{d}")) for t, d in zip(out["title"], out["description"])]
    return out
