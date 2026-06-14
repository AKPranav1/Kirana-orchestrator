import re
from typing import Tuple

# ---------------------------------------------------------------------------
# Number word → float mappings
# Covers: Hindi/Hinglish, Kannada, Tamil, Telugu, Marathi, Gujarati,
#         Bengali, Punjabi, Malayalam, Odia
# ---------------------------------------------------------------------------
NUM_MAP: dict[str, float] = {
    # ── Digits (ASCII) ──────────────────────────────────────────────────────
    "0": 0, "1": 1, "2": 2, "3": 3, "4": 4,
    "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,

    # ── Hindi / Hinglish ────────────────────────────────────────────────────
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4,
    "paanch": 5, "paach": 5, "chhe": 6, "saat": 7, "aath": 8,
    "nau": 9, "das": 10, "aadha": 0.5, "half": 0.5,

    # ── Kannada ─────────────────────────────────────────────────────────────
    "ondu": 1, "eradu": 2, "mooru": 3, "naalu": 4, "aidu": 5,
    "aaru": 6, "yelu": 7, "entu": 8, "ombattu": 9, "hattu": 10,
    "ardha": 0.5,

    # ── Tamil ───────────────────────────────────────────────────────────────
    "onru": 1, "rendu": 2, "moondru": 3, "naangu": 4, "aindhu": 5,
    "aaru": 6, "ezhu": 7, "ettu": 8, "onbathu": 9, "pathu": 10,
    "arai": 0.5,

    # ── Telugu ──────────────────────────────────────────────────────────────
    "okati": 1, "rendu": 2, "mudu": 3, "nalugu": 4, "aidu": 5,
    "aaru": 6, "edu": 7, "enimidi": 8, "tommidi": 9, "padi": 10,
    "ardha": 0.5,

    # ── Marathi ─────────────────────────────────────────────────────────────
    "ek": 1, "don": 2, "teen": 3, "char": 4, "paach": 5,
    "saha": 6, "saat": 7, "aath": 8, "nava": 9, "daha": 10,
    "nidha": 0.5,

    # ── Gujarati ────────────────────────────────────────────────────────────
    "ek": 1, "be": 2, "tran": 3, "char": 4, "paanch": 5,
    "chha": 6, "saat": 7, "aath": 8, "nav": 9, "das": 10,

    # ── Bengali ─────────────────────────────────────────────────────────────
    "ek": 1, "dui": 2, "tin": 3, "char": 4, "paanch": 5,
    "choy": 6, "saat": 7, "aath": 8, "noy": 9, "dosh": 10,
    "adha": 0.5,

    # ── Punjabi ─────────────────────────────────────────────────────────────
    "ikk": 1, "do": 2, "teen": 3, "char": 4, "panj": 5,
    "chhe": 6, "satt": 7, "atth": 8, "nau": 9, "das": 10,
    "adha": 0.5,

    # ── Malayalam ───────────────────────────────────────────────────────────
    "onnu": 1, "randu": 2, "moonu": 3, "naalu": 4, "anchu": 5,
    "aaru": 6, "ezhu": 7, "ettu": 8, "ombathu": 9, "pathu": 10,
    "pakuthi": 0.5,

    # ── Odia ────────────────────────────────────────────────────────────────
    "gote": 1, "dui": 2, "tini": 3, "chari": 4, "paan": 5,
    "chha": 6, "saat": 7, "aath": 8, "nau": 9, "dasa": 10,
    "ardha": 0.5,
}

# Build a compiled regex for all number words (longest-match order)
_NUM_WORDS_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(NUM_MAP.keys(), key=len, reverse=True)) + r")\b",
    flags=re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Unit alias → canonical unit mappings
# ---------------------------------------------------------------------------
UNIT_MAP: dict[str, str] = {
    # Weight
    "kilo": "kg",   "kilos": "kg",  "killo": "kg",  "kg": "kg",
    "kilogram": "kg", "kilograms": "kg", "kilograam": "kg",
    "gram": "gm",   "gm": "gm",    "grm": "gm",     "grams": "gm",
    "graam": "gm",
    # Volume
    "litre": "litre",  "liter": "litre",  "liters": "litre",
    "litres": "litre", "l": "litre",      "ltr": "litre",
    "litar": "litre",  "litaru": "litre", "litrulu": "litre",
    "ml": "ml", "milli": "ml", "millilitre": "ml", "milliliter": "ml",
    # Count / Pack
    "packet": "packet", "pack": "packet", "pkt": "packet", "packets": "packet",
    "paakit": "packet", "paaket": "packet", "patket": "packet",
    "piece": "piece",  "pc": "piece",   "pieces": "piece", "pcs": "piece",
    "tukadu": "piece", "tukda": "piece", "tuni": "piece", "mukka": "piece",
    "bottle": "bottle", "bottles": "bottle",
    "box": "box",       "boxes": "box",
    "dozen": "dozen",   "doz": "dozen",
    "bundle": "bundle",
}
_UNIT_WORDS_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(UNIT_MAP.keys(), key=len, reverse=True)) + r")\b",
    flags=re.IGNORECASE,
)

# Indic digit transliteration
_INDIC_DIGIT_TABLE = str.maketrans(
    "०१२३४५६७८९০১২৩৪৫৬৭৮৯੦੧੨੩੪੫੬੭੮੯૦૧૨૩૪૫૬૭૮૯೦೧೨೩೪೫೬೭೮೯൦൧൨൩൪൫൬൭൮૯୦୧୨୩୪୫୬୭୮୯௦௧௨௩௪௫௬௭௮௯౦౧౨౩౪౫౬౭౮౯",
    "0123456789" * 9,
)

# Enhanced split delimiters – includes "ke saath", "split with", etc.
_SPLIT_PATTERN = re.compile(
    r",|।|،"                 # punctuation delimiters
    r"| and | & "            # English
    r"| aur | or "           # Hindi
    r"| mattu | adu "        # Kannada
    r"| agum | um "          # Tamil
    r"| mariyu | tho "       # Telugu
    r"| ani | va "           # Marathi / Gujarati
    r"| ebong | o "          # Bengali
    r"| te | ate "           # Punjabi
    r"| um | kum "           # Malayalam
    r"| o | ebang "          # Odia
    r"| split with | ke saath | saath | with "   # split phrases
    r"| ko | ke liye | ko dena | ko do ",        # Hindi "to", "give to"
    flags=re.IGNORECASE,
)

def normalize_text(text: str) -> Tuple[str, dict]:
    """
    Normalises a multilingual grocery order string into a clean ASCII-digit,
    canonical-unit string.
    """
    original = text
    t = text.strip()
    t = re.sub(r"\s+", " ", t)

    # Indic digits → ASCII
    t = t.translate(_INDIC_DIGIT_TABLE)

    # Number words → digits
    def _repl_num(m: re.Match) -> str:
        word = m.group(0).lower()
        val = NUM_MAP.get(word)
        if val is None:
            return word
        return str(int(val)) if val == int(val) else str(val)

    t = _NUM_WORDS_PATTERN.sub(_repl_num, t)

    # Unit aliases → canonical tokens
    def _repl_unit(m: re.Match) -> str:
        return UNIT_MAP.get(m.group(0).lower(), m.group(0).lower())

    t = _UNIT_WORDS_PATTERN.sub(_repl_unit, t)

    return t, {"original": original}

def split_multilingual(text: str) -> list[str]:
    """Splits a grocery order string on any multilingual item delimiter."""
    parts = _SPLIT_PATTERN.split(text)
    return [p.strip() for p in parts if p.strip()]