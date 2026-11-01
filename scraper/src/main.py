"""
The Polite Scraper - FlyRank Internship Week 5 (Assignment A9)
Pipeline: fetch -> extract -> normalize -> validate -> store -> report
"""

import os
import sys
import time
from pathlib import Path
import requests

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"

# Configuration
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/girishubhayu659-bit/fastapi-crud-api)"
REQUEST_TIMEOUT = 10.0
BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"

def fetch_page(url: str, cache_filename: str) -> tuple[str, bool, int]:
    """
    Fetch a page politely with timeout and user-agent.
    Saves HTML to cache/ if not already cached.
    Returns: (html_content, was_cached, byte_size)
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    # If already cached, read from disk
    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        byte_size = cache_path.stat().st_size
        return html, True, byte_size

    # Polite fetch
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

    # Check status code strictly
    if response.status_code != 200:
        raise RuntimeError(f"Fetch failed for {url} with status code {response.status_code}")

    html = response.text
    cache_path.write_text(html, encoding="utf-8")
    byte_size = len(response.content)
    return html, False, byte_size

def main():
    print("Stage 1: Fetch and cache HTML")
    url = BASE_URL
    cache_file = "catalogue-page-1.html"

    html, was_cached, size = fetch_page(url, cache_file)
    if was_cached:
        print(f"CACHE HIT: {cache_file} ({size} bytes)")
    else:
        print(f"FETCH: {url} -> {cache_file} ({size} bytes)")

if __name__ == "__main__":
    main()
