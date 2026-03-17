"""
matching_engine.py
------------------
Rule-based outfit matching for Vinted Outfit Match prototype.
This is a v1 placeholder — designed to be swapped for an ML model later.

Logic summary:
- Gender: hard filter (Men/Women separate, Unisex matches both)
- Season: soft score boost
- Usage/Occasion: soft score boost
- Colour harmony: soft score boost
- Category compatibility: defines which article types can match together
- One result per outfit role (top, bottom, shoes, accessory, etc.)
"""

import os
import pandas as pd
import random

from services.image_url import get_image_url


# ---------------------------------------------------------------------------
# GENDER COMPATIBILITY
# Hard filter — Men's items never match Women's and vice versa.
# Unisex is compatible with everyone.
# Boys/Girls are only compatible with each other and Unisex.
# ---------------------------------------------------------------------------
GENDER_COMPAT = {
    "Men":    ["Men", "Unisex"],
    "Women":  ["Women", "Unisex"],
    "Unisex": ["Men", "Women", "Unisex", "Boys", "Girls"],
    "Boys":   ["Boys", "Unisex"],
    "Girls":  ["Girls", "Unisex"],
}


# ---------------------------------------------------------------------------
# COLOUR HARMONY
# Based on classic fashion colour theory + what's most common in the dataset.
# Soft score: +30 if colours are compatible.
# ---------------------------------------------------------------------------
COLOUR_COMPAT = {
    "Black":        ["White", "Grey", "Red", "Blue", "Navy Blue", "Silver",
                     "Gold", "Beige", "Cream", "Off White", "Pink", "Yellow",
                     "Maroon", "Green", "Multi"],
    "White":        ["Black", "Grey", "Blue", "Navy Blue", "Red", "Green",
                     "Beige", "Pink", "Brown", "Gold", "Silver", "Multi",
                     "Teal", "Olive", "Maroon"],
    "Blue":         ["White", "Grey", "Black", "Beige", "Brown", "Navy Blue",
                     "Silver", "Off White", "Cream"],
    "Navy Blue":    ["White", "Beige", "Grey", "Silver", "Gold", "Cream",
                     "Off White", "Brown", "Red"],
    "Grey":         ["White", "Black", "Blue", "Navy Blue", "Red", "Pink",
                     "Purple", "Teal", "Silver"],
    "Brown":        ["Beige", "Cream", "White", "Olive", "Khaki", "Blue",
                     "Mustard", "Tan", "Off White", "Coffee Brown"],
    "Beige":        ["Brown", "White", "Black", "Navy Blue", "Olive",
                     "Khaki", "Tan", "Cream", "Mustard", "Gold"],
    "Red":          ["Black", "White", "Grey", "Navy Blue", "Beige", "Gold"],
    "Green":        ["White", "Beige", "Brown", "Khaki", "Olive", "Navy Blue",
                     "Black", "Mustard"],
    "Olive":        ["Beige", "Brown", "White", "Khaki", "Mustard", "Black"],
    "Khaki":        ["Brown", "Olive", "Beige", "White", "Navy Blue", "Black"],
    "Pink":         ["White", "Grey", "Black", "Beige", "Gold", "Silver",
                     "Mauve", "Lavender", "Nude"],
    "Purple":       ["White", "Grey", "Black", "Silver", "Gold", "Lavender"],
    "Maroon":       ["White", "Beige", "Black", "Gold", "Grey", "Cream"],
    "Yellow":       ["White", "Black", "Grey", "Navy Blue", "Brown", "Mustard"],
    "Mustard":      ["Brown", "Olive", "Beige", "Black", "Navy Blue", "White"],
    "Orange":       ["White", "Black", "Brown", "Beige", "Navy Blue"],
    "Teal":         ["White", "Grey", "Black", "Beige", "Gold", "Brown"],
    "Gold":         ["Black", "White", "Navy Blue", "Brown", "Maroon", "Beige"],
    "Silver":       ["Black", "White", "Grey", "Navy Blue", "Blue"],
    "Cream":        ["Brown", "Beige", "Black", "Navy Blue", "Maroon", "Gold"],
    "Off White":    ["Black", "Brown", "Navy Blue", "Beige", "Maroon"],
    "Lavender":     ["White", "Grey", "Purple", "Pink", "Silver"],
    "Peach":        ["White", "Brown", "Beige", "Gold", "Cream"],
    "Rust":         ["Brown", "Beige", "White", "Black", "Olive"],
    "Burgundy":     ["White", "Beige", "Black", "Grey", "Gold"],
    "Charcoal":     ["White", "Black", "Grey", "Red", "Blue"],
    "Turquoise Blue": ["White", "Black", "Brown", "Beige"],
    "Nude":         ["White", "Beige", "Brown", "Black", "Gold"],
    "Multi":        ["Black", "White", "Beige", "Grey", "Navy Blue"],
}


