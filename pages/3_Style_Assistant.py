"""
Page 3: Style Assistant (THE STAR FEATURE)
------------------------------------------
AI-powered fashion chatbot with Gemini tool calling.
Supports weather-aware outfit recommendations, wardrobe search,
catalog discovery, and outfit saving through natural conversation.

Features:
- Multi-turn conversation with persistent history
- Tool calling (weather, wardrobe, catalog, outfits)
- Inline item cards rendered from item references in assistant text
- Add to Cart on each recommended item card
- Save outfit from multi-item recommendations
- Contextual entry from other pages
- Suggested prompt pills for empty state
- "Style my latest item" auto-searches wardrobe
"""

import streamlit as st
import os
import sys
import re
import pandas as pd
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Shared UI: page config + CSS + sidebar (must be first)
from services.shared_ui import setup_page, add_to_cart
setup_page("Style Assistant — Vinted Outfit Match V2")

from services.style_assistant import chat, parse_item_references, clean_response_text
from services.weather_service import get_weather_summary
from services.profile_manager import load_profile
from services.wardrobe_manager import load_wardrobe, get_item
from services.outfit_manager import create_outfit
from services.wishlist_manager import add_wishlist_item, is_item_wishlisted

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
IMAGE_DIR = os.path.join(DATA_DIR, "images")
WARDROBE_IMAGES_DIR = os.path.join(DATA_DIR, "wardrobe_images")


