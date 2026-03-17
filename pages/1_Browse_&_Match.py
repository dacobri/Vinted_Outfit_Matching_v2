"""
Page 1: Browse & Match
----------------------
Browse the Vinted product catalog and find matching items.
Upgraded from A1 with cleaner UI, item detail view with tabs,
pagination, attribute pills, cart, and contextual "Ask Style Assistant".
"""

import streamlit as st
import pandas as pd
from PIL import Image
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Shared UI: page config + CSS + sidebar (must be first)
from services.shared_ui import setup_page, add_to_cart
setup_page("Browse & Match — Vinted Outfit Match V2")

from services.matching_engine import OutfitMatcher
from services.wishlist_manager import add_wishlist_item, is_item_wishlisted

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
IMAGE_DIR = os.path.join(DATA_DIR, "images")

ITEMS_PER_PAGE = 25


# ---------------------------------------------------------------------------
# Callbacks for cart / wishlist (run at start of rerun — reliable in tabs)
# ---------------------------------------------------------------------------
def _handle_cart_add(item_dict):
    added = add_to_cart(item_dict)
    st.session_state._cart_msg = "Added to cart!" if added else "Already in your cart."


def _handle_wishlist_add(item_dict):
    add_wishlist_item(item_dict)
    st.session_state._cart_msg = "Added to wishlist!"


def _handle_bundle_cart(bundle_list):
    added_count = sum(1 for p in bundle_list if add_to_cart(p))
    st.session_state._cart_msg = (
        f"Added {added_count} item(s) to cart!" if added_count > 0
        else "All items already in your cart."
    )


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading matching engine...")
def load_matcher():
    return OutfitMatcher()


@st.cache_data(show_spinner=False)
def load_catalog():
    df = pd.read_csv(os.path.join(DATA_DIR, "vinted_catalog.csv"), on_bad_lines="skip")
    df["usage"] = df["usage"].fillna("Casual")
    df["season"] = df["season"].fillna("Fall")
    df["baseColour"] = df["baseColour"].fillna("Multi")
    df = df[df["masterCategory"].isin(["Apparel", "Accessories", "Footwear"])].copy()
    return df.reset_index(drop=True)


def get_image(item_id):
    path = os.path.join(IMAGE_DIR, f"{int(item_id)}.jpg")
    if os.path.exists(path):
        try:
            return Image.open(path)
        except Exception:
            return None
    return None


def condition_badge(cond):
    mapping = {
        "New": ("badge-new", "New"),
        "Like new": ("badge-likenew", "Like new"),
        "Good": ("badge-good", "Good"),
        "Fair": ("badge-fair", "Fair"),
    }
    cls, label = mapping.get(cond, ("badge-good", cond))
    return f'<span class="badge {cls}">{label}</span>'


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "selected_item_id" not in st.session_state:
    st.session_state.selected_item_id = None
if "browse_page" not in st.session_state:
    st.session_state.browse_page = 0

matcher = load_matcher()
df = load_catalog()

# Show cart feedback from previous action (persists across rerun)
if "_cart_msg" in st.session_state:
    st.toast(st.session_state._cart_msg)
    del st.session_state._cart_msg


