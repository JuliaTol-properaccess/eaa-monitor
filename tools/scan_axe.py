#!/usr/bin/env python3
"""Batch-toegankelijkheidsscan met axe-core (dezelfde engine als wcag-scan.nl).

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
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Dezelfde watchdog als de scraper. Bewust hergebruikt in plaats van een tweede
# variant: de drie lagen (SIGALRM -> chromium-kill -> reaper) zijn daar duur
# betaald en uitgetest, en een kopie zou apart verrotten.
from tools.scrape_footer import (  # noqa: E402
    SiteTimeout, site_deadline, _kill_browser_processes, _resume_argv,
    RECOVERY_CAP_S,
)

ROOT = Path(__file__).resolve().parent.parent
AXE_JS = ROOT / "tools" / "vendor" / "axe.min.js"

# WCAG A/AA t/m 2.2. Best-practice en AAA bewust weggelaten.
WCAG_AA_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"]

NAVIGATION_TIMEOUT = 30_000  # ms per goto
SETTLE_MS = 1_500            # even laten renderen na domcontentloaded
MIN_DOM = 50                 # minder elementen = pagina niet echt gerenderd

# Harde wall-clock-cap per site. De losse Playwright-timeouts dekken goto en
# wait_for_load_state, maar niet een hang in page.evaluate (de axe-run zelf) of
# een wedged driver. Zonder deze cap hield één site de scan van 4 augustus 2026
# tegen tot de jobcap van 60 minuten; alle runs ervoor deden 21-25 minuten.
# Ruim boven een trage-maar-echte scan (goto 30s + settle + networkidle + axe).
SCAN_CAP_S = 120

# Tussentijds wegschrijven, zodat een afgebroken run zijn werk niet verliest.
FLUSH_EVERY = 25

# Hoe vaak de scan zichzelf mag herstarten na een onbreekbare hang.
MAX_SCAN_RESTARTS = 5

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


def aggregate(results):
    """Bouw de regelfrequentie op uit de resultaten.

    Uit de scan-lus gehaald zodat een hervatte run (zie --resume-from) de
    aggregatie gewoon opnieuw kan berekenen uit de teruggelezen resultaten,
    in plaats van een half opgebouwde teller mee te moeten slepen.
    """
    rule_agg = {}
    for rec in results:
        if rec.get("status") != "ok":
            continue
        for v in rec.get("violations", []):
            a = rule_agg.setdefault(
                v["id"],
                {"sites": 0, "nodes": 0, "impact": v["impact"],
                 "sc": v["sc"], "help": v["help"]},
            )
            a["sites"] += 1
            a["nodes"] += v["nodes"]
    return dict(sorted(rule_agg.items(), key=lambda kv: kv[1]["sites"], reverse=True))


def build_payload(results, tags):
    return {
        "axe_tags": tags or "all",
        "scanned": len(results),
        "rule_frequency": aggregate(results),
        "results": results,
    }


def write_payload(out_path, results, tags):
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(build_payload(results, tags), indent=2, ensure_ascii=False))
    tmp.replace(out)


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
    # Zelfherstart na een onbreekbare hang; zet de reaper zelf.
    ap.add_argument("--resume-from", type=int, default=0, help=argparse.SUPPRESS)
    ap.add_argument("--restarts", type=int, default=0, help=argparse.SUPPRESS)
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
          f"{'alle regels incl. best-practice' if not tags else 'alleen WCAG A/AA'}",
          flush=True)

    # Hervat na een zelfherstart: de reaper heeft alles tot en met de hangende
    # site al weggeschreven, dus die lezen we terug.
    results = []
    if args.resume_from and Path(args.out).exists():
        try:
            results = json.loads(Path(args.out).read_text()).get("results", [])
            print(f"Hervat bij site {args.resume_from + 1}/{len(sites)} met "
                  f"{len(results)} eerdere resultaten "
                  f"(herstart {args.restarts}/{MAX_SCAN_RESTARTS})", flush=True)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Waarschuwing: deelbestand onleesbaar ({exc}); "
                  f"begin opnieuw vanaf site {args.resume_from + 1}", flush=True)

    # Waar de main thread nu mee bezig is; de reaper leest dit uit een eigen thread.
    current = {"index": args.resume_from, "site": None}

    def _reap_scan():
        """Laatste vangnet: een site hangt zo dat noch SIGALRM noch de
        chromium-kill de main thread lostrekt. Leg hem vast als timeout, schrijf
        weg en herstart de scan vanaf de site erna. Zie _reap_shard in
        scrape_footer.py voor dezelfde aanpak en de achtergrond."""
        hanger = current["site"]
        if hanger is not None:
            results.append({
                "name": hanger.get("name", hanger["url"]),
                "url": hanger["url"],
                "status": "timeout",
                "error": f"Onbreekbare hang > {SCAN_CAP_S}s; scan hervat",
            })
        naam = hanger["url"] if hanger else "onbekend"
        try:
            write_payload(args.out, results, tags)
        except Exception:  # noqa: BLE001
            pass

        resume_at = current["index"] + 1
        if args.restarts >= MAX_SCAN_RESTARTS or resume_at >= len(sites):
            print(f"\nWATCHDOG: {naam} hangt onbreekbaar; scan afgesloten met "
                  f"{len(results)} resultaten (geen herstart meer over).", flush=True)
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(0)

        print(f"\nWATCHDOG: {naam} hangt onbreekbaar; scan hervat bij site "
              f"{resume_at + 1}/{len(sites)} "
              f"(herstart {args.restarts + 1}/{MAX_SCAN_RESTARTS}).", flush=True)
        sys.stdout.flush()
        sys.stderr.flush()
        try:
            _kill_browser_processes()
        except Exception:  # noqa: BLE001
            pass
        os.execv(sys.executable,
                 [sys.executable] + _resume_argv(sys.argv, resume_at, args.restarts + 1))

    UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    with sync_playwright() as p:
        def new_browser():
            b = p.chromium.launch(headless=True)
            return b, b.new_context(user_agent=UA)

        def safe_new_browser():
            """new_browser onder een eigen cap.

            Een verse browser starten kan zélf hangen op een wedged driver, en
            dit draait in de except-tak, dus buiten de per-site-deadline. Dat is
            precies waar shard 4 en 9 van de scraper op sneuvelden (zie
            _recover_page in scrape_footer.py). Lukt het niet, dan is er binnen
            dit proces niets meer te redden en herstart de reaper de scan.
            """
            try:
                with site_deadline(RECOVERY_CAP_S, on_giveup=_reap_scan):
                    return new_browser()
            except SiteTimeout:
                print("  (browserherstel mislukt, scan herstart)", flush=True)
                _reap_scan()
                raise  # _reap_scan hoort niet terug te keren

        browser, context = new_browser()
        for i, site in enumerate(sites, 1):
            if i <= args.resume_from:
                continue
            current["index"], current["site"] = i - 1, site
            if not browser.is_connected():  # herstart na een crash
                print("  (browser herstart)", flush=True)
                browser, context = safe_new_browser()
            url = site["url"]
            name = site.get("name", url)
            page = context.new_page()
            page.set_default_timeout(NAVIGATION_TIMEOUT)
            rec = {"name": name, "url": url}
            t0 = time.time()
            try:
                # Harde wall-clock-cap om de losse Playwright-timeouts heen: die
                # dekken de axe-run in page.evaluate niet. Zie SCAN_CAP_S.
                with site_deadline(SCAN_CAP_S, on_giveup=_reap_scan):
                    violations, dom_elements = scan_site(page, url, axe_source, tags)
                rec["dom_elements"] = dom_elements
                rec["load_ms"] = int((time.time() - t0) * 1000)
                if violations is None:
                    rec["status"] = "niet-gerenderd"
                    print(f"[{i}/{len(sites)}] {name:<16} NIET GERENDERD "
                          f"({dom_elements} elem)", flush=True)
                else:
                    rec["status"] = "ok"
                    rec["violations"] = violations
                    rec["total_nodes"] = sum(v["nodes"] for v in violations)
                    print(f"[{i}/{len(sites)}] {name:<16} {len(violations):>3} regels, "
                          f"{rec['total_nodes']:>4} elem, dom={dom_elements} "
                          f"({time.time()-t0:.1f}s)", flush=True)
            except SiteTimeout:
                # Cap-hit: niet te scannen, nooit "geen fouten gevonden". De
                # browser kan corrupt zijn, dus vers beginnen.
                rec["status"] = "timeout"
                rec["error"] = f"Per-site cap {SCAN_CAP_S}s overschreden"
                print(f"[{i}/{len(sites)}] {name:<16} CAP ({SCAN_CAP_S}s)", flush=True)
                try:
                    _kill_browser_processes()
                except Exception:  # noqa: BLE001
                    pass
                browser, context = safe_new_browser()
            except PlaywrightTimeout:
                rec["status"] = "timeout"
                print(f"[{i}/{len(sites)}] {name:<16} TIMEOUT", flush=True)
            except Exception as e:  # noqa: BLE001
                rec["status"] = "error"
                rec["error"] = str(e)[:200]
                print(f"[{i}/{len(sites)}] {name:<16} ERROR: {str(e)[:80]}", flush=True)
            finally:
                try:
                    page.close()
                except Exception:  # noqa: BLE001
                    pass
            results.append(rec)
            if len(results) % FLUSH_EVERY == 0:
                write_payload(args.out, results, tags)
        browser.close()

    write_payload(args.out, results, tags)

    rule_agg = aggregate(results)
    ok = [r for r in results if r["status"] == "ok"]
    print(f"\nGescand: {len(ok)}/{len(results)} geslaagd. Detail: {args.out}", flush=True)
    if ok:
        print("\nMeest voorkomende fouten (op hoeveel sites):")
        for rid, a in list(rule_agg.items())[:15]:
            sc = f"SC {a['sc']}" if a["sc"] else ""
            print(f"  {a['sites']:>2} sites  {a['nodes']:>5} elem  "
                  f"{(a['impact'] or '?'):<8} {rid}  {sc}")


if __name__ == "__main__":
    main()
