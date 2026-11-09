"""Editable skill taxonomy + word-boundary-safe skill extractor."""
from __future__ import annotations

import json
import re
from pathlib import Path

from saudi_jobs.textnorm import alias_regex, normalize_text

DEFAULT_TAXONOMY = Path(__file__).parent / "data" / "skills_taxonomy.json"
CERT_CATEGORY = "Certifications"


class Taxonomy:
    """category -> canonical skill -> aliases. Canonical name is an implicit alias."""

    def __init__(self, categories: dict[str, dict[str, list[str]]]):
        if not categories:
            raise ValueError("taxonomy has no categories")
        self.categories = categories
        self._category_of: dict[str, str] = {}
        self._aliases: dict[str, list[str]] = {}
        seen: dict[str, str] = {}
        for cat, skills in categories.items():
            for skill, aliases in skills.items():
                if skill in self._category_of:
                    raise ValueError(f"duplicate skill name: {skill}")
                self._category_of[skill] = cat
                allal = [skill, *aliases]
                self._aliases[skill] = allal
                for a in allal:
                    key = normalize_text(a)
                    if not key:
                        raise ValueError(f"empty alias in skill {skill}")
                    if key in seen and seen[key] != skill:
                        raise ValueError(f"alias {a!r} belongs to both {seen[key]!r} and {skill!r}")
                    seen[key] = skill

    @classmethod
    def from_json(cls, path: str | Path | None = None) -> "Taxonomy":
        with open(path or DEFAULT_TAXONOMY, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or "categories" not in data:
            raise ValueError("taxonomy JSON needs a top-level 'categories' object")
        return cls(data["categories"])

    @property
    def skills(self) -> list[str]:
        return list(self._category_of)

    def category_of(self, skill: str) -> str:
        return self._category_of[skill]

    def aliases(self, skill: str) -> list[str]:
        return list(self._aliases[skill])


class SkillExtractor:
    """Finds taxonomy skills in free text (English or Arabic).

    Matching is case-insensitive, Arabic-normalised and word-boundary safe
    ("Java" does not match "JavaScript"; "AI" does not match "maintain").
    If a match is fully contained in a longer match of a different skill, the longer
    one wins ("Excel Macros" -> VBA, not Excel), except for certifications, so
    "AWS Certified" still counts AWS.
    """

    def __init__(self, taxonomy: Taxonomy | None = None):
        self.taxonomy = taxonomy or Taxonomy.from_json()
        self._patterns: list[tuple[str, re.Pattern[str]]] = []
        for skill in self.taxonomy.skills:
            alts = sorted({normalize_text(a) for a in self.taxonomy.aliases(skill)}, key=len, reverse=True)
            self._patterns.append((skill, re.compile("|".join(alias_regex(a) for a in alts))))

    def extract(self, text: object) -> list[str]:
        norm = normalize_text(text)
        if not norm:
            return []
        spans: list[tuple[str, int, int]] = []
        for skill, pat in self._patterns:
            for m in pat.finditer(norm):
                spans.append((skill, m.start(), m.end()))
        keep: set[str] = set()
        for skill, s, e in spans:
            dominated = any(
                o != skill
                and os_ <= s
                and e <= oe
                and (oe - os_) > (e - s)
                and self.taxonomy.category_of(o) != CERT_CATEGORY
                for o, os_, oe in spans
            )
            if not dominated:
                keep.add(skill)
        return sorted(keep)
