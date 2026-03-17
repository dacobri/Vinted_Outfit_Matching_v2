# Vinted Outfit Match V2 — AI-Powered Wardrobe & Styling Assistant

An upgraded Streamlit prototype that combines a second-hand fashion catalog with an AI-powered personal stylist. Built as Assignment 2 for the PDAI (Prototyping with Data & AI) course at Esade Business School.

## Overview

Vinted Outfit Match V2 transforms a basic catalog-matching prototype into a full-featured wardrobe management and AI styling platform. Users can upload photos of their real clothes, which are automatically processed with background removal and AI-powered attribute tagging. The centerpiece is a conversational Style Assistant — a multi-turn chatbot powered by Google Gemini that uses tool calling to access the user's wardrobe, check live weather conditions, search a 44K+ product catalog, and build complete outfit recommendations through natural conversation.

The prototype demonstrates advanced LLM integration patterns: Gemini Vision for structured clothing attribute extraction, multi-turn function calling with five distinct tools, RAG-like retrieval over personal wardrobe data and product catalogs, and sophisticated post-processing that renders inline visual item cards from structured model output.

## Features

| Page | Description |
|------|-------------|
| **Home** | Dashboard with quick stats (wardrobe count, outfit count, catalog size) and navigation cards to all features |
| **Browse & Match** | Explore 44K+ catalog items with filters. Click any item to see AI-matched complementary pieces and complete outfit bundles. Add items to cart or wishlist |
| **My Wardrobe** | Upload clothing photos → AI removes backgrounds (rembg) → Gemini Vision auto-tags type, color, pattern, material, season, occasion → editable form → save. Match wardrobe items against the catalog or build complete outfits |
| **Style Assistant** | Multi-turn chatbot with Gemini tool calling. Gets weather, searches wardrobe and catalog, saves outfits. Renders inline item cards in responses |
| **My Outfits** | Gallery of saved outfit boards with visual flat-lay layouts. Create manually or through the chatbot |
| **My Profile** | Set name, city, sizes, style preferences, and favorite colors. Personalizes all AI recommendations |
| **Cart** | Review items added from Browse & Match or My Wardrobe. Adjust quantities, remove items, and see order totals |
| **Wishlist** | Saved catalog items and outfit combinations you want to revisit. Add items from Browse & Match or wardrobe detail views |

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Frontend | Streamlit | Rapid prototyping with Python, multi-page app support |
| LLM (text + vision) | Google Gemini API (`gemini-2.5-flash`) | Free tier, function calling support, vision capabilities |
| Weather | Open-Meteo API | Free, no API key needed, accurate global coverage |
| Background removal | `rembg` (Python) | Local open-source model, no API key, transparent PNG output |
| Data storage | JSON files | Simple persistence for prototype (wardrobe, outfits, profile, wishlist) |
| Product catalog | CSV + images | 44K+ items from Kaggle fashion dataset with Vinted-style attributes |

## AI Integration Details

### 1. Gemini Vision — Structured Clothing Attribute Extraction
When a user uploads a clothing photo, Gemini Vision analyzes it with a carefully engineered prompt that returns a strict JSON schema with eight attributes (type, color, pattern, material, season, occasion, formality, gender). The response is parsed and pre-fills an editable form, combining AI intelligence with human oversight.

### 2. Multi-Turn Chatbot with Tool Calling
The Style Assistant implements Gemini's function calling with five tools:
- `get_weather` — Fetches live weather from Open-Meteo to give weather-appropriate outfit advice
- `search_wardrobe` — Queries the user's personal items with multi-attribute fuzzy filtering
- `search_catalog` — Searches 44K+ Vinted catalog items across multiple text fields
- `get_saved_outfits` — Retrieves previously saved outfit combinations
- `save_outfit` — Persists outfit recommendations the user likes

The chatbot handles up to 3 rounds of iterative tool calling per turn, allowing Gemini to chain tools (e.g., check weather → search wardrobe → suggest purchases to fill gaps).

