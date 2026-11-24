#!/usr/bin/env python3
"""Maak een editie van de driewekelijkse LinkedIn-carousel van de EAA-monitor.

    python3 tools/maak_carousel.py                 # cijfers van origin/main
    python3 tools/maak_carousel.py --ref werkmap   # cijfers uit deze checkout
    python3 tools/maak_carousel.py --geen-pdf      # alleen html, json en post.md

Schrijft naar social-posts/<peildatum>_eaa-monitor-editie/:
  cijfers.json   uitvoer van tools/carousel_cijfers.py
  carousel.html  het sjabloon met de cijfers erin
  carousel.pdf   5 pagina's van 1080x1350 px, afgedrukt met headless Chromium
  post.md        concept-posttekst; "wat viel op" vult Julia zelf in

Het script verzint geen observaties. Verschillen boven de drempel komen als
kandidaat in een commentaarregel in post.md, niet in de posttekst.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.carousel_cijfers import STANDAARD_VANAF, laad  # noqa: E402

SJABLOON = ROOT / "social-posts" / "carousel-sjabloon" / "carousel.html"
UITMAP = ROOT / "social-posts"
AANTAL_PAGINAS = 5
# Kandidaat voor "wat viel op": minstens zoveel procentpunt verschil
# met de vorige editie, alleen bij sectoren van 30 sites of meer.
DREMPEL_PCT_PUNT = 3

MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
           "augustus", "september", "oktober", "november", "december"]
BLOK = re.compile(r"(<!-- CIJFERS-BEGIN -->).*?(<!-- CIJFERS-EIND -->)", re.S)
HASHTAGS = "#toegankelijkheid #WCAG #EuropeanAccessibilityAct #digitaletoegankelijkheid #ecommerce"


def datum_lang(iso):
    j, m, d = iso.split("-")
    return f"{int(d)} {MAANDEN[int(m) - 1]} {j}"


def getal(n):
    return f"{n:,}".replace(",", ".")


def vul_sjabloon(html, cijfers):
    """Vervang het blok tussen CIJFERS-BEGIN en CIJFERS-EIND door de cijfers."""
    if len(BLOK.findall(html)) != 1:
        raise ValueError("het sjabloon moet precies één CIJFERS-blok hebben")
    data = json.dumps(cijfers, ensure_ascii=False, indent=2).replace("</", "<\\/")
    blok = f'\\1\n<script type="application/json" id="cijfers">\n{data}\n</script>\n\\2'
    return BLOK.sub(lambda m: m.expand(blok), html)


def noemer_toen(sector, datum):
    for punt in sector.get("lijn", []):
        if punt["datum"] == datum:
            return punt["gecontroleerd"]
    return None


def kandidaten(cijfers):
    """Regels voor het commentaar onder "wat viel op". Feiten, geen duiding."""
    regels = []
    groepen = [("totaal", cijfers["totaal"], False)] + [
        (s["naam"], s, s["klein"]) for s in cijfers["sectoren"]]
    for naam, s, klein in groepen:
        v = s["vorige_editie"]
        if klein or abs(v["pct_punt"]) < DREMPEL_PCT_PUNT:
            continue
        regels.append(f"{naam}: {v['pct_met_toen']}% -> {s['pct_met']}% "
                      f"({v['pct_punt']:+d} procentpunt sinds {datum_lang(v['datum'])})")
    if not regels:
        regels.append(f"Geen verschil van {DREMPEL_PCT_PUNT} procentpunt of meer bij "
                      "sectoren van 30 sites of meer, sinds de vorige editie.")
    t = cijfers["totaal"]
    v = t["vorige_editie"]
    regels.append(f"Ter info, totaal: {v['met']:+d} sites met verklaring sinds "
                  f"{datum_lang(v['datum'])}.")
    toen = noemer_toen(t, v["datum"])
    if toen is not None and toen != t["gecontroleerd"]:
        regels.append(f"Ter info, de noemer veranderde: {getal(toen)} -> "
                      f"{getal(t['gecontroleerd'])} gecontroleerde sites. Een verschil "
                      "in procenten komt deels daardoor.")
    kleine = [s["naam"] for s in cijfers["sectoren"] if s["klein"]]
    if kleine:
        regels.append("Kleine groepen (onder 30 sites), daar is één site al "
                      "meerdere procentpunten: " + ", ".join(kleine) + ".")
    return regels


def posttekst(cijfers):
    t, w = cijfers["totaal"], cijfers["wcag_scan"]
    peil = datum_lang(cijfers["peildatum"])
    gescand = w["total"] - w["niet_scanbaar"]
    groot = [s for s in cijfers["sectoren"] if not s["klein"]]
    per_sector = ", ".join(f"{s['noun']} {s['pct_met']}%" for s in groot)
    commentaar = "\n".join(f"     - {r}" for r in kandidaten(cijfers))
    bronnen = "\n".join(f"  - {b}" for b in cijfers["bron"]["bestanden"])

    return f"""---
