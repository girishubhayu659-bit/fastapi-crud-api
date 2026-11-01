"""
The Polite Scraper - FlyRank Internship Week 5 (Assignment A9)
Pipeline: fetch -> extract -> normalize -> validate -> store -> report
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ValidationError, field_validator

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"

# Configuration
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/girishubhayu659-bit/fastapi-crud-api)"
REQUEST_TIMEOUT = 10.0
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
MAX_CATALOGUE_PAGES = 3
POLITE_DELAY_SECONDS = 0.5

class BookRecord(BaseModel):
    """Pydantic schema for validated, normalized book records."""
    title: str = Field(..., min_length=1, description="Book title")
    product_url: str = Field(..., description="Canonical absolute product URL")
    price_text: str = Field(..., min_length=1, description="Raw price string including currency")
    price_gbp: float = Field(..., ge=0.0, description="Clean numeric price in GBP")
    availability_text: str = Field(..., min_length=1, description="Raw stock availability string")
    rating_text: str = Field(..., min_length=1, description="Star rating string")
    description: Optional[str] = Field(None, description="Book description text or null")
    source_page: str = Field(..., description="Provenance catalogue page URL")
    fetched_at: str = Field(..., description="Provenance ISO 8601 UTC timestamp")

    @field_validator("product_url", "source_page")
    @classmethod
    def validate_https_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError(f"URL must start with https://, got: {v}")
        return v

def fetch_page(url: str, cache_filename: str) -> tuple[str, bool, int]:
    """
    Fetch a page politely with timeout and user-agent.
    Saves HTML to cache/ if not already cached.
    Cached pages need no delay. Real requests wait at least 0.5s.
    Returns: (html_content, was_cached, byte_size)
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        byte_size = cache_path.stat().st_size
        return html, True, byte_size

    # Polite delay for real network request
    time.sleep(POLITE_DELAY_SECONDS)

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

    if response.status_code != 200:
        raise RuntimeError(f"Fetch failed for {url} with status code {response.status_code}")

    html = response.text
    cache_path.write_text(html, encoding="utf-8")
    byte_size = len(response.content)
    return html, False, byte_size

def get_book_slug(product_url: str) -> str:
    """Generate safe cache filename slug from product url."""
    parts = product_url.rstrip("/").split("/")
    if parts[-1].endswith(".html"):
        slug = parts[-2]
    else:
        slug = parts[-1]
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", slug)

def normalize_price(price_text: str) -> float:
    """Extract clean float value from currency string (e.g. '£51.77' -> 51.77)."""
    match = re.search(r"(\d+(?:\.\d+)?)", price_text)
    if not match:
        raise ValueError(f"Could not extract numeric price from: {price_text}")
    return float(match.group(1))

def discover_catalogue_pages(start_url: str, max_pages: int = 3) -> tuple[int, list[dict]]:
    """
    Traverse catalogue pages following the 'next' link up to max_pages.
    Returns: (catalogue_page_count, list_of_discovered_items)
    """
    current_url = start_url
    pages_processed = 0
    discovered_items: list[dict] = []
    seen_urls = set()

    while current_url and pages_processed < max_pages:
        pages_processed += 1
        cache_filename = f"catalogue-page-{pages_processed}.html"
        html, was_cached, size = fetch_page(current_url, cache_filename)

        soup = BeautifulSoup(html, "html.parser")

        pods = soup.select("article.product_pod h3 a")
        for pod in pods:
            href = pod.get("href")
            if href:
                absolute_url = urljoin(current_url, href)
                if absolute_url not in seen_urls:
                    seen_urls.add(absolute_url)
                    discovered_items.append({
                        "product_url": absolute_url,
                        "source_page": current_url
                    })

        next_li = soup.select_one("li.next a")
        if next_li and pages_processed < max_pages:
            next_href = next_li.get("href")
            current_url = urljoin(current_url, next_href)
        else:
            current_url = None

    return pages_processed, discovered_items

