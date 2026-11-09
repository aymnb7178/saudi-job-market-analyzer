"""Skill extraction, text normalisation and taxonomy rules."""
from __future__ import annotations

import json

import pytest

from saudi_jobs.enrich import enrich
from saudi_jobs.skills import SkillExtractor, Taxonomy
from saudi_jobs.textnorm import normalize_text


def test_word_boundaries(extractor):
    assert extractor.extract("Java developer") == ["Java"]
    assert extractor.extract("JavaScript developer") == ["JavaScript"]
    assert "Artificial Intelligence" not in extractor.extract("Must maintain and explain reports")
    assert extractor.extract("C++ and C#") == ["C#", "C++"]


def test_arabic_aliases_and_clitics(extractor):
    assert extractor.extract("خبرة في بايثون") == ["Python"]
    assert extractor.extract("المهارات: الإكسل و باور بي آي") == ["Excel", "Power BI"]
    assert extractor.extract("نستخدم بالاكسل") == ["Excel"]  # "with Excel" (clitic ب + ال)


def test_multiword_alias_with_spaces_and_hyphens(extractor):
    assert "Power BI" in extractor.extract("Power BI dashboards")
    assert "Power BI" in extractor.extract("Power-BI")
    assert "Google IT Support Certificate" in extractor.extract("Google IT Support certificate preferred")


def test_longer_match_wins_but_certs_keep_base_skill(extractor):
    assert extractor.extract("Excel Macros") == ["VBA"]
    got = extractor.extract("AWS Certified")
    assert "AWS" in got and "AWS Certified" in got


def test_certifications_detected(extractor):
    got = extractor.extract("CCNA or Security+ or CompTIA A+ required")
    assert {"CCNA", "Security+", "CompTIA A+"} <= set(got)


def test_normalize_text_arabic_folding():
    assert normalize_text("إكسل") == normalize_text("اكسل")
    assert normalize_text("مَكَّة") == normalize_text("مكه")
    assert normalize_text("٨٠٠٠") == "8000"
    assert normalize_text(None) == "" and normalize_text(float("nan")) == ""


def test_extractor_recall_on_synthetic_truth(raw, extractor):
    df = enrich(raw.drop(columns=["true_skills", "true_role"]), extractor)
    hit = total = 0
    for truth, found in zip(raw["true_skills"], df["skills"]):
        hit += len(set(truth) & set(found))
        total += len(truth)
    assert hit / total >= 0.97


def test_custom_taxonomy_is_editable(tmp_path):
    path = tmp_path / "t.json"
    path.write_text(json.dumps({"categories": {"Tools": {"Rust": ["rustlang", "راست"]}}}), encoding="utf-8")
    ext = SkillExtractor(Taxonomy.from_json(path))
    assert ext.extract("We use rustlang daily; trust matters") == ["Rust"]


def test_duplicate_alias_rejected():
    with pytest.raises(ValueError, match="belongs to both"):
        Taxonomy({"A": {"X": ["foo"], "Y": ["Foo"]}})
