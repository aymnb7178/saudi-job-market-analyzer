"""Job-title, seniority, city and sector normalisation (English + Arabic)."""
from __future__ import annotations

import re

from saudi_jobs.textnorm import alias_regex, normalize_text

ROLES = ["Data Analyst", "IT Support Specialist", "Python Developer", "AI/Automation Engineer"]
OTHER = "Other"

# First matching role wins, so "AI Data Analyst" -> AI/Automation Engineer.
_ROLE_RULES: list[tuple[str, list[str]]] = [
    ("AI/Automation Engineer", [r"\bai\b", "machine learning", r"\bml\b", "automation", "ذكاء اصطناعي",
                                "اتمتة", "تعلم الآلة", "الذكاء الاصطناعي", "الأتمتة"]),
    ("Data Analyst", ["data analyst", "data analytics", "business intelligence", r"\bbi (analyst|developer)",
                      "reporting analyst", "insights analyst", "محلل بيانات", "تحليل البيانات", "تحليل بيانات",
                      "ذكاء الأعمال"]),
    ("IT Support Specialist", ["it support", "help ?desk", "service desk", "technical support",
                               "desktop support", "it technician", "support engineer", "الدعم الفني",
                               "دعم فني", "الدعم التقني", "دعم تقني", "فني حاسب", "فني تقنية معلومات"]),
    ("Python Developer", ["python", "بايثون", "بايثن", "بيثون"]),
]
_ROLE_RE = [(r, re.compile("|".join(normalize_text(p) if p[:1] != "\\" and "?" not in p and "(" not in p else p
                                    for p in pats))) for r, pats in _ROLE_RULES]


def normalize_title(title: object) -> str:
    """Map a raw job title to one of ROLES, else 'Other'."""
    t = normalize_text(title)
    for role, rx in _ROLE_RE:
        if rx.search(t):
            return role
    return OTHER


_SENIORITY_RULES = [
    ("Lead", ["lead", "principal", "head of", "staff engineer", "رئيس", "قائد"]),
    ("Senior", [r"senior", r"sr\.?", "خبير", "اول", "متقدم"]),
    ("Junior", ["junior", r"jr\.?", "entry", "trainee", "intern", "internship", "graduate", "fresh",
                "مبتدئ", "مبتدي", "متدرب", "حديث التخرج", "تدريب"]),
    ("Mid", ["mid", "intermediate", "متوسط"]),
]
_SEN_RE = [(lvl, re.compile("(?<!\\w)(?:" + "|".join(
    p if "\\" in p else normalize_text(p) for p in pats) + ")(?![a-z؀-ۿ])")) for lvl, pats in _SENIORITY_RULES]
SENIORITY_LEVELS = ["Junior", "Mid", "Senior", "Lead", "Unspecified"]


def normalize_seniority(explicit: object = None, title: object = None) -> str:
    """Use the explicit column when recognisable, else infer from title keywords."""
    for source in (explicit, title):
        t = normalize_text(source)
        if not t:
            continue
        for lvl, rx in _SEN_RE:
            if rx.search(t):
                return lvl
    return "Unspecified"


_CITIES: dict[str, list[str]] = {
    "Riyadh": ["Riyadh", "Riyad", "الرياض"],
    "Jeddah": ["Jeddah", "Jiddah", "Jidda", "Jedda", "جدة"],
    "Makkah": ["Makkah", "Mecca", "Makka", "Mekkah", "مكة المكرمة", "مكة"],
    "Madinah": ["Madinah", "Medina", "Madina", "Al Madinah", "المدينة المنورة", "المدينة"],
    "Dammam": ["Dammam", "الدمام"],
    "Khobar": ["Khobar", "Al Khobar", "Alkhobar", "الخبر"],
    "Dhahran": ["Dhahran", "الظهران"],
    "Taif": ["Taif", "Ta'if", "الطائف"],
    "NEOM": ["NEOM", "نيوم"],
    "Abha": ["Abha", "أبها"],
    "Tabuk": ["Tabuk", "تبوك"],
    "Jubail": ["Jubail", "الجبيل"],
    "Yanbu": ["Yanbu", "ينبع"],
    "Buraidah": ["Buraidah", "بريدة"],
    "Hail": ["Hail", "حائل"],
    "Jazan": ["Jazan", "Jizan", "جازان"],
    "Remote": ["Remote", "Work from home", "WFH", "عن بعد"],
}
CITY_ALIASES = _CITIES

_SECTORS: dict[str, list[str]] = {
    "Telecom": ["Telecom", "Telecommunications", "اتصالات"],
    "Technology": ["Technology", "Information Technology", "IT Services", "Software", "Tech", "تقنية", "تكنولوجيا",
                   "برمجيات", "تقنية المعلومات"],
    "Banking & Finance": ["Banking", "Bank", "Finance", "Financial Services", "Fintech", "Insurance", "بنوك",
                          "مصرفي", "مالية", "تأمين"],
    "Government": ["Government", "Public Sector", "Ministry", "حكومي", "حكومة", "وزارة"],
    "Healthcare": ["Healthcare", "Health", "Hospital", "Medical", "Pharma", "صحة", "الرعاية الصحية", "مستشفى", "طبي"],
    "Retail & E-commerce": ["Retail", "E-commerce", "Ecommerce", "Commerce", "تجزئة", "التجارة الإلكترونية", "تجارة"],
    "Energy": ["Energy", "Oil", "Gas", "Utilities", "Petrochemical", "طاقة", "نفط", "بتروكيماويات"],
    "Education": ["Education", "University", "School", "Training", "تعليم", "جامعة"],
    "Logistics": ["Logistics", "Supply Chain", "Transport", "Shipping", "Delivery", "لوجستيات", "نقل", "شحن"],
    "Hospitality & Tourism": ["Hospitality", "Tourism", "Hotel", "Travel", "سياحة", "ضيافة", "فنادق"],
    "Construction & Real Estate": ["Construction", "Real Estate", "عقارات", "مقاولات", "إنشاءات"],
}
SECTOR_ALIASES = _SECTORS


def _compile(table: dict[str, list[str]]) -> list[tuple[str, re.Pattern[str]]]:
    out = []
    for canon, aliases in table.items():
        alts = sorted({normalize_text(a) for a in [canon, *aliases]}, key=len, reverse=True)
        out.append((canon, re.compile("|".join(alias_regex(a) for a in alts))))
    return out


_CITY_RE = _compile(_CITIES)
_SECTOR_RE = _compile(_SECTORS)


def _earliest(text: object, table: list[tuple[str, re.Pattern[str]]]) -> str:
    t = normalize_text(text)
    best: tuple[int, str] | None = None
    for canon, rx in table:
        m = rx.search(t)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), canon)
    return best[1] if best else OTHER


def normalize_city(city: object) -> str:
    """Canonical Saudi city (or 'Remote'); unknown/foreign values -> 'Other'."""
    return _earliest(city, _CITY_RE)


def normalize_sector(sector: object) -> str:
    return _earliest(sector, _SECTOR_RE)
