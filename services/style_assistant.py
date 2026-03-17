"""
style_assistant.py
------------------
Gemini-powered fashion chatbot with tool calling.

Implements a multi-turn conversational assistant that can:
- Check weather (current + multi-day forecast) for any city
- Search the user's wardrobe
- Search the Vinted product catalog
- View and save outfit combinations
- Analyze uploaded clothing images

Uses the google-genai SDK with manual tool execution flow.
"""

import json
import os
import pandas as pd

from google import genai
from google.genai import types

from services.weather_service import get_weather
from services.wardrobe_manager import load_wardrobe, search_items
from services.outfit_manager import load_outfits, create_outfit
from services.profile_manager import get_profile_summary

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CATALOG_PATH = os.path.join(DATA_DIR, "vinted_catalog.csv")

# ---------------------------------------------------------------------------
# Tool definitions for Gemini function calling
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_weather",
            description=(
                "Get weather conditions for a city — current conditions and optionally "
                "a multi-day forecast (up to 16 days). Use this when recommending "
                "outfits for a specific day, date range, or trip. For trips or future "
                "dates, set forecast_days to cover the period (e.g. 7 for next week)."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "city": types.Schema(
                        type="STRING",
                        description="City name, e.g. 'Barcelona', 'Paris', 'New York', 'Tokyo'"
                    ),
                    "forecast_days": types.Schema(
                        type="INTEGER",
                        description="Number of days to forecast (1-16). Default 1 for today only. Use 7 for 'next week', 3 for 'next few days', etc."
                    ),
                },
                required=["city"],
            ),
        ),
        types.FunctionDeclaration(
            name="search_wardrobe",
            description=(
                "Search the user's personal wardrobe for items they already own. "
                "ALWAYS call this FIRST when the user asks for outfit recommendations, "
                "'what should I wear', or styling advice — the default is to recommend "
                "from items they own. Call with no filters to get the full wardrobe, "
                "or pass filters to narrow down. Returns real items with IDs, names, "
                "colors, types, and images."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "category": types.Schema(
                        type="STRING",
                        description="Filter by clothing type, e.g. 'T-Shirt', 'Jeans', 'Sneakers', 'Jacket'"
                    ),
                    "color": types.Schema(
                        type="STRING",
                        description="Filter by color, e.g. 'Blue', 'Black', 'White', 'Navy Blue'"
                    ),
                    "occasion": types.Schema(
                        type="STRING",
                        description="Filter by occasion, e.g. 'Casual', 'Formal', 'Party', 'Business'"
                    ),
                    "season": types.Schema(
                        type="STRING",
                        description="Filter by season, e.g. 'Summer', 'Winter', 'Spring', 'Fall'"
                    ),
                    "formality": types.Schema(
                        type="STRING",
                        description="Filter by formality level, e.g. 'Casual', 'Smart Casual', 'Business', 'Formal'"
                    ),
                },
            ),
        ),
        types.FunctionDeclaration(
            name="search_catalog",
            description=(
                "Search the Vinted second-hand catalog for items to BUY. "
                "ONLY use this when the user explicitly asks to shop, buy, or discover "
                "new items — e.g. 'what should I buy', 'suggest new items', "
                "'what's missing from my wardrobe', 'find me a party dress'. "
                "Do NOT use this for general outfit recommendations (use search_wardrobe "
                "instead). Returns real catalog items with IDs, names, prices, and images."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "query": types.Schema(
                        type="STRING",
                        description="Search query, e.g. 'blue denim jacket', 'summer dress floral', 'white sneakers casual men'"
                    ),
                    "gender": types.Schema(
                        type="STRING",
                        description="Filter by gender: 'Men', 'Women', 'Boys', 'Girls', 'Unisex'"
                    ),
                    "max_price": types.Schema(
                        type="NUMBER",
                        description="Maximum price in EUR"
                    ),
                },
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_saved_outfits",
            description="Retrieve all saved outfit combinations from My Outfits. Use when the user asks about their saved looks or wants to revisit previous outfits.",
            parameters=types.Schema(
                type="OBJECT",
                properties={},
            ),
        ),
        types.FunctionDeclaration(
            name="save_outfit",
            description="Save an outfit combination that the user likes to My Outfits. Use when the user confirms they want to save a recommended outfit.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "name": types.Schema(
                        type="STRING",
                        description="A descriptive name for the outfit, e.g. 'Casual Friday', 'Summer Beach Day'"
                    ),
                    "item_ids": types.Schema(
                        type="ARRAY",
                        items=types.Schema(type="STRING"),
                        description="List of wardrobe item IDs to include in the outfit"
                    ),
                    "occasion": types.Schema(
                        type="STRING",
                        description="The occasion this outfit is for"
                    ),
                    "season": types.Schema(
                        type="STRING",
                        description="The season this outfit is best for"
                    ),
                },
                required=["name", "item_ids"],
            ),
        ),
    ]
)


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def _execute_tool(name: str, args: dict) -> dict:
    """Execute a tool call and return the result as a dict."""

    if name == "get_weather":
        forecast_days = int(args.get("forecast_days", 1))
        result = get_weather(args.get("city", "Barcelona"), forecast_days=forecast_days)
        if result:
            return result
        return {"error": f"Could not fetch weather for '{args.get('city')}'"}

    elif name == "search_wardrobe":
        items = search_items(
            category=args.get("category"),
            color=args.get("color"),
            occasion=args.get("occasion"),
            season=args.get("season"),
            formality=args.get("formality"),
        )
        # Tag each item for the UI
        for item in items:
            item["_source"] = "wardrobe"
        if items:
            return {"items": items, "count": len(items)}
        return {"items": [], "count": 0, "message": "No items found matching those filters in the wardrobe."}

    elif name == "search_catalog":
        try:
            df = pd.read_csv(CATALOG_PATH, on_bad_lines="skip")
            query = args.get("query", "").lower()
            query_terms = query.split()

            # Use AND logic: all terms must match somewhere in the row
            if query_terms:
                combined = (
                    df["productDisplayName"].fillna("").astype(str).str.lower() + " " +
                    df["articleType"].fillna("").astype(str).str.lower() + " " +
                    df["baseColour"].fillna("").astype(str).str.lower() + " " +
                    df["season"].fillna("").astype(str).str.lower() + " " +
                    df["usage"].fillna("").astype(str).str.lower() + " " +
                    df["gender"].fillna("").astype(str).str.lower()
                )
                mask = pd.Series([True] * len(df))
                for term in query_terms:
                    mask = mask & combined.str.contains(term, na=False)
            else:
                mask = pd.Series([True] * len(df))

            # Apply optional filters
            gender = args.get("gender", "")
            if gender:
                mask = mask & (df["gender"].fillna("").astype(str).str.lower() == gender.lower())
            max_price = args.get("max_price")
            if max_price:
                mask = mask & (df["price"] <= float(max_price))

            results = df[mask].head(8)
            items = []
            for _, row in results.iterrows():
                items.append({
                    "id": str(row["id"]),
                    "name": row["productDisplayName"],
                    "type": row["articleType"],
                    "color": row.get("baseColour", ""),
                    "price": row["price"],
                    "season": row.get("season", ""),
                    "occasion": row.get("usage", ""),
                    "gender": row.get("gender", ""),
                    "condition": row.get("condition", "Good"),
                    "image_path": f"data/images/{row['id']}.jpg",
                    "_source": "catalog",
                })
            return {"items": items, "count": len(items)}
        except Exception as e:
            return {"error": f"Catalog search failed: {str(e)}"}

    elif name == "get_saved_outfits":
        outfits = load_outfits()
        return {"outfits": outfits, "count": len(outfits)}

    elif name == "save_outfit":
        outfit = create_outfit(
            name=args.get("name", "Untitled Outfit"),
            item_ids=args.get("item_ids", []),
            occasion=args.get("occasion", "Casual"),
            season=args.get("season", "All"),
            source="assistant",
        )
        return {"success": True, "outfit": outfit}

    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Vinted Style AI, a friendly and knowledgeable fashion assistant integrated into the Vinted platform. You help users build outfits from their own wardrobe and discover new items to buy from the catalog.

