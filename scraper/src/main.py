"""
The Polite Scraper - FlyRank Internship Week 5 (Assignment A9)
Pipeline: fetch -> extract -> normalize -> validate -> store -> report
"""

import os
import sys
import time
from pathlib import Path
from urllib.parse import urljoin
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

def discover_catalogue_pages(start_url: str, max_pages: int = 3) -> tuple[int, list[tuple[str, str]], list[str]]:
    """
    Traverse catalogue pages following the 'next' link up to max_pages.
    Returns: (catalogue_page_count, discovered_book_items, unique_book_urls)
    """
    current_url = start_url
    pages_processed = 0
    all_discovered_links: list[tuple[str, str]] = [] # (book_url, source_page)

    while current_url and pages_processed < max_pages:
        pages_processed += 1
        cache_filename = f"catalogue-page-{pages_processed}.html"
        html, was_cached, size = fetch_page(current_url, cache_filename)

        if was_cached:
            print(f"CACHE HIT: {cache_filename} ({size} bytes)")
        else:
            print(f"FETCH: {current_url} -> {cache_filename} ({size} bytes)")

        soup = BeautifulSoup(html, "html.parser")

        # Collect book links from article.product_pod
        pods = soup.select("article.product_pod h3 a")
        for pod in pods:
            href = pod.get("href")
            if href:
                absolute_url = urljoin(current_url, href)
                all_discovered_links.append((absolute_url, current_url))

        # Check for next page link
        next_li = soup.select_one("li.next a")
        if next_li and pages_processed < max_pages:
            next_href = next_li.get("href")
            current_url = urljoin(current_url, next_href)
        else:
            current_url = None

    # Deduplicate preserving order
    unique_urls = list(dict.fromkeys(url for url, _ in all_discovered_links))
    return pages_processed, all_discovered_links, unique_urls

def main():
    print("Stage 2: Discover three catalogue pages")
    cat_pages, discovered_items, unique_urls = discover_catalogue_pages(START_URL, MAX_CATALOGUE_PAGES)
    print(f"catalogue_pages={cat_pages} , discovered={len(discovered_items)} , unique_urls={len(unique_urls)}")

if __name__ == "__main__":
    main()
