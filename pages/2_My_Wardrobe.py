"""
Page 2: My Wardrobe
-------------------
Upload and manage personal clothing items.
Features:
- Photo upload with AI background removal (rembg)
- Auto-tagging via Gemini Vision (structured JSON extraction)
- Editable attribute form
- Wardrobe grid with filters and actions
- Item detail view with matching and outfit building
"""

import streamlit as st
import os
import sys
import uuid
from PIL import Image
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Shared UI: page config + CSS + sidebar (must be first)
from services.shared_ui import setup_page, add_to_cart
setup_page("My Wardrobe — Vinted Outfit Match V2")

from services.wardrobe_manager import (
    load_wardrobe, add_item, delete_item, get_wardrobe_count, search_items
)
from services.image_processor import remove_background, save_wardrobe_image, auto_tag_image
from services.wishlist_manager import add_wishlist_item, is_item_wishlisted
from services.outfit_manager import create_outfit
from services.image_url import get_image_url

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
IMAGE_DIR = os.path.join(DATA_DIR, "images")
WARDROBE_IMAGES_DIR = os.path.join(DATA_DIR, "wardrobe_images")


@st.cache_resource(show_spinner="Loading matching engine...")
def load_matcher():
    from services.matching_engine import OutfitMatcher
    return OutfitMatcher()