You have access to these tools — use them proactively:
- get_weather: Check weather (current or multi-day forecast) for any city. Supports forecast_days for trips and future dates.
- search_wardrobe: Browse the user's personal wardrobe items (what they already own).
- search_catalog: Search the Vinted catalog for items to buy (second-hand marketplace).
- get_saved_outfits: View the user's saved outfit combinations in My Outfits.
- save_outfit: Save an outfit to My Outfits when the user wants to keep a recommendation.

User profile:
{profile_data}

CRITICAL RULES FOR TOOL USAGE:
1. WARDROBE FIRST: For any outfit recommendation, styling advice, or "what should I wear" question, ALWAYS call search_wardrobe FIRST. The default mode is styling from items the user ALREADY OWNS. Make multiple search_wardrobe calls with different filters if needed to find tops, bottoms, shoes, accessories separately.
2. CATALOG ONLY WHEN ASKED: Only call search_catalog when the user explicitly asks to buy, shop, discover new items, or when you identify specific gaps in their wardrobe. Phrases like "what should I buy", "suggest new items", "what's missing", "find me a [item]" trigger catalog search.
3. WEATHER FOR CONTEXT: Call get_weather when the user mentions today, a specific day, a trip, or a location. For trips or "next week", use forecast_days=7. For "tomorrow", use forecast_days=2. For other cities, pass that city name.
4. REAL ITEMS ONLY: NEVER invent or hallucinate items. Only recommend items that were returned from search_wardrobe or search_catalog tool results. Use the exact item names, IDs, and attributes from the tool results.
5. REFERENCE FORMAT: When you mention a specific item in your response, ALWAYS include a reference tag right after the item name:
   - For wardrobe items: [WARDROBE_ITEM:item_id]
   - For catalog items: [CATALOG_ITEM:item_id]
   The UI uses these to display item cards with images. Without these tags, no images will show.

