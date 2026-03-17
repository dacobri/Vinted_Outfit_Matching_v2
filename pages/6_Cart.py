"""
Page 6: Shopping Cart
---------------------
View items added to cart from Browse & Match, with remove buttons,
total price calculation, and a simulated checkout flow.
"""

import streamlit as st
import os
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Shared UI: page config + CSS + sidebar (must be first)
from services.shared_ui import setup_page, remove_from_cart, get_cart_count
from services.image_url import get_image_url
setup_page("Cart — Vinted Outfit Match V2")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
IMAGE_DIR = os.path.join(DATA_DIR, "images")


def get_image(item_id):
    return get_image_url(int(item_id)) if item_id else None


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "cart" not in st.session_state:
    st.session_state.cart = []
if "checkout_done" not in st.session_state:
    st.session_state.checkout_done = False

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Shopping Cart</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">Review your selected items before checkout</div>', unsafe_allow_html=True)

cart_items = st.session_state.cart

# ---------------------------------------------------------------------------
# Empty cart state
# ---------------------------------------------------------------------------
if not cart_items:
    if st.session_state.checkout_done:
        # Post-checkout thank you
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🎉</div>
            <div class="empty-state-title">Order confirmed!</div>
            <div class="empty-state-text">Thank you for your purchase. Your items are on their way!<br>(This is a prototype — no real transaction was made.)</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 Continue Browsing", use_container_width=True, key="post_checkout_browse"):
            st.session_state.checkout_done = False
            st.switch_page("pages/1_Browse_&_Match.py")
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🛒</div>
            <div class="empty-state-title">Your cart is empty</div>
            <div class="empty-state-text">Browse the catalog to find items you love, then add them to your cart.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 Browse Catalog", use_container_width=True, key="empty_cart_browse"):
            st.switch_page("pages/1_Browse_&_Match.py")
    st.stop()

# ---------------------------------------------------------------------------
# Cart items list
# ---------------------------------------------------------------------------
total_price = 0.0

for idx, item in enumerate(cart_items):
    item_col, info_col, price_col, action_col = st.columns([1, 3, 1, 1])

    with item_col:
        img = item.get("image_path") or get_image(item.get("id", 0))
        if img:
            st.image(img, width=80)
        else:
            st.markdown('<div style="background:#f0f0f0;width:80px;height:80px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:28px;">👕</div>', unsafe_allow_html=True)

    with info_col:
        st.markdown(f'<div style="font-weight:600;font-size:15px;margin-top:8px;">{item.get("name", "Item")[:50]}</div>', unsafe_allow_html=True)
        pills = []
        if item.get("type"):
            pills.append(f'<span class="pill pill-teal">{item["type"]}</span>')
        if item.get("color"):
            pills.append(f'<span class="pill pill-grey">{item["color"]}</span>')
        if item.get("condition"):
            pills.append(f'<span class="pill pill-grey">{item["condition"]}</span>')
        st.markdown(" ".join(pills), unsafe_allow_html=True)

    with price_col:
        price = float(item.get("price", 0))
        total_price += price
        st.markdown(f'<div style="font-size:18px;font-weight:700;color:#007782;margin-top:12px;">€{price:.2f}</div>', unsafe_allow_html=True)

    with action_col:
        if st.button("🗑️ Remove", key=f"remove_cart_{item.get('id', idx)}", use_container_width=True):
            remove_from_cart(str(item.get("id", "")))
            st.rerun()

    st.markdown('<hr style="margin:8px 0;border-color:#f0f0f0;">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Cart summary & checkout
# ---------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)

summary_col, checkout_col = st.columns([2, 1])

with summary_col:
    st.markdown(f"""
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:14px;color:#888;">Cart total ({len(cart_items)} item{'s' if len(cart_items) != 1 else ''})</div>
                <div style="font-size:28px;font-weight:700;color:#007782;">€{total_price:.2f}</div>
            </div>
            <div style="font-size:13px;color:#555;">
                🚚 Free shipping on orders over €50
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with checkout_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✅ Proceed to Checkout", use_container_width=True, key="checkout_btn", type="primary"):
        st.session_state.checkout_done = True
        st.session_state.cart = []
        st.rerun()

    if st.button("🗑️ Clear Cart", use_container_width=True, key="clear_cart_btn"):
        st.session_state.cart = []
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Continue shopping link
if st.button("🔍 Continue Browsing", use_container_width=True, key="continue_browse"):
    st.switch_page("pages/1_Browse_&_Match.py")
