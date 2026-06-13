import json
from typing import Tuple, Optional
from pathlib import Path

# rapidfuzz is an optional dependency for better fuzzy matching in production.
# Provide a lightweight fallback when it's not available in the runtime environment.
try:
    from rapidfuzz import process, fuzz

    _HAS_RAPIDFUZZ = True
except Exception:
    _HAS_RAPIDFUZZ = False


class SKUMatcher:
    def __init__(self, catalog_path: str):
        path = Path(catalog_path)
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        self.catalog = raw.get("store_default", {})
        self.aliases = {}
        for key, v in self.catalog.items():
            for a in v.get("aliases", []):
                self.aliases[a.lower()] = (v["canonical"], v.get("unit"))
        self.alias_list = list(self.aliases.keys())

    def match(self, name: str, cutoff: int = 70) -> Tuple[str, Optional[str], float]:
        if not name:
            return name, None, 0.0
        key = name.lower().strip()
        if key in self.aliases:
            canon, unit = self.aliases[key]
            return canon, unit, 100.0

        if _HAS_RAPIDFUZZ:
            match = process.extractOne(key, self.alias_list, scorer=fuzz.WRatio)
            if match:
                candidate, score, _ = match
                if score >= cutoff:
                    canon, unit = self.aliases[candidate]
                    return canon, unit, float(score)
        else:
            # Simple fallback: prefix/substring match with a modest score
            for candidate in self.alias_list:
                if key == candidate:
                    canon, unit = self.aliases[candidate]
                    return canon, unit, 100.0
                if key in candidate or candidate in key:
                    canon, unit = self.aliases[candidate]
                    return canon, unit, 75.0

        return name, None, 0.0
