import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ValidationError, field_validator
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
BOOKS_CACHE_DIR = CACHE_DIR / "books"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
BOOKS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Crypt-Jazib/flyrank-task-api)"
REQUEST_TIMEOUT = 10
REQUEST_DELAY_SECONDS = 0.6


class BookRecord(BaseModel):
    title: str = Field(min_length=1)
    product_url: str
    price_text: str = Field(min_length=1)
    price_gbp: float = Field(ge=0)
    availability_text: str = Field(min_length=1)
    rating_text: str = Field(min_length=1)
    description: str | None = None
    source_page: str
    fetched_at: str = Field(min_length=1)

    @field_validator("product_url", "source_page")
    @classmethod
    def must_be_https_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("URL must start with https://")
        return value


def parse_price_gbp(price_text: str | None) -> float:
    if not price_text:
        raise ValueError("Missing price_text")
    match = re.search(r"(\d+(?:\.\d+)?)", price_text)
    if not match:
        raise ValueError(f"Could not parse numeric price from '{price_text}'")
    return round(float(match.group(1)), 2)


def fetch_page(url: str, cache_path: Path, use_delay: bool = True, quiet: bool = False) -> tuple[str, bool]:
    """Fetch HTML with cache check, polite delay, and single retry on timeout/5xx only."""
    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        if not quiet:
            print(f"CACHE HIT | {cache_path.name} ({len(html.encode('utf-8'))} bytes)")
        return html, True

    headers = {"User-Agent": USER_AGENT}
    last_error: Exception | None = None

    for attempt in range(2):
        if use_delay or attempt > 0:
            time.sleep(REQUEST_DELAY_SECONDS * (attempt + 1))

        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        except requests.Timeout as exc:
            last_error = RuntimeError(f"Timeout fetching {url}: {exc}")
            continue
        except requests.RequestException as exc:
            raise RuntimeError(f"Network error fetching {url}: {exc}") from exc

        if response.status_code == 200:
            response.encoding = "utf-8"
            html = response.text
            cache_path.write_text(html, encoding="utf-8")
            if not quiet:
                print(f"FETCH     | {cache_path.name} ({len(html.encode('utf-8'))} bytes)")
            return html, False

        if response.status_code in (403, 404):
            raise RuntimeError(f"HTTP {response.status_code} (not retrying) for {url}")

        if 500 <= response.status_code < 600:
            last_error = RuntimeError(f"HTTP {response.status_code} server error for {url}")
            continue

        raise RuntimeError(f"Unexpected HTTP {response.status_code} for {url}")

    raise last_error or RuntimeError(f"Failed to fetch {url}")


def discover_books(start_url: str, max_pages: int = 3) -> tuple[list[dict], int, int]:
    """Return (discovered_links, pages_fetched_live, cache_hits)."""
    current_url = start_url
    pages_visited = 0
    pages_fetched = 0
    cache_hits = 0
    discovered: list[dict] = []
    seen_urls: set[str] = set()

    while current_url and pages_visited < max_pages:
        pages_visited += 1
        html, from_cache = fetch_page(
            current_url,
            CACHE_DIR / f"catalogue-page-{pages_visited}.html",
            use_delay=(pages_visited > 1),
        )
        if from_cache:
            cache_hits += 1
        else:
            pages_fetched += 1

        soup = BeautifulSoup(html, "html.parser")
        for article in soup.select("article.product_pod"):
            link_tag = article.select_one("h3 a")
            if not link_tag or not link_tag.get("href"):
                continue
            product_url = urljoin(current_url, link_tag["href"])
            if product_url not in seen_urls:
                seen_urls.add(product_url)
                discovered.append(
                    {
                        "product_url": product_url,
                        "source_page": current_url,
                    }
                )

        next_link = soup.select_one("li.next a")
        current_url = urljoin(current_url, next_link["href"]) if next_link and next_link.get("href") else None

    print(
        f"catalogue_pages={pages_visited}, "
        f"discovered={len(discovered)}, "
        f"unique_urls={len(seen_urls)}"
    )
    return discovered, pages_fetched, cache_hits


