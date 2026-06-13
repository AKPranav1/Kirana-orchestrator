import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ingestion.utils import normalize_text


def test_normalize_simple():
    s = "ek kilo aata aur do packet maggi"
    out, md = normalize_text(s)
    assert ("1" in out) or ("1.0" in out)
    assert ("kg" in out) or ("kilo" in out)
