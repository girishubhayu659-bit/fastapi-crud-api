# The Polite Scraper (FlyRank Internship - Week 5 / Assignment A9)

A polite, resilient web scraping pipeline that traverses the first 3 catalogue pages of Books to Scrape, visits all 60 book detail pages, turns messy HTML into clean, schema-validated JSON records, survives broken pages without crashing, and produces an honest audit run report.

---

## Target Classification

- **Target Site:** Books to Scrape (`https://books.toscrape.com/`)
- **Purpose / Why:** Books to Scrape is an open web scraping sandbox created specifically for students and engineers to practise extracting web data without violating real-world terms of service. As documented on [toscrape.com](https://toscrape.com): *"A fictional bookstore that desperately wants to be scraped. It's a safe place for beginners learning web scraping and for developers validating their scraping technologies as well."*
- **Scope / How Much:** Exactly the first 3 catalogue pages, discovering and visiting 60 unique book detail pages.
- **Data Collected:**
  - `title` (string)
  - `product_url` (canonical absolute URL string)
  - `price_text` (raw price string, e.g. `"£51.77"`)
  - `price_gbp` (clean numeric float, e.g. `51.77`)
  - `availability_text` (raw stock string, e.g. `"In stock (22 available)"`)
  - `rating_text` (star rating string, e.g. `"Three"`)
  - `description` (book description text, or `null` if omitted)
  - `source_page` (provenance catalogue page URL)
  - `fetched_at` (ISO 8601 UTC timestamp receipt)
- **Why Appropriate Here:** Scraping this site is appropriate because the site exists solely as a designated practice target; no private, copyrighted, or sensitive user data exists, and the workload is strictly limited to 63 total requests paced politely with rate limiting and local disk caching.
- **Robots.txt Check:**
  - URL checked: `https://books.toscrape.com/robots.txt`
  - Result: Returned HTTP status `404 Not Found` (`no robots file found`).
  - Interpretation: A missing `robots.txt` is not an automatic license to scrape, but Books to Scrape's stated sandbox charter explicitly invites practice scraping.

> **Ethics Commitment:**
> "I will not reuse this code on another site without checking its rules and terms first."

---
