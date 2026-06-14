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
        import re

        # 1) Exact alias
        if key in self.aliases:
            canon, unit = self.aliases[key]
            try:
                print(f"[sku_match] exact alias match: key={key!r} -> canon={canon!r} unit={unit!r}", flush=True)
            except Exception:
                pass
            return canon, unit, 100.0

        # 2) rapidfuzz global match (if available)
        if _HAS_RAPIDFUZZ:
            try:
                match = process.extractOne(key, self.alias_list, scorer=fuzz.WRatio)
                if match:
                    candidate, score, _ = match
                    if score >= cutoff:
                        canon, unit = self.aliases[candidate]
                        try:
                            print(f"[sku_match] rapidfuzz match: key={key!r} -> candidate={candidate!r} score={score}", flush=True)
                        except Exception:
                            pass
                        return canon, unit, float(score)
            except Exception:
                pass

        # 3) deterministic fallbacks: exact candidate, whole-word, substring
        for candidate in self.alias_list:
            if key == candidate:
                canon, unit = self.aliases[candidate]
                try:
                    print(f"[sku_match] fallback exact: key={key!r} -> candidate={candidate!r}", flush=True)
                except Exception:
                    pass
                return canon, unit, 100.0

        for candidate in self.alias_list:
            try:
                if re.search(rf"\b{re.escape(key)}\b", candidate):
                    canon, unit = self.aliases[candidate]
                    try:
                        print(f"[sku_match] whole-word match: key={key!r} -> candidate={candidate!r}", flush=True)
                    except Exception:
                        pass
                    return canon, unit, 90.0
                if re.search(rf"\b{re.escape(candidate)}\b", key):
                    canon, unit = self.aliases[candidate]
                    return canon, unit, 90.0
            except re.error:
                continue

        for candidate in self.alias_list:
            if key in candidate or candidate in key:
                canon, unit = self.aliases[candidate]
                try:
                    print(f"[sku_match] substring match: key={key!r} -> candidate={candidate!r}", flush=True)
                except Exception:
                    pass
                return canon, unit, 75.0

        # 4) Token fallback: try individual tokens (longest first). Useful when
        # input contains noise words like 'bars', 'please' or plurals.
        tokens = [t.strip() for t in re.split(r"[^\w]+", key) if t.strip()]
        tokens = sorted(tokens, key=len, reverse=True)
        stopwords = {"please", "pls", "bar", "bars", "piece", "pieces", "pack", "packet", "kg", "g", "gm", "for", "my", "me"}
        for tok in tokens:
            if not tok or tok in stopwords:
                continue
            if tok in self.aliases:
                canon, unit = self.aliases[tok]
                try:
                    print(f"[sku_match] token alias match: token={tok!r} -> canon={canon!r}", flush=True)
                except Exception:
                    pass
                return canon, unit, 85.0
            if _HAS_RAPIDFUZZ:
                try:
                    match = process.extractOne(tok, self.alias_list, scorer=fuzz.WRatio)
                    if match:
                        candidate, score, _ = match
                        if score >= max(60, cutoff - 10):
                            canon, unit = self.aliases[candidate]
                            try:
                                print(f"[sku_match] rapidfuzz token match: token={tok!r} -> candidate={candidate!r} score={score}", flush=True)
                            except Exception:
                                pass
                            return canon, unit, float(score)
                except Exception:
                    pass

        # nothing matched — return original
        return name, None, 0.0
