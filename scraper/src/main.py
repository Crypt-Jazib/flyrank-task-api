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


def normalize_and_validate(raw_record: dict) -> BookRecord:
    candidate = {
        **raw_record,
        "price_gbp": parse_price_gbp(raw_record.get("price_text")),
    }
    return BookRecord.model_validate(candidate)


def main():
    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    book_links = discover_books(start_url, max_pages=3)

    valid_by_url: dict[str, dict] = {}
    errors: list[dict] = []

    for item in book_links:
        cache_file = BOOKS_CACHE_DIR / slug_from_book_url(item["product_url"])
        html, _ = fetch_page(
            item["product_url"],
            cache_file,
            use_delay=True,
            quiet=True,
        )
        raw = extract_book_record(html, item["product_url"], item["source_page"])
        try:
            validated = normalize_and_validate(raw)
            valid_by_url[validated.product_url] = validated.model_dump()
        except (ValidationError, ValueError) as exc:
            errors.append({"product_url": item["product_url"], "reason": str(exc), "raw": raw})

    books_path = OUTPUT_DIR / "books.json"
    errors_path = OUTPUT_DIR / "errors.json"
    books_path.write_text(json.dumps(list(valid_by_url.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    errors_path.write_text(json.dumps(errors, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"valid_records={len(valid_by_url)}, invalid_records={len(errors)}")


if __name__ == "__main__":
    main()