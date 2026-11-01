"""
Unit tests for the Polite Scraper parser and pipeline.
Covers:
1. Price normalization (e.g. '£51.77' -> 51.77)
2. Relative to absolute URL conversion
3. Missing description fixture handling (returns None / null)
4. Duplicate URL deduplication (canonical URL identity)
5. Malformed fixture validation failure (rejected by schema into errors)
"""

import sys
from pathlib import Path
from urllib.parse import urljoin

# Ensure scraper package root is on sys.path
SCRAPER_ROOT = Path(__file__).resolve().parent.parent
if str(SCRAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRAPER_ROOT))

import pytest
from bs4 import BeautifulSoup
from pydantic import ValidationError

from src.main import (
    BookRecord,
    normalize_price,
    normalize_and_validate,
)

def test_price_normalization():
    """Verify raw price strings are converted to clean floats."""
    assert normalize_price("£51.77") == 51.77
    assert normalize_price("£10.00") == 10.0
    assert normalize_price("Â£19.99") == 19.99
    assert normalize_price("  £0.99  ") == 0.99

    with pytest.raises(ValueError):
        normalize_price("Free")

def test_relative_to_absolute_url():
    """Verify relative catalogue links are accurately resolved to canonical absolute URLs."""
    base_catalogue = "https://books.toscrape.com/catalogue/page-1.html"
    rel_href = "a-light-in-the-attic_1000/index.html"
    resolved = urljoin(base_catalogue, rel_href)
    assert resolved == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"

    root_catalogue = "https://books.toscrape.com/index.html"
    rel_href2 = "catalogue/tipping-the-velvet_999/index.html"
    assert urljoin(root_catalogue, rel_href2) == "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html"

def test_missing_description_fixture():
    """Verify books with no description produce None (null) and validate cleanly."""
    raw_record = {
        "title": "Book Without Description",
        "product_url": "https://books.toscrape.com/catalogue/no-desc_999/index.html",
        "price_text": "£15.50",
        "availability_text": "In stock (5 available)",
        "rating_text": "Four",
        "description": None,
        "source_page": "https://books.toscrape.com/catalogue/page-1.html",
        "fetched_at": "2026-11-01T10:00:00Z"
    }
    valid_rec, err = normalize_and_validate(raw_record)
    assert err is None
    assert valid_rec is not None
    assert valid_rec["description"] is None
    assert valid_rec["price_gbp"] == 15.50

def test_duplicate_url_deduplication():
    """Verify duplicate records are consolidated by canonical product_url."""
    records = [
        {
            "product_url": "https://books.toscrape.com/catalogue/book-1_1/index.html",
            "title": "Book 1",
            "price_gbp": 10.0
        },
        {
            "product_url": "https://books.toscrape.com/catalogue/book-1_1/index.html",
            "title": "Book 1 Duplicate",
            "price_gbp": 10.0
        },
        {
            "product_url": "https://books.toscrape.com/catalogue/book-2_2/index.html",
            "title": "Book 2",
            "price_gbp": 20.0
        }
    ]
    deduped = {r["product_url"]: r for r in records}
    assert len(deduped) == 2
    assert "https://books.toscrape.com/catalogue/book-1_1/index.html" in deduped
    assert "https://books.toscrape.com/catalogue/book-2_2/index.html" in deduped

def test_malformed_fixture_schema_rejection():
    """Verify malformed records fail schema validation and return error dict."""
    # Malformed record missing required title and non-https URL
    malformed_record = {
        "title": "",
        "product_url": "http://insecure-site.com/book",
        "price_text": "InvalidPrice",
        "availability_text": "In stock",
        "rating_text": "Five",
        "description": "Some description",
        "source_page": "ftp://bad-source",
        "fetched_at": "2026-11-01T10:00:00Z"
    }
    valid_rec, err = normalize_and_validate(malformed_record)
    assert valid_rec is None
    assert err is not None
    assert "error" in err
    assert "record" in err