OUTFIT BUILDING STRATEGY:
- Search the wardrobe multiple times with different category filters (e.g. one for tops, one for bottoms, one for shoes) to build a complete outfit
- Pick specific items from the results and explain WHY they work together
- Consider color harmony, occasion appropriateness, season, and weather
- If the wardrobe lacks a key piece, suggest searching the catalog for it

RESPONSE STYLE:
- Be conversational, warm, and enthusiastic about fashion
- Explain your reasoning: why items pair well, color theory, style cohesion
- When you recommend items, use their actual names from the tool results
- Offer to save the outfit if the user likes it"""


def build_system_prompt() -> str:
    """Build the system prompt with current user profile data."""
    profile_data = get_profile_summary()
    return SYSTEM_PROMPT.format(profile_data=profile_data)


# ---------------------------------------------------------------------------
# Chat function — the main entry point
# ---------------------------------------------------------------------------

def chat(
    user_message: str,
    chat_history: list,
    api_key: str,
) -> tuple[str, list, list]:
    """
    Process a user message through the Style Assistant.

    Args:
        user_message: The user's text message
        chat_history: List of previous messages (dicts with role/content)
        api_key: Gemini API key

    Returns:
        (assistant_response, updated_history, tool_results)
        - assistant_response: The text response to display
        - updated_history: The full chat history including this exchange
        - tool_results: List of tool call results with item data for inline rendering
    """
    client = genai.Client(api_key=api_key)

    system_prompt = build_system_prompt()

    # Build the contents list for Gemini
    contents = []

    # Add chat history
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])],
            )
        )

    # Add the new user message
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        )
    )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[TOOL_DECLARATIONS],
        temperature=0.7,
    )

    all_tool_results = []
    assistant_text = ""

    # Iterative tool calling loop (max 8 rounds for complex multi-tool chains)
    for _round in range(8):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )
        except Exception as e:
            error_msg = f"I'm having trouble connecting to my AI backend right now. Please try again in a moment. (Error: {str(e)[:100]})"
            return error_msg, chat_history, []

        # Parse all parts from the response
        function_call_parts = []
        text_parts = []

        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    function_call_parts.append(part)
                if part.text:
                    text_parts.append(part.text)

        # Collect any text produced in this round
        if text_parts:
            assistant_text = "\n".join(text_parts)

        if not function_call_parts:
            # No tool calls — we have the final response
            break

        # Execute tool calls and send results back
        contents.append(response.candidates[0].content)

        # Execute each function call
        function_response_parts = []
        for part in function_call_parts:
            fc = part.function_call
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}

            print(f"  [Tool Call] {tool_name}({tool_args})")
            result = _execute_tool(tool_name, tool_args)
            all_tool_results.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result,
            })

            function_response_parts.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response=result,
                )
            )

        # Add function responses back to the conversation
        contents.append(
            types.Content(
                role="user",
                parts=function_response_parts,
            )
        )

    # If no text was collected at all, provide a fallback
    if not assistant_text.strip():
        assistant_text = "I searched through your wardrobe and the catalog but couldn't put together a complete response. Could you try rephrasing your request?"

    # Update chat history
    updated_history = chat_history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_text},
    ]

    return assistant_text, updated_history, all_tool_results


def parse_item_references(text: str) -> list:
    """
    Parse item references from assistant response text.
    Returns list of dicts with source ('wardrobe' or 'catalog') and item_id.
    """
    import re
    refs = []
    # Match [WARDROBE_ITEM:id] and [CATALOG_ITEM:id]
    pattern = r'\[(WARDROBE_ITEM|CATALOG_ITEM):([^\]]+)\]'
    for match in re.finditer(pattern, text):
        source = "wardrobe" if match.group(1) == "WARDROBE_ITEM" else "catalog"
        refs.append({"source": source, "id": match.group(2).strip()})
    return refs


def clean_response_text(text: str) -> str:
    """Remove item reference markers from the response text for clean display."""
    import re
    return re.sub(r'\s*\[(WARDROBE_ITEM|CATALOG_ITEM):[^\]]+\]', '', text)
