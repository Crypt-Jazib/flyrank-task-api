# The Polite Scraper (Week 5 — Assignment A9)

A polite, deterministic Python scraping pipeline that fetches the first three catalogue pages of **Books to Scrape**, extracts raw metadata from all 60 book detail pages, normalizes prices and URLs, validates every record with Pydantic, survives broken pages without crashing, and generates an honest run report.

## Target Classification
- **Target Site:** `https://books.toscrape.com` (operated by ToScrape, `https://toscrape.com`)[cite: 4, 5]
- **Why It Is Appropriate:** `toscrape.com` explicitly states that Books to Scrape is a public sandbox built specifically for developers and students to practice web scraping safely without harming production websites[cite: 3, 5].
- **Scope:** Only the first **3 catalogue pages** (`page-1.html` through `page-3.html`) and the **60 book detail pages** linked from them[cite: 3, 5].
- **Data Collected:** Book title, canonical product URL, raw price text, normalized GBP price (`float`), availability text, star rating text, description (or `null`), source catalogue page URL, and UTC fetch timestamp[cite: 6, 7].
- **Robots Check Result (`https://books.toscrape.com/robots.txt`):** Returned `404 Not Found` (no `robots.txt` file found; a missing file is not automatic permission, which is why we also verified the explicit sandbox notice on `toscrape.com`).
- **Rule of Engagement:** I will not reuse this code on another site without checking its rules and terms first.