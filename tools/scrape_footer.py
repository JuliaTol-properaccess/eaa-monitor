#!/usr/bin/env python3
"""
Scrape Dutch webshop footers to check for accessibility statement links.
Uses Playwright (headless Chromium) to handle JavaScript-rendered pages.

Usage:
    python tools/scrape_footer.py
    python tools/scrape_footer.py --limit 5   # test with first 5 shops
"""

import json
import re
import sys
import time
import random
import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Paths
ROOT = Path(__file__).resolve().parent.parent
WEBSHOPS_FILE = ROOT / "data" / "webshops.json"
RESULTS_FILE = ROOT / "data" / "results.json"
OBJECTIONS_FILE = ROOT / "data" / "objections.json"
HISTORY_FILE = ROOT / "data" / "history.json"
INDEX_FILE = ROOT / "public" / "index.html"
LLMS_FILE = ROOT / "public" / "llms.txt"

# Keywords to detect accessibility statement links (case-insensitive)
KEYWORDS_TEXT = [
    "toegankelijkheid",
    "toegankelijkheidsverklaring",
    "accessibility",
    "barrierefreiheit",
]
KEYWORDS_HREF = [
    "toegankelijkheid",
    "toegankelijkheidsverklaring",
    "accessibility",
    "a11y",
]

# Playwright settings
NAVIGATION_TIMEOUT = 15000  # 15 seconds
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def find_footer_area(soup):
    """Find the footer area of the page. Returns a list of elements to search."""
    areas = []

    # 1. <footer> elements
    footers = soup.find_all("footer")
    if footers:
        areas.extend(footers)

    # 2. Elements with footer-like IDs or classes
    footer_patterns = re.compile(r"footer|site-footer|page-footer|main-footer", re.I)
    for el in soup.find_all(id=footer_patterns):
        if el not in areas:
            areas.append(el)
    for el in soup.find_all(class_=footer_patterns):
        if el not in areas:
            areas.append(el)

    return areas


def check_links_for_statement(links, base_url):
    """Check a list of <a> tags for accessibility statement links."""
    for link in links:
        href = link.get("href", "")
        text = link.get_text(strip=True).lower()
        href_lower = href.lower()

        # Check link text
        if any(kw in text for kw in KEYWORDS_TEXT):
            return {
                "has_statement": True,
                "statement_url": urljoin(base_url, href),
                "statement_link_text": link.get_text(strip=True),
            }

        # Check href
        if any(kw in href_lower for kw in KEYWORDS_HREF):
            return {
                "has_statement": True,
                "statement_url": urljoin(base_url, href),
                "statement_link_text": link.get_text(strip=True),
            }

    return None


