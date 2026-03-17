"""
wardrobe_manager.py
-------------------
CRUD operations for the user's personal wardrobe stored in data/wardrobe.json.
Each item has a unique ID, clothing attributes, optional image, and date added.
"""

import json
import os
import uuid
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
WARDROBE_PATH = os.path.join(DATA_DIR, "wardrobe.json")
WARDROBE_IMAGES_DIR = os.path.join(DATA_DIR, "wardrobe_images")


def _ensure_dirs():
    """Create data directories if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(WARDROBE_IMAGES_DIR, exist_ok=True)


def load_wardrobe() -> list:
    """Load all wardrobe items from disk."""
    if os.path.exists(WARDROBE_PATH):
        try:
            with open(WARDROBE_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_wardrobe(items: list) -> None:
    """Persist wardrobe items to disk."""
    _ensure_dirs()
    with open(WARDROBE_PATH, "w") as f:
        json.dump(items, f, indent=2)


def add_item(
    name: str,
    item_type: str,
    color: str,
    pattern: str = "Solid",
    material: str = "",
    season: list = None,
    occasion: list = None,
    formality: str = "Casual",
    gender: str = "Unisex",
    image_filename: str = "",
) -> dict:
    """Add a new item to the wardrobe and return it."""
    items = load_wardrobe()
    new_item = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "type": item_type,
        "color": color,
        "pattern": pattern,
        "material": material,
        "season": season or ["Spring", "Summer", "Fall", "Winter"],
        "occasion": occasion or ["Casual"],
        "formality": formality,
        "gender": gender,
        "image_filename": image_filename,
        "date_added": datetime.now().isoformat(),
    }
    items.append(new_item)
    save_wardrobe(items)
    return new_item


def delete_item(item_id: str) -> bool:
    """Remove an item by ID. Returns True if found and removed."""
    items = load_wardrobe()
    original_len = len(items)
    items = [i for i in items if i["id"] != item_id]
    if len(items) < original_len:
        save_wardrobe(items)
        return True
    return False


def get_item(item_id: str) -> dict | None:
    """Retrieve a single item by ID."""
    for item in load_wardrobe():
        if item["id"] == item_id:
            return item
    return None


def search_items(
    category: str = None,
    color: str = None,
    occasion: str = None,
    season: str = None,
    formality: str = None,
) -> list:
    """
    Search wardrobe items with optional filters.
    Uses case-insensitive partial matching.
    """
    items = load_wardrobe()
    results = []
    for item in items:
        if category and category.lower() not in item.get("type", "").lower():
            continue
        if color and color.lower() not in item.get("color", "").lower():
            continue
        if occasion:
            item_occasions = [o.lower() for o in item.get("occasion", [])]
            if not any(occasion.lower() in o for o in item_occasions):
                continue
        if season:
            item_seasons = [s.lower() for s in item.get("season", [])]
            if not any(season.lower() in s for s in item_seasons):
                continue
        if formality and formality.lower() not in item.get("formality", "").lower():
            continue
        results.append(item)
    return results


def get_wardrobe_count() -> int:
    """Return the number of items in the wardrobe."""
    return len(load_wardrobe())


if __name__ == "__main__":
    print(f"Wardrobe has {get_wardrobe_count()} items")
    # Quick test: add and remove
    test = add_item("Test Tee", "T-Shirt", "Navy Blue", occasion=["Casual"])
    print(f"Added: {test['name']} (id={test['id']})")
    print(f"Search for T-Shirt: {len(search_items(category='T-Shirt'))} found")
    deleted = delete_item(test["id"])
    print(f"Deleted: {deleted}")
    print(f"Wardrobe now has {get_wardrobe_count()} items")
