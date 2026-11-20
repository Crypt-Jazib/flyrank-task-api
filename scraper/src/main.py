from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
BOOKS_CACHE_DIR = CACHE_DIR / "books"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
BOOKS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Crypt-Jazib/flyrank-task-api)"
REQUEST_TIMEOUT = 10
REQUEST_DELAY_SECONDS = 0.6


def fetch_page(url: str, cache_path: Path, use_delay: bool = True, quiet: bool = False) -> tuple[str, bool]:
    """Return (html, from_cache)."""
    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        if not quiet:
            print(f"CACHE HIT | {cache_path.name} ({len(html.encode('utf-8'))} bytes)")
        return html, True

    if use_delay:
        time.sleep(REQUEST_DELAY_SECONDS)

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {response.status_code}")

    response.encoding = "utf-8"
    html = response.text
    cache_path.write_text(html, encoding="utf-8")
    if not quiet:
        print(f"FETCH     | {cache_path.name} ({len(html.encode('utf-8'))} bytes)")
    return html, False


def discover_books(start_url: str, max_pages: int = 3) -> list[dict]:
    current_url = start_url
    pages_visited = 0
    discovered: list[dict] = []
    seen_urls: set[str] = set()

    while current_url and pages_visited < max_pages:
        pages_visited += 1
        html, _ = fetch_page(
            current_url,
            CACHE_DIR / f"catalogue-page-{pages_visited}.html",
            use_delay=(pages_visited > 1),
        )
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
    return discovered


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


def main():
    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    book_links = discover_books(start_url, max_pages=3)

    raw_records = []
    for idx, item in enumerate(book_links, start=1):
        cache_file = BOOKS_CACHE_DIR / slug_from_book_url(item["product_url"])
        html, from_cache = fetch_page(
            item["product_url"],
            cache_file,
            use_delay=True,
            quiet=True,
        )
        if not from_cache and idx % 10 == 0:
            print(f"Fetched {idx}/{len(book_links)} detail pages...")
        record = extract_book_record(html, item["product_url"], item["source_page"])
        raw_records.append(record)

    print(f"detail_pages={len(raw_records)}")
    print("Sample raw record:")
    print(json.dumps(raw_records[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()