### 3. RAG-Like Retrieval
Rather than stuffing the entire wardrobe and catalog into the prompt, the chatbot uses tool calling as a retrieval mechanism — Gemini decides what to search for based on the conversation context, retrieves relevant items, then synthesizes recommendations from the results.

### 4. Structured Output Parsing for Visual Rendering
Assistant responses contain item reference markers (`[WARDROBE_ITEM:id]`, `[CATALOG_ITEM:id]`) that the UI parses and replaces with visual item cards showing thumbnails, names, and attributes. This demonstrates non-trivial post-processing of LLM output.

## Setup & Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd Vinted_Outfit_Match_V2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Gemini API key (free at https://aistudio.google.com/apikey)
echo "GEMINI_API_KEY=your_key_here" > .env

# 4. Run the app
streamlit run app.py
```

**Note:** The first wardrobe upload may be slow as `rembg` downloads its model (~170MB) on first use.

## Project Structure

```
Vinted_Outfit_Match_V2/
├── app.py                      # Main entry point, home page with stats and navigation
├── pages/
│   ├── 1_Browse_&_Match.py     # Catalog browsing + matching engine UI
│   ├── 2_My_Wardrobe.py        # Upload flow + wardrobe grid + detail views
│   ├── 3_Style_Assistant.py    # Chatbot with tool calling (star feature)
│   ├── 4_Saved_Outfits.py      # Outfit boards gallery + manual creation
│   ├── 5_My_Profile.py         # User preferences and settings
│   ├── 6_Cart.py               # Shopping cart with quantity management
│   └── 7_Wishlist.py           # Saved items and outfit wishlists
├── services/
│   ├── __init__.py             # Package marker
│   ├── shared_ui.py            # Page config, global CSS theme, sidebar, cart helpers
│   ├── matching_engine.py      # Rule-based outfit matching (from A1, refactored)
│   ├── wardrobe_manager.py     # CRUD for wardrobe.json
│   ├── outfit_manager.py       # CRUD for outfits.json
│   ├── profile_manager.py      # CRUD for profile.json
│   ├── wishlist_manager.py     # CRUD for wishlist.json (items + outfits)
│   ├── style_assistant.py      # Gemini chat + tool calling orchestration
│   ├── weather_service.py      # Open-Meteo API wrapper with geocoding
│   └── image_processor.py      # rembg background removal + Gemini Vision tagging
├── data/
│   ├── vinted_catalog.csv      # 44K+ product catalog
│   ├── images/                 # Product thumbnails (matched by ID)
│   ├── wardrobe.json           # User's wardrobe (created at runtime)
│   ├── wardrobe_images/        # Uploaded + background-removed photos
│   ├── outfits.json            # Saved outfits (created at runtime)
│   ├── wishlist.json           # Wishlist data (created at runtime)
│   └── profile.json            # User profile (created at runtime)
├── .streamlit/
│   └── config.toml             # Streamlit theme (teal palette, light mode)
├── .env                        # API key (gitignored)
├── .gitignore
├── requirements.txt
└── README.md
```

## What's New in V2

- **AI Style Assistant chatbot** with multi-turn conversation and Gemini function calling (5 tools)
- **Vision-based auto-tagging** — upload a photo, get structured clothing attributes via Gemini Vision
- **Background removal** — rembg removes image backgrounds for clean wardrobe display
- **Weather-aware recommendations** — live weather data integrated into outfit suggestions
- **Personal wardrobe management** — upload, tag, filter, and organize your real clothes
- **Outfit saving and gallery** — save combinations from the chatbot or create them manually
- **User profile system** — style preferences, sizes, and location personalize all AI responses
- **Cart and Wishlist** — add items to cart from any page, save favorites to wishlist for later, persistent across sessions
- **Inline item cards in chat** — visual product cards rendered within chatbot responses
- **Contextual page navigation** — "Ask Style Assistant" buttons from Browse and Wardrobe pages pre-fill the chatbot
- **Complete UI redesign** — Vinted-inspired teal theme with custom CSS, hover animations, pill tags, and polished layout
- **Modular service architecture** — clean separation of concerns with 9 dedicated service modules