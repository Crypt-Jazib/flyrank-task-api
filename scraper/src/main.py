from pathlib import Path
import time
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Crypt-Jazib/flyrank-task-api)"
REQUEST_TIMEOUT = 10
REQUEST_DELAY_SECONDS = 0.6


def fetch_page(url: str, cache_filename: str, use_delay: bool = True) -> str:
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"CACHE HIT | {cache_filename} ({len(html.encode('utf-8'))} bytes)")
        return html

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
    return html


def main():
    page_1_url = "https://books.toscrape.com/catalogue/page-1.html"
    fetch_page(page_1_url, "catalogue-page-1.html", use_delay=False)


if __name__ == "__main__":
    main()