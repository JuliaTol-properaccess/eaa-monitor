#!/usr/bin/env python3
"""Batch-toegankelijkheidsscan met axe-core (dezelfde engine als wcag-scan.eu).

Draait axe-core 4.11 in headless Chromium via Playwright over een lijst sites en
aggregeert de violations. Standaard alleen WCAG A/AA-regels: best-practice-regels
(zoals de landmark-checks) tellen NIET mee, want die zijn in NL geen WCAG-falen.

Gebruik:
    python tools/scan_axe.py                         # ingebouwde proeflijst
    python tools/scan_axe.py --list data/webshops.json --limit 100
    python tools/scan_axe.py --include-best-practice # ook landmarks e.d.

De regelcatalogus (wat wel/niet meetelt) genereer je met tools/gen_axe_rules.js
en staat in data/axe-rules.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

ROOT = Path(__file__).resolve().parent.parent
AXE_JS = ROOT / "tools" / "vendor" / "axe.min.js"

# WCAG A/AA t/m 2.2. Best-practice en AAA bewust weggelaten.
WCAG_AA_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"]

NAVIGATION_TIMEOUT = 30_000  # ms per goto
SETTLE_MS = 1_500            # even laten renderen na domcontentloaded
MIN_DOM = 50                 # minder elementen = pagina niet echt gerenderd

DEFAULT_SITES = [
    {"name": "bol", "url": "https://www.bol.com"},
    {"name": "Albert Heijn", "url": "https://www.ah.nl"},
    {"name": "Coolblue", "url": "https://www.coolblue.nl"},
    {"name": "MediaMarkt", "url": "https://www.mediamarkt.nl"},
    {"name": "HEMA", "url": "https://www.hema.nl"},
    {"name": "Picnic", "url": "https://www.picnic.app/nl/"},
]


def sc_from_tags(tags):
    """wcag143 -> '1.4.3' (best-effort, voor leesbaarheid)."""
    for t in tags:
        if t.startswith("wcag") and t[4:].isdigit():
            n = t[4:]
            if len(n) == 3:
                return f"{n[0]}.{n[1]}.{n[2]}"
            if len(n) >= 4:
                return f"{n[0]}.{n[1]}.{n[2:]}"
    return ""


def dom_count(page):
    return page.evaluate("() => document.querySelectorAll('*').length")


def scan_site(page, url, axe_source, tags):
    """Return (violations, dom_elements).

    violations is None als de pagina niet echt rendert (redirect, consent-stap,
    bot-muur): dan is het 'niet te scannen', nooit 'geen fouten gevonden'.
    """
    page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
    page.wait_for_timeout(SETTLE_MS)
    dom = dom_count(page)
    if dom < MIN_DOM:  # geef redirect/SPA/consent meer tijd, dan opnieuw meten
        try:
            page.wait_for_load_state("networkidle", timeout=8_000)
        except PlaywrightTimeout:
            pass
        page.wait_for_timeout(2_500)
        dom = dom_count(page)
    if dom < MIN_DOM:
        return None, dom

    page.evaluate(axe_source)  # injectie via evaluate omzeilt CSP
    options = {"resultTypes": ["violations"]}
    if tags:
        options["runOnly"] = {"type": "tag", "values": tags}
    result = page.evaluate(
        "async (opts) => await window.axe.run(document, opts)", options
    )
    dom = dom_count(page)  # opnieuw meten: bevestig dat de pagina nog stond
    if dom < MIN_DOM:
        return None, dom
    violations = []
    for v in result.get("violations", []):
        violations.append(
            {
                "id": v["id"],
                "impact": v.get("impact"),
                "sc": sc_from_tags(v.get("tags", [])),
                "help": v.get("helpUrl"),
                "nodes": len(v.get("nodes", [])),
            }
        )
    return violations, dom


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", help="JSON-bestand met [{name,url}, ...]")
    ap.add_argument("--limit", type=int, default=0, help="max aantal sites")
    ap.add_argument("--out", default=".tmp/axe-scan.json")
    ap.add_argument(
        "--include-best-practice",
        action="store_true",
        help="ook best-practice-regels (landmarks e.d.) meetellen",
    )
    args = ap.parse_args()

    if not AXE_JS.exists():
        sys.exit(f"axe-core niet gevonden op {AXE_JS}. Eerst vendoren.")
    axe_source = AXE_JS.read_text()

    if args.list:
        sites = json.loads(Path(args.list).read_text())
        if isinstance(sites, dict):
            for k in ("webshops", "sites", "items", "results"):
                if isinstance(sites.get(k), list):
                    sites = sites[k]
                    break
    else:
        sites = DEFAULT_SITES
    if args.limit:
        sites = sites[: args.limit]

    tags = None if args.include_best_practice else WCAG_AA_TAGS
    print(f"axe-core scan | {len(sites)} sites | "
          f"{'alle regels incl. best-practice' if not tags else 'alleen WCAG A/AA'}")

    results = []
    rule_agg = {}  # id -> {sites, nodes, impact, sc, help}
    UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    with sync_playwright() as p:
        def new_browser():
            b = p.chromium.launch(headless=True)
            return b, b.new_context(user_agent=UA)

        browser, context = new_browser()
        for i, site in enumerate(sites, 1):
            if not browser.is_connected():  # herstart na een crash
                print("  (browser herstart)")
                browser, context = new_browser()
            url = site["url"]
            name = site.get("name", url)
            page = context.new_page()
            page.set_default_timeout(NAVIGATION_TIMEOUT)
            rec = {"name": name, "url": url}
            t0 = time.time()
            try:
                violations, dom_elements = scan_site(page, url, axe_source, tags)
                rec["dom_elements"] = dom_elements
                rec["load_ms"] = int((time.time() - t0) * 1000)
                if violations is None:
                    rec["status"] = "niet-gerenderd"
                    print(f"[{i}/{len(sites)}] {name:<16} NIET GERENDERD "
                          f"({dom_elements} elem)")
                else:
                    rec["status"] = "ok"
                    rec["violations"] = violations
                    rec["total_nodes"] = sum(v["nodes"] for v in violations)
                    for v in violations:
                        a = rule_agg.setdefault(
                            v["id"],
                            {"sites": 0, "nodes": 0, "impact": v["impact"],
                             "sc": v["sc"], "help": v["help"]},
                        )
                        a["sites"] += 1
                        a["nodes"] += v["nodes"]
                    print(f"[{i}/{len(sites)}] {name:<16} {len(violations):>3} regels, "
                          f"{rec['total_nodes']:>4} elem, dom={dom_elements} "
                          f"({time.time()-t0:.1f}s)")
            except PlaywrightTimeout:
                rec["status"] = "timeout"
                print(f"[{i}/{len(sites)}] {name:<16} TIMEOUT")
            except Exception as e:  # noqa: BLE001
                rec["status"] = "error"
                rec["error"] = str(e)[:200]
                print(f"[{i}/{len(sites)}] {name:<16} ERROR: {str(e)[:80]}")
            finally:
                try:
                    page.close()
                except Exception:  # noqa: BLE001
                    pass
            results.append(rec)
        browser.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "axe_tags": tags or "all",
        "scanned": len(results),
        "rule_frequency": dict(
            sorted(rule_agg.items(), key=lambda kv: kv[1]["sites"], reverse=True)
        ),
        "results": results,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    ok = [r for r in results if r["status"] == "ok"]
    print(f"\nGescand: {len(ok)}/{len(results)} geslaagd. Detail: {out}")
    if ok:
        print("\nMeest voorkomende fouten (op hoeveel sites):")
        top = sorted(rule_agg.items(), key=lambda kv: kv[1]["sites"], reverse=True)
        for rid, a in top[:15]:
            sc = f"SC {a['sc']}" if a["sc"] else ""
            print(f"  {a['sites']:>2} sites  {a['nodes']:>5} elem  "
                  f"{(a['impact'] or '?'):<8} {rid}  {sc}")


if __name__ == "__main__":
    main()
