"""
outfit_manager.py
-----------------
CRUD operations for saved outfits stored in data/outfits.json.
Each outfit is a named collection of item IDs with metadata.
"""

import json
import os
import uuid
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUTFITS_PATH = os.path.join(DATA_DIR, "outfits.json")


def load_outfits() -> list:
    """Load all saved outfits from disk."""
    if os.path.exists(OUTFITS_PATH):
        try:
            with open(OUTFITS_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_outfits(outfits: list) -> None:
    """Persist outfits to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTFITS_PATH, "w") as f:
        json.dump(outfits, f, indent=2)


def create_outfit(
    name: str,
    item_ids: list,
    occasion: str = "Casual",
    season: str = "All",
    source: str = "manual",
    weather_info: str = "",
    recommended_items: list = None,
) -> dict:
    """Create and save a new outfit. Returns the created outfit.

    Args:
        recommended_items: Optional list of full item dicts (for catalog items
            that can't be looked up from the wardrobe). Stored alongside item_ids
            so the Saved Outfits page can display them.
    """
    outfits = load_outfits()
    new_outfit = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "item_ids": item_ids,
        "occasion": occasion,
        "season": season,
        "source": source,
        "weather_info": weather_info,
        "created_at": datetime.now().isoformat(),
    }
    if recommended_items:
        new_outfit["recommended_items"] = recommended_items
    outfits.append(new_outfit)
    save_outfits(outfits)
    return new_outfit


def delete_outfit(outfit_id: str) -> bool:
    """Remove an outfit by ID. Returns True if found and removed."""
    outfits = load_outfits()
    original_len = len(outfits)
    outfits = [o for o in outfits if o["id"] != outfit_id]
    if len(outfits) < original_len:
        save_outfits(outfits)
        return True
    return False


def get_outfit(outfit_id: str) -> dict | None:
    """Retrieve a single outfit by ID."""
    for outfit in load_outfits():
        if outfit["id"] == outfit_id:
            return outfit
    return None


def get_outfit_count() -> int:
    """Return the number of saved outfits."""
    return len(load_outfits())


if __name__ == "__main__":
    print(f"Saved outfits: {get_outfit_count()}")
    test = create_outfit("Test Look", ["abc", "def"], "Casual", "Summer")
    print(f"Created: {test['name']} (id={test['id']})")
    deleted = delete_outfit(test["id"])
    print(f"Deleted: {deleted}")
    print(f"Outfits now: {get_outfit_count()}")
