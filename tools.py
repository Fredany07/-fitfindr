"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.
    """
    listings = load_listings()

    # Step 1: Filter by price
    if max_price is not None:
        listings = [item for item in listings if item["price"] <= max_price]

    # Step 2: Filter by size (case-insensitive, partial match)
    if size is not None:
        size_lower = size.lower()
        listings = [
            item for item in listings
            if size_lower in item["size"].lower()
        ]

    # Step 3: Score each listing by keyword overlap with description
    keywords = description.lower().split()

    def score(item):
        # Build a blob of all text fields to search against
        searchable = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("category", ""),
            item.get("brand", "") or "",
            " ".join(item.get("style_tags", [])),
            " ".join(item.get("colors", [])),
        ]).lower()

        return sum(1 for keyword in keywords if keyword in searchable)

    # Step 4: Score and drop zero-match listings
    scored = [(item, score(item)) for item in listings]
    scored = [(item, s) for item, s in scored if s > 0]

    # Step 5: Sort by score descending and return just the dicts
    scored.sort(key=lambda x: x[1], reverse=True)
    print("DEBUG scored:", len(scored))
    return [item for item, _ in scored]



# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.
    """
    client = _get_groq_client()

    item_summary = (
        f"Item: {new_item.get('title', 'Unknown item')}\n"
        f"Category: {new_item.get('category', 'unknown')}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Condition: {new_item.get('condition', 'unknown')}\n"
        f"Price: ${new_item.get('price', '?')}\n"
        f"Platform: {new_item.get('platform', 'unknown')}"
    )

    wardrobe_items = wardrobe.get("items", [])

    # Step 1: Check if wardrobe is empty
    if not wardrobe_items:
        prompt = (
            f"A user is considering buying this secondhand item:\n\n"
            f"{item_summary}\n\n"
            f"They haven't provided their wardrobe yet. Give them 1–2 general "
            f"outfit ideas — what types of pieces pair well with this item, "
            f"what vibe or aesthetic it suits, and how to style it. "
            f"Keep it specific and practical, not generic."
        )
    else:
        # Step 2: Format wardrobe items into a readable list
        wardrobe_text = "\n".join(
            f"- {w.get('name', 'item')} ({w.get('category', '')})"
            f"{', colors: ' + ', '.join(w.get('colors', [])) if w.get('colors') else ''}"
            for w in wardrobe_items
        )

        prompt = (
            f"A user is considering buying this secondhand item:\n\n"
            f"{item_summary}\n\n"
            f"Their current wardrobe includes:\n{wardrobe_text}\n\n"
            f"Suggest 1–2 complete outfit combinations using the new item "
            f"and specific pieces from their wardrobe. Name the exact wardrobe "
            f"pieces in each suggestion. Include a brief styling tip for each outfit."
        )

    # Step 3: Call the LLM
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a stylish, friendly personal stylist who specializes "
                    "in thrift and secondhand fashion. Your suggestions are specific, "
                    "practical, and feel like advice from a knowledgeable friend — "
                    "not a generic fashion magazine."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=400,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.
    """
    # Step 1: Guard against empty outfit
    if not outfit or not outfit.strip():
        return (
            "Could not generate fit card — outfit description was missing. "
            "Please try your search again."
        )

    title = new_item.get("title", "this thrifted piece")
    price = new_item.get("price", "?")
    platform = new_item.get("platform", "a thrift app")

    prompt = (
        f"Write a casual, authentic Instagram/TikTok caption for this thrifted outfit.\n\n"
        f"Thrifted item: {title} — ${price} from {platform}\n"
        f"Outfit: {outfit}\n\n"
        f"Rules:\n"
        f"- 2 to 4 sentences max\n"
        f"- Sound like a real person posting an OOTD, not a brand\n"
        f"- Mention the item name, price, and platform naturally (once each)\n"
        f"- Capture the outfit vibe in specific terms\n"
        f"- Use 1–2 relevant emojis\n"
        f"- Do NOT use hashtags"
    )

    client = _get_groq_client()

    # Step 2: Call LLM with higher temperature for variety
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write short, authentic social media captions for thrift fashion. "
                    "Your tone is casual, confident, and specific — never generic or salesy."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=150,
        temperature=1.0,
    )

    return response.choices[0].message.content.strip()