def check_webshop(page, url):
    """Check a single webshop for an accessibility statement link."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
        # Wait a bit for JS to render
        page.wait_for_timeout(2000)
    except PlaywrightTimeout:
        # Retry once
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
            page.wait_for_timeout(2000)
        except PlaywrightTimeout:
            return {
                "has_statement": False,
                "statement_url": None,
                "statement_link_text": None,
                "scrape_status": "timeout",
                "error": f"Timeout after {NAVIGATION_TIMEOUT}ms (2 attempts)",
            }
        except Exception as e:
            return {
                "has_statement": False,
                "statement_url": None,
                "statement_link_text": None,
                "scrape_status": "error",
                "error": str(e),
            }
    except Exception as e:
        return {
            "has_statement": False,
            "statement_url": None,
            "statement_link_text": None,
            "scrape_status": "error",
            "error": str(e),
        }

    try:
        html = page.content()
    except Exception as e:
        return {
            "has_statement": False,
            "statement_url": None,
            "statement_link_text": None,
            "scrape_status": "error",
            "error": str(e),
        }

    soup = BeautifulSoup(html, "html.parser")

    # Try footer areas first
    footer_areas = find_footer_area(soup)
    if footer_areas:
        for area in footer_areas:
            links = area.find_all("a", href=True)
            result = check_links_for_statement(links, url)
            if result:
                result["scrape_status"] = "success"
                result["error"] = None
                return result

    # Fallback: check all links on the page
    all_links = soup.find_all("a", href=True)
    result = check_links_for_statement(all_links, url)
    if result:
        result["scrape_status"] = "success"
        result["error"] = None
        return result

    return {
        "has_statement": False,
        "statement_url": None,
        "statement_link_text": None,
        "scrape_status": "success",
        "error": None,
    }


# ── GEO output: bake stats + schema into served HTML and llms.txt ──
#
# The dashboard renders all numbers client-side from results.json, so AI-crawlers
# that do not run JavaScript see empty placeholders. To stay citable we bake the
# headline numbers, a Dataset JSON-LD block and llms.txt at scrape time. The
# values mirror public/app.js exactly: webshops that filed an objection are
# excluded, and "met verklaring" means has_statement AND scrape_status success.

CATEGORY_LABELS = {
    "marketplace": "Marketplace",
    "elektronica": "Elektronica",
    "mode": "Mode",
    "supermarkt": "Supermarkt",
    "drogisterij": "Drogisterij",
    "wonen": "Wonen",
    "sport": "Sport",
    "boeken": "Boeken",
    "speelgoed": "Speelgoed",
    "overig": "Overig",
}

MONTHS_NL = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]


def _normalize_url(url):
    """Mirror app.js normalizeUrl: strip protocol, leading www, trailing slash."""
    if not url:
        return ""
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = re.sub(r"/+$", "", u)
    return u


def _load_objection_urls():
    """Return a set of normalized URLs that have filed an objection."""
    try:
        with open(OBJECTIONS_FILE) as f:
            data = json.load(f)
        if isinstance(data, list):
            return {_normalize_url(o.get("url")) for o in data if o.get("url")}
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return set()


def _pct(n, total):
    return round(n / total * 100) if total else 0


def _public_stats(webshops):
    """Compute stats the way the dashboard shows them (objections already removed)."""
    total = len(webshops)
    with_statement = sum(
        1 for r in webshops if r["has_statement"] and r["scrape_status"] == "success"
    )
    errors = sum(1 for r in webshops if r["scrape_status"] != "success")
    without_statement = total - with_statement - errors
    return {
        "total": total,
        "with_statement": with_statement,
        "without_statement": without_statement,
        "errors": errors,
        "pct_with": _pct(with_statement, total),
        "pct_without": _pct(without_statement, total),
        "pct_error": _pct(errors, total),
    }


def _category_breakdown(webshops):
    """Per-category found/total, sorted by total descending (matches the cards)."""
    cats = {}
    for r in webshops:
        c = r["category"]
        cats.setdefault(c, {"total": 0, "found": 0})
        cats[c]["total"] += 1
        if r["has_statement"] and r["scrape_status"] == "success":
            cats[c]["found"] += 1
    return sorted(cats.items(), key=lambda kv: kv[1]["total"], reverse=True)


def _date_nl(iso):
    """Format an ISO timestamp as e.g. '6 juni 2026' (date part only, no version quirks)."""
    year, month, day = iso[:10].split("-")
    return f"{int(day)} {MONTHS_NL[int(month) - 1]} {year}"


def _replace_region(html, start, end, new_inner):
    """Replace everything between two literal marker strings, keeping the markers."""
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    return pattern.sub(lambda _m: start + new_inner + end, html, count=1)


def _geo_summary_inner(stats, breakdown, date_nl):
    cat_str = ", ".join(
        f"{CATEGORY_LABELS.get(c, c)} {d['found']}/{d['total']}" for c, d in breakdown
    )
    return f"""
    <section aria-label="Samenvatting" class="max-w-7xl mx-auto px-4 sm:px-6 mt-8">
      <div class="bg-lightgrey rounded-xl p-6 text-darkblue">
        <p class="text-base leading-relaxed">
          Op <strong>{date_nl}</strong> controleerde de EAA Monitor
          <strong>{stats['total']} Nederlandse webshops</strong> op een toegankelijkheidsverklaring.
          <strong>{stats['with_statement']} webshops ({stats['pct_with']}%)</strong> publiceren er een; <strong>{stats['without_statement']} ({stats['pct_without']}%)</strong>
          doen dat niet en bij <strong>{stats['errors']} ({stats['pct_error']}%)</strong> kon de controle niet worden voltooid.
        </p>
        <p class="mt-3 text-sm leading-relaxed text-gray-600">
          Resultaat per categorie (met verklaring van totaal): {cat_str}.
        </p>
        <p class="mt-3 text-sm text-gray-500">Laatst bijgewerkt: {date_nl}.</p>
      </div>
    </section>
    """


def _dataset_jsonld(stats, date_nl, date_iso):
    obj = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": "https://eaa-monitor.nl/#dataset",
        "name": "Toegankelijkheidsverklaringen Nederlandse webshops",
        "description": (
            f"Wekelijkse meting of {stats['total']} Nederlandse webshops een "
            f"toegankelijkheidsverklaring publiceren. Op {date_nl}: "
            f"{stats['with_statement']} met verklaring, {stats['without_statement']} zonder, "
            f"{stats['errors']} niet te controleren."
        ),
        "url": "https://eaa-monitor.nl/",
        "creator": {
            "@type": "Organization",
            "name": "Proper Access",
            "url": "https://www.properaccess.nl",
        },
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "isAccessibleForFree": True,
        "inLanguage": "nl-NL",
        "dateModified": date_iso,
        "temporalCoverage": f"2026-03/{date_iso[:7]}",
        "measurementTechnique": (
            "Geautomatiseerde controle van de footer op links naar een "
            "toegankelijkheidsverklaring"
        ),
        "variableMeasured": [
            {"@type": "PropertyValue", "name": "Aantal gecontroleerde webshops", "value": stats["total"]},
            {"@type": "PropertyValue", "name": "Webshops met toegankelijkheidsverklaring", "value": stats["with_statement"]},
            {"@type": "PropertyValue", "name": "Webshops zonder toegankelijkheidsverklaring", "value": stats["without_statement"]},
            {"@type": "PropertyValue", "name": "Webshops niet te controleren", "value": stats["errors"]},
            {"@type": "PropertyValue", "name": "Percentage met verklaring", "value": stats["pct_with"], "unitText": "PERCENT"},
        ],
        "distribution": [{
            "@type": "DataDownload",
            "encodingFormat": "application/json",
            "contentUrl": "https://eaa-monitor.nl/data/results.json",
        }],
    }
    return (
        "\n  <script type=\"application/ld+json\">\n  "
        + json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n  </script>\n  "
    )


def patch_index_html(stats, breakdown, date_nl, date_iso):
    """Bake current numbers and the Dataset JSON-LD into the served index.html."""
    html = INDEX_FILE.read_text(encoding="utf-8")
    html = _replace_region(html, "<!-- GEO-SUMMARY:START -->", "<!-- GEO-SUMMARY:END -->",
                           _geo_summary_inner(stats, breakdown, date_nl))
    html = _replace_region(html, "<!--STAT:total-->", "<!--/STAT-->", str(stats["total"]))
    html = _replace_region(html, "<!--STAT:pctWith-->", "<!--/STAT-->", f"{stats['pct_with']}%")
    html = _replace_region(html, "<!--STAT:pctWithout-->", "<!--/STAT-->", f"{stats['pct_without']}%")
    html = _replace_region(html, "<!--CHART:total-->", "<!--/STAT-->", str(stats["total"]))
    html = _replace_region(html, "<!--LASTUPDATED-->", "<!--/LASTUPDATED-->",
                           f"Laatst bijgewerkt: {date_nl}")
    html = _replace_region(html, "<!-- JSONLD-DATASET:START -->", "<!-- JSONLD-DATASET:END -->",
                           _dataset_jsonld(stats, date_nl, date_iso))
    INDEX_FILE.write_text(html, encoding="utf-8")
    print(f"Patched {INDEX_FILE}")


def write_llms_txt(stats, date_nl):
    """(Re)generate public/llms.txt with the current headline figure."""
    content = f"""# EAA Monitor

