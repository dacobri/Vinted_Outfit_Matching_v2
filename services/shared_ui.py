"""
shared_ui.py
------------
Shared UI components rendered on every page:
- Light theme enforcement via Streamlit config
- Global CSS theme injection
- Custom branded sidebar (logo, navigation, cart indicator, profile summary)
- Cart helper functions

This module ensures visual consistency across all pages.
"""

import streamlit as st
import os
import sys

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from services.profile_manager import load_profile, profile_exists
from services.wardrobe_manager import get_wardrobe_count
from services.outfit_manager import get_outfit_count
from services.wishlist_manager import get_wishlist_item_count, get_wishlist_outfit_count


def get_cart_count() -> int:
    """Get number of items in the cart from session state."""
    if "cart" not in st.session_state:
        st.session_state.cart = []
    return len(st.session_state.cart)


def setup_page(page_title: str = "Vinted Outfit Match V2"):
    """
    Call at the top of every page BEFORE any other st calls.
    Sets page config, injects CSS, and renders the custom sidebar.
    """
    st.set_page_config(
        page_title=page_title,
        page_icon="👗",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    except ImportError:
        pass

    _inject_css()
    _render_sidebar()


def _inject_css():
    """Inject the full global CSS theme."""
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Force light theme ── */
:root {
    color-scheme: light !important;
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"],
[data-testid="stHeader"], [data-testid="stToolbar"] {
    background-color: #FAFAFA !important;
    color: #1A1A1A !important;
}
* { font-family: 'Inter', sans-serif; }

/* ── Hide Streamlit chrome + default page nav ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Main content area ── */
.block-container {
    padding: 1.5rem 2rem !important;
    max-width: 1200px !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #E8E8E8 !important;
}
[data-testid="stSidebar"] * {
    color: #1A1A1A !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    font-size: 14px;
}

/* ── Cards ── */
.card {
    background: #FFFFFF;
    border-radius: 8px;
    border: 1px solid #E8E8E8;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    padding: 16px;
    transition: all 0.2s ease;
}
.card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    transform: translateY(-2px);
}

/* ── Item cards ── */
.item-card {
    background: #FFFFFF;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #E8E8E8;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    transition: all 0.2s ease;
    cursor: pointer;
    height: 100%;
}
.item-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    transform: translateY(-2px);
    border-color: #09B1BA;
}
.item-card-body { padding: 10px 12px 12px; }
.item-card-price { font-size: 16px; font-weight: 700; color: #1A1A1A; }
.item-card-name { font-size: 12px; color: #555555; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ── Pill tags ── */
.pill {
    display: inline-block;
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 24px;
    font-weight: 500;
    margin: 2px 2px 2px 0;
}
.pill-teal { background: #E0F4F4; color: #007782; border: 1px solid #B2DFDB; }
.pill-grey { background: #F5F5F5; color: #555555; border: 1px solid #E8E8E8; }
.pill-green { background: #E8F5E9; color: #2E7D32; }

/* ── Condition badges ── */
.badge { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 20px; margin-top: 6px; font-weight: 500; }
.badge-new      { background: #e8f5e9; color: #2e7d32; }
.badge-likenew  { background: #e3f2fd; color: #1565c0; }
.badge-good     { background: #fff8e1; color: #f57f17; }
.badge-fair     { background: #fce4ec; color: #c62828; }

/* ── Buttons ── */
.stButton > button {
    background-color: #007782 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 8px 20px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background-color: #09B1BA !important;
    box-shadow: 0 2px 8px rgba(0,119,130,0.3) !important;
}
.stButton > button[kind="secondary"] {
    background-color: transparent !important;
    color: #007782 !important;
    border: 1.5px solid #007782 !important;
}
.stButton > button[kind="secondary"]:hover {
    background-color: #E0F4F4 !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 2px solid #E8E8E8; }
.stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0 !important; font-weight: 500 !important; color: #666 !important; padding: 8px 16px !important; }
.stTabs [aria-selected="true"] { color: #007782 !important; border-bottom: 2px solid #007782 !important; }

/* ── Chat styling ── */
[data-testid="stChatMessage"] {
    border-radius: 12px !important;
    padding: 12px 16px !important;
    margin-bottom: 8px !important;
    background-color: #FFFFFF !important;
}

/* ── Selectbox / input ── */
.stSelectbox > div > div { border-radius: 8px !important; }
.stTextInput > div > div > input { border-radius: 8px !important; }
.stMultiSelect > div > div { border-radius: 8px !important; }

/* ── Section headers ── */
.section-title { font-size: 22px; font-weight: 700; color: #1A1A1A; margin-bottom: 4px; }
.section-subtitle { font-size: 13px; color: #888; margin-bottom: 20px; }

/* ── Filter bar ── */
.filter-bar {
    background: #FFFFFF;
    border: 1px solid #E8E8E8;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

/* ── Detail view tags ── */
.detail-tag {
    display: inline-block;
    background: #E0F4F4;
    color: #007782;
    border: 1px solid #B2DFDB;
    border-radius: 20px;
    font-size: 12px;
    padding: 4px 12px;
    margin: 3px 4px 3px 0;
    font-weight: 500;
}

/* ── Chat inline item cards ── */
.chat-item-card {
    background: #FFFFFF;
    border: 1px solid #E8E8E8;
    border-radius: 8px;
    padding: 8px;
    text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
}
.chat-item-card img { border-radius: 6px; max-height: 100px; object-fit: cover; }

/* ── Weather pill ── */
.weather-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: #E0F4F4; color: #007782; border: 1px solid #B2DFDB;
    border-radius: 20px; padding: 4px 14px; font-size: 13px; font-weight: 500;
}

/* ── Empty state ── */
.empty-state { text-align: center; padding: 60px 20px; color: #888; }
.empty-state-icon { font-size: 48px; margin-bottom: 16px; }
.empty-state-title { font-size: 18px; font-weight: 600; color: #555; margin-bottom: 8px; }
.empty-state-text { font-size: 14px; color: #888; margin-bottom: 20px; }

/* ── Outfit board ── */
.outfit-board { background: #F8F8F8; border-radius: 12px; border: 1px solid #E8E8E8; padding: 20px; min-height: 300px; position: relative; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #CCC; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #AAA; }

hr { border-color: #E8E8E8 !important; margin: 24px 0 !important; }

/* ── Pagination ── */
.pagination { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 20px 0; }
</style>
""", unsafe_allow_html=True)


def _render_sidebar():
    """Render the branded sidebar on every page."""
    cart_count = get_cart_count()
    cart_badge = f" ({cart_count})" if cart_count > 0 else ""
    wishlist_count = get_wishlist_item_count() + get_wishlist_outfit_count()
    wishlist_badge = f" ({wishlist_count})" if wishlist_count > 0 else ""

    with st.sidebar:
        st.markdown("""
        <div style="padding: 8px 0 16px;">
            <div style="font-size: 22px; font-weight: 700; color: #007782; letter-spacing: -0.5px;">
                vinted <span style="color: #09B1BA;">✦</span> outfit match
            </div>
            <div style="font-size: 12px; color: #888; margin-top: 2px;">
                AI-powered styling assistant · V2
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Navigation
        st.page_link("app.py", label="🏠  Home", use_container_width=True)
        st.page_link("pages/1_Browse_&_Match.py", label="🔍  Browse & Match", use_container_width=True)
        st.page_link("pages/2_My_Wardrobe.py", label="👕  My Wardrobe", use_container_width=True)
        st.page_link("pages/3_Style_Assistant.py", label="💬  Style Assistant", use_container_width=True)
        st.page_link("pages/4_Saved_Outfits.py", label="✨  My Outfits", use_container_width=True)
        st.page_link("pages/5_My_Profile.py", label="👤  My Profile", use_container_width=True)
        st.page_link("pages/6_Cart.py", label=f"🛒  Cart{cart_badge}", use_container_width=True)
        st.page_link("pages/7_Wishlist.py", label=f"❤️  My Wishlist{wishlist_badge}", use_container_width=True)

        st.markdown("---")

        # Profile summary
        if profile_exists():
            profile = load_profile()
            name = profile.get("name", "")
            city = profile.get("city", "")
            if name:
                st.markdown(f"""
                <div style="padding: 10px; background: #F5F5F5; border-radius: 8px; font-size: 13px;">
                    <div style="font-weight: 600; color: #1A1A1A;">👤 {name}</div>
                    <div style="color: #888; margin-top: 2px;">📍 {city}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="padding: 10px; background: #FFF8E1; border-radius: 8px; font-size: 13px; color: #F57F17;">
                ⚠️ Set up your profile for personalized recommendations
            </div>
            """, unsafe_allow_html=True)


def add_to_cart(item: dict):
    """Add an item dict to the session cart. Prevents duplicates by id."""
    if "cart" not in st.session_state:
        st.session_state.cart = []
    # Check for duplicates
    existing_ids = {i.get("id") for i in st.session_state.cart}
    item_id = str(item.get("id", ""))
    if item_id and item_id not in existing_ids:
        st.session_state.cart.append(item)
        return True
    return False


def remove_from_cart(item_id: str):
    """Remove an item from cart by ID."""
    if "cart" not in st.session_state:
        return
    st.session_state.cart = [i for i in st.session_state.cart if str(i.get("id")) != str(item_id)]
