"""
Page 7: My Wishlist
-------------------
User's wishlist of saved individual items and outfit combinations.
Supports removing items, moving items to cart, and moving outfits to My Outfits.
"""

import streamlit as st
import os
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Shared UI: page config + CSS + sidebar (must be first)
from services.shared_ui import setup_page, add_to_cart
setup_page("My Wishlist — Vinted Outfit Match V2")

from services.wishlist_manager import (
    load_wishlist,
    remove_wishlist_item,
    remove_wishlist_outfit,
)
from services.outfit_manager import create_outfit
from services.wardrobe_manager import load_wardrobe
from services.image_url import get_image_url

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
IMAGE_DIR = os.path.join(DATA_DIR, "images")
WARDROBE_IMAGES_DIR = os.path.join(DATA_DIR, "wardrobe_images")


# Show toast feedback from previous action
if "_wishlist_msg" in st.session_state:
    st.toast(st.session_state._wishlist_msg)
    del st.session_state._wishlist_msg


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">My Wishlist</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">Items and outfits you\'ve saved for later</div>', unsafe_allow_html=True)

wishlist = load_wishlist()
items = wishlist.get("items", [])
outfits = wishlist.get("outfits", [])

total_count = len(items) + len(outfits)

if total_count == 0:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">❤️</div>
        <div class="empty-state-title">Your wishlist is empty</div>
        <div class="empty-state-text">Browse items or ask the Style Assistant to find pieces you love!</div>
    </div>
    """, unsafe_allow_html=True)

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("🔍 Browse Catalog", use_container_width=True, key="wl_browse"):
            st.switch_page("pages/1_Browse_&_Match.py")
    with bc2:
        if st.button("💬 Ask Style Assistant", use_container_width=True, key="wl_chat"):
            st.switch_page("pages/3_Style_Assistant.py")
    st.stop()


# ---------------------------------------------------------------------------
# Wishlisted Items
# ---------------------------------------------------------------------------
if items:
    st.markdown(f"### Items ({len(items)})")

    cols_per_row = 4
    for row_start in range(0, len(items), cols_per_row):
        row_items = items[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, item in zip(cols, row_items):
            with col:
                source = item.get("_source", "catalog")
                item_id = str(item.get("id", ""))

                st.markdown('<div class="item-card">', unsafe_allow_html=True)

                # Image
                img_shown = False
                if source == "wardrobe":
                    img_file = item.get("image_filename", "")
                    if img_file:
                        img_path = os.path.join(WARDROBE_IMAGES_DIR, img_file)
                        if os.path.exists(img_path):
                            try:
                                st.image(img_path, use_container_width=True)
                                img_shown = True
                            except Exception:
                                pass
                else:
                    img_path = item.get("image_path") or get_image_url(item_id)
                    try:
                        st.image(img_path, use_container_width=True)
                        img_shown = True
                    except Exception:
                        pass

                if not img_shown:
                    st.markdown('<div style="background:#f0f0f0;height:160px;display:flex;align-items:center;justify-content:center;font-size:30px;">👕</div>', unsafe_allow_html=True)

                name = item.get("name", item.get("type", "Item"))
                color = item.get("color", "")
                price_str = f"€{item['price']}" if "price" in item else ""
                source_label = "📦 Catalog" if source == "catalog" else "👕 Wardrobe"

                st.markdown(f"""
                <div class="item-card-body">
                    <div class="item-card-price">{price_str}</div>
                    <div class="item-card-name">{name[:45]}</div>
                    <div style="font-size:10px;color:#09B1BA;margin-top:4px;">{source_label}</div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # Action buttons
                b1, b2 = st.columns(2)
                with b1:
                    if source == "catalog" and item.get("price"):
                        if st.button("🛒", key=f"wl_cart_{item_id}_{row_start}", use_container_width=True, help="Move to Cart"):
                            cart_item = {
                                "id": item_id,
                                "name": name,
                                "type": item.get("type", ""),
                                "color": color,
                                "price": float(item.get("price", 0)),
                                "condition": item.get("condition", "Good"),
                                "image_path": item.get("image_path", get_image_url(item_id)),
                                "_source": "catalog",
                            }
                            add_to_cart(cart_item)
                            remove_wishlist_item(item_id)
                            st.session_state._wishlist_msg = f"Moved to cart!"
                            st.rerun()
                with b2:
                    if st.button("❌", key=f"wl_rm_{item_id}_{row_start}", use_container_width=True, help="Remove"):
                        remove_wishlist_item(item_id)
                        st.session_state._wishlist_msg = "Removed from wishlist"
                        st.rerun()