def get_api_key():
    """Get Gemini API key from environment or Streamlit secrets."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass
    return key


@st.cache_data(show_spinner=False)
def _load_catalog_df():
    """Cache the catalog dataframe for fast item lookups."""
    try:
        return pd.read_csv(os.path.join(DATA_DIR, "vinted_catalog.csv"), on_bad_lines="skip")
    except Exception:
        return pd.DataFrame()


def get_catalog_item(item_id):
    """Look up a catalog item by ID."""
    try:
        df = _load_catalog_df()
        row = df[df["id"] == int(item_id)]
        if not row.empty:
            r = row.iloc[0]
            return {
                "id": str(r["id"]),
                "name": r["productDisplayName"],
                "type": r["articleType"],
                "color": r.get("baseColour", ""),
                "price": r["price"],
                "condition": r.get("condition", "Good"),
                "image_path": os.path.join(IMAGE_DIR, f"{r['id']}.jpg"),
                "_source": "catalog",
            }
    except Exception:
        pass
    return None


def resolve_items_for_message(assistant_text: str, tool_results: list) -> list:
    """
    Resolve the ACTUAL items the assistant is recommending by:
    1. Parsing [WARDROBE_ITEM:id] and [CATALOG_ITEM:id] references from text
    2. Looking up those specific items from tool results or directly from data
    3. Falling back to tool-result items only if NO references are found

    This ensures displayed cards match what the assistant is describing.
    """
    # Step 1: Try to get specific item references from the assistant text
    refs = parse_item_references(assistant_text)

    if refs:
        # Build lookup from all tool results for fast access
        tool_items_by_id = {}
        for tr in tool_results:
            result = tr.get("result", {})
            for item in result.get("items", []):
                item_id = str(item.get("id", ""))
                if item_id:
                    tool_items_by_id[item_id] = item

        resolved = []
        for ref in refs:
            item_id = ref["id"]
            source = ref["source"]

            # First check tool results (fastest, already have full data)
            if item_id in tool_items_by_id:
                resolved.append(tool_items_by_id[item_id])
                continue

            # Direct lookup from wardrobe or catalog
            if source == "wardrobe":
                wardrobe_item = get_item(item_id)
                if wardrobe_item:
                    wardrobe_item["_source"] = "wardrobe"
                    resolved.append(wardrobe_item)
            else:
                catalog_item = get_catalog_item(item_id)
                if catalog_item:
                    resolved.append(catalog_item)

        if resolved:
            return resolved

    # Step 2: Fallback — use items from tool results (search_wardrobe / search_catalog)
    # Only use this if no explicit references were found
    items_from_tools = []
    for tr in tool_results:
        result = tr.get("result", {})
        if "items" in result:
            items_from_tools.extend(result["items"][:6])

    return items_from_tools[:8]


def render_item_cards(items: list, msg_key: str):
    """
    Render inline item cards with Add to Cart buttons.
    items: list of item dicts to display
    msg_key: unique key prefix for buttons in this message
    """
    if not items:
        return

    cols_count = min(len(items), 4)
    cols = st.columns(cols_count)

    for idx, item in enumerate(items[:cols_count]):
        with cols[idx]:
            source = item.get("_source", "catalog")

            # Get image path
            if source == "wardrobe":
                img_file = item.get("image_filename", "")
                img_path = os.path.join(WARDROBE_IMAGES_DIR, img_file) if img_file else ""
            else:
                img_path = item.get("image_path", "")
                if img_path and not img_path.startswith("/"):
                    img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_path)

            st.markdown('<div class="chat-item-card">', unsafe_allow_html=True)

            if img_path and os.path.exists(img_path):
                try:
                    st.image(img_path, use_container_width=True)
                except Exception:
                    st.markdown("👕", unsafe_allow_html=True)
            else:
                st.markdown('<div style="background:#f5f5f5;height:80px;display:flex;align-items:center;justify-content:center;font-size:24px;border-radius:6px;">👕</div>', unsafe_allow_html=True)

            name = item.get("name", item.get("type", "Item"))
            color = item.get("color", "")
            price_str = f"€{item['price']}" if "price" in item else ""
            source_label = "📦 Catalog" if source == "catalog" else "👕 Wardrobe"

            st.markdown(f"""
            <div style="padding:6px 4px;">
                <div style="font-size:11px;font-weight:600;color:#1A1A1A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name[:30]}</div>
                <div style="font-size:10px;color:#888;">{color} {price_str}</div>
                <div style="font-size:9px;color:#09B1BA;margin-top:2px;">{source_label}</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Action buttons for catalog items
            if source == "catalog" and item.get("id"):
                ab1, ab2 = st.columns(2)
                with ab1:
                    btn_key = f"cart_{msg_key}_{item['id']}_{idx}"
                    if st.button("🛒", key=btn_key, use_container_width=True, help="Add to Cart"):
                        cart_item = {
                            "id": str(item["id"]),
                            "name": name,
                            "type": item.get("type", ""),
                            "color": color,
                            "price": float(item.get("price", 0)),
                            "condition": item.get("condition", "Good"),
                            "image_path": f"data/images/{item['id']}.jpg",
                            "_source": "catalog",
                        }
                        if add_to_cart(cart_item):
                            st.rerun()
                with ab2:
                    wl_key = f"wl_{msg_key}_{item['id']}_{idx}"
                    already_wl = is_item_wishlisted(str(item["id"]))
                    wl_icon = "❤️" if already_wl else "🤍"
                    if st.button(wl_icon, key=wl_key, use_container_width=True, help="Wishlist", disabled=already_wl):
                        wl_item = {
                            "id": str(item["id"]),
                            "name": name,
                            "type": item.get("type", ""),
                            "color": color,
                            "price": float(item.get("price", 0)),
                            "condition": item.get("condition", "Good"),
                            "image_path": f"data/images/{item['id']}.jpg",
                            "_source": "catalog",
                        }
                        add_wishlist_item(wl_item)
                        st.rerun()


