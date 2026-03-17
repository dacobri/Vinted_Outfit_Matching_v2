"""
Page 5: My Profile
------------------
User settings that personalize the AI assistant's recommendations.
Includes name, city, gender, sizes, style preferences, and color swatches.
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Shared UI: page config + CSS + sidebar (must be first)
from services.shared_ui import setup_page
setup_page("My Profile — Vinted Outfit Match V2")

from services.profile_manager import load_profile, save_profile, profile_exists

st.markdown('<div class="section-title">My Profile</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">Personalize your style recommendations</div>', unsafe_allow_html=True)

# Onboarding message for first-time users
if not profile_exists():
    st.info("👋 **Welcome!** Set up your profile so the Style Assistant can give you personalized recommendations.")

profile = load_profile()

# ---------------------------------------------------------------------------
# Profile form
# ---------------------------------------------------------------------------
with st.form("profile_form"):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Name", value=profile.get("name", ""), placeholder="Your name")
        city = st.text_input(
            "City",
            value=profile.get("city", "Barcelona"),
            help="Used for weather-based outfit recommendations",
        )
        gender_options = ["Men", "Women", "Non-binary", "Prefer not to say"]
        gender_idx = gender_options.index(profile.get("gender", "Prefer not to say")) if profile.get("gender") in gender_options else 3
        gender = st.selectbox("Gender", gender_options, index=gender_idx)

    with col2:
        size_options = ["XS", "S", "M", "L", "XL", "XXL"]
        top_idx = size_options.index(profile.get("top_size", "M")) if profile.get("top_size") in size_options else 2
        top_size = st.selectbox("Top Size", size_options, index=top_idx)

        bottom_idx = size_options.index(profile.get("bottom_size", "M")) if profile.get("bottom_size") in size_options else 2
        bottom_size = st.selectbox("Bottom Size", size_options, index=bottom_idx)

        shoe_options = [f"EU {s}" for s in range(36, 49)]
        shoe_idx = shoe_options.index(profile.get("shoe_size", "EU 42")) if profile.get("shoe_size") in shoe_options else 6
        shoe_size = st.selectbox("Shoe Size", shoe_options, index=shoe_idx)

    st.markdown("---")

    # Style preferences as multi-select
    style_options = [
        "Casual", "Formal", "Streetwear", "Minimalist", "Bohemian",
        "Sporty", "Classic", "Preppy", "Vintage", "Avant-garde"
    ]
    style_prefs = st.multiselect(
        "Style Preferences",
        style_options,
        default=profile.get("style_preferences", []),
        help="Select all styles you like",
    )

    st.markdown("---")

    # Preferred colors
    color_options = [
        "Black", "White", "Navy", "Grey", "Beige", "Brown",
        "Red", "Green", "Blue", "Pink", "Yellow", "Purple",
        "Orange", "Teal", "Burgundy", "Olive",
    ]
    color_hex = {
        "Black": "#1A1A1A", "White": "#F5F5F5", "Navy": "#1B2A4A",
        "Grey": "#888888", "Beige": "#D4C5A9", "Brown": "#6B4226",
        "Red": "#DC3545", "Green": "#28A745", "Blue": "#007BFF",
        "Pink": "#E91E8C", "Yellow": "#FFC107", "Purple": "#6F42C1",
        "Orange": "#FD7E14", "Teal": "#007782", "Burgundy": "#722F37",
        "Olive": "#6B8E23",
    }

    preferred_colors = st.multiselect(
        "Preferred Colors",
        color_options,
        default=profile.get("preferred_colors", []),
        help="Select your favorite colors to wear",
    )

    # Show color swatches as a visual preview
    if preferred_colors:
        swatches = ""
        for c in preferred_colors:
            hex_val = color_hex.get(c, "#888")
            swatches += f'<span style="display:inline-block;width:24px;height:24px;border-radius:50%;background:{hex_val};margin:2px 4px;border:2px solid #E8E8E8;" title="{c}"></span> '
        st.markdown(f"<div style='margin-top:8px;'>{swatches}</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    submitted = st.form_submit_button("💾 Save Profile", use_container_width=True)

    if submitted:
        updated_profile = {
            "name": name,
            "city": city,
            "gender": gender,
            "top_size": top_size,
            "bottom_size": bottom_size,
            "shoe_size": shoe_size,
            "style_preferences": style_prefs,
            "preferred_colors": preferred_colors,
        }
        save_profile(updated_profile)
        st.success("✅ Profile saved! Your Style Assistant will use these preferences.")
        st.rerun()