# ---------------------------------------------------------------------------
# Wishlisted Outfits
# ---------------------------------------------------------------------------
if outfits:
    if items:
        st.markdown("---")
    st.markdown(f"### Outfits ({len(outfits)})")

    wardrobe_items = load_wardrobe()

    cols_per_row = 2
    for row_start in range(0, len(outfits), cols_per_row):
        row_outfits = outfits[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)

        for col, outfit in zip(cols, row_outfits):
            with col:
                wl_id = outfit.get("wishlist_id", "")
                outfit_name = outfit.get("name", "Untitled Outfit")

                st.markdown(f"""
                <div class="card" style="margin-bottom:16px;">
                    <div style="font-size:18px;font-weight:700;color:#1A1A1A;margin-bottom:8px;">
                        ❤️ {outfit_name}
                    </div>
                """, unsafe_allow_html=True)

                # Show outfit item images
                outfit_item_list = outfit.get("recommended_items", [])
                if outfit_item_list:
                    item_cols = st.columns(min(len(outfit_item_list), 4))
                    for ic, oi in zip(item_cols, outfit_item_list[:4]):
                        with ic:
                            img_shown = False
                            oi_source = oi.get("_source", "catalog")
                            oi_id = str(oi.get("id", ""))

                            # Try wardrobe image
                            img_file = oi.get("image_filename", "")
                            if img_file:
                                img_p = os.path.join(WARDROBE_IMAGES_DIR, img_file)
                                if os.path.exists(img_p):
                                    st.image(img_p, use_container_width=True)
                                    img_shown = True

                            # Try catalog image via Cloudinary
                            if not img_shown and oi_source == "catalog":
                                cat_url = oi.get("image_path") or get_image_url(oi_id)
                                try:
                                    st.image(cat_url, use_container_width=True)
                                    img_shown = True
                                except Exception:
                                    pass

                            if not img_shown:
                                img_path_field = oi.get("image_path", "")
                                if img_path_field and (img_path_field.startswith("http") or os.path.exists(img_path_field)):
                                    try:
                                        st.image(img_path_field, use_container_width=True)
                                        img_shown = True
                                    except Exception:
                                        pass

                            if not img_shown:
                                st.markdown('<div style="background:#f5f5f5;height:80px;display:flex;align-items:center;justify-content:center;border-radius:6px;">👕</div>', unsafe_allow_html=True)

                            st.markdown(f'<div style="font-size:10px;text-align:center;color:#555;">{oi.get("type","")}</div>', unsafe_allow_html=True)

                # Tags
                tags_html = ""
                if outfit.get("occasion"):
                    tags_html += f'<span class="pill pill-teal">{outfit["occasion"]}</span>'
                if outfit.get("season"):
                    tags_html += f'<span class="pill pill-grey">{outfit["season"]}</span>'
                st.markdown(f'<div style="margin-top:8px;">{tags_html}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # Action buttons
                ob1, ob2 = st.columns(2)
                with ob1:
                    if st.button("✨ Save to My Outfits", key=f"wl_save_outfit_{wl_id}", use_container_width=True):
                        item_ids = [str(oi.get("id", "")) for oi in outfit.get("recommended_items", []) if oi.get("id")]
                        create_outfit(
                            name=outfit_name,
                            item_ids=item_ids,
                            occasion=outfit.get("occasion", "Casual"),
                            season=outfit.get("season", "All"),
                            source="wishlist",
                            recommended_items=outfit.get("recommended_items", []),
                        )
                        remove_wishlist_outfit(wl_id)
                        st.session_state._wishlist_msg = f"Outfit saved to My Outfits!"
                        st.rerun()
                with ob2:
                    if st.button("❌ Remove", key=f"wl_rm_outfit_{wl_id}", use_container_width=True):
                        remove_wishlist_outfit(wl_id)
                        st.session_state._wishlist_msg = "Outfit removed from wishlist"
                        st.rerun()
