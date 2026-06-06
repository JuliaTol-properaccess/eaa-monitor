#!/usr/bin/env python3
"""
Scrape the WebwinkelKeur member directory to build a list of Dutch webshops.
Outputs new entries to data/webshops.json (merges with existing).

WebwinkelKeur lists its certified shops at https://www.webwinkelkeur.nl/leden/
The listing is server-rendered (15 shops per page, ~539 pages). Each shop has a
profile page at /webshop/<slug>_<id> whose embedded JSON-LD contains the real
shop website URL. The dashboard JSON API is behind an anti-bot challenge, so we
use the server-rendered HTML instead.

Because this is a large one-time scrape (~8000 profile pages), progress is cached
to .tmp/webwinkelkeur_profiles.json so an interrupted run can resume without
re-fetching everything.

Usage:
    python tools/scrape_webwinkelkeur.py                 # full run
    python tools/scrape_webwinkelkeur.py --pages 2       # test with first 2 pages
    python tools/scrape_webwinkelkeur.py --dry-run       # don't write to webshops.json
    python tools/scrape_webwinkelkeur.py --fresh         # ignore the resume cache
"""

import json
import re
import time
import random
import argparse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
WEBSHOPS_FILE = ROOT / "data" / "webshops.json"
CACHE_FILE = ROOT / ".tmp" / "webwinkelkeur_profiles.json"

BASE_URL = "https://www.webwinkelkeur.nl"
LIST_URL = "https://www.webwinkelkeur.nl/leden/?page={page}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9",
}

# Map common keywords in names to categories (same scheme as scrape_thuiswinkel.py)
CATEGORY_KEYWORDS = {
    "elektronica": ["elektronica", "computer", "telefoon", "laptop", "printer", "inkt", "toner", "hardware", "gaming", "accu", "kabel", "led"],
    "mode": ["kleding", "mode", "fashion", "schoenen", "shoes", "sieraden", "jewelry", "accessoires", "lingerie", "horloge", "bril"],
    "supermarkt": ["supermarkt", "boodschappen", "food", "voeding", "levensmiddelen", "drank", "wijn", "koffie"],
    "drogisterij": ["drogist", "parfum", "beauty", "cosmetica", "gezondheid", "apotheek", "vitamines", "health", "huidverzorging", "haar"],
    "wonen": ["wonen", "meubel", "interieur", "tuin", "verlichting", "lamp", "gordijn", "bed", "matras", "keuken", "badkamer", "verf", "gereedschap", "beslag", "vloer", "behang"],
    "sport": ["sport", "fitness", "fiets", "outdoor", "camping", "dart", "voetbal", "yoga"],
    "boeken": ["boek", "book", "lezen"],
    "speelgoed": ["speelgoed", "toys", "spel", "baby", "kinder", "puzzel"],
    "marketplace": ["marketplace", "platform"],
}


def guess_category(name):
    text = (name or "").lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "overig"


def normalize_url(url):
    """Normalize URL for deduplication."""
    if not url:
        return None
    url = url.strip().rstrip("/")
    if url.startswith("http://"):
        url = "https://" + url[7:]
    if not url.startswith("https://"):
        url = "https://" + url
    return url


def get_total_pages(session):
    """Determine how many listing pages there are from the pagination links."""
    resp = session.get(LIST_URL.format(page=1), headers=HEADERS, timeout=20)
    resp.raise_for_status()
    max_page = 1
    for match in re.finditer(r"/leden/\?page=(\d+)", resp.text):
        max_page = max(max_page, int(match.group(1)))
    return max_page


def scrape_listing_page(session, page):
    """Return the list of profile URLs shown on one listing page (de-duplicated)."""
    resp = session.get(LIST_URL.format(page=page), headers=HEADERS, timeout=20)
    resp.raise_for_status()
    urls = re.findall(r'href="(https://www\.webwinkelkeur\.nl/webshop/[^"]+)"', resp.text)
    seen = set()
    ordered = []
    for u in urls:
        u = u.rstrip("/")
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def extract_profile(session, profile_url):
    """Fetch a profile page and pull the shop website + name from its JSON-LD.

    Streams the response and stops as soon as the JSON-LD block is read, so we
    download ~135KB instead of the full ~360KB page.
    """
    pid = profile_url.rstrip("/").split("_")[-1]
    try:
        resp = session.get(profile_url, headers=HEADERS, timeout=20, stream=True)
        resp.raise_for_status()
        buf = ""
        ldjson = None
        for chunk in resp.iter_content(chunk_size=16384, decode_unicode=True):
            if not chunk:
                continue
            buf += chunk
            m = re.search(r'<script type="application/ld\+json">(.*?)</script>', buf, re.S)
            if m:
                ldjson = m.group(1)
                break
            if len(buf) > 300000:
                break
        resp.close()
    except Exception as e:
        return None, None, f"fetch-fout: {e}"

    if not ldjson:
        return None, None, "geen JSON-LD"

    try:
        data = json.loads(ldjson)
    except Exception:
        return None, None, "JSON-LD onleesbaar"

    nodes = data.get("@graph", []) if isinstance(data, dict) else []
    org = None
    for n in nodes:
        if isinstance(n, dict) and n.get("@type") == "Organization":
            # Prefer the Organization whose @id matches this profile's id;
            # the page also lists recommended shops we must not pick up.
            if pid and pid in str(n.get("@id", "")):
                org = n
                break
            if org is None:
                org = n

    if not org:
        return None, None, "geen Organization-node"

    return org.get("url"), org.get("name"), None


