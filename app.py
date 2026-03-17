"""
app.py — Vinted Outfit Match V2
================================
Main entry point. Configures the page, injects the global CSS theme,
and renders the landing / home page with navigation to all features.

Run with:  streamlit run app.py
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Shared UI: page config + CSS + sidebar (must be first)
from services.shared_ui import setup_page
setup_page("Vinted Outfit Match V2 — Home")

from services.wardrobe_manager import get_wardrobe_count
from services.outfit_manager import get_outfit_count

# ---------------------------------------------------------------------------
# Home page content
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Welcome to Vinted Outfit Match V2</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">Your AI-powered wardrobe & styling assistant</div>', unsafe_allow_html=True)

wardrobe_count = get_wardrobe_count()
outfit_count = get_outfit_count()

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div class="card" style="text-align: center;">
        <div style="font-size: 32px; margin-bottom: 8px;">👕</div>
        <div style="font-size: 24px; font-weight: 700; color: #007782;">{wardrobe_count}</div>
        <div style="font-size: 13px; color: #888;">Items in wardrobe</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="card" style="text-align: center;">
        <div style="font-size: 32px; margin-bottom: 8px;">✨</div>
        <div style="font-size: 24px; font-weight: 700; color: #007782;">{outfit_count}</div>
        <div style="font-size: 13px; color: #888;">My outfits</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="card" style="text-align: center;">
        <div style="font-size: 32px; margin-bottom: 8px;">🛍️</div>
        <div style="font-size: 24px; font-weight: 700; color: #007782;">44K+</div>
        <div style="font-size: 13px; color: #888;">Catalog items</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("### Get Started")
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="card">
        <div style="font-size: 24px; margin-bottom: 8px;">🔍</div>
        <div style="font-weight: 600; font-size: 16px; margin-bottom: 6px;">Browse & Match</div>
        <div style="font-size: 13px; color: #555; line-height: 1.5;">
            Explore 44K+ second-hand items. Click any item to see AI-powered complementary matches and complete outfit suggestions.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Browse Catalog →", key="home_browse"):
        st.switch_page("pages/1_Browse_&_Match.py")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("""
    <div class="card">
        <div style="font-size: 24px; margin-bottom: 8px;">💬</div>
        <div style="font-weight: 600; font-size: 16px; margin-bottom: 6px;">Style Assistant</div>
        <div style="font-size: 13px; color: #555; line-height: 1.5;">
            Chat with your AI stylist. Get weather-aware outfit recommendations, wardrobe analysis, and shopping suggestions.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Start Chatting →", key="home_chat"):
        st.switch_page("pages/3_Style_Assistant.py")

with col2:
    st.markdown("""
    <div class="card">
        <div style="font-size: 24px; margin-bottom: 8px;">👕</div>
        <div style="font-weight: 600; font-size: 16px; margin-bottom: 6px;">My Wardrobe</div>
        <div style="font-size: 13px; color: #555; line-height: 1.5;">
            Upload photos of your clothes. AI removes backgrounds and auto-tags each item with type, color, material, and more.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Open Wardrobe →", key="home_wardrobe"):
        st.switch_page("pages/2_My_Wardrobe.py")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("""
    <div class="card">
        <div style="font-size: 24px; margin-bottom: 8px;">👤</div>
        <div style="font-weight: 600; font-size: 16px; margin-bottom: 6px;">My Profile</div>
        <div style="font-size: 13px; color: #555; line-height: 1.5;">
            Set your style preferences, sizes, and location. The AI uses your profile to personalize every recommendation.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Set Up Profile →", key="home_profile"):
        st.switch_page("pages/5_My_Profile.py")
