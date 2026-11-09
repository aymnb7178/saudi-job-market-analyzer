"""Seeded generator for a SYNTHETIC job-posting dataset (demo and tests only).

Nothing here is real market data. Skill-demand probabilities, salaries, city and sector
weights are invented by the author to exercise the analytics. Every row has
``source == "synthetic"`` and every generated report says so.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from saudi_jobs.skills import Taxonomy
from saudi_jobs.textnorm import has_arabic

SYNTHETIC_SOURCE = "synthetic"
N_MONTHS = 18  # 2025-01 .. 2026-06

# role -> (weight, EN titles, AR titles, base monthly mid salary in SAR, {skill: (prob, drift per month)})
_ROLES = {
    "Data Analyst": (
        0.30,
        ["Data Analyst", "Business Intelligence Analyst", "Reporting Analyst", "Data Analyst"],
        ["محلل بيانات", "محلل ذكاء الأعمال", "محلل بيانات"],
        11000,
        {"SQL": (.80, 0), "Excel": (.75, -.002), "Power BI": (.58, .004), "Python": (.42, .006),
         "Tableau": (.28, 0), "Data Visualization": (.50, 0), "Statistics": (.35, 0), "Data Cleaning": (.30, 0),
         "ETL": (.15, 0), "Communication": (.50, 0), "Attention to Detail": (.30, 0), "Presentation Skills": (.25, 0),
         "Problem Solving": (.30, 0), "Pandas": (.18, .004), "DAX": (.20, .002), "Power Query": (.20, 0),
         "Databases": (.20, 0), "Looker Studio": (.12, 0), "PL-300": (.06, 0),
         "Google Data Analytics Certificate": (.05, 0), "Azure": (.08, .002), "Machine Learning": (.06, .004)},
    ),
    "IT Support Specialist": (
        0.27,
        ["IT Support Specialist", "Help Desk Technician", "IT Support Engineer", "Technical Support Specialist"],
        ["أخصائي دعم فني", "فني دعم فني", "مهندس دعم تقني"],
        8000,
        {"Help Desk": (.55, 0), "Troubleshooting": (.70, 0), "Windows Server": (.35, 0), "Active Directory": (.45, 0),
         "Networking": (.45, 0), "Microsoft 365": (.40, .004), "Hardware Support": (.35, -.002),
         "Customer Service": (.50, 0), "Communication": (.50, 0), "CCNA": (.15, 0), "CompTIA A+": (.12, 0),
         "Network+": (.10, 0), "Google IT Support Certificate": (.08, .002), "ITIL Foundation": (.10, 0),
         "Security+": (.06, .002), "Linux": (.20, 0), "Virtualization": (.15, 0), "Firewalls & VPN": (.15, 0),
         "Cybersecurity": (.10, .005), "TCP/IP": (.20, 0), "Cisco": (.15, 0), "Teamwork": (.30, 0),
         "Time Management": (.20, 0), "Problem Solving": (.40, 0), "Cloud Computing": (.08, .004)},
    ),
    "Python Developer": (
        0.23,
        ["Python Developer", "Backend Developer (Python)", "Python Software Engineer", "Python Developer"],
        ["مطور بايثون", "مطور برمجيات بايثون"],
        14000,
        {"Python": (1.0, 0), "REST APIs": (.55, 0), "SQL": (.55, 0), "Git": (.65, 0), "Linux": (.30, 0),
         "Docker": (.30, .008), "JavaScript": (.20, 0), "Databases": (.30, 0), "CI/CD": (.20, .003),
         "AWS": (.25, 0), "Pandas": (.18, 0), "Teamwork": (.35, 0), "Problem Solving": (.40, 0),
         "Communication": (.30, 0), "Cloud Computing": (.12, .004), "Azure": (.10, 0), "Kubernetes": (.08, .003),
         "Shell Scripting": (.15, 0), "Machine Learning": (.08, .004)},
    ),
    "AI/Automation Engineer": (
        0.17,
        ["AI Engineer", "Machine Learning Engineer", "Automation Engineer", "AI Automation Specialist"],
        ["مهندس ذكاء اصطناعي", "مهندس أتمتة", "مهندس تعلم الآلة"],
        17000,
        {"Python": (.80, 0), "Machine Learning": (.55, 0), "Artificial Intelligence": (.45, 0),
         "LLMs": (.22, .014), "Generative AI": (.18, .014), "NLP": (.30, .002), "Deep Learning": (.30, 0),
         "TensorFlow": (.20, -.004), "PyTorch": (.25, .003), "n8n": (.10, .008), "Workflow Automation": (.28, .006),
         "Prompt Engineering": (.15, .012), "LangChain": (.06, .010), "Chatbots": (.15, 0), "REST APIs": (.35, 0),
         "Docker": (.25, 0), "Git": (.40, 0), "AWS": (.20, 0), "Computer Vision": (.15, 0), "scikit-learn": (.25, 0),
         "Communication": (.30, 0), "Problem Solving": (.35, 0), "SQL": (.30, 0), "OpenCV": (.08, 0)},
    ),
}

_OTHER_TITLES = [("Accountant", "Accounting"), ("Sales Executive", "Retail"), ("HR Coordinator", "Healthcare"),
                 ("محاسب", "مالية"), ("مسؤول مبيعات", "تجزئة")]

_CITY_W = {"Riyadh": .36, "Jeddah": .17, "Makkah": .06, "Madinah": .05, "Dammam": .08, "Khobar": .07, "Taif": .03,
           "NEOM": .03, "Remote": .06, "Abha": .02, "Tabuk": .01, "Jubail": .02, "Yanbu": .01, "Dhahran": .03}
_SECTOR_W = {"Technology": .24, "Telecom": .12, "Banking & Finance": .14, "Government": .12, "Healthcare": .07,
             "Retail & E-commerce": .10, "Energy": .07, "Education": .04, "Logistics": .05,
             "Hospitality & Tourism": .03, "Construction & Real Estate": .02}
_SENIORITY_W = {"Junior": .30, "Mid": .40, "Senior": .25, "Lead": .05}
_SEN_MULT = {"Junior": .60, "Mid": 1.0, "Senior": 1.5, "Lead": 2.0}
_SEN_TITLE_EN = {"Junior": "Junior ", "Mid": "", "Senior": "Senior ", "Lead": "Lead "}
_SEN_TITLE_AR = {"Junior": " مبتدئ", "Mid": "", "Senior": " متقدم", "Lead": " قائد"}
_SEN_COL = {"Junior": "Junior", "Mid": "Mid-level", "Senior": "Senior", "Lead": "Lead"}


def _pick(rng, weights: dict[str, float]) -> str:
    keys = list(weights)
    p = np.array([weights[k] for k in keys], dtype=float)
    return keys[int(rng.choice(len(keys), p=p / p.sum()))]


def _salary_fields(rng, role_base: float, sen: str) -> dict:
    mid = role_base * _SEN_MULT[sen] * float(rng.lognormal(0, 0.15))
    lo, hi = round(mid * 0.85 / 500) * 500, round(mid * 1.15 / 500) * 500
    fmt = int(rng.integers(0, 5))
    out: dict = {"salary": None, "salary_min": None, "salary_max": None, "salary_period": None}
    if fmt == 0:
        out["salary"] = f"{lo:,} - {hi:,} SAR/month"
    elif fmt == 1:
        out["salary"] = f"{lo}-{hi} ريال شهريا"
    elif fmt == 2:
        out["salary"] = f"{lo * 12:,} - {hi * 12:,} SAR per year"
    elif fmt == 3:
        out["salary"] = f"SAR {lo / 1000:g}k - {hi / 1000:g}k"
    else:
        out.update(salary_min=float(lo), salary_max=float(hi), salary_period="monthly")
    return out


def _description(rng, title, city_raw, skills, arabic: bool, tax: Taxonomy) -> str:
    def render(skill: str) -> str:
        if arabic:
            ar = [a for a in tax.aliases(skill) if has_arabic(a)]
            if ar:
                return ar[0]
        return skill

    skills = list(skills)
    rng.shuffle(skills)
    cut = max(1, int(len(skills) * 0.75))
    req, nice = [render(s) for s in skills[:cut]], [render(s) for s in skills[cut:]]
    if arabic:
        text = f"نبحث عن {title} للانضمام إلى فريقنا في {city_raw}. المتطلبات: خبرة في " + " و ".join(req) + "."
        if nice:
            text += " يفضل المعرفة بـ" + " و ".join(nice) + "."
        return text
    text = f"We are hiring a {title} in {city_raw}. Requirements: hands-on experience with " + ", ".join(req) + "."
    if nice:
        text += " Nice to have: " + ", ".join(nice) + "."
    return text


def generate_postings(n: int = 1500, seed: int = 42, taxonomy: Taxonomy | None = None,
                      with_truth: bool = False) -> pd.DataFrame:
    """Generate ``n`` synthetic postings (deterministic for a given seed)."""
    from saudi_jobs.normalize import CITY_ALIASES, SECTOR_ALIASES

    tax = taxonomy or Taxonomy.from_json()
    rng = np.random.default_rng(seed)
    role_w = {r: v[0] for r, v in _ROLES.items()}
    month_w = np.linspace(1.0, 1.5, N_MONTHS)  # volume grows over the window
    month_w /= month_w.sum()
    rows = []
    for i in range(n):
        m = int(rng.choice(N_MONTHS, p=month_w))
        year, mon = 2025 + m // 12, m % 12 + 1
        day = int(rng.integers(1, 29))
        arabic = bool(rng.random() < 0.20)
        sen = _pick(rng, _SENIORITY_W)
        city = _pick(rng, _CITY_W)
        sector = _pick(rng, _SECTOR_W)
        city_raw = str(rng.choice(CITY_ALIASES[city]))
        if rng.random() < 0.25 and city != "Remote" and not has_arabic(city_raw):
            city_raw += ", Saudi Arabia"
        sector_raw = str(rng.choice(SECTOR_ALIASES[sector]))
        if rng.random() < 0.03:  # unrelated posting that should normalise to "Other"
            t_en, sec = _OTHER_TITLES[int(rng.integers(len(_OTHER_TITLES)))]
            title, role, skills = t_en, "Other", ["Communication"] if rng.random() < .5 else []
            base = 7000.0
        else:
            role = _pick(rng, role_w)
            _, en, ar, base, pool = _ROLES[role]
            title = str(rng.choice(ar if arabic else en))
            if rng.random() < 0.4:
                title = (_SEN_TITLE_EN[sen] + title) if not arabic else title + _SEN_TITLE_AR[sen]
            skills = [s for s, (p, d) in pool.items()
                      if rng.random() < min(0.97, max(0.02, p + d * (m - N_MONTHS / 2)))] if role != "Other" else []
            if not skills:
                skills = [next(iter(pool))]
        row = {
            "title": title, "company": f"Synthetic Co {int(rng.integers(1, 81)):03d}", "city": city_raw,
            "sector": sector_raw, "posted_date": f"{year}-{mon:02d}-{day:02d}",
            "description": _description(rng, title, city_raw, skills, arabic, tax),
            "salary": None, "salary_min": None, "salary_max": None, "salary_period": None,
            "seniority": _SEN_COL[sen] if rng.random() < 0.35 else None, "source": SYNTHETIC_SOURCE,
        }
        if rng.random() < 0.45:
            row.update(_salary_fields(rng, base, sen))
        if with_truth:
            row["true_skills"] = tuple(sorted(skills))
            row["true_role"] = role
        rows.append(row)
    return pd.DataFrame(rows)
