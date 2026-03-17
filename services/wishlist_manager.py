"""
wishlist_manager.py
-------------------
CRUD operations for the user's wishlist stored in data/wishlist.json.
Supports both individual items and full outfits.
"""

import json
import os
import uuid
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
WISHLIST_PATH = os.path.join(DATA_DIR, "wishlist.json")


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_wishlist() -> dict:
    """Load the wishlist from disk. Returns dict with 'items' and 'outfits' lists."""
    if os.path.exists(WISHLIST_PATH):
        try:
            with open(WISHLIST_PATH, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("items", [])
                    data.setdefault("outfits", [])
                    return data
        except (json.JSONDecodeError, IOError):
            pass
    return {"items": [], "outfits": []}


def save_wishlist(data: dict) -> None:
    _ensure_dirs()
    with open(WISHLIST_PATH, "w") as f:
        json.dump(data, f, indent=2)


def add_wishlist_item(item: dict) -> bool:
    """Add an item to the wishlist. Returns True if added, False if duplicate."""
    wl = load_wishlist()
    item_id = str(item.get("id", ""))
    existing_ids = {str(i.get("id", "")) for i in wl["items"]}
    if item_id and item_id in existing_ids:
        return False
    entry = dict(item)
    entry["wishlisted_at"] = datetime.now().isoformat()
    wl["items"].append(entry)
    save_wishlist(wl)
    return True


def remove_wishlist_item(item_id: str) -> bool:
    wl = load_wishlist()
    original = len(wl["items"])
    wl["items"] = [i for i in wl["items"] if str(i.get("id", "")) != str(item_id)]
    if len(wl["items"]) < original:
        save_wishlist(wl)
        return True
    return False


def add_wishlist_outfit(outfit: dict) -> str:
    """Add an outfit to the wishlist. Returns the wishlist outfit ID."""
    wl = load_wishlist()
    entry = dict(outfit)
    entry["wishlist_id"] = str(uuid.uuid4())[:8]
    entry["wishlisted_at"] = datetime.now().isoformat()
    wl["outfits"].append(entry)
    save_wishlist(wl)
    return entry["wishlist_id"]


def remove_wishlist_outfit(wishlist_id: str) -> bool:
    wl = load_wishlist()
    original = len(wl["outfits"])
    wl["outfits"] = [o for o in wl["outfits"] if o.get("wishlist_id") != wishlist_id]
    if len(wl["outfits"]) < original:
        save_wishlist(wl)
        return True
    return False


def get_wishlist_item_count() -> int:
    wl = load_wishlist()
    return len(wl["items"])


def get_wishlist_outfit_count() -> int:
    wl = load_wishlist()
    return len(wl["outfits"])


def is_item_wishlisted(item_id: str) -> bool:
    wl = load_wishlist()
    return str(item_id) in {str(i.get("id", "")) for i in wl["items"]}
