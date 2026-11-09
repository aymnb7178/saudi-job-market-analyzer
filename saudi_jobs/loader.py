"""Load and validate job postings from CSV or JSON."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ValidationError, field_validator

REQUIRED = ["title", "company", "city", "sector", "posted_date", "description"]
OPTIONAL = ["salary", "salary_min", "salary_max", "salary_period", "seniority", "source"]


class JobPosting(BaseModel):
    title: str
    company: str
    city: str
    sector: str
    posted_date: date
    description: str
    salary: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_period: str | None = None
    seniority: str | None = None
    source: str | None = None

    @field_validator("title", "company", "city", "sector", "description")
    @classmethod
    def _non_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


@dataclass
class LoadResult:
    frame: pd.DataFrame
    rejected: list[tuple[int, str]] = field(default_factory=list)
    duplicates_removed: int = 0


def _read_raw(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("postings", data.get("data"))
        if not isinstance(data, list):
            raise ValueError("JSON must be a list of postings or an object with a 'postings' list")
        return pd.DataFrame(data)
    raise ValueError(f"unsupported input format {suffix!r} (use .csv or .json)")


def load_postings(path: str | Path) -> LoadResult:
    """Read, validate and de-duplicate postings. Bad rows are collected, not fatal."""
    raw = _read_raw(Path(path))
    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")
    raw = raw.copy()
    raw["posted_date"] = pd.to_datetime(raw["posted_date"], errors="coerce", format="mixed").dt.date
    rows, rejected = [], []
    for idx, rec in enumerate(raw.to_dict("records")):
        rec = {k: (None if (v is None or (isinstance(v, float) and v != v) or v is pd.NaT or v == "") else v)
               for k, v in rec.items() if k in REQUIRED + OPTIONAL}
        try:
            rows.append(JobPosting.model_validate(rec).model_dump())
        except ValidationError as exc:
            rejected.append((idx, "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in exc.errors())))
    cols = REQUIRED + OPTIONAL
    frame = pd.DataFrame(rows, columns=cols)
    before = len(frame)
    frame = frame.drop_duplicates(subset=["title", "company", "city", "posted_date", "description"])
    frame = frame.reset_index(drop=True)
    return LoadResult(frame, rejected, before - len(frame))
