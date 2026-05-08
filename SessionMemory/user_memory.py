import re
import csv
from pathlib import Path

# ---------------------------------------------------------------------------
# Auto-build brand list from the cleaned CSV — always in sync, no hardcoding.
# Category filtering is intentionally NOT done here: the hybrid semantic search
# (BM25 + dense) already handles category intent naturally and reliably.
# Hardcoded or auto-generated category keyword maps create wrong matches
# (e.g. "cotton" -> "Cotton Sheets" when user asked about panties).
# ---------------------------------------------------------------------------

_BASE = Path(__file__).resolve().parent.parent
_CSV  = _BASE / "DataCleaning" / "cleaned_data.csv"


def _load_brands(csv_path: Path) -> list[str]:
    """Return all unique brand names (lowercase), sorted longest-first."""
    brands: set[str] = set()
    if not csv_path.exists():
        print(f"UserMemory WARNING: CSV not found at {csv_path}", flush=True)
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            b = row.get("brand", "").strip()
            if b:
                brands.add(b.lower())
    # Sort longest-first so "fruit of the loom" matches before "fruit"
    return sorted(brands, key=len, reverse=True)


KNOWN_BRANDS: list[str] = _load_brands(_CSV)
print(f"Catalog loaded: {len(KNOWN_BRANDS)} brands", flush=True)


# ---------------------------------------------------------------------------
# UserMemory
# ---------------------------------------------------------------------------

class UserMemory:
    def __init__(self):
        self.pref = {"budget": None, "brand": None}

    def update(self, text: str):
        t = text.lower()

        # --- Budget: range "1000-3000" or "1000 to 3000" → upper bound ---
        range_match = re.search(r'(\d+)\s*(?:-|\bto\b)\s*(\d+)', t)
        if range_match:
            self.pref["budget"] = int(range_match.group(2))
        else:
            numbers = re.findall(r'\b(\d{3,7})\b', t)
            if numbers:
                self.pref["budget"] = max(int(n) for n in numbers)

        # --- Brand: longest-match first so multi-word brands win ---
        found_brand = None
        for brand in KNOWN_BRANDS:      # already sorted longest-first
            if brand in t:
                found_brand = brand.title()
                break

        if found_brand:
            self.pref["brand"] = found_brand
        elif not any(b.split()[0] in t for b in KNOWN_BRANDS):
            # No brand signal in this turn → clear stale brand
            self.pref["brand"] = None

    def summary(self) -> str:
        return str(self.pref)