titel: "EAA-monitor, stand van de telling {peil}"
soort: linkedin-document
taal: nl
status: concept
peildatum: {cijfers['peildatum']}
scandatum: {w['scandatum']}
bron_ref: {cijfers['bron']['ref']}
bronbestanden:
{bronnen}
---

# LinkedIn-post: EAA-monitor, stand van de telling {peil}

**Format:** documentbericht, `carousel.pdf`, {AANTAL_PAGINAS} pagina's van 1080x1350.
**Cijfers:** `cijfers.json`, meting van {peil}, WCAG-scan van {datum_lang(w['scandatum'])}. Vergelijk ze vlak voor publicatie met eaa-monitor.nl.

---

## Posttekst

We volgen {getal(t['totaal'])} Nederlandse websites in {len(cijfers['sectoren'])} sectoren. Elke week kijken we of er een toegankelijkheidsverklaring in de footer staat.

Op {peil} had {t['pct_met']}% van de sites die we konden controleren er een: {getal(t['met'])} van de {getal(t['gecontroleerd'])}.

Per sector: {per_sector}. De kleinere sectoren staan in de carousel, met het aantal sites erbij.

[WAT VIEL OP: vul zelf in]
<!-- Kandidaten, uit de cijfers gerekend:
{commentaar}
-->

Sites met een verklaring scannen we ook automatisch op WCAG-fouten. Bij {getal(w['fouten'])} van de {getal(gescand)} gescande sites vond de scan minstens één fout. Dat is {w['pct_fouten_van_gescand']}%. Een automatische scan vindt een deel van de fouten. Vindt de scan niets, dan weet je nog niet of de site toegankelijk is.

Zoek je eigen site op via eaa-monitor.nl.

<!-- Geen maker-attributie (Flonam) in post of visuals, op verzoek. -->

{HASHTAGS}
"""


def drukaf(html_pad, pdf_pad):
    """Druk het gevulde sjabloon af naar PDF met headless Chromium (Playwright)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        pagina = browser.new_page(viewport={"width": 1080, "height": 1350})
        pagina.goto(html_pad.resolve().as_uri(), wait_until="load")
        pagina.evaluate("document.fonts.ready")
        n = pagina.locator(".slide").count()
        if n != AANTAL_PAGINAS:
            raise RuntimeError(f"{n} slides in de pagina, verwacht {AANTAL_PAGINAS}")
        pagina.pdf(path=str(pdf_pad), prefer_css_page_size=True, print_background=True,
                   display_header_footer=False, tagged=True)
        browser.close()


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ref", default="origin/main",
                   help="git-ref voor de cijfers, of 'werkmap' voor de bestanden op schijf")
    p.add_argument("--vanaf", default=STANDAARD_VANAF, help="begin van de lijn (JJJJ-MM-DD)")
    p.add_argument("--geen-pdf", action="store_true", help="sla het afdrukken over")
    args = p.parse_args()

    cijfers = laad(args.ref, args.vanaf)
    for w in cijfers["waarschuwingen"]:
        print("let op:", w, file=sys.stderr)

    # Twee niveaus onder de repo, zodat de relatieve fontpaden in het sjabloon kloppen.
    uit = UITMAP / f"{cijfers['peildatum']}_eaa-monitor-editie"
    uit.mkdir(parents=True, exist_ok=True)
    (uit / "cijfers.json").write_text(
        json.dumps(cijfers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html_pad = uit / "carousel.html"
    html_pad.write_text(vul_sjabloon(SJABLOON.read_text(encoding="utf-8"), cijfers),
                        encoding="utf-8")
    post = uit / "post.md"
    if post.exists():
        print(f"{post.relative_to(ROOT)} bestaat al en blijft staan", file=sys.stderr)
    else:
        post.write_text(posttekst(cijfers), encoding="utf-8")
    if not args.geen_pdf:
        drukaf(html_pad, uit / "carousel.pdf")
    print(uit.relative_to(ROOT))


if __name__ == "__main__":
    main()
