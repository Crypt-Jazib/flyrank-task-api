from pathlib import Path
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Crypt-Jazib/flyrank-task-api)"
REQUEST_TIMEOUT = 10
REQUEST_DELAY_SECONDS = 0.6


def fetch_page(url: str, cache_filename: str, use_delay: bool = True) -> tuple[str, bool]:
    """Return (html, from_cache)."""
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"CACHE HIT | {cache_filename} ({len(html.encode('utf-8'))} bytes)")
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
    print(f"FETCH     | {cache_filename} ({len(html.encode('utf-8'))} bytes)")
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
            f"catalogue-page-{pages_visited}.html",
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


def main():
    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    discover_books(start_url, max_pages=3)


if __name__ == "__main__":
    main()