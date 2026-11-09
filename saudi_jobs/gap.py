"""Skills-gap tool: what does a target role ask for that the user does not list yet?"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from saudi_jobs.normalize import OTHER, ROLES, normalize_title
from saudi_jobs.skills import SkillExtractor

MUST, IMPORTANT, NICE = "Must-have", "Important", "Nice-to-have"


def tier(share_pct: float) -> str:
    return MUST if share_pct >= 50 else IMPORTANT if share_pct >= 25 else NICE


def resolve_role(role: str) -> str:
    """Accept canonical names (any case), common English or Arabic titles."""
    for r in ROLES:
        if role.strip().lower() == r.lower():
            return r
    r = normalize_title(role)
    if r == OTHER:
        raise ValueError(f"unknown role {role!r}; choose one of: {', '.join(ROLES)}")
    return r


@dataclass
class GapResult:
    role: str
    n_postings: int
    have: pd.DataFrame      # user skills that the role asks for: skill, category, share_pct
    missing: pd.DataFrame   # ranked: priority, skill, category, share_pct, tier
    unrecognised: list[str] = field(default_factory=list)
    coverage_top10_pct: float = 0.0   # how many of the role's 10 most requested skills the user has
    postings_half_matched_pct: float = 0.0  # postings where user has >= half of the listed skills


def skill_gap(df: pd.DataFrame, user_skills: list[str], target_role: str, extractor: SkillExtractor,
              top: int = 10, include_soft: bool = False, min_share_pct: float = 5.0) -> GapResult:
    """Rank the skills a user lacks for ``target_role`` by their share of that role's postings.

    ``user_skills`` may use English or Arabic names/aliases; anything that does not map to the
    taxonomy is returned in ``unrecognised`` rather than silently dropped.
    """
    role = resolve_role(target_role)
    sub = df[df["role"] == role]
    if sub.empty:
        raise ValueError(f"no postings for role {role!r} in the data")
    tax = extractor.taxonomy
    owned: set[str] = set()
    unrecognised: list[str] = []
    for raw in user_skills:
        if not raw.strip():
            continue
        found = extractor.extract(raw)
        (owned.update(found) if found else unrecognised.append(raw.strip()))

    counts: dict[str, int] = {}
    for sk in sub["skills"]:
        for s in sk:
            counts[s] = counts.get(s, 0) + 1
    n = len(sub)
    table = pd.DataFrame(
        [(s, tax.category_of(s), round(100 * c / n, 1)) for s, c in counts.items()],
        columns=["skill", "category", "share_pct"],
    ).sort_values(["share_pct", "skill"], ascending=[False, True]).reset_index(drop=True)

    have = table[table["skill"].isin(owned)].reset_index(drop=True)
    miss = table[~table["skill"].isin(owned) & (table["share_pct"] >= min_share_pct)]
    if not include_soft:
        miss = miss[miss["category"] != "Soft Skills"]
    miss = miss.head(top).reset_index(drop=True)
    miss.insert(0, "priority", range(1, len(miss) + 1))
    miss["tier"] = miss["share_pct"].map(tier)

    top10 = list(table.head(10)["skill"])
    cov = 100 * sum(s in owned for s in top10) / len(top10) if top10 else 0.0
    with_skills = [sk for sk in sub["skills"] if sk]
    half = (100 * sum(len(owned.intersection(sk)) * 2 >= len(sk) for sk in with_skills) / len(with_skills)
            if with_skills else 0.0)
    return GapResult(role, n, have, miss, unrecognised, round(cov, 1), round(half, 1))
