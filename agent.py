"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── query parser ──────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Parse a natural language query to extract description, size, and max_price.

    Strategy: regex patterns to pull out size and price, then use the
    remaining text as the description.

    Examples:
        "vintage tee under $30 size M"
        → {"description": "vintage tee", "size": "M", "max_price": 30.0}

        "looking for a denim jacket"
        → {"description": "denim jacket", "size": None, "max_price": None}
    """
    query_lower = query.lower()

    # Extract max_price — matches patterns like "under $30", "$30", "30 dollars"
    max_price = None
    price_match = re.search(r"\$(\d+(?:\.\d+)?)|under\s+\$?(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s+dollars", query_lower)
    if price_match:
        # Get whichever group matched
        raw = price_match.group(1) or price_match.group(2) or price_match.group(3)
        max_price = float(raw)

    # Extract size — matches patterns like "size M", "size XL", "in a medium"
    size = None
    size_match = re.search(
        r"\bsize\s+([a-z0-9/]+)\b|"
        r"\bin\s+(?:a\s+)?(?:size\s+)?([a-z0-9/]+)\b|"
        r"\b(xxs|xs|s\b|m\b|l\b|xl|xxl|2xl|3xl|w\d+|us\s?\d+(?:\.\d+)?)",
        query_lower
    )
    if size_match:
        raw_size = size_match.group(1) or size_match.group(2) or size_match.group(3)
        if raw_size:
            size = raw_size.strip().upper()

    # Build description by removing price and size fragments from query
    description = query_lower
    description = re.sub(r"(under\s+)?\$\d+(?:\.\d+)?", "", description)
    description = re.sub(r"\d+(?:\.\d+)?\s+dollars", "", description)
    description = re.sub(r"\bsize\s+[a-z0-9/]+\b", "", description)
    description = re.sub(r"\bin\s+(?:a\s+)?(?:size\s+)?[a-z0-9/]+\b", "", description)
    description = re.sub(r"\b(xxs|xs|xl|xxl|2xl|3xl)\b", "", description)

    # Clean up filler words
    filler = r"\b(looking for|i want|i need|find me|got any|got|any|a|an|the|some|im|i'm|please|help|me)\b"
    description = re.sub(filler, "", description)
    description = re.sub(r"\s+", " ", description).strip()

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """

    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse the query
    parsed = _parse_query(query)
    session["parsed"] = parsed

    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]

    # Step 3: Search for listings
    results = search_listings(description, size=size, max_price=max_price)
    session["search_results"] = results

    # If no results — set error and return early (do NOT call suggest_outfit)
    if not results:
        session["error"] = (
            "No listings found matching your search. "
            "Try adjusting your description, removing the size filter, "
            "or increasing your budget."
        )
        return session

    # Step 4: Select the top result
    session["selected_item"] = results[0]

    # Step 5: Suggest an outfit
    outfit_suggestion = suggest_outfit(session["selected_item"], wardrobe)
    session["outfit_suggestion"] = outfit_suggestion

    # Step 6: Create the fit card
    fit_card = create_fit_card(outfit_suggestion, session["selected_item"])
    session["fit_card"] = fit_card

    # Step 7: Return completed session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: vintage tee ===\n")
    session = run_agent(
        query="looking for a vintage tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")