# ---------------------------------------------------------------------------
# USAGE / OCCASION COMPATIBILITY
# Soft score: +25 if occasions are compatible.
# Casual is treated broadly since 77% of catalog is Casual.
# ---------------------------------------------------------------------------
USAGE_COMPAT = {
    "Casual":      ["Casual", "Smart Casual", "Travel", "Home"],
    "Formal":      ["Formal", "Smart Casual"],
    "Smart Casual": ["Smart Casual", "Casual", "Formal"],
    "Sports":      ["Sports", "Casual"],
    "Ethnic":      ["Ethnic", "Party"],
    "Party":       ["Party", "Casual", "Ethnic"],
    "Travel":      ["Travel", "Casual", "Sports"],
    "Home":        ["Home", "Casual"],
}


# ---------------------------------------------------------------------------
# SEASON COMPATIBILITY
# Soft score: +15 if seasons are compatible.
# Fall is treated as all-season (matches anything).
# Summer <-> Spring are cross-compatible since dataset shows Spring is thin.
# ---------------------------------------------------------------------------
SEASON_COMPAT = {
    "Summer": ["Summer", "Spring", "Fall"],
    "Winter": ["Winter", "Fall"],
    "Spring": ["Spring", "Summer", "Fall"],
    "Fall":   ["Fall", "Summer", "Winter", "Spring"],  # wildcard
}


# ---------------------------------------------------------------------------
# OUTFIT ROLES
# Each article type is assigned a role. get_outfit_bundle() picks
# one item per role to build a diverse outfit.
# ---------------------------------------------------------------------------
ARTICLE_ROLES = {
    # Tops
    "Tshirts": "top", "Shirts": "top", "Tops": "top", "Blouses": "top",
    "Sweaters": "top", "Sweatshirts": "top", "Jackets": "top",
    "Blazers": "top", "Kurtas": "top", "Kurtis": "top", "Tunics": "top",
    "Shrug": "top", "Waistcoat": "top", "Nehru Jackets": "top",
    "Suits": "top", "Rain Jacket": "top", "Lounge Tshirts": "top",
    "Camisoles": "top",

    # Bottoms
    "Jeans": "bottom", "Trousers": "bottom", "Shorts": "bottom",
    "Track Pants": "bottom", "Skirts": "bottom", "Capris": "bottom",
    "Leggings": "bottom", "Jeggings": "bottom", "Salwar": "bottom",
    "Churidar": "bottom", "Patiala": "bottom", "Lounge Pants": "bottom",
    "Lounge Shorts": "bottom", "Rain Trousers": "bottom",

    # Full outfits (treat as top — no bottom needed)
    "Dresses": "top", "Rompers": "top", "Jumpsuit": "top",
    "Sarees": "top", "Lehenga Choli": "top", "Kurta Sets": "top",
    "Clothing Set": "top", "Tracksuits": "top",

    # Shoes
    "Casual Shoes": "shoes", "Formal Shoes": "shoes", "Sports Shoes": "shoes",
    "Heels": "shoes", "Flats": "shoes", "Sandals": "shoes",
    "Flip Flops": "shoes", "Boots": "shoes", "Sports Sandals": "shoes",
    "Booties": "shoes",

    # Watches
    "Watches": "watch",

    # Bags
    "Handbags": "bag", "Backpacks": "bag", "Clutches": "bag",
    "Wallets": "bag", "Laptop Bag": "bag", "Duffel Bag": "bag",
    "Rucksacks": "bag", "Messenger Bag": "bag", "Waist Pouch": "bag",

    # Jewellery / small accessories
    "Sunglasses": "accessory", "Belts": "accessory", "Socks": "accessory",
    "Ties": "accessory", "Cufflinks": "accessory", "Scarves": "accessory",
    "Stoles": "accessory", "Mufflers": "accessory", "Caps": "accessory",
    "Hat": "accessory", "Earrings": "accessory", "Necklace and Chains": "accessory",
    "Bracelet": "accessory", "Bangle": "accessory", "Ring": "accessory",
    "Pendant": "accessory", "Jewellery Set": "accessory", "Wristbands": "accessory",
    "Headband": "accessory", "Dupatta": "accessory", "Gloves": "accessory",
    "Suspenders": "accessory", "Ties and Cufflinks": "accessory",
}

# The roles we want in a complete outfit bundle, in priority order
# Core clothing first (top, bottom, shoes), then max 1 accessory slot
OUTFIT_ROLE_ORDER = ["top", "bottom", "shoes", "accessory"]

# Accessory-type roles that should be limited in get_matches()
ACCESSORY_ROLES = {"watch", "bag", "accessory"}