def extract_raw_book_record(product_url: str, source_page: str) -> dict:
    """
    Fetch detail page politely, cache it, and extract raw record with 8 required fields.
    """
    slug = get_book_slug(product_url)
    cache_filename = f"book-{slug}.html"

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    html, was_cached, _ = fetch_page(product_url, cache_filename)

    soup = BeautifulSoup(html, "html.parser")

    product_main = soup.select_one("article.product_page .product_main")
    if not product_main:
        product_main = soup.select_one(".product_main")

    title = None
    price_text = None
    availability_text = None
    rating_text = None

    if product_main:
        h1 = product_main.select_one("h1")
        if h1:
            title = h1.get_text(strip=True)

        price_tag = product_main.select_one("p.price_color")
        if price_tag:
            raw_p = price_tag.get_text(strip=True)
            # Remove mojibake UTF-8 artifact Â if present
            price_text = raw_p.replace("\u00c2", "").replace("Â", "")

        avail_tag = product_main.select_one("p.instock.availability")
        if avail_tag:
            availability_text = " ".join(avail_tag.get_text().split())

        star_tag = product_main.select_one("p.star-rating")
        if star_tag:
            classes = star_tag.get("class", [])
            rating_classes = [c for c in classes if c != "star-rating"]
            if rating_classes:
                rating_text = rating_classes[0]

    description = None
    desc_header = soup.select_one("#product_description")
    if desc_header:
        desc_sibling = desc_header.find_next_sibling("p")
        if desc_sibling:
            desc_text = desc_sibling.get_text(strip=True)
            description = desc_text if desc_text else None

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }

def normalize_and_validate(raw_record: dict) -> tuple[Optional[dict], Optional[dict]]:
    """
    Normalize raw record and validate against BookRecord schema.
    Returns: (valid_dict, None) or (None, error_dict)
    """
    try:
        # Normalize price_text -> price_gbp
        price_gbp = normalize_price(raw_record.get("price_text", ""))
        normalized = dict(raw_record)
        normalized["price_gbp"] = price_gbp

        # Validate with Pydantic
        record = BookRecord(**normalized)
        return record.model_dump(), None
    except Exception as exc:
        error_info = {
            "record": raw_record,
            "error": str(exc),
            "failed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        return None, error_info

def save_records(records: list[dict], errors: list[dict]):
    """
    Save validated records to output/books.json and errors to output/errors.json idempotently.
    Deduplicates by canonical product_url.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Deduplicate by canonical product_url
    deduped_records = {}
    for r in records:
        deduped_records[r["product_url"]] = r
    final_records = list(deduped_records.values())

    books_path = OUTPUT_DIR / "books.json"
    books_path.write_text(json.dumps(final_records, indent=2, ensure_ascii=False), encoding="utf-8")

    errors_path = OUTPUT_DIR / "errors.json"
    errors_path.write_text(json.dumps(errors, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    print("Stage 4: Clean it, check it, store it")
    cat_pages, discovered_items = discover_catalogue_pages(START_URL, MAX_CATALOGUE_PAGES)

    valid_records: list[dict] = []
    error_records: list[dict] = []

    for item in discovered_items:
        raw_record = extract_raw_book_record(item["product_url"], item["source_page"])
        valid_rec, err = normalize_and_validate(raw_record)
        if valid_rec:
            valid_records.append(valid_rec)
        else:
            error_records.append(err)

    save_records(valid_records, error_records)

    # Load stored books.json to verify idempotency and types
    saved = json.loads((OUTPUT_DIR / "books.json").read_text(encoding="utf-8"))
    count = len(saved)
    all_prices_numeric = all(isinstance(r["price_gbp"], (int, float)) for r in saved)
    all_urls_https = all(r["product_url"].startswith("https://") for r in saved)

    print(f"records_stored={count}")
    print(f"all_prices_numeric={all_prices_numeric}")
    print(f"all_urls_https={all_urls_https}")

if __name__ == "__main__":
    main()
