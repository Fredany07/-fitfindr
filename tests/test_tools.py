# tests/test_tools.py

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings tests ─────────────────────────────────────────────────────

def test_search_returns_results():
    """A broad search should return at least one result."""
    results = search_listings("vintage tee", max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_returns_dicts_with_expected_fields():
    """Every result should have the required fields."""
    results = search_listings("jacket", max_price=100)
    for item in results:
        for field in ["id", "title", "price", "size", "platform"]:
            assert field in item, f"Missing field: {field}"

def test_search_empty_results():
    """An impossible query should return an empty list, not crash."""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    """No result should exceed max_price."""
    results = search_listings("jacket", max_price=20)
    assert all(item["price"] <= 20 for item in results)

def test_search_size_filter():
    """All results should contain the requested size (case-insensitive)."""
    results = search_listings("vintage", size="M", max_price=100)
    for item in results:
        assert "m" in item["size"].lower()

def test_search_sorted_by_relevance():
    """Results should be a list sorted by score."""
    results = search_listings("vintage denim", max_price=100)
    assert isinstance(results, list)


# ── suggest_outfit tests ──────────────────────────────────────────────────────

def test_suggest_outfit_returns_string():
    """suggest_outfit should return a non-empty string."""
    results = search_listings("vintage tee", max_price=50)
    assert len(results) > 0, "Need at least one search result to test suggest_outfit"
    output = suggest_outfit(results[0], get_example_wardrobe())
    assert isinstance(output, str)
    assert len(output) > 0

def test_suggest_outfit_empty_wardrobe():
    """Empty wardrobe should return general advice, not crash."""
    results = search_listings("vintage tee", max_price=50)
    assert len(results) > 0
    output = suggest_outfit(results[0], get_empty_wardrobe())
    assert isinstance(output, str)
    assert len(output) > 0


# ── create_fit_card tests ─────────────────────────────────────────────────────

def test_create_fit_card_returns_string():
    """create_fit_card should return a non-empty string for valid input."""
    results = search_listings("vintage tee", max_price=50)
    assert len(results) > 0
    outfit = suggest_outfit(results[0], get_example_wardrobe())
    card = create_fit_card(outfit, results[0])
    assert isinstance(card, str)
    assert len(card) > 0

def test_create_fit_card_empty_outfit():
    """Empty outfit string should return an error message, not crash."""
    results = search_listings("vintage tee", max_price=50)
    assert len(results) > 0
    card = create_fit_card("", results[0])
    assert isinstance(card, str)
    assert "Could not generate fit card" in card

def test_create_fit_card_whitespace_outfit():
    """Whitespace-only outfit string should also return the error message."""
    results = search_listings("vintage tee", max_price=50)
    assert len(results) > 0
    card = create_fit_card("   ", results[0])
    assert isinstance(card, str)
    assert "Could not generate fit card" in card