def render_save_outfit(items: list, msg_key: str):
    """
    Show a 'Save as Outfit' option when the assistant recommends 2+ items.
    Includes the seed item (the item the user asked about) if present.
    """
    if len(items) < 2:
        return

    save_key = f"save_outfit_{msg_key}"

    # Check if already saved for this message
    saved_outfits_set = st.session_state.get("_saved_outfit_msgs", set())
    if msg_key in saved_outfits_set:
        st.markdown('<div style="font-size:12px;color:#2E7D32;margin-top:4px;">✅ Outfit saved!</div>', unsafe_allow_html=True)
        return

    # Use an expander to keep it tidy
    with st.expander("💾 Save as Outfit", expanded=False):
        outfit_name = st.text_input(
            "Outfit name",
            placeholder="e.g. Rainy Monday Work Look",
            key=f"name_{save_key}",
        )
        if st.button("Save Outfit", key=save_key, use_container_width=True):
            if outfit_name.strip():
                # Build full items list — include the seed item (the item the user asked about)
                all_items = list(items)
                seed_item = st.session_state.get("chat_seed_item")
                if seed_item:
                    seed_id = str(seed_item.get("id", ""))
                    existing_ids = {str(it.get("id", "")) for it in all_items}
                    if seed_id and seed_id not in existing_ids:
                        all_items.insert(0, seed_item)

                item_ids = [str(item.get("id", "")) for item in all_items if item.get("id")]
                # Store full item data so My Outfits page can display catalog items
                recommended_items = []
                for item in all_items:
                    rec = {
                        "id": str(item.get("id", "")),
                        "name": item.get("name", ""),
                        "type": item.get("type", ""),
                        "color": item.get("color", ""),
                        "_source": item.get("_source", "catalog"),
                    }
                    if "price" in item:
                        rec["price"] = item["price"]
                    if "image_filename" in item:
                        rec["image_filename"] = item["image_filename"]
                    if "image_path" in item:
                        rec["image_path"] = item["image_path"]
                    if "condition" in item:
                        rec["condition"] = item["condition"]
                    recommended_items.append(rec)

                create_outfit(
                    name=outfit_name.strip(),
                    item_ids=item_ids,
                    occasion="Casual",
                    season="All",
                    source="assistant",
                    recommended_items=recommended_items,
                )
                # Mark as saved
                if "_saved_outfit_msgs" not in st.session_state:
                    st.session_state._saved_outfit_msgs = set()
                st.session_state._saved_outfit_msgs.add(msg_key)
                st.rerun()
            else:
                st.warning("Please enter an outfit name.")


def get_latest_wardrobe_context() -> str:
    """Build a chat context message about the most recently added wardrobe item."""
    items = load_wardrobe()
    if not items:
        return "I'd like to style my latest wardrobe item, but my wardrobe is empty. Can you help me get started by suggesting what items to add first?"
    # Items are stored in order — last item is the most recent
    latest = items[-1]
    return (
        f"I just added a new item to my wardrobe: a {latest.get('color', '')} {latest.get('type', 'item')} "
        f"called \"{latest.get('name', 'my item')}\". "
        f"It's {latest.get('material', '')} material, {latest.get('formality', 'casual')} style, "
        f"good for {', '.join(latest.get('season', ['all seasons']))}. "
        f"Can you suggest outfits I can build with it using my other wardrobe items? "
        f"Also suggest any catalog items that would complement it."
    )


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_tool_results" not in st.session_state:
    st.session_state.chat_tool_results = {}
if "chat_resolved_items" not in st.session_state:
    st.session_state.chat_resolved_items = {}

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
col_header, col_weather = st.columns([3, 1])