def slug_from_book_url(product_url: str) -> str:
    parts = [p for p in urlparse(product_url).path.split("/") if p]
    slug = parts[-2] if len(parts) >= 2 else "book"
    return f"{slug}.html"


def extract_book_record(html: str, product_url: str, source_page: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    product_main = soup.select_one("div.product_main")
    if not product_main:
        raise ValueError(f"Missing product_main section on {product_url}")

    title_el = product_main.select_one("h1")
    price_el = product_main.select_one("p.price_color")
    avail_el = product_main.select_one("p.instock.availability")
    rating_el = product_main.select_one("p.star-rating")

    rating_text = None
    if rating_el:
        for cls in rating_el.get("class", []):
            if cls != "star-rating":
                rating_text = cls
                break

    description = None
    desc_header = soup.select_one("#product_description")
    if desc_header:
        desc_p = desc_header.find_next_sibling("p")
        if desc_p and desc_p.get_text(strip=True):
            description = desc_p.get_text(strip=True)

    return {
        "title": title_el.get_text(strip=True) if title_el else None,
        "product_url": product_url,
        "price_text": price_el.get_text(strip=True) if price_el else None,
        "availability_text": " ".join(avail_el.get_text().split()) if avail_el else None,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def normalize_and_validate(raw_record: dict) -> BookRecord:
    candidate = {
        **raw_record,
        "price_gbp": parse_price_gbp(raw_record.get("price_text")),
    }
    return BookRecord.model_validate(candidate)


def main():
    parser = argparse.ArgumentParser(description="Polite scraper for Books to Scrape (first 3 pages).")
    parser.add_argument(
        "--test-broken-url",
        action="store_true",
        help="Inject one non-existent book URL to verify fault tolerance.",
    )
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc)
    start_perf = time.perf_counter()

    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    book_links, pages_fetched, cache_hits = discover_books(start_url, max_pages=3)

    if args.test_broken_url:
        book_links.append(
            {
                "product_url": "https://books.toscrape.com/catalogue/this-book-does-not-exist_999999/index.html",
                "source_page": start_url,
            }
        )

    valid_by_url: dict[str, dict] = {}
    errors: list[dict] = []
    failed_pages: list[dict] = []

    for item in book_links:
        url = item["product_url"]
        cache_file = BOOKS_CACHE_DIR / slug_from_book_url(url)
        try:
            html, from_cache = fetch_page(url, cache_file, use_delay=True, quiet=True)
            if from_cache:
                cache_hits += 1
            else:
                pages_fetched += 1
        except Exception as exc:
            print(f"WARN | Skipping failed page {url}: {exc}")
            failed_pages.append({"url": url, "reason": str(exc)})
            continue

        try:
            raw = extract_book_record(html, url, item["source_page"])
            validated = normalize_and_validate(raw)
            valid_by_url[validated.product_url] = validated.model_dump()
        except (ValidationError, ValueError) as exc:
            errors.append({"product_url": url, "reason": str(exc)})

    duration_seconds = round(time.perf_counter() - start_perf, 3)

    books_path = OUTPUT_DIR / "books.json"
    errors_path = OUTPUT_DIR / "errors.json"
    report_path = OUTPUT_DIR / "run-report.json"

    books_path.write_text(json.dumps(list(valid_by_url.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    errors_path.write_text(json.dumps(errors, indent=2, ensure_ascii=False), encoding="utf-8")

    report = {
        "started_at": started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": duration_seconds,
        "pages_fetched": pages_fetched,
        "cache_hits": cache_hits,
        "valid_records": len(valid_by_url),
        "invalid_records": len(errors),
        "failed_pages": len(failed_pages),
        "failed_page_details": failed_pages,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()