"""
image_processor.py
------------------
Image processing pipeline:
1. Background removal using rembg (local open-source model)
2. Clothing attribute extraction using Gemini Vision

The auto-tagging returns structured JSON with type, color, pattern,
material, season, occasion, formality, and gender.
"""

import os
import json
import base64
import io
import traceback

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
WARDROBE_IMAGES_DIR = os.path.join(DATA_DIR, "wardrobe_images")

# Lazy-loaded rembg session to avoid slow imports at startup
_rembg_session = None


def _get_rembg_session():
    """Lazily initialize rembg to avoid slow cold start."""
    global _rembg_session
    if _rembg_session is None:
        try:
            from rembg import new_session
            _rembg_session = new_session("u2net")
        except ImportError:
            print("rembg not installed. Background removal will be skipped.")
            return None
        except Exception as e:
            print(f"rembg init error: {e}")
            return None
    return _rembg_session


def remove_background(image_bytes: bytes) -> bytes | None:
    """
    Remove background from a clothing image.
    Returns PNG bytes with transparent background, or None on failure.
    """
    try:
        from rembg import remove
        session = _get_rembg_session()
        if session is None:
            return None
        result = remove(image_bytes, session=session)
        return result
    except Exception as e:
        print(f"Background removal error: {e}")
        traceback.print_exc()
        return None


def save_wardrobe_image(image_bytes: bytes, filename: str) -> str:
    """Save processed image to wardrobe_images/ and return the filename."""
    os.makedirs(WARDROBE_IMAGES_DIR, exist_ok=True)
    filepath = os.path.join(WARDROBE_IMAGES_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    return filename


def auto_tag_image(image_bytes: bytes, api_key: str) -> dict | None:
    """
    Use Gemini Vision to analyze a clothing image and extract structured attributes.
    Returns a dict with type, color, pattern, material, season, occasion,
    formality, and gender. Returns None on failure.
    """
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = """Analyze this clothing item image and return a JSON object with these exact keys:
{
  "type": "<clothing type, e.g. T-Shirt, Jeans, Sneakers, Blazer, Dress, Hoodie, Jacket, Skirt, Shorts, Sweater, Boots, Sandals, Bag, Watch, Sunglasses, Scarf, Hat>",
  "color": "<primary color, e.g. Navy Blue, Black, White, Red, Beige, Grey, Brown, Green, Pink, Multi>",
  "pattern": "<pattern, one of: Solid, Striped, Plaid, Floral, Graphic, Abstract, Polka Dot, Animal Print, Camouflage, Color Block>",
  "material": "<material, e.g. Cotton, Denim, Leather, Polyester, Wool, Silk, Linen, Suede, Canvas, Knit>",
  "season": ["<applicable seasons from: Spring, Summer, Fall, Winter>"],
  "occasion": ["<applicable occasions from: Casual, Formal, Smart Casual, Business, Party, Sports, Travel>"],
  "formality": "<one of: Casual, Smart Casual, Business, Formal>",
  "gender": "<one of: Men, Women, Unisex>"
}

Return ONLY the JSON object, no markdown, no explanation."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    ],
                )
            ],
        )

        text = response.text.strip()
        # Clean up markdown code blocks if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        result = json.loads(text)
        return result

    except json.JSONDecodeError as e:
        print(f"Failed to parse Gemini Vision response as JSON: {e}")
        return None
    except Exception as e:
        print(f"Gemini Vision error: {e}")
        traceback.print_exc()
        return None


def analyze_image_for_chat(image_bytes: bytes, api_key: str) -> dict | None:
    """
    Analyze an image uploaded in the chat context.
    Same as auto_tag_image but returns additional descriptive text.
    """
    return auto_tag_image(image_bytes, api_key)


if __name__ == "__main__":
    print("Image processor module loaded.")
    print(f"Wardrobe images dir: {WARDROBE_IMAGES_DIR}")
    print(f"rembg available: {_get_rembg_session() is not None}")