def get_api_key():
    """Get Gemini API key from environment or Streamlit secrets."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass
    return key


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "show_upload" not in st.session_state:
    st.session_state.show_upload = False
if "auto_tags" not in st.session_state:
    st.session_state.auto_tags = None
if "processed_image" not in st.session_state:
    st.session_state.processed_image = None
if "uploaded_image_bytes" not in st.session_state:
    st.session_state.uploaded_image_bytes = None
if "selected_wardrobe_item_id" not in st.session_state:
    st.session_state.selected_wardrobe_item_id = None

# Show toast feedback
if "_cart_msg" in st.session_state:
    st.toast(st.session_state._cart_msg)
    del st.session_state._cart_msg

wardrobe_items = load_wardrobe()


# ---------------------------------------------------------------------------
# Callbacks for cart / wishlist (run at start of rerun — reliable in tabs)
# ---------------------------------------------------------------------------
def _handle_cart_add(item_dict):
    added = add_to_cart(item_dict)
    st.session_state._cart_msg = "Added to cart!" if added else "Already in cart."


def _handle_wishlist_add(item_dict):
    add_wishlist_item(item_dict)
    st.session_state._cart_msg = "Added to wishlist!"


# ===========================================================================
# WARDROBE ITEM DETAIL VIEW
# ===========================================================================
def show_wardrobe_item_detail(item_id):
    """Detail view for a wardrobe item with matching and outfit building."""
    st.components.v1.html("<script>window.parent.document.querySelector('section.main').scrollTo(0, 0);</script>", height=0)

    if st.button("← Back to wardrobe"):
        st.session_state.selected_wardrobe_item_id = None
        st.rerun()

    # Find the item
    item = None
    for wi in wardrobe_items:
        if wi["id"] == item_id:
            item = wi
            break

    if not item:
        st.error("Item not found in your wardrobe.")
        return

    # --- Item header ---
    left, right = st.columns([1, 2])
    with left:
        img_file = item.get("image_filename", "")
        if img_file:
            img_path = os.path.join(WARDROBE_IMAGES_DIR, img_file)
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            else:
                st.markdown('<div style="background:#f0f0f0;border-radius:8px;height:300px;display:flex;align-items:center;justify-content:center;font-size:60px;">👕</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background:#f0f0f0;border-radius:8px;height:300px;display:flex;align-items:center;justify-content:center;font-size:60px;">👕</div>', unsafe_allow_html=True)

    with right:
        st.markdown(f'<div style="font-size:20px;font-weight:700;margin-bottom:4px;">{item["name"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:16px;font-weight:500;color:#007782;margin-bottom:12px;">👕 In your wardrobe</div>', unsafe_allow_html=True)

        # Attribute pills
        attrs = [
            ("Type", item.get("type", "")),
            ("Color", item.get("color", "")),
            ("Material", item.get("material", "")),
            ("Pattern", item.get("pattern", "")),
            ("Formality", item.get("formality", "")),
            ("Gender", item.get("gender", "")),
        ]
        pills_html = '<div style="display:flex;flex-wrap:wrap;gap:6px;">'
        for label, value in attrs:
            if value and str(value).strip():
                pills_html += f'<span class="detail-tag">{label}: {value}</span>'
        seasons = item.get("season", [])
        if seasons:
            pills_html += f'<span class="detail-tag">Season: {", ".join(seasons)}</span>'
        occasions = item.get("occasion", [])
        if occasions:
            pills_html += f'<span class="detail-tag">Occasion: {", ".join(occasions)}</span>'
        pills_html += '</div>'
        st.markdown(pills_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Action buttons
        ac1, ac2 = st.columns(2)
        with ac1:
            if st.button("💬 Style with AI", use_container_width=True, key="detail_style"):
                st.session_state.chat_history = []
                st.session_state.chat_tool_results = {}
                st.session_state.chat_resolved_items = {}
                st.session_state.chat_seed_item = {
                    "id": item["id"],
                    "name": item.get("name", ""),
                    "type": item.get("type", ""),
                    "color": item.get("color", ""),
                    "image_filename": item.get("image_filename", ""),
                    "formality": item.get("formality", ""),
                    "season": item.get("season", []),
                    "_source": "wardrobe",
                }
                st.session_state.chat_context = (
                    f"I want to style my {item.get('color', '')} {item.get('type', '')} "
                    f"called \"{item.get('name', 'my item')}\". "
                    f"It's {item.get('material', '')} material, {item.get('formality', 'casual')} style, "
                    f"good for {', '.join(item.get('season', ['all seasons']))}. "
                    f"Should I style it with items from my wardrobe, or would you like to suggest items from the catalog to buy? "
                    f"Please ask me which I prefer before making recommendations."
                )
                st.switch_page("pages/3_Style_Assistant.py")
        with ac2:
            if st.button("🗑️ Delete Item", use_container_width=True, key="detail_delete"):
                delete_item(item["id"])
                st.session_state.selected_wardrobe_item_id = None
                st.rerun()

    st.markdown("---")

    # --- Matching and Outfit Building ---
    matcher = load_matcher()

    tab1, tab2 = st.tabs(["✨ Match with", "👗 Build complete outfit"])

    with tab1:
        st.markdown("**Items that match well with this**")

        match_source = st.radio(
            "Match from:",
            ["From catalog", "From my wardrobe"],
            horizontal=True,
            key="match_source",
        )

        if match_source == "From catalog":
            with st.spinner("Finding catalog matches..."):
                matches = matcher.get_matches_for_wardrobe_item(item, num_matches=6)

            if not matches:
                st.info("No catalog matches found for this item type.")
            else:
                cols = st.columns(3)
                for i, match in enumerate(matches):
                    with cols[i % 3]:
                        st.markdown('<div class="item-card">', unsafe_allow_html=True)
                        st.image(get_image_url(match['id']), use_container_width=True)
                        st.markdown(f"""
                        <div class="item-card-body">
                            <div class="item-card-price">€{match['price']}</div>
                            <div class="item-card-name">{match['name'][:45]}</div>
                            <div style="font-size:11px;color:#09B1BA;font-weight:500;margin-top:4px;">✦ {match['explanation']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                        _m_item = {
                            "id": str(match["id"]),
                            "name": match["name"],
                            "type": match.get("type", match.get("articleType", "")),
                            "color": match.get("color", match.get("colour", "")),
                            "price": float(match["price"]),
                            "condition": match.get("condition", "Good"),
                            "image_path": get_image_url(match['id']),
                            "_source": "catalog",
                        }
                        mc1, mc2 = st.columns(2)
                        with mc1:
                            st.button("🛒", key=f"wm_cart_{match['id']}_{i}",
                                      use_container_width=True, help="Add to Cart",
                                      on_click=_handle_cart_add, args=(_m_item,))
                        with mc2:
                            m_wl = is_item_wishlisted(str(match["id"]))
                            m_icon = "❤️" if m_wl else "🤍"
                            st.button(m_icon, key=f"wm_wl_{match['id']}_{i}",
                                      use_container_width=True, help="Wishlist",
                                      disabled=m_wl,
                                      on_click=_handle_wishlist_add, args=(_m_item,))
        else:
            # Wardrobe-to-wardrobe matching
            with st.spinner("Finding wardrobe matches..."):
                matches = matcher.get_wardrobe_matches(item, wardrobe_items, num_matches=6)

            if not matches:
                st.info("No matching items found in your wardrobe. Try adding more items!")
            else:
                cols = st.columns(3)
                for i, match in enumerate(matches):
                    with cols[i % 3]:
                        m_img = match.get("image_filename", "")
                        st.markdown('<div class="item-card">', unsafe_allow_html=True)
                        if m_img:
                            m_img_path = os.path.join(WARDROBE_IMAGES_DIR, m_img)
                            if os.path.exists(m_img_path):
                                st.image(m_img_path, use_container_width=True)
                            else:
                                st.markdown('<div style="background:#f0f0f0;height:140px;display:flex;align-items:center;justify-content:center;font-size:36px;">👕</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div style="background:#f0f0f0;height:140px;display:flex;align-items:center;justify-content:center;font-size:36px;">👕</div>', unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="item-card-body">
                            <div style="font-weight:600;font-size:14px;">{match['name'][:45]}</div>
                            <div><span class="pill pill-teal">{match.get('type', '')}</span></div>
                            <div style="font-size:11px;color:#09B1BA;font-weight:500;margin-top:4px;">✦ {match.get('explanation', 'Complementary style')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown("**Complete outfit built around this item**")

        outfit_source = st.radio(
            "Build from:",
            ["From catalog", "From my wardrobe"],
            horizontal=True,
            key="outfit_source",
        )

        if outfit_source == "From catalog":
            with st.spinner("Building outfit from catalog..."):
                bundle = matcher.get_outfit_bundle_for_wardrobe_item(item, num_items=4)

            if not bundle or len(bundle) < 2:
                st.info("Could not build a complete outfit with catalog items.")
            else:
                catalog_items = [b for b in bundle if not b.get("is_seed")]
                total_price = sum(b["price"] for b in catalog_items)

                st.markdown(f"""
                <div style="background:#E0F4F4;border:1px solid #B2DFDB;border-radius:8px;padding:14px 20px;
                            margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;">
                    <div>
                        <div style="font-size:13px;color:#555;">Catalog items total</div>
                        <div style="font-size:22px;font-weight:700;color:#007782;">€{total_price:.0f}</div>
                    </div>
                    <div style="font-size:13px;color:#007782;font-weight:500;">
                        {len(bundle)} pieces including your item
                    </div>
                </div>
                """, unsafe_allow_html=True)

                cols = st.columns(len(bundle))
                for pidx, (col, piece) in enumerate(zip(cols, bundle)):
                    with col:
                        is_seed = piece.get("is_seed", False)
                        border = "2px solid #09B1BA" if is_seed else "1px solid #E8E8E8"

                        st.markdown(f'<div style="background:#fff;border-radius:8px;border:{border};overflow:hidden;">', unsafe_allow_html=True)

                        if is_seed:
                            img_f = piece.get("image_filename", "")
                            if img_f:
                                ip = os.path.join(WARDROBE_IMAGES_DIR, img_f)
                                if os.path.exists(ip):
                                    st.image(ip, use_container_width=True)
                                else:
                                    st.markdown('<div style="background:#f0f0f0;height:120px;display:flex;align-items:center;justify-content:center;font-size:30px;">👕</div>', unsafe_allow_html=True)
                            else:
                                st.markdown('<div style="background:#f0f0f0;height:120px;display:flex;align-items:center;justify-content:center;font-size:30px;">👕</div>', unsafe_allow_html=True)
                        else:
                            st.image(get_image_url(piece['id']), use_container_width=True)

                        role_label = piece.get("role", "item").capitalize()
                        seed_label = " · Yours" if is_seed else ""
                        price_str = f"€{piece['price']:.0f}" if piece.get("price") else "Owned"
                        st.markdown(f"""
                        <div style="padding:8px 10px 12px;">
                            <div style="font-size:10px;font-weight:600;color:#09B1BA;text-transform:uppercase;">{role_label}{seed_label}</div>
                            <div style="font-size:12px;color:#555;margin-top:2px;">{piece.get('name', '')[:35]}</div>
                            <div style="font-size:15px;font-weight:700;margin-top:4px;">{price_str}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                        # Individual cart + wishlist for catalog items
                        if not is_seed:
                            _p_item = {
                                "id": str(piece["id"]),
                                "name": piece.get("name", ""),
                                "type": piece.get("articleType", ""),
                                "color": piece.get("colour", piece.get("color", "")),
                                "price": float(piece["price"]),
                                "condition": piece.get("condition", "Good"),
                                "image_path": get_image_url(piece['id']),
                                "_source": "catalog",
                            }
                            pc1, pc2 = st.columns(2)
                            with pc1:
                                st.button("🛒", key=f"wo_cart_{piece['id']}_{pidx}",
                                          use_container_width=True, help="Add to Cart",
                                          on_click=_handle_cart_add, args=(_p_item,))
                            with pc2:
                                p_wl = is_item_wishlisted(str(piece["id"]))
                                p_icon = "❤️" if p_wl else "🤍"
                                st.button(p_icon, key=f"wo_wl_{piece['id']}_{pidx}",
                                          use_container_width=True, help="Wishlist",
                                          disabled=p_wl,
                                          on_click=_handle_wishlist_add, args=(_p_item,))

                # Save outfit button
                st.markdown("<br>", unsafe_allow_html=True)
                sc1, sc2 = st.columns([3, 1])
                with sc1:
                    outfit_name = st.text_input("Outfit name", placeholder="e.g. Weekend Casual Look", key="wo_outfit_name")
                with sc2:
                    if st.button("💾 Save Outfit", use_container_width=True, key="wo_save_outfit"):
                        if outfit_name and outfit_name.strip():
                            item_ids = [str(b.get("id", "")) for b in bundle if b.get("id")]
                            rec_items = []
                            for b in bundle:
                                rec = {
                                    "id": str(b.get("id", "")),
                                    "name": b.get("name", ""),
                                    "type": b.get("articleType", b.get("type", "")),
                                    "color": b.get("colour", b.get("color", "")),
                                    "_source": b.get("_source", "catalog"),
                                }
                                if b.get("price"):
                                    rec["price"] = b["price"]
                                if b.get("image_filename"):
                                    rec["image_filename"] = b["image_filename"]
                                if b.get("image_path"):
                                    rec["image_path"] = b["image_path"]
                                if b.get("condition"):
                                    rec["condition"] = b["condition"]
                                rec_items.append(rec)
                            create_outfit(
                                name=outfit_name.strip(),
                                item_ids=item_ids,
                                occasion="Casual",
                                season="All",
                                source="wardrobe_builder",
                                recommended_items=rec_items,
                            )
                            st.session_state._cart_msg = f"Outfit '{outfit_name.strip()}' saved!"
                            st.rerun()
                        else:
                            st.warning("Enter an outfit name first.")

        else:
            # Wardrobe-only outfit building
            st.markdown('<div style="font-size:13px;color:#888;margin-bottom:16px;">Assembling an outfit from your existing wardrobe items</div>', unsafe_allow_html=True)

            with st.spinner("Building outfit from wardrobe..."):
                w_matches = matcher.get_wardrobe_matches(item, wardrobe_items, num_matches=4)

            if not w_matches:
                st.info("Not enough wardrobe items to build a complete outfit. Try adding more!")
            else:
                from services.matching_engine import ARTICLE_ROLES
                type_mapping = {
                    "T-Shirt": "Tshirts", "Shirt": "Shirts", "Blouse": "Blouses",
                    "Sweater": "Sweaters", "Hoodie": "Sweatshirts", "Jacket": "Jackets",
                    "Blazer": "Blazers", "Coat": "Jackets", "Dress": "Dresses",
                    "Skirt": "Skirts", "Jeans": "Jeans", "Trousers": "Trousers",
                    "Shorts": "Shorts", "Sneakers": "Casual Shoes", "Boots": "Boots",
                    "Sandals": "Sandals", "Heels": "Heels", "Flats": "Flats",
                }
                seed_type = type_mapping.get(item.get("type", ""), item.get("type", ""))
                seed_role = ARTICLE_ROLES.get(seed_type, "other")

                bundle = [{
                    "id": item["id"],
                    "name": item.get("name", ""),
                    "type": item.get("type", ""),
                    "role": seed_role,
                    "color": item.get("color", ""),
                    "image_filename": item.get("image_filename", ""),
                    "is_seed": True,
                    "_source": "wardrobe",
                }]

                filled_roles = {seed_role}
                for m in w_matches:
                    m_type = type_mapping.get(m.get("type", ""), m.get("type", ""))
                    m_role = ARTICLE_ROLES.get(m_type, "other")
                    if m_role not in filled_roles:
                        m["role"] = m_role
                        m["is_seed"] = False
                        bundle.append(m)
                        filled_roles.add(m_role)
                    if len(bundle) >= 4:
                        break

                cols = st.columns(len(bundle))
                for pidx, (col, piece) in enumerate(zip(cols, bundle)):
                    with col:
                        is_seed = piece.get("is_seed", False)
                        border = "2px solid #09B1BA" if is_seed else "1px solid #E8E8E8"

                        st.markdown(f'<div style="background:#fff;border-radius:8px;border:{border};overflow:hidden;">', unsafe_allow_html=True)
                        p_img = piece.get("image_filename", "")
                        if p_img:
                            ip = os.path.join(WARDROBE_IMAGES_DIR, p_img)
                            if os.path.exists(ip):
                                st.image(ip, use_container_width=True)
                            else:
                                st.markdown('<div style="background:#f0f0f0;height:120px;display:flex;align-items:center;justify-content:center;font-size:30px;">👕</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div style="background:#f0f0f0;height:120px;display:flex;align-items:center;justify-content:center;font-size:30px;">👕</div>', unsafe_allow_html=True)

                        role_label = piece.get("role", "item").capitalize()
                        seed_label = " · Yours" if is_seed else ""
                        st.markdown(f"""
                        <div style="padding:8px 10px 12px;">
                            <div style="font-size:10px;font-weight:600;color:#09B1BA;text-transform:uppercase;">{role_label}{seed_label}</div>
                            <div style="font-size:12px;color:#555;margin-top:2px;">{piece.get('name', '')[:35]}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                # Save wardrobe outfit
                st.markdown("<br>", unsafe_allow_html=True)
                sc1, sc2 = st.columns([3, 1])
                with sc1:
                    w_outfit_name = st.text_input("Outfit name", placeholder="e.g. Monday Work Look", key="ww_outfit_name")
                with sc2:
                    if st.button("💾 Save Outfit", use_container_width=True, key="ww_save_outfit"):
                        if w_outfit_name and w_outfit_name.strip():
                            item_ids = [str(b.get("id", "")) for b in bundle if b.get("id")]
                            rec_items = []
                            for b in bundle:
                                rec = {
                                    "id": str(b.get("id", "")),
                                    "name": b.get("name", ""),
                                    "type": b.get("type", ""),
                                    "color": b.get("color", ""),
                                    "_source": "wardrobe",
                                }
                                if b.get("image_filename"):
                                    rec["image_filename"] = b["image_filename"]
                                rec_items.append(rec)
                            create_outfit(
                                name=w_outfit_name.strip(),
                                item_ids=item_ids,
                                occasion="Casual",
                                season="All",
                                source="wardrobe_builder",
                                recommended_items=rec_items,
                            )
                            st.session_state._cart_msg = f"Outfit '{w_outfit_name.strip()}' saved!"
                            st.rerun()
                        else:
                            st.warning("Enter an outfit name first.")


# ===========================================================================
# WARDROBE GRID VIEW
# ===========================================================================
def show_wardrobe_grid():
    st.markdown('<div class="section-title">My Wardrobe</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Upload photos — AI removes backgrounds and auto-tags your clothes</div>', unsafe_allow_html=True)

    # Top bar: item count + filters + add button
    top_col1, top_col2, top_col3, top_col4, top_col5 = st.columns([2, 1.5, 1.5, 1.5, 1.5])

    with top_col1:
        st.markdown(f"**{len(wardrobe_items)}** items in your wardrobe")
    with top_col2:
        filter_type = st.selectbox("Type", ["All"] + sorted(set(i.get("type", "") for i in wardrobe_items if i.get("type"))), key="w_filter_type", label_visibility="collapsed")
    with top_col3:
        filter_color = st.selectbox("Color", ["All"] + sorted(set(i.get("color", "") for i in wardrobe_items if i.get("color"))), key="w_filter_color", label_visibility="collapsed")
    with top_col4:
        all_seasons = set()
        for i in wardrobe_items:
            for s in i.get("season", []):
                all_seasons.add(s)
        filter_season = st.selectbox("Season", ["All"] + sorted(all_seasons), key="w_filter_season", label_visibility="collapsed")
    with top_col5:
        if st.button("➕ Add Item", use_container_width=True):
            st.session_state.show_upload = not st.session_state.show_upload
            st.session_state.auto_tags = None
            st.session_state.processed_image = None
            st.rerun()

    # ---------------------------------------------------------------------------
    # Upload flow
    # ---------------------------------------------------------------------------
    if st.session_state.show_upload:
        st.markdown("---")
        st.markdown("### Add a new item")

        upload_tab, manual_tab = st.tabs(["📸 Upload Photo", "✏️ Manual Entry"])

        with upload_tab:
            uploaded_file = st.file_uploader(
                "Drag and drop a clothing photo",
                type=["jpg", "jpeg", "png", "webp"],
                key="wardrobe_upload",
            )

            if uploaded_file is not None and st.session_state.uploaded_image_bytes != uploaded_file.getvalue():
                raw_bytes = uploaded_file.getvalue()
                st.session_state.uploaded_image_bytes = raw_bytes

                with st.spinner("🔄 Processing your item — removing background..."):
                    cleaned = remove_background(raw_bytes)

                if cleaned:
                    filename = f"{uuid.uuid4().hex[:8]}.png"
                    save_wardrobe_image(cleaned, filename)
                    st.session_state.processed_image = filename
                    st.session_state.processed_image_bytes = cleaned
                else:
                    filename = f"{uuid.uuid4().hex[:8]}.png"
                    save_wardrobe_image(raw_bytes, filename)
                    st.session_state.processed_image = filename
                    st.session_state.processed_image_bytes = raw_bytes
                    st.warning("Background removal unavailable — using original image.")

                api_key = get_api_key()
                if api_key:
                    with st.spinner("🤖 AI is analyzing your clothing item..."):
                        tags = auto_tag_image(st.session_state.processed_image_bytes, api_key)
                    if tags:
                        st.session_state.auto_tags = tags
                    else:
                        st.session_state.auto_tags = None
                        st.warning("AI tagging unavailable — please fill in the details manually.")
                else:
                    st.session_state.auto_tags = None
                    st.info("Set your Gemini API key in `.env` for automatic AI tagging.")

                st.rerun()

            if st.session_state.processed_image:
                img_col, form_col = st.columns([1, 2])
                with img_col:
                    img_path = os.path.join(WARDROBE_IMAGES_DIR, st.session_state.processed_image)
                    if os.path.exists(img_path):
                        st.image(img_path, caption="Background removed", width=250)

                with form_col:
                    tags = st.session_state.auto_tags or {}

                    type_options = [
                        "T-Shirt", "Shirt", "Blouse", "Sweater", "Hoodie", "Jacket",
                        "Blazer", "Coat", "Dress", "Skirt", "Jeans", "Trousers",
                        "Shorts", "Sneakers", "Boots", "Sandals", "Heels", "Flats",
                        "Bag", "Watch", "Sunglasses", "Scarf", "Hat", "Belt", "Other"
                    ]
                    default_type = tags.get("type", "T-Shirt")
                    type_idx = type_options.index(default_type) if default_type in type_options else 0

                    item_name = st.text_input("Item Name", value=f"My {tags.get('type', 'Item')}", key="add_name")
                    item_type = st.selectbox("Type", type_options, index=type_idx, key="add_type")

                    c1, c2 = st.columns(2)
                    with c1:
                        color_options = [
                            "Black", "White", "Navy Blue", "Blue", "Grey", "Brown", "Beige",
                            "Red", "Green", "Pink", "Yellow", "Purple", "Orange", "Teal",
                            "Cream", "Olive", "Burgundy", "Multi"
                        ]
                        default_color = tags.get("color", "Black")
                        color_idx = color_options.index(default_color) if default_color in color_options else 0
                        item_color = st.selectbox("Color", color_options, index=color_idx, key="add_color")
                    with c2:
                        pattern_options = ["Solid", "Striped", "Plaid", "Floral", "Graphic", "Abstract", "Polka Dot", "Animal Print", "Color Block"]
                        default_pattern = tags.get("pattern", "Solid")
                        pattern_idx = pattern_options.index(default_pattern) if default_pattern in pattern_options else 0
                        item_pattern = st.selectbox("Pattern", pattern_options, index=pattern_idx, key="add_pattern")

                    c3, c4 = st.columns(2)
                    with c3:
                        material_options = ["Cotton", "Denim", "Leather", "Polyester", "Wool", "Silk", "Linen", "Suede", "Canvas", "Knit", "Other"]
                        default_material = tags.get("material", "Cotton")
                        material_idx = material_options.index(default_material) if default_material in material_options else 0
                        item_material = st.selectbox("Material", material_options, index=material_idx, key="add_material")
                    with c4:
                        formality_options = ["Casual", "Smart Casual", "Business", "Formal"]
                        default_formality = tags.get("formality", "Casual")
                        formality_idx = formality_options.index(default_formality) if default_formality in formality_options else 0
                        item_formality = st.selectbox("Formality", formality_options, index=formality_idx, key="add_formality")

                    season_options = ["Spring", "Summer", "Fall", "Winter"]
                    default_seasons = tags.get("season", ["Spring", "Summer", "Fall", "Winter"])
                    if isinstance(default_seasons, str):
                        default_seasons = [default_seasons]
                    item_seasons = st.multiselect("Seasons", season_options, default=[s for s in default_seasons if s in season_options], key="add_seasons")

                    occasion_options = ["Casual", "Formal", "Smart Casual", "Business", "Party", "Sports", "Travel"]
                    default_occasions = tags.get("occasion", ["Casual"])
                    if isinstance(default_occasions, str):
                        default_occasions = [default_occasions]
                    item_occasions = st.multiselect("Occasions", occasion_options, default=[o for o in default_occasions if o in occasion_options], key="add_occasions")

                    gender_options = ["Men", "Women", "Unisex"]
                    default_gender = tags.get("gender", "Unisex")
                    gender_idx = gender_options.index(default_gender) if default_gender in gender_options else 2
                    item_gender = st.selectbox("Gender", gender_options, index=gender_idx, key="add_gender")

                    if st.button("💾 Save to Wardrobe", use_container_width=True, key="save_upload"):
                        add_item(
                            name=item_name, item_type=item_type, color=item_color,
                            pattern=item_pattern, material=item_material,
                            season=item_seasons, occasion=item_occasions,
                            formality=item_formality, gender=item_gender,
                            image_filename=st.session_state.processed_image,
                        )
                        st.success(f"✅ **{item_name}** added to your wardrobe!")
                        st.session_state.show_upload = False
                        st.session_state.auto_tags = None
                        st.session_state.processed_image = None
                        st.session_state.uploaded_image_bytes = None
                        st.rerun()

        with manual_tab:
            st.markdown("Add an item without a photo:")
            with st.form("manual_add"):
                m_name = st.text_input("Item Name", placeholder="e.g. My Navy Blazer")
                mc1, mc2 = st.columns(2)
                with mc1:
                    m_type = st.selectbox("Type", [
                        "T-Shirt", "Shirt", "Blouse", "Sweater", "Hoodie", "Jacket",
                        "Blazer", "Coat", "Dress", "Skirt", "Jeans", "Trousers",
                        "Shorts", "Sneakers", "Boots", "Sandals", "Heels", "Flats",
                        "Bag", "Watch", "Sunglasses", "Scarf", "Hat", "Belt", "Other"
                    ], key="m_type")
                    m_color = st.selectbox("Color", [
                        "Black", "White", "Navy Blue", "Blue", "Grey", "Brown", "Beige",
                        "Red", "Green", "Pink", "Yellow", "Purple", "Orange", "Teal",
                        "Cream", "Olive", "Burgundy", "Multi"
                    ], key="m_color")
                with mc2:
                    m_pattern = st.selectbox("Pattern", ["Solid", "Striped", "Plaid", "Floral", "Graphic", "Abstract"], key="m_pattern")
                    m_material = st.selectbox("Material", ["Cotton", "Denim", "Leather", "Polyester", "Wool", "Silk", "Linen", "Other"], key="m_material")

                m_seasons = st.multiselect("Seasons", ["Spring", "Summer", "Fall", "Winter"], default=["Spring", "Summer", "Fall", "Winter"], key="m_seasons")
                m_occasions = st.multiselect("Occasions", ["Casual", "Formal", "Smart Casual", "Business", "Party", "Sports", "Travel"], default=["Casual"], key="m_occasions")
                m_formality = st.selectbox("Formality", ["Casual", "Smart Casual", "Business", "Formal"], key="m_formality")
                m_gender = st.selectbox("Gender", ["Men", "Women", "Unisex"], key="m_gender")

                if st.form_submit_button("💾 Save to Wardrobe", use_container_width=True):
                    if m_name:
                        add_item(
                            name=m_name, item_type=m_type, color=m_color,
                            pattern=m_pattern, material=m_material,
                            season=m_seasons, occasion=m_occasions,
                            formality=m_formality, gender=m_gender,
                        )
                        st.success(f"✅ **{m_name}** added to your wardrobe!")
                        st.session_state.show_upload = False
                        st.rerun()
                    else:
                        st.error("Please enter an item name.")

    # ---------------------------------------------------------------------------
    # Wardrobe grid
    # ---------------------------------------------------------------------------
    st.markdown("---")

    # Apply filters
    filtered_items = wardrobe_items
    if filter_type != "All":
        filtered_items = [i for i in filtered_items if i.get("type") == filter_type]
    if filter_color != "All":
        filtered_items = [i for i in filtered_items if i.get("color") == filter_color]
    if filter_season != "All":
        filtered_items = [i for i in filtered_items if filter_season in i.get("season", [])]

    if not filtered_items and not wardrobe_items:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">👕</div>
            <div class="empty-state-title">Your wardrobe is empty</div>
            <div class="empty-state-text">Upload photos of your clothes to get started.<br>AI will remove backgrounds and auto-tag each item.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("➕ Add Your First Item", key="empty_add"):
            st.session_state.show_upload = True
            st.rerun()
    elif not filtered_items:
        st.info("No items match your current filters.")
    else:
        cols_per_row = 4
        for row_start in range(0, len(filtered_items), cols_per_row):
            row_items = filtered_items[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, item in zip(cols, row_items):
                with col:
                    # Clickable image → opens detail view
                    img_file = item.get("image_filename", "")
                    img_path = os.path.join(WARDROBE_IMAGES_DIR, img_file) if img_file else ""
                    has_img = img_file and os.path.exists(img_path)

                    st.markdown('<div class="item-card">', unsafe_allow_html=True)
                    if has_img:
                        st.image(img_path, use_container_width=True)
                    else:
                        st.markdown('<div style="background:#f0f0f0;height:150px;display:flex;align-items:center;justify-content:center;font-size:36px;border-radius:6px;">👕</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="item-card-body">
                        <div style="font-weight:600; font-size:14px;">{item['name'][:30]}</div>
                        <div><span class="pill pill-teal">{item.get('type', 'Item')}</span></div>
                        <div style="font-size:12px; color:#888; margin-top:4px;">
                            {item.get('color', '')} · {item.get('formality', '')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    # Tapping the card image opens detail (full-width invisible button)
                    if st.button("View details", key=f"view_{item['id']}", use_container_width=True, type="secondary"):
                        st.session_state.selected_wardrobe_item_id = item["id"]
                        st.rerun()

                    # Action buttons — only Style + Delete
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button("💬 Style", key=f"style_{item['id']}", use_container_width=True):
                            st.session_state.chat_history = []
                            st.session_state.chat_tool_results = {}
                            st.session_state.chat_resolved_items = {}
                            st.session_state.chat_seed_item = {
                                "id": item["id"],
                                "name": item.get("name", ""),
                                "type": item.get("type", ""),
                                "color": item.get("color", ""),
                                "image_filename": item.get("image_filename", ""),
                                "formality": item.get("formality", ""),
                                "season": item.get("season", []),
                                "_source": "wardrobe",
                            }
                            st.session_state.chat_context = (
                                f"I want to style my {item.get('color', '')} {item.get('type', '')} "
                                f"called \"{item.get('name', 'my item')}\". "
                                f"It's {item.get('material', '')} material, {item.get('formality', 'casual')} style, "
                                f"good for {', '.join(item.get('season', ['all seasons']))}. "
                                f"Should I style it with items from my wardrobe, or would you like to suggest items from the catalog to buy? "
                                f"Please ask me which I prefer before making recommendations."
                            )
                            st.switch_page("pages/3_Style_Assistant.py")
                    with bc2:
                        if st.button("🗑️", key=f"del_{item['id']}", use_container_width=True):
                            delete_item(item["id"])
                            st.rerun()


# ===========================================================================
# ROUTING
# ===========================================================================
if st.session_state.selected_wardrobe_item_id is not None:
    show_wardrobe_item_detail(st.session_state.selected_wardrobe_item_id)
else:
    show_wardrobe_grid()
