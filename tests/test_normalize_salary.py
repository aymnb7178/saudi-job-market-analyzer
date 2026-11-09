"""Title, city, sector, seniority and salary parsing."""
from __future__ import annotations

import pytest

from saudi_jobs.normalize import normalize_city, normalize_sector, normalize_seniority, normalize_title
from saudi_jobs.salary import parse_salary, salary_from_numbers


@pytest.mark.parametrize("title,role", [
    ("Senior Data Analyst", "Data Analyst"), ("محلل بيانات", "Data Analyst"),
    ("Help Desk Technician", "IT Support Specialist"), ("أخصائي دعم فني", "IT Support Specialist"),
    ("Python Developer", "Python Developer"), ("مطور بايثون", "Python Developer"),
    ("AI Data Analyst", "AI/Automation Engineer"), ("مهندس ذكاء اصطناعي", "AI/Automation Engineer"),
    ("Accountant", "Other"),
])
def test_title_normalization(title, role):
    assert normalize_title(title) == role


@pytest.mark.parametrize("raw,city", [
    ("Riyadh, Saudi Arabia", "Riyadh"), ("جدة", "Jeddah"), ("Mecca", "Makkah"), ("الخبر", "Khobar"),
    ("Medina", "Madinah"), ("الطائف", "Taif"), ("NEOM", "NEOM"), ("عن بعد", "Remote"), ("Dubai", "Other"),
])
def test_city_normalization(raw, city):
    assert normalize_city(raw) == city


def test_sector_and_seniority():
    assert normalize_sector("اتصالات") == "Telecom"
    assert normalize_sector("Fintech") == "Banking & Finance"
    assert normalize_seniority("Mid-level", "Python Developer") == "Mid"
    assert normalize_seniority(None, "Senior Python Developer") == "Senior"
    assert normalize_seniority(None, "محلل بيانات مبتدئ") == "Junior"
    assert normalize_seniority(None, "Data Analyst") == "Unspecified"


def test_salary_monthly_and_annual():
    s = parse_salary("8,000 - 12,000 SAR/month")
    assert (s.min_monthly, s.max_monthly, s.period) == (8000, 12000, "month")
    a = parse_salary("96,000 - 144,000 SAR per year")
    assert (a.min_monthly, a.max_monthly, a.period) == (8000, 12000, "year")


def test_salary_arabic_k_suffix_and_inference():
    s = parse_salary("٨٠٠٠-١٢٠٠٠ ريال شهريا")
    assert (s.min_monthly, s.max_monthly) == (8000, 12000)
    k = parse_salary("SAR 10-12k")
    assert (k.min_monthly, k.max_monthly) == (10000, 12000) and k.period_inferred
    y = parse_salary("96k - 120k ريال سنويا")
    assert y.min_monthly == 8000 and not y.period_inferred


def test_salary_rejects_unusable_text():
    for bad in [None, "", "competitive", "5000 USD/month", "50 SAR per hour", "20"]:
        assert parse_salary(bad) is None


def test_salary_from_numeric_columns():
    s = salary_from_numbers(9000, 11000, "monthly")
    assert s.mid_monthly == 10000
    assert salary_from_numbers(None, None) is None