with col_header:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
        <div style="background:#007782;color:white;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;">🤖</div>
        <div>
            <div style="font-size:20px;font-weight:700;color:#1A1A1A;">Vinted Style AI</div>
            <div style="font-size:12px;color:#888;">Your personal fashion assistant</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_weather:
    profile = load_profile()
    city = profile.get("city", "Barcelona")
    weather_text = get_weather_summary(city)
    st.markdown(f'<div class="weather-pill">🌤️ {weather_text}</div>', unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# API key check
# ---------------------------------------------------------------------------
api_key = get_api_key()
if not api_key:
    st.warning("⚠️ **Gemini API key not found.** Set `GEMINI_API_KEY` in your `.env` file or Streamlit secrets to enable the Style Assistant.")
    st.code("# In your .env file:\nGEMINI_API_KEY=your_key_here", language="bash")
    st.stop()

# ---------------------------------------------------------------------------
# Handle context from other pages
# ---------------------------------------------------------------------------
if "chat_context" in st.session_state and st.session_state.chat_context:
    context_msg = st.session_state.chat_context
    st.session_state.chat_context = None  # Clear so it doesn't repeat

    if not st.session_state.chat_history:
        # Auto-send the context as the first message
        with st.spinner("🤖 Thinking..."):
            response, updated_history, tool_results = chat(
                context_msg, st.session_state.chat_history, api_key
            )
        st.session_state.chat_history = updated_history
        msg_idx = len(updated_history) - 1
        st.session_state.chat_tool_results[msg_idx] = tool_results
        # Resolve items for this message
        resolved = resolve_items_for_message(response, tool_results)
        st.session_state.chat_resolved_items[msg_idx] = resolved
        st.rerun()

# ---------------------------------------------------------------------------
# Suggested prompts (shown when chat is empty)
# ---------------------------------------------------------------------------
if not st.session_state.chat_history:
    st.markdown("""
    <div style="text-align:center;padding:40px 20px 20px;">
        <div style="font-size:36px;margin-bottom:12px;">👗</div>
        <div style="font-size:18px;font-weight:600;color:#1A1A1A;margin-bottom:6px;">What can I help you with?</div>
        <div style="font-size:14px;color:#888;margin-bottom:24px;">Ask me anything about fashion, your wardrobe, or today's weather</div>
    </div>
    """, unsafe_allow_html=True)

    suggested_prompts = [
        "What should I wear to work today?",
        "Build me a casual weekend outfit",
        "Style my latest item",
        "What outfit could I buy for a party?",
        "What's missing from my wardrobe?",
        "Suggest new items that match my style",
    ]

    # Render as buttons in 3 columns
    cols = st.columns(3)
    for i, prompt in enumerate(suggested_prompts):
        with cols[i % 3]:
            if st.button(prompt, key=f"suggest_{i}", use_container_width=True):
                # "Style my latest item" uses special context
                if prompt == "Style my latest item":
                    actual_prompt = get_latest_wardrobe_context()
                else:
                    actual_prompt = prompt

                with st.spinner("🤖 Thinking..."):
                    response, updated_history, tool_results = chat(
                        actual_prompt, st.session_state.chat_history, api_key
                    )
                st.session_state.chat_history = updated_history
                msg_idx = len(updated_history) - 1
                st.session_state.chat_tool_results[msg_idx] = tool_results
                resolved = resolve_items_for_message(response, tool_results)
                st.session_state.chat_resolved_items[msg_idx] = resolved
                st.rerun()

# ---------------------------------------------------------------------------
# Chat history display
# ---------------------------------------------------------------------------
for i, msg in enumerate(st.session_state.chat_history):
    role = msg["role"]
    content = msg["content"]

    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(content)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            # Clean item reference markers from display text
            display_text = clean_response_text(content)
            st.markdown(display_text)

            # Render resolved item cards (accurate to what the assistant described)
            resolved_items = st.session_state.chat_resolved_items.get(i, [])
            if not resolved_items and i in st.session_state.chat_tool_results:
                # Lazy resolve for messages from before we tracked resolved items
                tool_results = st.session_state.chat_tool_results[i]
                if tool_results:
                    resolved_items = resolve_items_for_message(content, tool_results)
                    st.session_state.chat_resolved_items[i] = resolved_items

            if resolved_items:
                render_item_cards(resolved_items, msg_key=f"hist_{i}")
                render_save_outfit(resolved_items, msg_key=f"hist_{i}")

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
user_input = st.chat_input("Ask me about outfits, your wardrobe, or what to wear...")

if user_input:
    # Display user message immediately
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # Get assistant response
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🤖 Thinking..."):
            response, updated_history, tool_results = chat(
                user_input, st.session_state.chat_history, api_key
            )

        st.session_state.chat_history = updated_history
        msg_idx = len(updated_history) - 1
        st.session_state.chat_tool_results[msg_idx] = tool_results

        # Resolve items for accurate display
        resolved_items = resolve_items_for_message(response, tool_results)
        st.session_state.chat_resolved_items[msg_idx] = resolved_items

        display_text = clean_response_text(response)
        st.markdown(display_text)

        if resolved_items:
            render_item_cards(resolved_items, msg_key=f"new_{msg_idx}")
            render_save_outfit(resolved_items, msg_key=f"new_{msg_idx}")

# ---------------------------------------------------------------------------
# Clear chat button (bottom of sidebar)
# ---------------------------------------------------------------------------
with st.sidebar:
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.chat_tool_results = {}
            st.session_state.chat_resolved_items = {}
            st.session_state._saved_outfit_msgs = set()
            st.session_state.chat_seed_item = None
            st.rerun()
