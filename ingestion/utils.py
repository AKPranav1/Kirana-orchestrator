import re
from typing import Tuple

NUM_MAP = {
    "ek": 1, "1": 1, "do": 2, "2": 2, "teen": 3, "3": 3, "char": 4, "chaar": 4, "4": 4, "paanch": 5, "5": 5, "aadha": 0.5,
}

UNIT_MAP = {
    "kilo": "kg", "kg": "kg", "kilos": "kg", "killo": "kg", "litre": "litre", "liter": "litre", "l": "litre", "litres": "litre", "packet": "packet", "pack": "packet", "piece": "piece", "pc": "piece", "gram": "gm", "gm": "gm",
}

def normalize_text(text: str) -> Tuple[str, dict]:
    original = text
    t = text.strip()
    t = re.sub(r"\s+", " ", t)

    devanagari_digits = str.maketrans("०१२३४५६७८९", "0123456789")
    t = t.translate(devanagari_digits)

    def repl_num(m):
        w = m.group(0).lower()
        v = NUM_MAP.get(w)
        return str(v) if v is not None else w

    t = re.sub(r"\b(ek|do|teen|char|chaar|paanch|aadha)\b", repl_num, t, flags=re.I)

    def repl_unit(m):
        u = m.group(0).lower()
        return UNIT_MAP.get(u, u)

    t = re.sub(r"\b(kilo|kilos|kg|litre|liter|l|litres|packet|pack|piece|pc|gram|gm)\b", repl_unit, t, flags=re.I)

    return t, {"original": original}