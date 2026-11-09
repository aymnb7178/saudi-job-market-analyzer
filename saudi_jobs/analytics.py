"""Aggregations over an enriched postings frame (see ``saudi_jobs.enrich.enrich``)."""
from __future__ import annotations

from collections import Counter
from itertools import combinations

import pandas as pd

from saudi_jobs.normalize import OTHER, ROLES, SENIORITY_LEVELS
from saudi_jobs.skills import Taxonomy


def _subset(df: pd.DataFrame, role: str | None) -> pd.DataFrame:
    return df if role is None else df[df["role"] == role]


def top_skills(df: pd.DataFrame, taxonomy: Taxonomy, n: int = 15, role: str | None = None,
               include_soft: bool = True) -> pd.DataFrame:
    """Skills ranked by the number of postings that mention them (share = % of postings)."""
    sub = _subset(df, role)
    counts = Counter(s for sk in sub["skills"] for s in sk)
    rows = [(s, taxonomy.category_of(s), c, round(100 * c / len(sub), 1)) for s, c in counts.items()
            if include_soft or taxonomy.category_of(s) != "Soft Skills"]
    out = pd.DataFrame(rows, columns=["skill", "category", "postings", "share_pct"])
    return out.sort_values(["postings", "skill"], ascending=[False, True]).head(n).reset_index(drop=True)


def skills_by_role(df: pd.DataFrame, taxonomy: Taxonomy, n: int = 8) -> dict[str, pd.DataFrame]:
    return {r: top_skills(df, taxonomy, n=n, role=r) for r in ROLES if (df["role"] == r).any()}


def skill_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Boolean posting x skill matrix."""
    skills = sorted({s for sk in df["skills"] for s in sk})
    data = {s: [s in sk for sk in df["skills"]] for s in skills}
    return pd.DataFrame(data, index=df.index, dtype=bool)


def cooccurrence(df: pd.DataFrame, skills: list[str]) -> pd.DataFrame:
    """Symmetric count matrix: cell (a, b) = postings mentioning both; diagonal = postings mentioning a."""
    m = skill_matrix(df).reindex(columns=skills, fill_value=False).astype(int)
    out = m.T.dot(m)
    out.index.name = out.columns.name = None
    return out


def top_pairs(df: pd.DataFrame, n: int = 10, min_postings: int = 20) -> pd.DataFrame:
    """Most frequent skill pairs with lift (>1 means they appear together more than chance)."""
    total = len(df)
    single = Counter(s for sk in df["skills"] for s in sk)
    pair = Counter(p for sk in df["skills"] for p in combinations(sorted(sk), 2))
    rows = [(a, b, c, round(c * total / (single[a] * single[b]), 2)) for (a, b), c in pair.items()
            if c >= min_postings]
    out = pd.DataFrame(rows, columns=["skill_a", "skill_b", "postings", "lift"])
    return out.sort_values(["postings", "skill_a"], ascending=[False, True]).head(n).reset_index(drop=True)


def monthly_trend(df: pd.DataFrame, skills: list[str]) -> pd.DataFrame:
    """Month x skill table: % of that month's postings mentioning the skill."""
    months = sorted(df["month"].unique())
    out = pd.DataFrame(0.0, index=months, columns=skills)
    for month, grp in df.groupby("month"):
        c = Counter(s for sk in grp["skills"] for s in sk)
        for s in skills:
            out.loc[month, s] = 100 * c.get(s, 0) / len(grp)
    return out.round(1)


def trend_movers(df: pd.DataFrame, n: int = 5, min_postings: int = 30) -> pd.DataFrame:
    """Change in share (percentage points) between the first and last third of the months."""
    months = sorted(df["month"].unique())
    k = max(1, len(months) // 3)
    early, late = df[df["month"].isin(months[:k])], df[df["month"].isin(months[-k:])]
    ce = Counter(s for sk in early["skills"] for s in sk)
    cl = Counter(s for sk in late["skills"] for s in sk)
    rows = []
    for s in set(ce) | set(cl):
        if ce[s] + cl[s] < min_postings:
            continue
        e, l = 100 * ce[s] / max(len(early), 1), 100 * cl[s] / max(len(late), 1)
        rows.append((s, round(e, 1), round(l, 1), round(l - e, 1)))
    out = pd.DataFrame(rows, columns=["skill", "early_pct", "late_pct", "change_pp"])
    return out.sort_values("change_pp", ascending=False).reset_index(drop=True).pipe(
        lambda d: pd.concat([d.head(n), d.tail(n)]).drop_duplicates("skill").reset_index(drop=True))


def breakdown(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Posting counts, share and median advertised monthly salary (midpoint) per value."""
    g = df.groupby(column)
    out = pd.DataFrame({
        "postings": g.size(),
        "salary_n": g["salary_monthly_mid"].count(),
        "median_salary_sar": g["salary_monthly_mid"].median().round(0),
    })
    out.insert(1, "share_pct", (100 * out["postings"] / len(df)).round(1))
    out = out.sort_values("postings", ascending=False)
    out.index.name = column
    return out.reset_index()


def seniority_split(df: pd.DataFrame) -> pd.DataFrame:
    """Role x seniority posting counts (roles other than 'Other')."""
    sub = df[df["role"] != OTHER]
    ct = pd.crosstab(sub["role"], sub["seniority_norm"]).reindex(columns=SENIORITY_LEVELS, fill_value=0)
    return ct.reindex([r for r in ROLES if r in ct.index])


def data_quality(df: pd.DataFrame, rejected: int = 0, duplicates: int = 0) -> dict[str, float | int]:
    n = len(df)
    return {
        "postings": n,
        "rejected_rows": rejected,
        "duplicates_removed": duplicates,
        "with_salary_pct": float(round(100 * df["salary_monthly_mid"].notna().mean(), 1)) if n else 0.0,
        "role_other_pct": float(round(100 * (df["role"] == OTHER).mean(), 1)) if n else 0.0,
        "city_other_pct": float(round(100 * (df["city_norm"] == OTHER).mean(), 1)) if n else 0.0,
        "seniority_unspecified_pct": float(round(100 * (df["seniority_norm"] == "Unspecified").mean(), 1)) if n else 0.0,
        "no_skill_found_pct": float(round(100 * (df["skills"].map(len) == 0).mean(), 1)) if n else 0.0,
    }


def is_synthetic(df: pd.DataFrame) -> bool:
    return "source" in df and len(df) > 0 and bool((df["source"] == "synthetic").all())
