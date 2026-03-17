"""
profile_manager.py
------------------
CRUD operations for user profile stored in data/profile.json.
Handles loading, saving, and providing defaults for user preferences.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PROFILE_PATH = os.path.join(DATA_DIR, "profile.json")

DEFAULT_PROFILE = {
    "name": "",
    "city": "Barcelona",
    "gender": "Prefer not to say",
    "top_size": "M",
    "bottom_size": "M",
    "shoe_size": "EU 42",
    "style_preferences": [],
    "preferred_colors": [],
}


def load_profile() -> dict:
    """Load user profile from disk, returning defaults if none exists."""
    if os.path.exists(PROFILE_PATH):
        try:
            with open(PROFILE_PATH, "r") as f:
                data = json.load(f)
            # Merge with defaults so new keys are always present
            merged = {**DEFAULT_PROFILE, **data}
            return merged
        except (json.JSONDecodeError, IOError):
            return DEFAULT_PROFILE.copy()
    return DEFAULT_PROFILE.copy()


def save_profile(profile: dict) -> None:
    """Persist user profile to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)


def profile_exists() -> bool:
    """Check whether the user has saved a profile before."""
    return os.path.exists(PROFILE_PATH)


def get_profile_summary() -> str:
    """Return a short text summary of the profile for the chatbot system prompt."""
    p = load_profile()
    if not p.get("name"):
        return "No profile set up yet."
    parts = [f"Name: {p['name']}"]
    if p.get("city"):
        parts.append(f"City: {p['city']}")
    if p.get("gender") and p["gender"] != "Prefer not to say":
        parts.append(f"Gender: {p['gender']}")
    if p.get("style_preferences"):
        parts.append(f"Style: {', '.join(p['style_preferences'])}")
    if p.get("preferred_colors"):
        parts.append(f"Favorite colors: {', '.join(p['preferred_colors'])}")
    sizes = []
    if p.get("top_size"):
        sizes.append(f"Top {p['top_size']}")
    if p.get("bottom_size"):
        sizes.append(f"Bottom {p['bottom_size']}")
    if p.get("shoe_size"):
        sizes.append(f"Shoe {p['shoe_size']}")
    if sizes:
        parts.append(f"Sizes: {', '.join(sizes)}")
    return " | ".join(parts)


if __name__ == "__main__":
    print("Profile exists:", profile_exists())
    p = load_profile()
    print("Current profile:", json.dumps(p, indent=2))
    p["name"] = "Test User"
    save_profile(p)
    print("Saved. Summary:", get_profile_summary())
