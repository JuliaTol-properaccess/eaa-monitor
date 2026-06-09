#!/usr/bin/env python3
"""
Vult publicatiedatums aan in data/bronnen.json (WAT-framework, Layer 3: Tool).

Haalt elke bron-URL op en probeert de publicatiedatum te vinden uit, in volgorde
van betrouwbaarheid: JSON-LD "datePublished", og/meta "article:published_time",
meta itemprop "datePublished", of een <time datetime=...>. Daarnaast een
Nederlandse tekstdatum-fallback (bv. "24 maart 2026").

Schrijft alleen een datum weg als die betrouwbaar te parsen is en binnen een
plausibele periode valt (2015-2026). Vindt de tool niets, dan blijft het veld
leeg: er wordt nooit een datum verzonnen. Bestaande 'date'-velden blijven staan
tenzij --overwrite is meegegeven.

Gebruik:
    python tools/fetch_bron_dates.py            # alleen ontbrekende datums
    python tools/fetch_bron_dates.py --overwrite  # ook bestaande opnieuw ophalen
    python tools/fetch_bron_dates.py --dry-run     # niets schrijven, alleen tonen
"""

import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "bronnen.json"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT = 20
MIN_YEAR, MAX_YEAR = 2015, 2026

NL_MONTHS = {
    "januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "augustus": 8, "september": 9, "oktober": 10, "november": 11,
    "december": 12,
}

# Extractiepatronen, in volgorde van betrouwbaarheid.
PATTERNS = [
    re.compile(r'"datePublished"\s*:\s*"([^"]+)"', re.I),
    re.compile(r'property=["\']article:published_time["\']\s+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'content=["\']([^"\']+)["\']\s+property=["\']article:published_time["\']', re.I),
    re.compile(r'itemprop=["\']datePublished["\']\s+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<time[^>]+datetime=["\']([^"\']+)["\']', re.I),
]

NL_DATE_RE = re.compile(
    r'(\d{1,2})\s+(januari|februari|maart|april|mei|juni|juli|augustus|'
    r'september|oktober|november|december)\s+(\d{4})', re.I,
)


def _valid(d: date) -> bool:
    return MIN_YEAR <= d.year <= MAX_YEAR


def _parse(raw: str):
    """Probeer een ISO-datum of NL-tekstdatum uit een string te halen."""
    raw = raw.strip()
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', raw)
    if m:
        try:
            d = date(int(m[1]), int(m[2]), int(m[3]))
            return d if _valid(d) else None
        except ValueError:
            return None
    m = NL_DATE_RE.search(raw)
    if m:
        try:
            d = date(int(m[3]), NL_MONTHS[m[2].lower()], int(m[1]))
            return d if _valid(d) else None
        except ValueError:
            return None
    return None


def extract_date(htmltext: str):
    for pat in PATTERNS:
        for match in pat.findall(htmltext):
            d = _parse(match)
            if d:
                return d
    return None


def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def main():
    overwrite = "--overwrite" in sys.argv
    dry_run = "--dry-run" in sys.argv

    sources = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    found, missed, skipped = 0, [], 0

    for s in sources:
        url = str(s.get("url", "")).strip()
        if not url:
            continue
        if s.get("date") and not overwrite:
            skipped += 1
            continue
        try:
            d = extract_date(fetch(url))
        except Exception as exc:  # noqa: BLE001 - netwerk/parsing best-effort
            d = None
            print(f"  ! fout bij {url}: {exc}")
        if d:
            s["date"] = d.isoformat()
            found += 1
            print(f"  ✓ {d.isoformat()}  {s.get('author','')} — {s.get('title','')[:50]}")
        else:
            missed.append(s)
            print(f"  – geen datum  {s.get('author','')} — {s.get('title','')[:50]}")
        time.sleep(0.4)

    print(f"\nGevonden: {found} | geen datum: {len(missed)} | overgeslagen (had al): {skipped}")
    if missed:
        print("Zonder datum:")
        for s in missed:
            print(f"  - {s.get('author','')}: {s.get('url')}")

    if dry_run:
        print("\n(dry-run: bronnen.json niet gewijzigd)")
        return
    DATA_FILE.write_text(
        json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nBijgewerkt: {DATA_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
