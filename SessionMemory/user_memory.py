import re
import csv
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Auto-build brand and category lists from the cleaned CSV.
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


def _load_categories(csv_path: Path) -> list[str]:
    categories: set[str] = set()
    if not csv_path.exists():
        print(f"UserMemory WARNING: CSV not found at {csv_path}", flush=True)
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            c = row.get("category_name", "").strip()
            if c:
                categories.add(c.lower())
    return sorted(categories, key=len, reverse=True)


def _load_category_counts(csv_path: Path) -> Counter:
    counts: Counter = Counter()
    if not csv_path.exists():
        return counts
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            c = row.get("category_name", "").strip()
            if c:
                counts[c] += 1
    return counts


KNOWN_BRANDS: list[str] = _load_brands(_CSV)
KNOWN_CATEGORIES: list[str] = _load_categories(_CSV)
CATEGORY_COUNTS: Counter = _load_category_counts(_CSV)
print(
    f"Catalog loaded: {len(KNOWN_BRANDS)} brands, {len(KNOWN_CATEGORIES)} categories",
    flush=True,
)


# ---------------------------------------------------------------------------
# UserMemory
# ---------------------------------------------------------------------------

class UserMemory:
    def __init__(self):
        self.pref = {"budget": None, "brand": None, "category": None}

    def _match_category(self, text: str) -> str | None:
        for category in KNOWN_CATEGORIES:
            if category in text:
                return category.title()
        return None

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

        found_category = self._match_category(t)
        if found_category:
            self.pref["category"] = found_category
        elif not any(c.split()[0] in t for c in KNOWN_CATEGORIES):
            self.pref["category"] = None

    def has_category_signal(self, text: str) -> bool:
        t = text.lower()
        return self._match_category(t) is not None

    def category_hints(self, limit: int = 6) -> list[str]:
        if not CATEGORY_COUNTS:
            return []
        return [name for name, _ in CATEGORY_COUNTS.most_common(limit)]

    def summary(self) -> str:
        return str(self.pref)
