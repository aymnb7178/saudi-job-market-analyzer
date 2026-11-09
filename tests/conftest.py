"""Shared fixtures: a small SYNTHETIC dataset (never real market data)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from saudi_jobs.datagen import generate_postings  # noqa: E402
from saudi_jobs.enrich import enrich  # noqa: E402
from saudi_jobs.skills import SkillExtractor, Taxonomy  # noqa: E402


@pytest.fixture(scope="session")
def taxonomy():
    return Taxonomy.from_json()


@pytest.fixture(scope="session")
def extractor(taxonomy):
    return SkillExtractor(taxonomy)


@pytest.fixture(scope="session")
def raw():
    return generate_postings(400, seed=7, with_truth=True)


@pytest.fixture(scope="session")
def frame(raw, extractor):
    return enrich(raw.drop(columns=["true_skills", "true_role"]), extractor)
