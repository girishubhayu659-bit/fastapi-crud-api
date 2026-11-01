"""
The Polite Scraper - FlyRank Internship Week 5 (Assignment A9)
Pipeline: fetch -> extract -> normalize -> validate -> store -> report
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
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
FAKE_TEST_URL = "https://books.toscrape.com/catalogue/fake-broken-book-9999/index.html"

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

def fetch_page_with_retry(url: str, cache_filename: str) -> tuple[Optional[str], bool, int, Optional[str]]:
    """
    Fetch a page politely with cache support and retry on 5xx/timeout.
    Does NOT retry 404 (not found) or 403 (forbidden).
    Returns: (html_content, was_cached, byte_size, error_message)
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        byte_size = cache_path.stat().st_size
        return html, True, byte_size, None

    headers = {"User-Agent": USER_AGENT}
    max_attempts = 2  # 1 initial try + 1 retry for transient 5xx/timeouts

    for attempt in range(1, max_attempts + 1):
        try:
            time.sleep(POLITE_DELAY_SECONDS)
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            status = response.status_code

            if status == 200:
                html = response.text
                cache_path.write_text(html, encoding="utf-8")
                return html, False, len(response.content), None

            # Polite rule: Do NOT retry 404 or 403
            if status in (403, 404):
                return None, False, 0, f"HTTP {status} (Not retried per politeness rules)"

            # Retry transient 5xx server errors once
            if status >= 500:
                if attempt < max_attempts:
                    time.sleep(1.0)
                    continue
                return None, False, 0, f"HTTP {status} Server Error"

            return None, False, 0, f"HTTP {status} Unexpected response"

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            if attempt < max_attempts:
                time.sleep(1.0)
                continue
            return None, False, 0, f"Network error: {exc}"
        except Exception as exc:
            return None, False, 0, f"Unexpected error: {exc}"

    return None, False, 0, "Max attempts reached"

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

def discover_catalogue_pages(start_url: str, max_pages: int = 3) -> tuple[int, list[dict], int, int]:
    """
    Traverse catalogue pages following the 'next' link up to max_pages.
    Returns: (catalogue_page_count, discovered_items, network_fetches, cache_hits)
    """
    current_url = start_url
    pages_processed = 0
    discovered_items: list[dict] = []
    seen_urls = set()
    cat_fetches = 0
    cat_cache_hits = 0

    while current_url and pages_processed < max_pages:
        pages_processed += 1
        cache_filename = f"catalogue-page-{pages_processed}.html"
        html, was_cached, _, err = fetch_page_with_retry(current_url, cache_filename)

        if was_cached:
            cat_cache_hits += 1
        else:
            cat_fetches += 1

        if not html:
            break

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

    return pages_processed, discovered_items, cat_fetches, cat_cache_hits

def extract_raw_book_record(product_url: str, source_page: str) -> tuple[Optional[dict], bool, Optional[str]]:
    """
    Fetch detail page politely, cache it, and extract raw record with 8 required fields.
    Returns: (raw_dict_or_None, was_cached, error_or_None)
    """
    slug = get_book_slug(product_url)
    cache_filename = f"book-{slug}.html"

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    html, was_cached, _, err = fetch_page_with_retry(product_url, cache_filename)

    if not html:
        return None, was_cached, err

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

    raw_record = {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }
    return raw_record, was_cached, None

def normalize_and_validate(raw_record: dict) -> tuple[Optional[dict], Optional[dict]]:
    """
    Normalize raw record and validate against BookRecord schema.
    Returns: (valid_dict, None) or (None, error_dict)
    """
    try:
        price_gbp = normalize_price(raw_record.get("price_text", ""))
        normalized = dict(raw_record)
        normalized["price_gbp"] = price_gbp

        record = BookRecord(**normalized)
        return record.model_dump(), None
    except Exception as exc:
        error_info = {
            "record": raw_record,
            "error": str(exc),
            "failed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        return None, error_info

def export_csv(records: list[dict], csv_path: Path):
    """
    Export validated records to CSV with flattened fields.
    """
    if not records:
        return
    fieldnames = [
        "title",
        "product_url",
        "price_text",
        "price_gbp",
        "availability_text",
        "rating_text",
        "description",
        "source_page",
        "fetched_at"
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            row = dict(rec)
            # Flatten None/null to empty string for clean CSV representation
            if row.get("description") is None:
                row["description"] = ""
            writer.writerow(row)

def run_scraper(inject_fake_url: bool = False) -> dict:
    """
    Run the full scraping pipeline, save JSON, CSV, errors, and run report.
    """
    start_time_dt = datetime.now(timezone.utc)
    start_time_iso = start_time_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    t0 = time.time()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cat_pages, discovered_items, cat_fetches, cat_cache_hits = discover_catalogue_pages(START_URL, MAX_CATALOGUE_PAGES)

    if inject_fake_url:
        print(f"[TEST] Injecting deliberately broken book URL: {FAKE_TEST_URL}")
        discovered_items.append({
            "product_url": FAKE_TEST_URL,
            "source_page": START_URL
        })

    valid_records: list[dict] = []
    error_records: list[dict] = []
    failed_pages = 0
    pages_fetched = cat_fetches
    cache_hits = cat_cache_hits

    for item in discovered_items:
        raw_record, was_cached, fetch_err = extract_raw_book_record(item["product_url"], item["source_page"])

        if was_cached:
            cache_hits += 1
        else:
            pages_fetched += 1

        if fetch_err:
            print(f"[SKIP] Failed page logged and skipped: {item['product_url']} -> {fetch_err}")
            failed_pages += 1
            continue

        valid_rec, val_err = normalize_and_validate(raw_record)
        if valid_rec:
            valid_records.append(valid_rec)
        else:
            error_records.append(val_err)

    # Deduplicate by canonical product_url
    deduped_records = {}
    for r in valid_records:
        deduped_records[r["product_url"]] = r
    final_records = list(deduped_records.values())

    # Write output/books.json
    books_path = OUTPUT_DIR / "books.json"
    books_path.write_text(json.dumps(final_records, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write output/books.csv (Stretch goal)
    csv_path = OUTPUT_DIR / "books.csv"
    export_csv(final_records, csv_path)

    # Write output/errors.json
    errors_path = OUTPUT_DIR / "errors.json"
    errors_path.write_text(json.dumps(error_records, indent=2, ensure_ascii=False), encoding="utf-8")

    duration = round(time.time() - t0, 3)

    report = {
        "start_time": start_time_iso,
        "duration_seconds": duration,
        "pages_fetched": pages_fetched,
        "cache_hits": cache_hits,
        "valid_records": len(final_records),
        "invalid_records": len(error_records),
        "failed_pages": failed_pages
    }

    report_path = OUTPUT_DIR / "run-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    return report

def main():
    parser = argparse.ArgumentParser(description="FlyRank Polite Scraper")
    parser.add_argument("--test-failure", action="store_true", help="Inject one fake broken URL to test failure survival")
    args = parser.parse_args()

    report = run_scraper(inject_fake_url=args.test_failure)
    print("\n--- RUN REPORT ---")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