# ---------------------------------------------------------------------------
# Browse view
# ---------------------------------------------------------------------------
def show_browse():
    st.markdown('<div class="section-title">Browse Items</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Click any item to see outfit recommendations</div>', unsafe_allow_html=True)

    # Filter bar
    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns([2.5, 1.2, 1.2, 1.2, 1.2])
    with c1:
        search = st.text_input("Search", placeholder="e.g. blue jeans, floral dress...", label_visibility="collapsed")
    with c2:
        gender_opts = ["All genders"] + sorted(df["gender"].dropna().unique().tolist())
        gender_f = st.selectbox("Gender", gender_opts, label_visibility="collapsed")
    with c3:
        cat_opts = ["All categories"] + sorted(df["articleType"].dropna().unique().tolist())
        cat_f = st.selectbox("Category", cat_opts, label_visibility="collapsed")
    with c4:
        usage_opts = ["All occasions"] + sorted(df["usage"].dropna().unique().tolist())
        usage_f = st.selectbox("Occasion", usage_opts, label_visibility="collapsed")
    with c5:
        season_opts = ["All seasons"] + sorted(df["season"].dropna().unique().tolist())
        season_f = st.selectbox("Season", season_opts, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # Apply filters
    filtered = df.copy()
    if search:
        filtered = filtered[filtered["productDisplayName"].str.contains(search, case=False, na=False)]
    if gender_f != "All genders":
        filtered = filtered[filtered["gender"] == gender_f]
    if cat_f != "All categories":
        filtered = filtered[filtered["articleType"] == cat_f]
    if usage_f != "All occasions":
        filtered = filtered[filtered["usage"] == usage_f]
    if season_f != "All seasons":
        filtered = filtered[filtered["season"] == season_f]

    total = len(filtered)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    # Clamp page
    if st.session_state.browse_page >= total_pages:
        st.session_state.browse_page = total_pages - 1
    if st.session_state.browse_page < 0:
        st.session_state.browse_page = 0

    current_page = st.session_state.browse_page

    st.markdown(f'<div style="font-size:13px;color:#888;margin-bottom:16px;">{total:,} items found · Page {current_page + 1} of {total_pages}</div>', unsafe_allow_html=True)

    if total == 0:
        st.info("No items match your filters. Try broadening your search.")
        return

    # Slice for current page
    start = current_page * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, total)
    page_df = filtered.iloc[start:end]

    cols_per_row = 5
    rows = [page_df.iloc[i:i + cols_per_row] for i in range(0, len(page_df), cols_per_row)]

    for row_df in rows:
        cols = st.columns(cols_per_row)
        for col, (_, item) in zip(cols, row_df.iterrows()):
            with col:
                st.markdown('<div class="item-card">', unsafe_allow_html=True)
                img = get_image(item["id"])
                if img:
                    st.image(img, use_container_width=True)
                else:
                    st.markdown('<div style="background:#f0f0f0;height:160px;display:flex;align-items:center;justify-content:center;font-size:30px;">👕</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="item-card-body">
                    <div class="item-card-price">€{item['price']}</div>
                    <div class="item-card-name">{item['productDisplayName'][:45]}</div>
                    {condition_badge(item['condition'])}
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                if st.button("View", key=f"item_{item['id']}", use_container_width=True):
                    st.session_state.selected_item_id = item["id"]
                    st.rerun()

    # Pagination controls
    st.markdown("<br>", unsafe_allow_html=True)
    pc1, pc2, pc3, pc4, pc5 = st.columns([1, 1, 2, 1, 1])
    with pc1:
        if st.button("⏮ First", disabled=(current_page == 0), use_container_width=True, key="pg_first"):
            st.session_state.browse_page = 0
            st.rerun()
    with pc2:
        if st.button("◀ Prev", disabled=(current_page == 0), use_container_width=True, key="pg_prev"):
            st.session_state.browse_page = current_page - 1
            st.rerun()
    with pc3:
        st.markdown(f'<div style="text-align:center;padding:8px;font-size:14px;font-weight:600;color:#007782;">Page {current_page + 1} / {total_pages}</div>', unsafe_allow_html=True)
    with pc4:
        if st.button("Next ▶", disabled=(current_page >= total_pages - 1), use_container_width=True, key="pg_next"):
            st.session_state.browse_page = current_page + 1
            st.rerun()
    with pc5:
        if st.button("Last ⏭", disabled=(current_page >= total_pages - 1), use_container_width=True, key="pg_last"):
            st.session_state.browse_page = total_pages - 1
            st.rerun()


# ---------------------------------------------------------------------------
# Item detail view
# ---------------------------------------------------------------------------
def show_item_detail(item_id):
    st.components.v1.html("<script>window.parent.document.querySelector('section.main').scrollTo(0, 0);</script>", height=0)

    if st.button("← Back to browse"):
        st.session_state.selected_item_id = None
        st.rerun()

    item_row = df[df["id"] == item_id]
    if item_row.empty:
        st.error("Item not found.")
        return
    item = item_row.iloc[0]

    left, right = st.columns([1, 2])
    with left:
        img = get_image(item_id)
        if img:
            st.image(img, use_container_width=True)
        else:
            st.markdown('<div style="background:#f0f0f0;border-radius:8px;height:300px;display:flex;align-items:center;justify-content:center;font-size:60px;">👕</div>', unsafe_allow_html=True)

    with right:
        st.markdown(f'<div style="font-size:20px;font-weight:700;margin-bottom:4px;">{item["productDisplayName"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:28px;font-weight:700;color:#007782;">€{item["price"]}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Attribute pills with labels
        attrs = [
            ("Category", item.get("articleType", "")),
            ("Gender", item.get("gender", "")),
            ("Color", item.get("baseColour", "")),
            ("Occasion", item.get("usage", "")),
            ("Season", item.get("season", "")),
            ("Condition", item.get("condition", "")),
        ]
        pills_html = '<div style="display:flex;flex-wrap:wrap;gap:6px;">'
        for label, value in attrs:
            if pd.notna(value) and str(value).strip():
                pills_html += f'<span class="detail-tag">{label}: {value}</span>'
        pills_html += '</div>'
        st.markdown(pills_html, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:#F5F5F5;border-radius:8px;padding:10px 14px;margin-top:16px;font-size:13px;color:#555;">
            👤 <span style="font-weight:600;color:#1A1A1A;">{item['seller']}</span> · Seller on Vinted
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Action buttons
        btn_c1, btn_c2, btn_c3 = st.columns(3)
        with btn_c1:
            if st.button("🛒 Add to Cart", use_container_width=True, key="add_cart_detail"):
                cart_item = {
                    "id": str(item["id"]),
                    "name": item["productDisplayName"],
                    "type": item["articleType"],
                    "color": item["baseColour"],
                    "price": float(item["price"]),
                    "condition": item.get("condition", "Good"),
                    "image_path": f"data/images/{item['id']}.jpg",
                    "_source": "catalog",
                }
                added = add_to_cart(cart_item)
                st.session_state._cart_msg = "Added to cart!" if added else "Already in your cart."
                st.rerun()

        with btn_c2:
            wishlisted = is_item_wishlisted(str(item["id"]))
            wl_label = "❤️ Wishlisted" if wishlisted else "🤍 Add to Wishlist"
            if st.button(wl_label, use_container_width=True, key="add_wishlist_detail", disabled=wishlisted):
                wl_item = {
                    "id": str(item["id"]),
                    "name": item["productDisplayName"],
                    "type": item["articleType"],
                    "color": item["baseColour"],
                    "price": float(item["price"]),
                    "condition": item.get("condition", "Good"),
                    "image_path": f"data/images/{item['id']}.jpg",
                    "_source": "catalog",
                }
                add_wishlist_item(wl_item)
                st.session_state._cart_msg = "Added to wishlist!"
                st.rerun()

        with btn_c3:
            if st.button("💬 Ask Style Assistant", use_container_width=True, key="ask_assistant"):
                # Clear chat history for fresh context
                st.session_state.chat_history = []
                st.session_state.chat_tool_results = {}
                st.session_state.chat_resolved_items = {}
                # Store seed item so outfit saving includes it
                st.session_state.chat_seed_item = {
                    "id": str(item["id"]),
                    "name": item["productDisplayName"],
                    "type": item["articleType"],
                    "color": item["baseColour"],
                    "price": float(item["price"]),
                    "condition": item.get("condition", "Good"),
                    "image_path": f"data/images/{item['id']}.jpg",
                    "_source": "catalog",
                }
                st.session_state.chat_context = (
                    f"I'm looking at a {item['baseColour']} {item['articleType']} "
                    f"({item['productDisplayName']}) on Vinted, priced at €{item['price']}. "
                    f"It's for {item['usage']} / {item['season']}. "
                    f"What would go well with it? Do I have anything in my wardrobe that matches?"
                )
                st.switch_page("pages/3_Style_Assistant.py")

    st.markdown("---")

    # Match tabs
    tab1, tab2 = st.tabs(["✨ Match with", "👗 Build complete outfit"])

    with tab1:
        st.markdown("**Items that match well with this**")
        st.markdown('<div style="font-size:13px;color:#888;margin-bottom:16px;">Based on colour harmony, occasion, and style compatibility</div>', unsafe_allow_html=True)

        with st.spinner("Finding matches..."):
            matches = matcher.get_matches(item_id, num_matches=6)

        if not matches:
            st.info("No matches found for this item type.")
        else:
            cols = st.columns(3)
            for i, match in enumerate(matches):
                with cols[i % 3]:
                    match_img = get_image(match["id"])
                    same_seller = match["seller"] == item["seller"]

                    st.markdown('<div class="item-card">', unsafe_allow_html=True)
                    if match_img:
                        st.image(match_img, use_container_width=True)
                    else:
                        st.markdown('<div style="background:#f0f0f0;height:140px;display:flex;align-items:center;justify-content:center;font-size:36px;">👚</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="item-card-body">
                        <div class="item-card-price">€{match['price']}</div>
                        <div class="item-card-name">{match['name'][:45]}</div>
                        <div style="font-size:11px;color:#09B1BA;font-weight:500;margin-top:4px;">✦ {match['explanation']}</div>
                        {condition_badge(match['condition'])}
                    </div>
                    """, unsafe_allow_html=True)
                    if same_seller:
                        st.markdown('<div style="background:#e8f5f4;border-top:1px solid #b2dfdb;padding:5px 12px;font-size:11px;color:#007782;font-weight:600;">📦 Same seller — bundle & save!</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    # Add to cart + wishlist buttons for matched items
                    _m_item = {
                        "id": str(match["id"]),
                        "name": match["name"],
                        "type": match.get("type", match.get("articleType", "")),
                        "color": match.get("color", match.get("colour", "")),
                        "price": float(match["price"]),
                        "condition": match.get("condition", "Good"),
                        "image_path": f"data/images/{match['id']}.jpg",
                        "_source": "catalog",
                    }
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        st.button("🛒 Add", key=f"cart_match_{match['id']}_{i}",
                                  use_container_width=True,
                                  on_click=_handle_cart_add, args=(_m_item,))
                    with mc2:
                        match_wl = is_item_wishlisted(str(match["id"]))
                        wl_icon = "❤️" if match_wl else "🤍"
                        st.button(wl_icon, key=f"wl_match_{match['id']}_{i}",
                                  use_container_width=True, help="Wishlist",
                                  disabled=match_wl,
                                  on_click=_handle_wishlist_add, args=(_m_item,))

    with tab2:
        st.markdown("**Complete outfit built around this item**")
        st.markdown('<div style="font-size:13px;color:#888;margin-bottom:16px;">One piece per role — top, bottom, shoes, and accessory</div>', unsafe_allow_html=True)

        with st.spinner("Building your outfit..."):
            bundle = matcher.get_outfit_bundle(item_id, num_items=4)

        if not bundle:
            st.info("Could not build a full outfit for this item.")
        else:
            total_price = matcher.get_total_price(bundle)
            same_seller_items = matcher.get_same_seller_items(bundle)

            st.markdown(f"""
            <div style="background:#E0F4F4;border:1px solid #B2DFDB;border-radius:8px;padding:14px 20px;
                        margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;">
                <div>
                    <div style="font-size:13px;color:#555;">Complete outfit total</div>
                    <div style="font-size:22px;font-weight:700;color:#007782;">€{total_price}</div>
                </div>
                <div style="font-size:13px;color:#007782;font-weight:500;">
                    {len(same_seller_items)} item(s) from same seller 📦
                </div>
            </div>
            """, unsafe_allow_html=True)

            cols = st.columns(len(bundle))
            for pidx, (col, piece) in enumerate(zip(cols, bundle)):
                with col:
                    piece_img = get_image(piece["id"])
                    is_seed = piece.get("is_seed", False)
                    border = "2px solid #09B1BA" if is_seed else "1px solid #E8E8E8"

                    st.markdown(f'<div style="background:#fff;border-radius:8px;border:{border};overflow:hidden;">', unsafe_allow_html=True)
                    if piece_img:
                        st.image(piece_img, use_container_width=True)
                    else:
                        st.markdown('<div style="background:#f0f0f0;height:120px;display:flex;align-items:center;justify-content:center;font-size:30px;">👕</div>', unsafe_allow_html=True)

                    role_label = piece["role"].capitalize()
                    seed_label = " · Selected" if is_seed else ""
                    st.markdown(f"""
                    <div style="padding:8px 10px 12px;">
                        <div style="font-size:10px;font-weight:600;color:#09B1BA;text-transform:uppercase;">{role_label}{seed_label}</div>
                        <div style="font-size:12px;color:#555;margin-top:2px;">{piece['name'][:35]}</div>
                        <div style="font-size:15px;font-weight:700;margin-top:4px;">€{piece['price']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    # Individual cart + wishlist buttons per piece
                    _p_item = {
                        "id": str(piece["id"]),
                        "name": piece["name"],
                        "type": piece.get("articleType", piece.get("role", "")),
                        "color": piece.get("colour", piece.get("color", "")),
                        "price": float(piece["price"]),
                        "condition": piece.get("condition", "Good"),
                        "image_path": f"data/images/{piece['id']}.jpg",
                        "_source": "catalog",
                    }
                    pc1, pc2 = st.columns(2)
                    with pc1:
                        st.button("🛒", key=f"cart_piece_{piece['id']}_{pidx}",
                                  use_container_width=True, help="Add to Cart",
                                  on_click=_handle_cart_add, args=(_p_item,))
                    with pc2:
                        p_wl = is_item_wishlisted(str(piece["id"]))
                        p_icon = "❤️" if p_wl else "🤍"
                        st.button(p_icon, key=f"wl_piece_{piece['id']}_{pidx}",
                                  use_container_width=True, help="Wishlist",
                                  disabled=p_wl,
                                  on_click=_handle_wishlist_add, args=(_p_item,))

            # Add full outfit to cart
            _bundle_items = [
                {
                    "id": str(p["id"]),
                    "name": p["name"],
                    "type": p.get("articleType", p.get("role", "")),
                    "color": p.get("colour", p.get("color", "")),
                    "price": float(p["price"]),
                    "condition": p.get("condition", "Good"),
                    "image_path": f"data/images/{p['id']}.jpg",
                    "_source": "catalog",
                }
                for p in bundle
            ]
            st.button("🛒 Add Full Outfit to Cart", use_container_width=True,
                       key="cart_bundle",
                       on_click=_handle_bundle_cart, args=(_bundle_items,))


# ---------------------------------------------------------------------------
# Route between browse and detail
# ---------------------------------------------------------------------------
if st.session_state.selected_item_id is None:
    show_browse()
else:
    show_item_detail(st.session_state.selected_item_id)
