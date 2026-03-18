#!/usr/bin/env python3
"""
Scrape Thuiswinkel.org member directory to build a list of Dutch webshops.
Outputs new entries to data/webshops.json (merges with existing).

Usage:
    python tools/scrape_thuiswinkel.py
    python tools/scrape_thuiswinkel.py --pages 3    # test with first 3 pages
    python tools/scrape_thuiswinkel.py --dry-run     # don't write to file
"""

import json
import re
import time
import random
import argparse
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
WEBSHOPS_FILE = ROOT / "data" / "webshops.json"

BASE_URL = "https://www.thuiswinkel.org"
LIST_URL = "https://www.thuiswinkel.org/leden/?page={page}#results"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9",
}

# Map common keywords in names/descriptions to categories
CATEGORY_KEYWORDS = {
    "elektronica": ["elektronica", "computer", "telefoon", "laptop", "printer", "inkt", "toner", "hardware", "gaming"],
    "mode": ["kleding", "mode", "fashion", "schoenen", "shoes", "sieraden", "jewelry", "accessoires"],
    "supermarkt": ["supermarkt", "boodschappen", "food", "voeding", "levensmiddelen"],
    "drogisterij": ["drogist", "parfum", "beauty", "cosmetica", "gezondheid", "apotheek", "vitamines", "health"],
    "wonen": ["wonen", "meubel", "interieur", "tuin", "verlichting", "lamp", "gordijn", "bed", "matras", "keuken", "badkamer", "verf", "gereedschap"],
    "sport": ["sport", "fitness", "fiets", "outdoor", "camping"],
    "boeken": ["boek", "book", "lezen"],
    "speelgoed": ["speelgoed", "toys", "spel", "baby", "kinder"],
    "marketplace": ["marketplace", "platform"],
}


def guess_category(name, description=""):
    """Guess category based on name and description."""
    text = f"{name} {description}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "overig"


def get_total_pages(session):
    """Fetch the first page and determine how many pages there are."""
    resp = session.get(LIST_URL.format(page=1), headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the highest page number in pagination links
    max_page = 1
    for link in soup.find_all("a", href=True):
        match = re.search(r"\?page=(\d+)", link["href"])
        if match:
            page_num = int(match.group(1))
            max_page = max(max_page, page_num)

    return max_page


def scrape_member_list(session, page):
    """Scrape a single page of the member listing. Returns list of member profile URLs and names."""
    resp = session.get(LIST_URL.format(page=page), headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    members = []
    for h3 in soup.find_all("h3"):
        link = h3.find("a", href=True)
        if link and "/leden/" in link["href"] and link["href"] != "/leden/":
            name = link.get_text(strip=True)
            profile_url = urljoin(BASE_URL, link["href"])
            members.append({"name": name, "profile_url": profile_url})

    return members


def scrape_member_profile(session, profile_url):
    """Scrape a member profile page to get the website URL."""
    try:
        resp = session.get(profile_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find the website URL - it's in a link after "Website URL" label
        website_url = None
        for strong in soup.find_all("strong"):
            if "website" in strong.get_text(strip=True).lower():
                # The URL link should be a sibling or nearby element
                parent = strong.parent
                if parent:
                    link = parent.find("a", href=True)
                    if link:
                        website_url = link["href"]
                        break

        # Fallback: look for external links that aren't thuiswinkel.org
        if not website_url:
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("http") and "thuiswinkel.org" not in href and "kiyoh" not in href:
                    website_url = href
                    break

        # Get description for category guessing
        description = ""
        desc_el = soup.find("div", class_=re.compile(r"description|about|intro", re.I))
        if desc_el:
            description = desc_el.get_text(strip=True)

        return website_url, description

    except Exception as e:
        print(f"    Fout bij ophalen profiel: {e}")
        return None, ""


def normalize_url(url):
    """Normalize URL for deduplication."""
    if not url:
        return None
    url = url.strip().rstrip("/")
    # Ensure https
    if url.startswith("http://"):
        url = "https://" + url[7:]
    if not url.startswith("https://"):
        url = "https://" + url
    return url


def main():
    parser = argparse.ArgumentParser(description="Scrape Thuiswinkel.org member directory")
    parser.add_argument("--pages", type=int, help="Limit number of pages to scrape")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to webshops.json")
    args = parser.parse_args()

    # Load existing webshops
    existing = []
    if WEBSHOPS_FILE.exists():
        with open(WEBSHOPS_FILE) as f:
            existing = json.load(f)

    existing_urls = set()
    for shop in existing:
        normalized = normalize_url(shop["url"])
        if normalized:
            existing_urls.add(normalized)

    print(f"Bestaande webshops: {len(existing)}")

    session = requests.Session()

    # Determine total pages
    total_pages = get_total_pages(session)
    if args.pages:
        total_pages = min(total_pages, args.pages)
    print(f"Thuiswinkel.org: {total_pages} pagina's te scrapen")

    # Phase 1: Collect all member profile URLs
    all_members = []
    for page in range(1, total_pages + 1):
        print(f"  Pagina {page}/{total_pages}...", end=" ", flush=True)
        try:
            members = scrape_member_list(session, page)
            all_members.extend(members)
            print(f"{len(members)} leden gevonden")
        except Exception as e:
            print(f"FOUT: {e}")
        time.sleep(random.uniform(0.5, 1.5))

    print(f"\nTotaal {len(all_members)} leden gevonden. Website-URL's ophalen...")

    # Phase 2: Fetch website URLs from individual profiles
    new_shops = []
    skipped = 0
    errors = 0

    for i, member in enumerate(all_members):
        print(f"  [{i + 1}/{len(all_members)}] {member['name']}...", end=" ", flush=True)

        website_url, description = scrape_member_profile(session, member["profile_url"])

        if not website_url:
            print("geen URL gevonden")
            errors += 1
            time.sleep(random.uniform(0.3, 0.8))
            continue

        normalized = normalize_url(website_url)
        if normalized in existing_urls:
            print("al bekend")
            skipped += 1
            time.sleep(random.uniform(0.3, 0.8))
            continue

        category = guess_category(member["name"], description)
        new_shop = {
            "name": member["name"],
            "url": normalized,
            "category": category,
        }
        new_shops.append(new_shop)
        existing_urls.add(normalized)
        print(f"NIEUW ({category})")

        time.sleep(random.uniform(0.3, 0.8))

    print(f"\nKlaar!")
    print(f"  Nieuw: {len(new_shops)}")
    print(f"  Al bekend: {skipped}")
    print(f"  Geen URL: {errors}")

    if new_shops and not args.dry_run:
        merged = existing + new_shops
        merged.sort(key=lambda s: s["name"].lower())

        with open(WEBSHOPS_FILE, "w") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)

        print(f"  Totaal in webshops.json: {len(merged)}")
    elif args.dry_run and new_shops:
        print(f"  Dry-run: {len(new_shops)} nieuwe shops NIET opgeslagen")
        for shop in new_shops[:10]:
            print(f"    - {shop['name']} ({shop['url']}) [{shop['category']}]")
        if len(new_shops) > 10:
            print(f"    ... en {len(new_shops) - 10} meer")


if __name__ == "__main__":
    main()
