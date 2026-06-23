#!/usr/bin/env python3
"""Live ground-truth-validatie van de detector tegen echte sites.

Draait de volledige scrape-flow (check_webshop + no-block retry) tegen de
handmatig geverifieerde lijst in tests/groundtruth_sites.json en meldt waar de
detector afwijkt. Anders dan tests/test_detector.py (deterministisch, geen
netwerk) is dit bedoeld voor periodieke handmatige validatie: 'bot-protected'
sites wisselen per run en tellen niet mee voor pass/fail.

Gebruik:
    python tests/check_live.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright  # noqa: E402
import tools.scrape_footer as s  # noqa: E402

GROUNDTRUTH = Path(__file__).resolve().parent / "groundtruth_sites.json"


def check(browser, page, url):
    r = s.check_webshop(page, url)
    if r["scrape_status"] == "error" and "wachtrij of lege render" in (r["error"] or ""):
        alt = s.recheck_unblocked(browser, url)
        if alt["scrape_status"] == "success":
            r = alt
    return r


def run():
    sites = json.load(open(GROUNDTRUTH, encoding="utf-8"))["sites"]
    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser, ctx, page = s._fresh_page(p, browser)
        for site in sites:
            url, expect = site["url"], site["expect"]
            r = check(browser, page, url)
            has, status = r["has_statement"], r["scrape_status"]
            if expect == "statement":
                ok = has
            elif expect == "none":
                ok = (not has) and status == "success"
            else:  # bot-protected: informatief
                ok = None
            mark = "info" if ok is None else ("PASS" if ok else "FAIL")
            got = "verklaring" if has else (status if status != "success" else "geen")
            print(f"  [{mark}] {url:32} verwacht={expect:13} kreeg={got}  {r.get('statement_url') or ''}")
            if ok is False:
                failures.append((url, expect, got, r.get("statement_url")))
            time.sleep(0.3)
        browser.close()

    print(f"\n  {len(failures)} afwijking(en) op harde verwachtingen (bot-protected niet meegeteld)")
    return not failures


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
