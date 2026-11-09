"""Text normalisation shared by all matchers (English + Arabic)."""
from __future__ import annotations

import re
import unicodedata

_AR_MARKS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_FOLD = str.maketrans(
    {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"}
)
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬٫", "01234567890123456789,.")
_WS = re.compile(r"\s+")
_ARABIC = re.compile("[؀-ۿ]")
# single-letter Arabic clitics (and, with, for, so, like) optionally followed by the article
_AR_PREFIX = "(?:[وبلفك]?ال|[وبلفك])?"


def normalize_text(text: object) -> str:
    """Lower-case, strip Arabic diacritics/tatweel, fold alef/teh-marbuta/alef-maqsura,
    convert Arabic-Indic digits to ASCII and collapse whitespace."""
    if text is None or (isinstance(text, float) and text != text):
        return ""
    s = unicodedata.normalize("NFKC", str(text)).lower()
    s = _AR_MARKS.sub("", s).translate(_FOLD).translate(_DIGITS)
    return _WS.sub(" ", s).strip()


def has_arabic(text: str) -> bool:
    return bool(_ARABIC.search(text))


def alias_regex(alias_norm: str) -> str:
    """Regex source matching an already-normalised alias on word boundaries.

    * spaces/hyphens inside an alias match any run of spaces, hyphens or underscores
    * Arabic aliases may carry a single-letter clitic and/or the article (e.g. "بالاكسل")
    * an alias that does not end in + or # is not matched when directly followed by them
    """
    esc = r"[\s\-_]+".join(re.escape(part) for part in re.split(r"[\s\-_]+", alias_norm) if part)
    pre = _AR_PREFIX if _ARABIC.match(alias_norm[:1]) else ""
    post = r"(?!\w)" + ("" if alias_norm[-1:] in "+#" else r"(?![+#])")
    return rf"(?<!\w){pre}{esc}{post}"
