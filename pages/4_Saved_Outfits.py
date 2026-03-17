"""
Page 4: Saved Outfits
---------------------
Gallery of saved outfit combinations displayed as visual outfit boards.
Supports manual outfit creation and outfits saved via the Style Assistant.
"""

import streamlit as st
import os
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Shared UI: page config + CSS + sidebar (must be first)
from services.shared_ui import setup_page
setup_page("My Outfits — Vinted Outfit Match V2")

from services.outfit_manager import load_outfits, delete_outfit, create_outfit
from services.wardrobe_manager import load_wardrobe
from services.image_url import get_image_url

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
IMAGE_DIR = os.path.join(DATA_DIR, "images")
WARDROBE_IMAGES_DIR = os.path.join(DATA_DIR, "wardrobe_images")


def get_wardrobe_item_by_id(item_id, wardrobe_items):
    """Find a wardrobe item by ID."""
    for item in wardrobe_items:
        if item["id"] == item_id:
            return item
    return None


def get_outfit_items(outfit, wardrobe_items):
    """
    Resolve outfit items, supporting both wardrobe items (by ID lookup)
    and catalog items (from stored recommended_items data).
    """
    # First try wardrobe lookup for each ID
    outfit_item_ids = outfit.get("item_ids", [])
    resolved = []
    unresolved_ids = set()

    for iid in outfit_item_ids:
        w_item = get_wardrobe_item_by_id(iid, wardrobe_items)
        if w_item:
            resolved.append(w_item)
        else:
            unresolved_ids.add(str(iid))

    # For unresolved IDs, check recommended_items (stored catalog data)
    rec_items = outfit.get("recommended_items", [])
    for rec in rec_items:
        rec_id = str(rec.get("id", ""))
        if rec_id in unresolved_ids:
            resolved.append(rec)
            unresolved_ids.discard(rec_id)

    return resolved


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">My Outfits</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">Your outfit combinations and style boards</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "show_create_outfit" not in st.session_state:
    st.session_state.show_create_outfit = False
if "selected_outfit_items" not in st.session_state:
    st.session_state.selected_outfit_items = []

outfits = load_outfits()
wardrobe_items = load_wardrobe()

# ---------------------------------------------------------------------------
# Top bar
# ---------------------------------------------------------------------------
top1, top2 = st.columns([3, 1])
with top1:
    st.markdown(f"**{len(outfits)}** outfits")
with top2:
    if st.button("➕ Create Outfit", use_container_width=True):
        st.session_state.show_create_outfit = not st.session_state.show_create_outfit
        st.session_state.selected_outfit_items = []
        st.rerun()

