#!/usr/bin/env python3
"""Deterministische regressietest voor de verklaring-detector.

Draait classify_html() uit tools/scrape_footer.py tegen HTML-fixtures die elk
een bekend patroon vertegenwoordigen (echte verklaring, overlay-widget, lange
marketingtekst, JS-framework-link, asset-bestand, bot-challenge, geen
verklaring). Geen netwerk, geen Playwright: snel en herhaalbaar, zodat een
wijziging in de detector meteen aantoont of we een false positive of false
negative introduceren.

Gebruik:
    python tests/test_detector.py        # print confusion matrix, exit 1 bij fout
    pytest tests/test_detector.py         # zelfde cases als losse asserts
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.scrape_footer import classify_html, statement_page_has_statement  # noqa: E402

# Een gewone footer met genoeg links zodat de <5-links-challengeregel niet afgaat.
_FILLER_LINKS = "".join(f'<a href="/p/{i}">Item {i}</a>' for i in range(8))


def _page(footer_inner="", body_extra="", filler=True):
    links = _FILLER_LINKS if filler else ""
    return (
        "<html><body>"
        f"<nav>{links}</nav>{body_extra}"
        f"<footer>{footer_inner}</footer>"
        "</body></html>"
    )


# (naam, base_url, html, verwacht_has_statement, verwacht_status, url_bevat)
CASES = [
    # ---- Positief: moet als verklaring herkend worden ----
    ("NL footer-label", "https://shop.nl",
     _page('<a href="/toegankelijkheidsverklaring">Toegankelijkheidsverklaring</a>'),
     True, "success", "toegankelijkheidsverklaring"),
    ("EN accessibility-statement", "https://shop.nl",
     _page('<a href="/accessibility-statement">Accessibility</a>'),
     True, "success", "accessibility-statement"),
    ("href-match, lege tekst (icoonlink)", "https://www.azerty.nl",
     _page('<a href="/klantenservice/voorwaarden/toegankelijkheidsverklaring"><span class="i"></span></a>'),
     True, "success", "toegankelijkheidsverklaring"),
    ("kort label 'Toegankelijkheid'", "https://www.swisssense.nl",
     _page('<a href="/toegankelijkheid">Toegankelijkheid</a>'),
     True, "success", "/toegankelijkheid"),
    ("cross-domein PDF (Foot Locker)", "https://www.footlocker.nl",
     _page('<a href="https://images.footlocker.com/dam/Accessibility_Statement_2025_NL.pdf">Toegankelijkheidsverklaring</a>'),
     True, "success", "Accessibility_Statement_2025_NL.pdf"),
    ("JS-framework: URL in JSON (MediaMarkt-PWA)", "https://www.mediamarkt.nl",
     _page(footer_inner="",
           body_extra=r'<script>window.__DATA__={"footer":[{"label":"Toegankelijkheidsverklaring",'
                      r'"url":"https://www.mediamarkt.nl/nl/legal/toegankelijkheidsverklaring"}]}</script>'),
     True, "success", "legal/toegankelijkheidsverklaring"),

    # ---- Negatief: moet GEEN verklaring opleveren (success, zonder) ----
    ("overlay-widget AccessiBe", "https://shop.nl",
     _page('<a href="https://accessibe.com/blog/knowledgebase/screen-reader-guide">Toegankelijkheid Screen-Reader Gids</a>'),
     False, "success", None),
    ("plugin-vendor dj-extensions", "https://duareds.nl",
     _page('<a href="https://dj-extensions.com/yootheme/dj-accessibility">Plugin voor webtoegankelijkheid</a>'),
     False, "success", None),
    ("lange marketingtekst met 'toegankelijkheid'", "https://wijnen.nl",
     _page('<a href="/product-tag/wijncadeau/">Wijn cadeaus. De populariteit komt voort uit '
           'de toegankelijkheid ervan, een goede fles wordt altijd gewaardeerd en is een '
           'geliefd cadeau bij elke gelegenheid het hele jaar door</a>'),
     False, "success", None),
    ("asset-only: a11y.js / accessibility.css", "https://shop.nl",
     _page(footer_inner='<script src="/js/dist/a11y.js"></script>'
           '<link rel="stylesheet" href="/wp-content/themes/x/accessibility/reduced-motion.css">'),
     False, "success", None),
    ("externe accessibility-CDN (ander domein)", "https://shop.nl",
     _page(body_extra='<script src="https://acsbapp.com/apps/accessibility-statement/app.js"></script>'),
     False, "success", None),
    ("gewone shop zonder verklaring", "https://shop.nl",
     _page('<a href="/contact">Contact</a><a href="/retour">Retourneren</a>'),
     False, "success", None),

    # ---- Niet te controleren: bot-challenge / lege render (<5 links) ----
    ("bot-challenge, weinig links", "https://www.kruidvat.nl",
     "<html><body><div class='footer'><a href='/verify'>Even geduld</a></div></body></html>",
     False, "error", None),
]


# Content-check op de gelinkte verklaringspagina (statement_page_has_statement):
# (naam, paginatekst, verwacht_verklaring). Een footer-link is gevonden; de vraag
# is of de DOELPAGINA echt een verklaring bevat.
# (naam, paginatekst, verwacht_verklaring)
CONTENT_CASES = [
    ("echte verklaring (NL)",
     "Toegankelijkheidsverklaring. Wij streven ernaar dat onze website voldoet aan "
     "de toegankelijkheidsnorm WCAG 2.1 niveau AA en EN 301 549.", True),
    ("echte verklaring (EN)",
     "Accessibility statement. This website aims to conform to WCAG 2.1 level AA.", True),
    ("minimale verklaring zonder het woord 'verklaring'",
     "Deze website voldoet gedeeltelijk aan de toegankelijkheidsnorm. We werken aan "
     "de bekende tekortkomingen.", True),
    ("Decathlon-geval: alleen een aanvraagformulier",
     "Toegankelijkheid website. Vraag hier een toegankelijke versie van een document "
     "aan. Naam. E-mailadres. Welk document heb je nodig? Versturen.", False),
    ("cookie-/privacypagina (geen verklaring)",
     "Cookiebeleid. We gebruiken cookies om je ervaring te verbeteren. Beheer je "
     "voorkeuren. Privacyverklaring.", False),
]


def run():
    rows = []
    ok = True
    for name, base, html, exp_has, exp_status, contains in CASES:
        r = classify_html(html, base)
        has = r["has_statement"]
        status = r["scrape_status"]
        passed = (has == exp_has) and (status == exp_status)
        if passed and contains:
            passed = contains in (r.get("statement_url") or "")
        ok = ok and passed
        rows.append((passed, name, exp_has, has, exp_status, status, r.get("statement_url")))

    # Confusion matrix over has_statement
    tp = sum(1 for p, n, eh, h, *_ in rows if eh and h)
    fp = sum(1 for p, n, eh, h, *_ in rows if (not eh) and h)
    fn = sum(1 for p, n, eh, h, *_ in rows if eh and (not h))
    tn = sum(1 for p, n, eh, h, *_ in rows if (not eh) and (not h))

    for passed, name, eh, h, es, st, su in rows:
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {name:42} verwacht={eh!s:5} kreeg={h!s:5} status={st}")
        if not passed:
            print(f"         -> statement_url={su!r}")

    print(f"\n  TP={tp}  FP={fp}  FN={fn}  TN={tn}   ({len(rows)} cases)")
    if fp:
        print("  WAARSCHUWING: false positive(s) - de monitor zou een verklaring claimen die er niet is.")
    if fn:
        print("  WAARSCHUWING: false negative(s) - de monitor zou een echte verklaring missen.")

    # Content-check op de gelinkte verklaringspagina (Decathlon-geval)
    print("\n  Content-check verklaringspagina:")
    for name, text, expected in CONTENT_CASES:
        got = statement_page_has_statement(text)
        passed = got == expected
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {name:48} verwacht={expected!s:5} kreeg={got!s:5}")

    print("\n  " + ("ALLES GOED" if ok else "REGRESSIE GEDETECTEERD"))
    return ok


# pytest-ingang: elke case een aparte assert
def test_detector_cases():
    for name, base, html, exp_has, exp_status, contains in CASES:
        r = classify_html(html, base)
        assert r["has_statement"] == exp_has, f"{name}: has_statement"
        assert r["scrape_status"] == exp_status, f"{name}: scrape_status"
        if contains:
            assert contains in (r.get("statement_url") or ""), f"{name}: url bevat {contains}"


def test_statement_page_content():
    for name, text, expected in CONTENT_CASES:
        assert statement_page_has_statement(text) == expected, name


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