# ---------------------------------------------------------------------------
# CATEGORY COMPATIBILITY
# Defines which article types complement each other.
# Key = seed article type, Value = list of compatible article types.
# ---------------------------------------------------------------------------
CATEGORY_COMPAT = {
    # --- Tops ---
    "Tshirts":      ["Jeans", "Shorts", "Track Pants", "Casual Shoes",
                     "Sports Shoes", "Flip Flops", "Watches", "Caps",
                     "Sunglasses", "Belts", "Backpacks", "Socks"],
    "Shirts":       ["Jeans", "Trousers", "Chinos", "Shorts", "Formal Shoes",
                     "Casual Shoes", "Watches", "Belts", "Sunglasses",
                     "Ties", "Cufflinks", "Wallets"],
    "Tops":         ["Jeans", "Skirts", "Shorts", "Leggings", "Heels",
                     "Flats", "Casual Shoes", "Handbags", "Sunglasses",
                     "Earrings", "Necklace and Chains", "Watches"],
    "Blazers":      ["Trousers", "Jeans", "Formal Shoes", "Casual Shoes",
                     "Shirts", "Ties", "Watches", "Belts", "Cufflinks"],
    "Suits":        ["Formal Shoes", "Ties", "Cufflinks", "Watches",
                     "Belts", "Wallets"],
    "Sweaters":     ["Jeans", "Trousers", "Casual Shoes", "Boots",
                     "Scarves", "Caps", "Watches"],
    "Sweatshirts":  ["Track Pants", "Jeans", "Sports Shoes", "Casual Shoes",
                     "Caps", "Backpacks", "Socks"],
    "Jackets":      ["Jeans", "Trousers", "Casual Shoes", "Sports Shoes",
                     "Backpacks", "Caps", "Watches"],
    "Kurtas":       ["Salwar", "Churidar", "Patiala", "Flats", "Sandals",
                     "Heels", "Earrings", "Necklace and Chains", "Dupatta",
                     "Handbags", "Watches"],
    "Kurtis":       ["Salwar", "Churidar", "Leggings", "Flats", "Sandals",
                     "Earrings", "Dupatta", "Handbags"],
    "Tunics":       ["Leggings", "Jeans", "Flats", "Sandals", "Handbags",
                     "Earrings"],
    "Waistcoat":    ["Shirts", "Trousers", "Formal Shoes", "Watches", "Ties"],
    "Nehru Jackets":["Kurtas", "Churidar", "Formal Shoes", "Watches"],
    "Shrug":        ["Tops", "Dresses", "Jeans", "Heels", "Handbags"],
    "Camisoles":    ["Jeans", "Shorts", "Skirts", "Casual Shoes", "Flats"],

    # --- Bottoms ---
    "Jeans":        ["Tshirts", "Shirts", "Tops", "Casual Shoes",
                     "Sports Shoes", "Heels", "Flats", "Belts",
                     "Watches", "Sunglasses", "Handbags", "Backpacks"],
    "Trousers":     ["Shirts", "Blazers", "Formal Shoes", "Casual Shoes",
                     "Belts", "Watches", "Ties"],
    "Shorts":       ["Tshirts", "Tops", "Casual Shoes", "Sports Shoes",
                     "Flip Flops", "Sunglasses", "Caps"],
    "Skirts":       ["Tops", "Blouses", "Heels", "Flats", "Handbags",
                     "Earrings", "Necklace and Chains"],
    "Track Pants":  ["Tshirts", "Sweatshirts", "Sports Shoes", "Socks",
                     "Caps", "Backpacks"],
    "Leggings":     ["Tops", "Kurtis", "Tunics", "Flats", "Casual Shoes",
                     "Handbags"],
    "Jeggings":     ["Tops", "Tshirts", "Casual Shoes", "Flats", "Handbags"],
    "Capris":       ["Tops", "Tshirts", "Casual Shoes", "Flats", "Sandals"],
    "Salwar":       ["Kurtas", "Kurtis", "Flats", "Sandals", "Earrings"],
    "Churidar":     ["Kurtas", "Kurtis", "Flats", "Sandals", "Earrings"],

    # --- Full outfits ---
    "Dresses":      ["Heels", "Flats", "Sandals", "Handbags", "Clutches",
                     "Earrings", "Necklace and Chains", "Sunglasses",
                     "Watches", "Scarves"],
    "Sarees":       ["Heels", "Flats", "Earrings", "Necklace and Chains",
                     "Bangle", "Handbags", "Clutches"],
    "Lehenga Choli":["Heels", "Flats", "Earrings", "Necklace and Chains",
                     "Bangle", "Clutches"],
    "Jumpsuit":     ["Heels", "Flats", "Casual Shoes", "Handbags", "Clutches",
                     "Earrings", "Sunglasses"],
    "Rompers":      ["Sandals", "Flats", "Casual Shoes", "Sunglasses",
                     "Handbags"],
    "Tracksuits":   ["Sports Shoes", "Socks", "Caps", "Backpacks",
                     "Wristbands"],

    # --- Shoes ---
    "Casual Shoes": ["Jeans", "Shorts", "Tshirts", "Shirts", "Tops",
                     "Watches", "Sunglasses", "Belts", "Backpacks"],
    "Formal Shoes": ["Trousers", "Suits", "Shirts", "Blazers", "Ties",
                     "Watches", "Belts", "Wallets"],
    "Sports Shoes": ["Track Pants", "Shorts", "Tshirts", "Sweatshirts",
                     "Socks", "Caps", "Backpacks", "Wristbands"],
    "Heels":        ["Dresses", "Skirts", "Jeans", "Trousers", "Tops",
                     "Handbags", "Clutches", "Earrings"],
    "Flats":        ["Jeans", "Skirts", "Dresses", "Leggings", "Kurtas",
                     "Handbags", "Earrings"],
    "Sandals":      ["Dresses", "Shorts", "Skirts", "Kurtas", "Tops",
                     "Handbags", "Sunglasses"],
    "Flip Flops":   ["Shorts", "Tshirts", "Casual Shoes", "Sunglasses"],
    "Sports Sandals":["Track Pants", "Shorts", "Tshirts", "Socks"],

    # --- Accessories / Watches / Bags ---
    "Watches":      ["Shirts", "Tshirts", "Jeans", "Trousers", "Formal Shoes",
                     "Casual Shoes", "Belts", "Wallets"],
    "Sunglasses":   ["Tshirts", "Shirts", "Tops", "Dresses", "Casual Shoes",
                     "Caps", "Handbags", "Backpacks"],
    "Belts":        ["Jeans", "Trousers", "Shirts", "Formal Shoes",
                     "Casual Shoes", "Watches"],
    "Handbags":     ["Dresses", "Tops", "Jeans", "Skirts", "Heels", "Flats",
                     "Sunglasses", "Earrings"],
    "Backpacks":    ["Tshirts", "Sweatshirts", "Jeans", "Track Pants",
                     "Casual Shoes", "Sports Shoes", "Caps"],
    "Clutches":     ["Dresses", "Sarees", "Heels", "Earrings",
                     "Necklace and Chains"],
    "Ties":         ["Shirts", "Suits", "Blazers", "Formal Shoes",
                     "Cufflinks", "Watches"],
    "Cufflinks":    ["Shirts", "Suits", "Blazers", "Ties", "Watches"],
    "Scarves":      ["Sweaters", "Jackets", "Coats", "Casual Shoes"],
    "Caps":         ["Tshirts", "Sweatshirts", "Jackets", "Sports Shoes",
                     "Casual Shoes", "Backpacks", "Sunglasses"],
    "Socks":        ["Sports Shoes", "Casual Shoes", "Track Pants", "Shorts"],
    "Earrings":     ["Dresses", "Tops", "Kurtas", "Sarees", "Handbags"],
    "Necklace and Chains": ["Dresses", "Tops", "Tshirts", "Handbags"],
    "Wallets":      ["Watches", "Belts", "Formal Shoes", "Shirts"],
    "Dupatta":      ["Kurtas", "Kurtis", "Salwar", "Churidar", "Sandals"],
    "Bangle":       ["Sarees", "Kurtas", "Lehenga Choli", "Earrings"],
}


