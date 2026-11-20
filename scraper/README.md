# The Polite Scraper (Week 5 — Assignment A9)

A polite, deterministic Python scraping pipeline that collects the first three catalogue pages of **Books to Scrape**, visits all 60 book detail pages, normalizes prices and URLs, validates every record against a Pydantic schema, survives broken pages without crashing, and writes an honest run report[cite: 3, 4].

## Target Classification
- **Target Site:** `https://books.toscrape.com` (`https://toscrape.com`)[cite: 4, 5]
- **Why It Is Appropriate:** `toscrape.com` explicitly states that Books to Scrape is a public sandbox built specifically for developers and students to practice web scraping safely without impacting production sites[cite: 3, 5].
- **Scope:** Only the first **3 catalogue pages** (`page-1.html` through `page-3.html`) and the **60 book detail pages** linked from them[cite: 3, 5].
- **Data Collected:** Book title, canonical product URL, raw price text, normalized GBP price (`float`), availability text, star rating text, description (or `null`), source catalogue page URL, and UTC fetch timestamp.
- **Robots Check Result (`https://books.toscrape.com/robots.txt`):** Returned `404 Not Found` (no `robots.txt` file found; a missing file is not automatic permission, which is why we also verified the explicit sandbox notice on `toscrape.com`).
- **Rule of Engagement:** I will not reuse this code on another site without checking its rules and terms first.

## Language & Lane
- **Lane:** Python 3.10+ (`requests`, `beautifulsoup4`, `pydantic`)[cite: 4]

## Quickstart (Run in Under 5 Minutes)

```powershell
# 1. Clone the repository and enter the scraper subfolder
git clone [https://github.com/Crypt-Jazib/flyrank-task-api.git](https://github.com/Crypt-Jazib/flyrank-task-api.git)
cd flyrank-task-api/scraper

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the scraper (produces output/books.json, output/errors.json, and output/run-report.json)
python src/main.py