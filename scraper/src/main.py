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
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

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
    # e.g., https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html -> a-light-in-the-attic_1000
    if parts[-1].endswith(".html"):
        slug = parts[-2]
    else:
        slug = parts[-1]
    # sanitize
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", slug)

def discover_catalogue_pages(start_url: str, max_pages: int = 3) -> tuple[int, list[dict]]:
    """
    Traverse catalogue pages following the 'next' link up to max_pages.
    Returns: (catalogue_page_count, list_of_discovered_items)
    where item is {"product_url": ..., "source_page": ...}
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

        # Collect book links from article.product_pod
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

        # Follow next link
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

    # Capture timestamp before/during fetch
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    html, was_cached, _ = fetch_page(product_url, cache_filename)

    soup = BeautifulSoup(html, "html.parser")

    # Aim selectors at product area: article.product_page
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
            price_text = price_tag.get_text(strip=True)

        avail_tag = product_main.select_one("p.instock.availability")
        if avail_tag:
            # Normalize internal whitespace while keeping text intact
            availability_text = " ".join(avail_tag.get_text().split())

        star_tag = product_main.select_one("p.star-rating")
        if star_tag:
            classes = star_tag.get("class", [])
            rating_classes = [c for c in classes if c != "star-rating"]
            if rating_classes:
                rating_text = rating_classes[0]

    # Description from #product_description + p
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

def main():
    print("Stage 3: Extract book details")
    cat_pages, discovered_items = discover_catalogue_pages(START_URL, MAX_CATALOGUE_PAGES)
    print(f"catalogue_pages={cat_pages} , discovered={len(discovered_items)}")

    raw_records = []
    for item in discovered_items:
        record = extract_raw_book_record(item["product_url"], item["source_page"])
        raw_records.append(record)

    # CHECKPOINT: print one complete raw record and summary detail_pages=60
    print("\n--- SAMPLE RAW RECORD ---")
    print(json.dumps(raw_records[0], indent=2))
    print(f"\ndetail_pages={len(raw_records)}")

if __name__ == "__main__":
    main()
