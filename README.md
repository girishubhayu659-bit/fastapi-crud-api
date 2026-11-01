# FlyRank Backend Track — Progressive API & Data Stack

> ### 📌 Project Milestones & Branches
> This repository documents the progressive evolution of our backend system across all internship weeks. Each milestone is preserved in its own branch with its dedicated code, configuration, and documentation:
>
> * 🚀 **Assignment 1:** [**Week 2 — In-Memory CRUD API**](https://github.com/girishubhayu659-bit/fastapi-crud-api/tree/w2-build-your-first-crud-api)
> * 🗄️ **Assignment 2:** [**Week 3 — SQLite Database Persistence**](https://github.com/girishubhayu659-bit/fastapi-crud-api/tree/w3-connecting-crud-to-database)
> * 🐳 **Assignment 3:** [**Week 3 — Containerized PostgreSQL Stack**](https://github.com/girishubhayu659-bit/fastapi-crud-api/tree/w3-containerize-your-stack)
> * 🔐 **Assignment 4:** [**Week 4 — Supabase Auth & JWT Protection**](https://github.com/girishubhayu659-bit/fastapi-crud-api/tree/w4-auth-login-and-protect)
> * 🕷️ **Assignment 5 (Current):** [**Week 5 — The Polite Scraper**](https://github.com/girishubhayu659-bit/fastapi-crud-api/tree/w5-the-polite-scraper)

---

# The Polite Scraper (FlyRank Internship · Week 5 · Assignment A9)

A polite, resilient web scraping pipeline located in the [`scraper/`](./scraper) directory that traverses the first 3 catalogue pages of Books to Scrape, discovers and visits all 60 book detail pages, turns messy HTML into clean, schema-validated JSON and CSV records, survives broken pages without crashing, and ends every run with an honest audit run report.

---

## 1. Target Classification

- **Target Site:** Books to Scrape (`https://books.toscrape.com/`)
- **Purpose / Why:** Books to Scrape is an open web scraping sandbox created specifically for beginners and developers to practise scraping without violating production websites' terms of service. As explicitly stated on [toscrape.com](https://toscrape.com):
  > *"A fictional bookstore that desperately wants to be scraped. It's a safe place for beginners learning web scraping and for developers validating their scraping technologies as well."*
- **Scope / How Much:** Exactly the first 3 catalogue pages, discovering and visiting 60 unique book detail pages.
- **Data Collected:**
  - `title` (string): Full book title from product page `<h1>`.
  - `product_url` (canonical absolute URL string): Unique identifier for deduplication.
  - `price_text` (raw string): Raw price string including currency symbol (e.g. `"£51.77"`).
  - `price_gbp` (numeric float): Clean numeric price normalized for sorting/filtering (e.g. `51.77`).
  - `availability_text` (raw string): Stock availability text (e.g. `"In stock (22 available)"`).
  - `rating_text` (string): Textual star rating (e.g. `"Three"`).
  - `description` (string or null): Book description paragraph, or `null` if omitted.
  - `source_page` (canonical URL string): Catalogue page from which the book link was discovered.
  - `fetched_at` (ISO 8601 UTC timestamp): Timestamp showing exactly when the record was retrieved (provenance).
- **Why Appropriate Here:** Scraping this site is appropriate because it is a designated public sandbox specifically built for scraping practice; no private, copyrighted, or sensitive user data exists, and the workload is strictly limited to 63 total requests paced politely with rate limiting and local disk caching.
- **Robots.txt Check:**
  - URL checked: `https://books.toscrape.com/robots.txt`
  - Result: Returned HTTP status `404 Not Found` (`no robots file found`).
  - Interpretation: A missing `robots.txt` is not an automatic permission to scrape, but Books to Scrape's stated sandbox charter explicitly invites practice scraping.

> **Ethics Commitment:**
> "I will not reuse this code on another site without checking its rules and terms first."

---

## 2. Lane & Installation

- **Lane:** Python 3.10+
- **HTTP Client:** `requests`
- **HTML Parser:** `beautifulsoup4`
- **Schema Validator:** `pydantic` (v2)
- **Test Framework:** `pytest`

### Quick Install

```bash
cd scraper
pip install -r requirements.txt
```

---

## 3. One Copy-Pasteable Run Command

```bash
# Run the pipeline
python scraper/src/main.py
```
*(Or `cd scraper && python src/main.py`)*

### Additional Commands

```bash
# Stage 5 Checkpoint: Prove failure survival by injecting a deliberately broken book URL
python scraper/src/main.py --test-failure

# Run parser & validation test suite
pytest scraper/tests/ -v
```

---

## 4. Record Schema (Pydantic)

Every record is validated against the following Pydantic schema before it is written to `output/books.json`. Records failing validation are redirected to `output/errors.json`:

```python
class BookRecord(BaseModel):
    title: str = Field(..., min_length=1, description="Book title")
    product_url: str = Field(..., description="Canonical absolute product URL starting with https://")
    price_text: str = Field(..., min_length=1, description="Raw price string including currency")
    price_gbp: float = Field(..., ge=0.0, description="Clean numeric price in GBP")
    availability_text: str = Field(..., min_length=1, description="Raw stock availability string")
    rating_text: str = Field(..., min_length=1, description="Star rating string")
    description: Optional[str] = Field(None, description="Book description text or null")
    source_page: str = Field(..., description="Provenance catalogue page URL starting with https://")
    fetched_at: str = Field(..., description="Provenance ISO 8601 UTC timestamp")
```

---

## 5. Politeness Rules

1. **Honest User-Agent:** Every request sends `FlyRankInternship-A9/1.0 (+https://github.com/girishubhayu659-bit/fastapi-crud-api)` so site maintainers can identify the crawler and contact the repository owner.
2. **Polite Delay:** Enforces a minimum `500 ms` delay (`time.sleep(0.5)`) between real network requests to avoid server hammering. Cached requests require 0 ms delay.
3. **Strict Timeouts:** Every network request has a `10.0 s` timeout so hanging requests terminate gracefully.
4. **Local Disk Cache:** HTML files are cached in `cache/` (`catalogue-page-*.html`, `book-*.html`). Subsequent development runs read directly from cache without hitting the remote server.
5. **Surviving Failures & Retry Rules:** Single retry with delay for transient network issues and `5xx` server errors. Never retries `404` (Not Found) or `403` (Forbidden).

---

## 6. Honest Limitation

This scraper is specialized for server-rendered HTML pages where all content is sent in the initial HTTP response. It does not execute JavaScript; modern Single Page Applications (SPAs) that load content client-side via JavaScript after initial pageload (such as `quotes.toscrape.com/js`) cannot be scraped with this pipeline without either reverse-engineering the underlying JSON API or using a headless browser engine like Playwright.

---

## 7. Why No Browser Was Needed

This assignment needed no browser: the data is already in the HTML the server sends, so a browser would only add cost. Using a headless browser (such as Chromium via Playwright or Puppeteer) would consume 10x-20x more memory and CPU cycles while introducing heavy binary dependencies with no data extraction benefit.

---

## 8. Real Run Report Proof

Below is the genuine `scraper/output/run-report.json` generated from running the pipeline against Books to Scrape:

```json
{
  "start_time": "2026-11-01T11:37:33Z",
  "duration_seconds": 0.704,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0
}
```

When tested with `--test-failure` (deliberately broken URL injected), the pipeline gracefully logs and skips the failure, finishing cleanly:

```json
{
  "start_time": "2026-11-01T11:36:00Z",
  "duration_seconds": 2.531,
  "pages_fetched": 1,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1
}
```

---

## 9. Ethics Note

- **Prioritize Official APIs:** Always check for and use an official, documented API when one exists. Web scraping is a fallback when no structured API is available.
- **Respect Access Controls:** Never bypass logins, CAPTCHAs, paywalls, or rate-limit blocks. If a server responds with HTTP 403 or 429, respect the refusal.
- **Collect Only What You Need:** Target only the specific fields and pages relevant to the task. Never crawl or store unbounded data indiscriminately.

---

## 10. Extras & Stretch Deliverables

1. **CSV Export:** The pipeline exports `scraper/output/books.csv` in addition to `books.json`, flattening optional null descriptions to clean empty strings.
2. **Parser Unit Tests:** A comprehensive 5-test suite in `scraper/tests/test_scraper.py` verifying:
   - Price normalization (`£51.77` -> `51.77`)
   - Relative to absolute URL resolution (`urljoin`)
   - Missing description fixture handling (`None` / `null`)
   - Duplicate URL deduplication (canonical URL identity)
   - Malformed fixture schema rejection (redirected to errors)