> Monitor die wekelijks controleert of Nederlandse webshops een
> toegankelijkheidsverklaring publiceren, zoals vereist door de European
> Accessibility Act (EAA). Een initiatief van Proper Access.

Laatste meting ({date_nl}): {stats['total']} webshops gecontroleerd,
{stats['with_statement']} ({stats['pct_with']}%) met toegankelijkheidsverklaring,
{stats['without_statement']} ({stats['pct_without']}%) zonder, en
{stats['errors']} ({stats['pct_error']}%) niet te controleren.

## Belangrijkste pagina's
- [Dashboard](https://eaa-monitor.nl/): cijfers, grafiek en volledige lijst van webshops
- [Over dit dashboard](https://eaa-monitor.nl/over.html): wie erachter zit en methodologie
- [Ingediende bezwaren](https://eaa-monitor.nl/bezwaren.html): webshops die buiten de EAA vallen

## Data
- [Volledige resultaten (JSON)](https://eaa-monitor.nl/data/results.json)

## Over de maker
EAA Monitor is gemaakt door Proper Access (https://www.properaccess.nl),
specialist in digitale toegankelijkheid. Oprichter: Julia Tol, senior auditor.
"""
    LLMS_FILE.write_text(content, encoding="utf-8")
    print(f"Wrote {LLMS_FILE}")


def update_history(stats, date_iso):
    """Append a weekly summary to data/history.json (idempotent per date).

    Append-only time series that feeds the LinkedIn post-generator (week-over-week
    deltas) and, later, a trend chart on the dashboard. Re-running on the same day
    overwrites that day's entry instead of duplicating it.
    """
    try:
        with open(HISTORY_FILE) as f:
            history = json.load(f)
        if not isinstance(history, list):
            history = []
    except (FileNotFoundError, json.JSONDecodeError):
        history = []

    entry = {
        "date": date_iso,
        "total": stats["total"],
        "with_statement": stats["with_statement"],
        "without_statement": stats["without_statement"],
        "errors": stats["errors"],
        "pct_with": stats["pct_with"],
    }

    history = [h for h in history if h.get("date") != date_iso]
    history.append(entry)
    history.sort(key=lambda h: h["date"])

    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Updated {HISTORY_FILE} ({len(history)} meetpunten)")


def generate_geo_assets(output):
    """Bake stats/schema into index.html and llms.txt from a results.json dict."""
    objection_urls = _load_objection_urls()
    public_webshops = [
        r for r in output["webshops"] if _normalize_url(r["url"]) not in objection_urls
    ]
    stats = _public_stats(public_webshops)
    breakdown = _category_breakdown(public_webshops)
    date_nl = _date_nl(output["last_updated"])
    date_iso = output["last_updated"][:10]
    patch_index_html(stats, breakdown, date_nl, date_iso)
    write_llms_txt(stats, date_nl)
    update_history(stats, date_iso)


def main():
    parser = argparse.ArgumentParser(description="Scrape webshop footers for accessibility statements")
    parser.add_argument("--limit", type=int, help="Limit number of webshops to check (for testing)")
    args = parser.parse_args()

    # Load webshops
    with open(WEBSHOPS_FILE) as f:
        webshops = json.load(f)

    if args.limit:
        webshops = webshops[: args.limit]

    print(f"Checking {len(webshops)} webshops...")

    results = []
    now = datetime.now(timezone.utc).isoformat()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="nl-NL",
        )
        page = context.new_page()

        for i, shop in enumerate(webshops):
            name = shop["name"]
            url = shop["url"]
            print(f"  [{i + 1}/{len(webshops)}] {name} ({url})...", end=" ", flush=True)

            result = check_webshop(page, url)
            result_entry = {
                "name": name,
                "url": url,
                "category": shop.get("category", "overig"),
                "has_statement": result["has_statement"],
                "statement_url": result["statement_url"],
                "statement_link_text": result["statement_link_text"],
                "last_checked": now,
                "scrape_status": result["scrape_status"],
                "error": result["error"],
            }
            results.append(result_entry)

            status = "GEVONDEN" if result["has_statement"] else "niet gevonden"
            if result["scrape_status"] != "success":
                status = f"FOUT ({result['scrape_status']})"
            print(status)

            # Random delay between requests (1-3 seconds)
            if i < len(webshops) - 1:
                time.sleep(random.uniform(1, 3))

        browser.close()

    # Count stats
    with_statement = sum(1 for r in results if r["has_statement"])
    errors = sum(1 for r in results if r["scrape_status"] != "success")
    without_statement = len(results) - with_statement - errors

    output = {
        "last_updated": now,
        "total": len(results),
        "with_statement": with_statement,
        "without_statement": without_statement,
        "errors": errors,
        "webshops": sorted(results, key=lambda x: x["name"].lower()),
    }

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Bake current numbers + Dataset schema into the served HTML and llms.txt so
    # AI-crawlers and no-JS visitors see real values instead of placeholders.
    generate_geo_assets(output)

    print(f"\nKlaar! Resultaten opgeslagen in {RESULTS_FILE}")
    print(f"  Totaal: {len(results)}")
    print(f"  Met verklaring: {with_statement}")
    print(f"  Zonder verklaring: {without_statement}")
    print(f"  Fouten: {errors}")


if __name__ == "__main__":
    main()
