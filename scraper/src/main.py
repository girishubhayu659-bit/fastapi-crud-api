"""
The Polite Scraper - FlyRank Internship Week 5 (Assignment A9)
Pipeline: fetch -> extract -> normalize -> validate -> store -> report
"""

import sys
from pathlib import Path

# Paths configuration
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"

def main():
    print("The Polite Scraper pipeline initialized.")

if __name__ == "__main__":
    main()