class OutfitMatcher:
    """
    Matches fashion items to build complementary outfits.
    Uses rule-based scoring with soft/hard filters.
    """

    def __init__(self, catalog_path=None):
        if catalog_path is None:
            catalog_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data", "vinted_catalog.csv"
            )
        self.df = pd.read_csv(catalog_path, on_bad_lines="skip")

        # Fill missing values with sensible defaults
        self.df["usage"] = self.df["usage"].fillna("Casual")
        self.df["season"] = self.df["season"].fillna("Fall")  # Fall = wildcard
        self.df["baseColour"] = self.df["baseColour"].fillna("Multi")
        self.df["gender"] = self.df["gender"].fillna("Unisex")

        # Filter to useful categories only (remove noise)
        useful = ["Apparel", "Accessories", "Footwear"]
        self.df = self.df[self.df["masterCategory"].isin(useful)].copy()
        self.df = self.df.reset_index(drop=True)

        print(f"Catalog loaded: {len(self.df):,} items ready for matching.")

    def _get_item(self, item_id):
        """Fetch a single item by ID."""
        result = self.df[self.df["id"] == item_id]
        if result.empty:
            return None
        return result.iloc[0]

    def _score_candidate(self, seed, candidate):
        """
        Score how well a candidate item matches the seed item.
        Returns an integer score (higher = better match).
        """
        score = 0

        # Colour harmony — soft +30
        seed_colour = seed["baseColour"]
        cand_colour = candidate["baseColour"]
        compatible_colours = COLOUR_COMPAT.get(seed_colour, [])
        if cand_colour in compatible_colours:
            score += 30

        # Usage/occasion — soft +25
        seed_usage = seed["usage"]
        cand_usage = candidate["usage"]
        compatible_usages = USAGE_COMPAT.get(seed_usage, [seed_usage])
        if cand_usage in compatible_usages:
            score += 25

        # Season — soft +15
        seed_season = seed["season"]
        cand_season = candidate["season"]
        compatible_seasons = SEASON_COMPAT.get(seed_season, [seed_season])
        if cand_season in compatible_seasons:
            score += 15

        # Same seller boost +40 (encourages bundle purchases)
        if seed["seller"] == candidate["seller"]:
            score += 40

        # Random variation so results feel less robotic
        score += random.randint(1, 15)

        return score

    def _gender_filter(self, seed_gender):
        """Return a filtered dataframe with only gender-compatible items."""
        allowed = GENDER_COMPAT.get(seed_gender, [seed_gender])
        return self.df[self.df["gender"].isin(allowed)]

    def _build_explanation(self, seed, candidate, score):
        """Generate a short human-readable explanation for the match."""
        reasons = []

        seed_colour = seed["baseColour"]
        cand_colour = candidate["baseColour"]
        if cand_colour in COLOUR_COMPAT.get(seed_colour, []):
            reasons.append(f"Colour harmony ({seed_colour} + {cand_colour})")

        seed_usage = seed["usage"]
        if candidate["usage"] in USAGE_COMPAT.get(seed_usage, []):
            reasons.append(f"{candidate['usage']} vibe")

        if seed["seller"] == candidate["seller"]:
            reasons.append("Same seller — save on shipping!")

        if not reasons:
            reasons.append("Complementary style")

        return " • ".join(reasons)

    def get_matches(self, item_id, num_matches=6):
        """
        Find num_matches complementary items for a given item_id.
        Returns a list of dicts with item info + score + explanation.
        """
        seed = self._get_item(item_id)
        if seed is None:
            print(f"Item {item_id} not found.")
            return []

        seed_article = seed["articleType"]
        compatible_types = CATEGORY_COMPAT.get(seed_article, [])

        if not compatible_types:
            print(f"No compatibility rules defined for: {seed_article}")
            return []

        # Hard filter: gender + compatible article types
        pool = self._gender_filter(seed["gender"])
        pool = pool[pool["articleType"].isin(compatible_types)]
        pool = pool[pool["id"] != item_id]  # exclude the seed itself

        if pool.empty:
            return []

        # Score all candidates
        pool = pool.copy()
        pool["_score"] = pool.apply(
            lambda row: self._score_candidate(seed, row), axis=1
        )

        # Sort by score descending
        pool = pool.sort_values("_score", ascending=False)

        # Pick top num_matches
        top = pool.head(num_matches * 3)  # take a larger sample first

        # Try to get variety in article types (avoid 3 identical types)
        # Also limit accessories: max 2 accessories total out of num_matches
        max_accessories = max(1, num_matches // 3)  # e.g. 2 out of 6
        seen_types = {}
        accessory_count = 0
        results = []
        for _, row in top.iterrows():
            atype = row["articleType"]
            role = ARTICLE_ROLES.get(atype, "other")

            # Limit accessories to prevent dominating recommendations
            if role in ACCESSORY_ROLES:
                if accessory_count >= max_accessories:
                    continue
                accessory_count += 1

            seen_types[atype] = seen_types.get(atype, 0) + 1
            if seen_types[atype] > 2:
                continue  # max 2 of the same article type
            explanation = self._build_explanation(seed, row, row["_score"])
            results.append({
                "id":          row["id"],
                "name":        row["productDisplayName"],
                "type":        atype,
                "articleType": atype,
                "subCategory": row["subCategory"],
                "color":       row["baseColour"],
                "colour":      row["baseColour"],
                "seller":      row["seller"],
                "price":       row["price"],
                "condition":   row["condition"],
                "score":       int(row["_score"]),
                "explanation": explanation,
                "image_path":  get_image_url(row['id']),
            })
            if len(results) >= num_matches:
                break

        return results

    def get_outfit_bundle(self, item_id, num_items=4):
        """
        Build a complete outfit around item_id.
        Guarantees one item per outfit role (top, bottom, shoes, accessory).
        Returns a list of dicts.
        """
        seed = self._get_item(item_id)
        if seed is None:
            return []

        seed_article = seed["articleType"]
        seed_role = ARTICLE_ROLES.get(seed_article, "other")

        # Start the bundle with the seed item
        bundle = [{
            "id":          seed["id"],
            "name":        seed["productDisplayName"],
            "articleType": seed_article,
            "role":        seed_role,
            "colour":      seed["baseColour"],
            "seller":      seed["seller"],
            "price":       seed["price"],
            "condition":   seed["condition"],
            "image_path":  get_image_url(seed['id']),
            "is_seed":     True,
        }]

        filled_roles = {seed_role}

        # Gender-compatible pool
        pool = self._gender_filter(seed["gender"])
        pool = pool[pool["id"] != item_id].copy()

        # Score the whole pool against seed
        pool["_score"] = pool.apply(
            lambda row: self._score_candidate(seed, row), axis=1
        )
        pool = pool.sort_values("_score", ascending=False)

        # Fill one slot per role in priority order
        roles_needed = [r for r in OUTFIT_ROLE_ORDER if r not in filled_roles]
        roles_needed = roles_needed[: num_items - 1]  # -1 because seed already added

        for role in roles_needed:
            # Get article types that belong to this role
            role_types = [art for art, r in ARTICLE_ROLES.items() if r == role]

            # Also filter by compatibility with seed article type
            compatible_types = CATEGORY_COMPAT.get(seed_article, [])
            if compatible_types:
                role_types = [t for t in role_types if t in compatible_types]

            # If no compatible types found for this role, use any type in that role
            if not role_types:
                role_types = [art for art, r in ARTICLE_ROLES.items() if r == role]

            candidates = pool[pool["articleType"].isin(role_types)]

            if candidates.empty:
                continue

            # Pick the top scorer for this role
            best = candidates.iloc[0]
            bundle.append({
                "id":          best["id"],
                "name":        best["productDisplayName"],
                "articleType": best["articleType"],
                "role":        role,
                "colour":      best["baseColour"],
                "seller":      best["seller"],
                "price":       best["price"],
                "condition":   best["condition"],
                "image_path":  get_image_url(best['id']),
                "is_seed":     False,
            })

            # Remove this item from pool so we don't pick it again
            pool = pool[pool["id"] != best["id"]]
            filled_roles.add(role)

        return bundle

    def _wardrobe_to_seed(self, wardrobe_item):
        """Convert a wardrobe item dict into a seed-like Series for scoring."""
        # Map wardrobe item fields to catalog-style fields
        type_str = wardrobe_item.get("type", "Other")
        return {
            "id": wardrobe_item["id"],
            "productDisplayName": wardrobe_item.get("name", ""),
            "articleType": type_str,
            "baseColour": wardrobe_item.get("color", "Multi"),
            "gender": wardrobe_item.get("gender", "Unisex"),
            "usage": (wardrobe_item.get("occasion", ["Casual"]) or ["Casual"])[0],
            "season": (wardrobe_item.get("season", ["Fall"]) or ["Fall"])[0],
            "seller": "__wardrobe__",
            "price": 0,
            "condition": "Good",
        }

    def get_matches_for_wardrobe_item(self, wardrobe_item, num_matches=6, source="catalog"):
        """
        Find matches for a wardrobe item.
        source: "catalog" to match from full catalog, "wardrobe" to match from wardrobe items.
        For wardrobe-to-wardrobe matching, pass wardrobe_items list.
        """
        seed = self._wardrobe_to_seed(wardrobe_item)
        seed_article = seed["articleType"]
        compatible_types = CATEGORY_COMPAT.get(seed_article, [])

        if not compatible_types:
            # Fallback: try common mappings for wardrobe types
            type_mapping = {
                "T-Shirt": "Tshirts", "Shirt": "Shirts", "Blouse": "Blouses",
                "Sweater": "Sweaters", "Hoodie": "Sweatshirts", "Jacket": "Jackets",
                "Blazer": "Blazers", "Coat": "Jackets", "Dress": "Dresses",
                "Skirt": "Skirts", "Jeans": "Jeans", "Trousers": "Trousers",
                "Shorts": "Shorts", "Sneakers": "Casual Shoes", "Boots": "Boots",
                "Sandals": "Sandals", "Heels": "Heels", "Flats": "Flats",
                "Bag": "Handbags", "Watch": "Watches", "Sunglasses": "Sunglasses",
                "Scarf": "Scarves", "Hat": "Caps", "Belt": "Belts",
            }
            mapped = type_mapping.get(seed_article)
            if mapped:
                seed["articleType"] = mapped
                seed_article = mapped
                compatible_types = CATEGORY_COMPAT.get(seed_article, [])

        if not compatible_types:
            return []

        # Convert seed dict to a pandas-like object for _score_candidate
        import pandas as pd
        seed_series = pd.Series(seed)

        # Gender-compatible pool from catalog
        pool = self._gender_filter(seed["gender"])
        pool = pool[pool["articleType"].isin(compatible_types)].copy()

        if pool.empty:
            return []

        # Score candidates
        pool["_score"] = pool.apply(
            lambda row: self._score_candidate(seed_series, row), axis=1
        )
        pool = pool.sort_values("_score", ascending=False)

        top = pool.head(num_matches * 3)

        max_accessories = max(1, num_matches // 3)
        seen_types = {}
        accessory_count = 0
        results = []
        for _, row in top.iterrows():
            atype = row["articleType"]
            role = ARTICLE_ROLES.get(atype, "other")

            if role in ACCESSORY_ROLES:
                if accessory_count >= max_accessories:
                    continue
                accessory_count += 1

            seen_types[atype] = seen_types.get(atype, 0) + 1
            if seen_types[atype] > 2:
                continue

            explanation = self._build_explanation(seed_series, row, row["_score"])
            results.append({
                "id":          row["id"],
                "name":        row["productDisplayName"],
                "type":        atype,
                "articleType": atype,
                "color":       row["baseColour"],
                "colour":      row["baseColour"],
                "seller":      row["seller"],
                "price":       row["price"],
                "condition":   row["condition"],
                "score":       int(row["_score"]),
                "explanation": explanation,
                "image_path":  get_image_url(row['id']),
            })
            if len(results) >= num_matches:
                break

        return results

    def get_wardrobe_matches(self, wardrobe_item, all_wardrobe_items, num_matches=6):
        """
        Find matching items from the user's wardrobe (not catalog).
        Uses same scoring logic adapted for wardrobe item dicts.
        """
        seed = self._wardrobe_to_seed(wardrobe_item)
        seed_article = seed["articleType"]
        compatible_types = CATEGORY_COMPAT.get(seed_article, [])

        # Map wardrobe types to catalog types for compatibility lookup
        type_mapping = {
            "T-Shirt": "Tshirts", "Shirt": "Shirts", "Blouse": "Blouses",
            "Sweater": "Sweaters", "Hoodie": "Sweatshirts", "Jacket": "Jackets",
            "Blazer": "Blazers", "Coat": "Jackets", "Dress": "Dresses",
            "Skirt": "Skirts", "Jeans": "Jeans", "Trousers": "Trousers",
            "Shorts": "Shorts", "Sneakers": "Casual Shoes", "Boots": "Boots",
            "Sandals": "Sandals", "Heels": "Heels", "Flats": "Flats",
            "Bag": "Handbags", "Watch": "Watches", "Sunglasses": "Sunglasses",
            "Scarf": "Scarves", "Hat": "Caps", "Belt": "Belts",
        }
        reverse_mapping = {v: k for k, v in type_mapping.items()}

        if not compatible_types:
            mapped = type_mapping.get(seed_article)
            if mapped:
                seed_article = mapped
                compatible_types = CATEGORY_COMPAT.get(seed_article, [])

        if not compatible_types:
            return []

        # Get wardrobe types that map to compatible catalog types
        compatible_wardrobe_types = set()
        for ct in compatible_types:
            if ct in reverse_mapping:
                compatible_wardrobe_types.add(reverse_mapping[ct])
            compatible_wardrobe_types.add(ct)  # also keep catalog names in case wardrobe uses them

        results = []
        for item in all_wardrobe_items:
            if item["id"] == wardrobe_item["id"]:
                continue
            item_type = item.get("type", "")
            if item_type not in compatible_wardrobe_types:
                continue

            # Simple scoring for wardrobe items
            score = 0
            item_color = item.get("color", "")
            seed_color = wardrobe_item.get("color", "")
            if item_color in COLOUR_COMPAT.get(seed_color, []):
                score += 30

            item_occasions = item.get("occasion", ["Casual"])
            seed_occasion = (wardrobe_item.get("occasion", ["Casual"]) or ["Casual"])[0]
            if seed_occasion in item_occasions:
                score += 25

            item_seasons = item.get("season", [])
            seed_seasons = wardrobe_item.get("season", [])
            if any(s in item_seasons for s in seed_seasons):
                score += 15

            score += random.randint(1, 15)

            role = ARTICLE_ROLES.get(type_mapping.get(item_type, item_type), "other")

            results.append({
                "id": item["id"],
                "name": item.get("name", ""),
                "type": item_type,
                "color": item_color,
                "image_filename": item.get("image_filename", ""),
                "formality": item.get("formality", ""),
                "season": item.get("season", []),
                "score": score,
                "role": role,
                "explanation": f"Matches your {seed_color} {wardrobe_item.get('type', '')}",
                "_source": "wardrobe",
            })

        # Sort by score, limit accessories
        results.sort(key=lambda x: x["score"], reverse=True)
        max_accessories = max(1, num_matches // 3)
        accessory_count = 0
        filtered = []
        for r in results:
            role = r.get("role", "other")
            if role in ACCESSORY_ROLES:
                if accessory_count >= max_accessories:
                    continue
                accessory_count += 1
            filtered.append(r)
            if len(filtered) >= num_matches:
                break

        return filtered

    def get_outfit_bundle_for_wardrobe_item(self, wardrobe_item, num_items=4, source="catalog"):
        """
        Build a complete outfit around a wardrobe item using catalog items.
        Returns a bundle list similar to get_outfit_bundle().
        """
        seed = self._wardrobe_to_seed(wardrobe_item)
        seed_article = seed["articleType"]

        # Map wardrobe type to catalog type
        type_mapping = {
            "T-Shirt": "Tshirts", "Shirt": "Shirts", "Blouse": "Blouses",
            "Sweater": "Sweaters", "Hoodie": "Sweatshirts", "Jacket": "Jackets",
            "Blazer": "Blazers", "Coat": "Jackets", "Dress": "Dresses",
            "Skirt": "Skirts", "Jeans": "Jeans", "Trousers": "Trousers",
            "Shorts": "Shorts", "Sneakers": "Casual Shoes", "Boots": "Boots",
            "Sandals": "Sandals", "Heels": "Heels", "Flats": "Flats",
            "Bag": "Handbags", "Watch": "Watches", "Sunglasses": "Sunglasses",
            "Scarf": "Scarves", "Hat": "Caps", "Belt": "Belts",
        }
        mapped = type_mapping.get(seed_article)
        if mapped:
            seed_article = mapped

        seed_role = ARTICLE_ROLES.get(seed_article, "other")

        import pandas as pd
        seed_series = pd.Series(seed)

        # Start bundle with wardrobe seed item
        bundle = [{
            "id": wardrobe_item["id"],
            "name": wardrobe_item.get("name", ""),
            "articleType": wardrobe_item.get("type", ""),
            "role": seed_role,
            "colour": wardrobe_item.get("color", ""),
            "price": 0,
            "condition": "Owned",
            "image_filename": wardrobe_item.get("image_filename", ""),
            "is_seed": True,
            "_source": "wardrobe",
        }]

        filled_roles = {seed_role}
        pool = self._gender_filter(seed.get("gender", "Unisex"))
        pool = pool[pool["id"] != wardrobe_item["id"]].copy()

        pool["_score"] = pool.apply(
            lambda row: self._score_candidate(seed_series, row), axis=1
        )
        pool = pool.sort_values("_score", ascending=False)

        roles_needed = [r for r in OUTFIT_ROLE_ORDER if r not in filled_roles]
        roles_needed = roles_needed[: num_items - 1]

        for role in roles_needed:
            role_types = [art for art, r in ARTICLE_ROLES.items() if r == role]
            compatible_types = CATEGORY_COMPAT.get(seed_article, [])
            if compatible_types:
                role_types = [t for t in role_types if t in compatible_types]
            if not role_types:
                role_types = [art for art, r in ARTICLE_ROLES.items() if r == role]

            candidates = pool[pool["articleType"].isin(role_types)]
            if candidates.empty:
                continue

            best = candidates.iloc[0]
            bundle.append({
                "id": best["id"],
                "name": best["productDisplayName"],
                "articleType": best["articleType"],
                "role": role,
                "colour": best["baseColour"],
                "color": best["baseColour"],
                "seller": best["seller"],
                "price": best["price"],
                "condition": best["condition"],
                "image_path": get_image_url(best['id']),
                "is_seed": False,
                "_source": "catalog",
            })
            pool = pool[pool["id"] != best["id"]]
            filled_roles.add(role)

        return bundle

    def get_total_price(self, bundle):
        """Calculate total price of an outfit bundle."""
        return sum(item["price"] for item in bundle)

    def get_same_seller_items(self, bundle):
        """Return items in the bundle that share the seed seller."""
        if not bundle:
            return []
        seed_seller = bundle[0]["seller"]
        return [item for item in bundle if item["seller"] == seed_seller]


# ---------------------------------------------------------------------------
# Quick test — run this file directly to check everything works
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    matcher = OutfitMatcher()

    # Grab a random item from the catalog to test with
    test_item = matcher.df.sample(1).iloc[0]
    test_id = test_item["id"]

    print(f"\nSeed item: [{test_id}] {test_item['productDisplayName']}")
    print(f"  Type: {test_item['articleType']} | Colour: {test_item['baseColour']}")
    print(f"  Gender: {test_item['gender']} | Usage: {test_item['usage']}")
    print(f"  Season: {test_item['season']} | Price: €{test_item['price']}")

    print("\n--- get_matches() ---")
    matches = matcher.get_matches(test_id, num_matches=6)
    if matches:
        for i, m in enumerate(matches, 1):
            print(f"  {i}. [{m['articleType']}] {m['name'][:50]}")
            print(f"       €{m['price']} | {m['colour']} | Score: {m['score']}")
            print(f"       Why: {m['explanation']}")
    else:
        print("  No matches found — check compatibility rules for this article type.")

    print("\n--- get_outfit_bundle() ---")
    bundle = matcher.get_outfit_bundle(test_id, num_items=4)
    total = matcher.get_total_price(bundle)
    for item in bundle:
        seed_tag = " ← seed" if item["is_seed"] else ""
        print(f"  [{item['role']}] {item['name'][:50]} | €{item['price']}{seed_tag}")
    print(f"  Total outfit price: €{total}")

    same_seller = matcher.get_same_seller_items(bundle)
    if len(same_seller) > 1:
        print(f"  {len(same_seller)} items from the same seller — bundle discount possible!")