# ---------------------------------------------------------------------------
# Manual outfit creation flow
# ---------------------------------------------------------------------------
if st.session_state.show_create_outfit:
    st.markdown("---")
    st.markdown("### Create a New Outfit")

    if not wardrobe_items:
        st.warning("Your wardrobe is empty. Add items to your wardrobe first to create outfits.")
    else:
        outfit_name = st.text_input("Outfit Name", placeholder="e.g. Friday Casual, Rainy Work Day")

        oc1, oc2 = st.columns(2)
        with oc1:
            outfit_occasion = st.selectbox("Occasion", ["Casual", "Formal", "Smart Casual", "Business", "Party", "Sports", "Travel"], key="create_occasion")
        with oc2:
            outfit_season = st.selectbox("Season", ["Spring", "Summer", "Fall", "Winter", "All"], key="create_season")

        st.markdown("**Select items from your wardrobe:**")

        # Selectable wardrobe grid
        cols_per_row = 5
        for row_start in range(0, len(wardrobe_items), cols_per_row):
            row = wardrobe_items[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, item in zip(cols, row):
                with col:
                    is_selected = item["id"] in st.session_state.selected_outfit_items
                    border_style = "3px solid #007782" if is_selected else "1px solid #E8E8E8"
                    bg = "#E0F4F4" if is_selected else "#FFFFFF"

                    st.markdown(f'<div style="background:{bg};border:{border_style};border-radius:8px;padding:8px;text-align:center;">', unsafe_allow_html=True)

                    img_file = item.get("image_filename", "")
                    if img_file:
                        img_path = os.path.join(WARDROBE_IMAGES_DIR, img_file)
                        if os.path.exists(img_path):
                            st.image(img_path, use_container_width=True)
                        else:
                            st.markdown("👕", unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="font-size:28px;">👕</div>', unsafe_allow_html=True)

                    st.markdown(f'<div style="font-size:11px;font-weight:600;">{item["name"][:20]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="font-size:10px;color:#888;">{item.get("type","")}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    check_label = "✅ Selected" if is_selected else "Select"
                    if st.button(check_label, key=f"sel_{item['id']}", use_container_width=True):
                        if is_selected:
                            st.session_state.selected_outfit_items.remove(item["id"])
                        else:
                            st.session_state.selected_outfit_items.append(item["id"])
                        st.rerun()

        # Selected items preview
        if st.session_state.selected_outfit_items:
            st.markdown(f"**{len(st.session_state.selected_outfit_items)} items selected**")

            if st.button("💾 Save Outfit", use_container_width=True, key="save_manual_outfit"):
                if outfit_name:
                    create_outfit(
                        name=outfit_name,
                        item_ids=st.session_state.selected_outfit_items,
                        occasion=outfit_occasion,
                        season=outfit_season,
                        source="manual",
                    )
                    st.success(f"✅ Outfit **{outfit_name}** saved!")
                    st.session_state.show_create_outfit = False
                    st.session_state.selected_outfit_items = []
                    st.rerun()
                else:
                    st.error("Please enter an outfit name.")

    st.markdown("---")

# ---------------------------------------------------------------------------
# Outfit gallery
# ---------------------------------------------------------------------------
if not outfits:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">✨</div>
        <div class="empty-state-title">No outfits yet</div>
        <div class="empty-state-text">Ask the Style Assistant to create one, or build your own!</div>
    </div>
    """, unsafe_allow_html=True)

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("💬 Ask Style Assistant", use_container_width=True, key="empty_chat"):
            st.session_state.chat_history = []
            st.session_state.chat_tool_results = {}
            st.session_state.chat_context = "Build me a complete outfit from my wardrobe"
            st.switch_page("pages/3_Style_Assistant.py")
    with bc2:
        if st.button("➕ Create Manually", use_container_width=True, key="empty_create"):
            st.session_state.show_create_outfit = True
            st.rerun()
else:
    # Display outfit cards
    cols_per_row = 2
    for row_start in range(0, len(outfits), cols_per_row):
        row_outfits = outfits[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)

        for col, outfit in zip(cols, row_outfits):
            with col:
                st.markdown(f"""
                <div class="card" style="margin-bottom:16px;">
                    <div style="font-size:18px;font-weight:700;color:#1A1A1A;margin-bottom:8px;">
                        {outfit['name']}
                    </div>
                """, unsafe_allow_html=True)

                # Outfit board — show item images in a grid
                outfit_items = get_outfit_items(outfit, wardrobe_items)

                if outfit_items:
                    # Layout items in a flat-lay style grid
                    item_cols = st.columns(min(len(outfit_items), 4))
                    for ic, oi in zip(item_cols, outfit_items[:4]):
                        with ic:
                            img_shown = False
                            source = oi.get("_source", "wardrobe")

                            # Try wardrobe image first
                            img_file = oi.get("image_filename", "")
                            if img_file:
                                img_path = os.path.join(WARDROBE_IMAGES_DIR, img_file)
                                if os.path.exists(img_path):
                                    st.image(img_path, use_container_width=True)
                                    img_shown = True

                            # Try catalog image via Cloudinary
                            if not img_shown and source == "catalog":
                                oi_id = oi.get("id", "")
                                if oi_id:
                                    try:
                                        st.image(get_image_url(oi_id), use_container_width=True)
                                        img_shown = True
                                    except Exception:
                                        pass

                            # Also try image_path field (handles both URLs and local paths)
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
                else:
                    st.markdown('<div style="color:#888;font-size:13px;padding:20px;">Items not found in wardrobe</div>', unsafe_allow_html=True)

                # Tags
                tags_html = ""
                if outfit.get("occasion"):
                    tags_html += f'<span class="pill pill-teal">{outfit["occasion"]}</span>'
                if outfit.get("season"):
                    tags_html += f'<span class="pill pill-grey">{outfit["season"]}</span>'
                if outfit.get("source") == "assistant":
                    tags_html += f'<span class="pill pill-green">AI Created</span>'
                if outfit.get("weather_info"):
                    tags_html += f'<span class="pill pill-grey">🌤️ {outfit["weather_info"]}</span>'

                st.markdown(f'<div style="margin-top:8px;">{tags_html}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # Delete button
                if st.button("🗑️ Delete", key=f"del_outfit_{outfit['id']}", use_container_width=True):
                    delete_outfit(outfit["id"])
                    st.rerun()
