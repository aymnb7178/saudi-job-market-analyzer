"""Salary parsing to SAR per month (English + Arabic, ranges, k-suffix, annual/monthly)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from saudi_jobs.textnorm import normalize_text

_NUM = re.compile(r"(\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(k\b|الف\b)?")
_FOREIGN = re.compile(r"\b(usd|eur|gbp|aed|egp|kwd|qar|inr)\b|[$€£]|دولار|درهم|يورو")
_MONTH = re.compile(r"month|monthly|/\s*mo\b|per mo\b|شهر")
_YEAR = re.compile(r"year|yearly|annual|annum|/\s*yr\b|p\.a\.|سنو|سنه|عام")
_OTHER_PERIOD = re.compile(r"\b(hour|hourly|week|weekly|day|daily)\b|ساعه|اسبوع|يومي")
ANNUAL_THRESHOLD = 40_000  # heuristic used only when the text names no period


@dataclass(frozen=True)
class Salary:
    min_monthly: float
    max_monthly: float
    period: str            # "month" or "year" (as stated or inferred)
    period_inferred: bool  # True when the text did not say and the heuristic was used
    raw: str

    @property
    def mid_monthly(self) -> float:
        return (self.min_monthly + self.max_monthly) / 2


def _finalize(lo: float, hi: float, period: str | None, raw: str) -> Salary | None:
    if lo > hi:
        lo, hi = hi, lo
    inferred = period is None
    if inferred:
        period = "year" if hi >= ANNUAL_THRESHOLD else "month"
    div = 12 if period == "year" else 1
    lo_m, hi_m = lo / div, hi / div
    if hi_m < 500 or hi_m > 1_000_000 or lo_m <= 0:
        return None
    return Salary(round(lo_m, 2), round(hi_m, 2), period, inferred, raw)


def parse_salary(text: object) -> Salary | None:
    """Parse free text like '8,000-12,000 SAR/month' or '96k - 120k ريال سنويا'.

    Assumes SAR when no currency is given; returns None for other currencies,
    hourly/daily/weekly pay, or unparseable text. Only the first two numbers are used.
    """
    raw = "" if text is None or (isinstance(text, float) and text != text) else str(text)
    t = normalize_text(raw)
    if not t or _FOREIGN.search(t) or _OTHER_PERIOD.search(t):
        return None
    nums = [(m.group(1), m.group(2)) for m in _NUM.finditer(t)][:2]
    if not nums:
        return None
    vals = [float(n.replace(",", "")) * (1000 if k else 1) for n, k in nums]
    if len(vals) == 2 and bool(nums[1][1]) != bool(nums[0][1]):  # "10-12k"
        i = 0 if nums[1][1] else 1
        if vals[i] < 1000:
            vals[i] *= 1000
    lo, hi = vals[0], vals[-1]
    period = "year" if _YEAR.search(t) else "month" if _MONTH.search(t) else None
    return _finalize(lo, hi, period, raw)


def salary_from_numbers(lo: object, hi: object, period: object = None) -> Salary | None:
    """Build a Salary from numeric min/max columns (either may be missing)."""
    try:
        a = float(lo) if lo is not None and lo == lo else None
        b = float(hi) if hi is not None and hi == hi else None
    except (TypeError, ValueError):
        return None
    if a is None and b is None:
        return None
    a, b = (a if a is not None else b), (b if b is not None else a)
    p = normalize_text(period)
    per = "year" if _YEAR.search(p) else "month" if _MONTH.search(p) else None
    return _finalize(a, b, per, f"{a}-{b}")