def load_cache():
    if CACHE_FILE.exists():
        try:
            return json.load(open(CACHE_FILE))
        except Exception:
            return {}
    return {}


def save_cache(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Scrape WebwinkelKeur member directory")
    parser.add_argument("--pages", type=int, help="Limit number of listing pages to scrape")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to webshops.json")
    parser.add_argument("--fresh", action="store_true", help="Ignore the resume cache and refetch")
    args = parser.parse_args()

    # Load existing webshops
    existing = []
    if WEBSHOPS_FILE.exists():
        existing = json.load(open(WEBSHOPS_FILE))
    existing_urls = {normalize_url(s["url"]) for s in existing if s.get("url")}
    print(f"Bestaande webshops: {len(existing)}")

    session = requests.Session()

    total_pages = get_total_pages(session)
    if args.pages:
        total_pages = min(total_pages, args.pages)
    print(f"WebwinkelKeur: {total_pages} listing-pagina's te scrapen")

    # Phase 1: collect all profile URLs from the listing pages
    profile_urls = []
    for page in range(1, total_pages + 1):
        try:
            urls = scrape_listing_page(session, page)
            profile_urls.extend(urls)
            print(f"  Listing {page}/{total_pages}: {len(urls)} profielen")
        except Exception as e:
            print(f"  Listing {page}/{total_pages}: FOUT {e}")
        time.sleep(random.uniform(0.4, 1.0))

    # de-dupe profile URLs across pages
    profile_urls = list(dict.fromkeys(profile_urls))
    print(f"\nTotaal {len(profile_urls)} unieke profielen. Website-URL's ophalen...")

    # Resume cache: profile_url -> {"url":..., "name":...} or {"error":...}
    cache = {} if args.fresh else load_cache()

    # Phase 2: fetch each profile's website
    processed = 0
    for i, purl in enumerate(profile_urls):
        if purl in cache and "url" in cache[purl]:
            continue  # already resolved in a previous run
        website, name, err = extract_profile(session, purl)
        if err:
            cache[purl] = {"error": err}
        else:
            cache[purl] = {"url": website, "name": name}
        processed += 1
        if processed % 25 == 0:
            save_cache(cache)
            print(f"  [{i + 1}/{len(profile_urls)}] verwerkt (laatste: {name or err})")
        time.sleep(random.uniform(0.3, 0.8))
    save_cache(cache)

    # Build new shops from the cache, de-duplicating on normalized URL
    new_shops = []
    no_url = 0
    for purl in profile_urls:
        entry = cache.get(purl, {})
        website = entry.get("url")
        if not website:
            no_url += 1
            continue
        normalized = normalize_url(website)
        if not normalized or normalized in existing_urls:
            continue
        name = entry.get("name") or purl.split("/webshop/")[-1].rsplit("_", 1)[0].replace("-", " ")
        new_shops.append({
            "name": name,
            "url": normalized,
            "category": guess_category(name),
        })
        existing_urls.add(normalized)

    print(f"\nKlaar!")
    print(f"  Nieuw: {len(new_shops)}")
    print(f"  Geen/al bekende URL: {len(profile_urls) - len(new_shops) - no_url} al bekend, {no_url} zonder URL")

    if new_shops and not args.dry_run:
        merged = existing + new_shops
        merged.sort(key=lambda s: s["name"].lower())
        with open(WEBSHOPS_FILE, "w") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        print(f"  Totaal in webshops.json: {len(merged)}")
    elif args.dry_run and new_shops:
        print(f"  Dry-run: {len(new_shops)} nieuwe shops NIET opgeslagen")
        for shop in new_shops[:15]:
            print(f"    - {shop['name']} ({shop['url']}) [{shop['category']}]")
        if len(new_shops) > 15:
            print(f"    ... en {len(new_shops) - 15} meer")


if __name__ == "__main__":
    main()
