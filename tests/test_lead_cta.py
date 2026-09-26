#!/usr/bin/env python3
"""Tests voor de lead-CTA op de sector- en hulppagina's.

    python tests/test_lead_cta.py
    pytest tests/test_lead_cta.py

De monitorpagina's zijn handgeschreven en hebben elk hun eigen kopie van het
CTA-blok, net als de header en de footer. Zonder test loopt zo'n kopie stil uit
elkaar: dat is eerder gebeurd met de navigatie (zie CLAUDE.md, "Navigatie: twee
plekken, geen één"). Deze test controleert per pagina dat er precies één CTA
staat, dat hij naar het offerteformulier wijst en dat dat anker bestaat.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.build_articles import INTAKE_HREF  # noqa: E402

PUBLIC = ROOT / "public"

SECTOREN = ["monitor", "monitor-financieel", "monitor-telecom", "monitor-vervoer",
            "monitor-media", "monitor-ebooks", "monitor-reizen"]
# Sector- en hulppagina's: de pagina's waar een bezoeker zijn eigen organisatie
# opzoekt of hulp zoekt. tools.html en wcag-audit.html komen uit build_hulp.py
# en build_auditbureaus.py.
CTA_PAGINAS = (
    [f"{s}.html" for s in SECTOREN]
    + [f"en/{s}.html" for s in SECTOREN]
    + ["tools.html", "wcag-audit.html"]
)

ANKER_PAGINA = "hulp-nodig.html"
ANKER = INTAKE_HREF.split("#", 1)[1]


def _html(naam):
    return (PUBLIC / naam).read_text(encoding="utf-8")


def test_elke_sector_en_hulppagina_heeft_een_cta():
    fouten = []
    for naam in CTA_PAGINAS:
        aantal = _html(naam).count('aria-labelledby="intake-heading"')
        if aantal != 1:
            fouten.append(f"{naam}: {aantal} CTA-secties")
    assert not fouten, "\n    " + "\n    ".join(fouten)


def test_de_cta_wijst_naar_het_offerteformulier():
    fouten = []
    for naam in CTA_PAGINAS:
        html = _html(naam)
        knoppen = re.findall(
            r'<a href="' + re.escape(INTAKE_HREF) + r'"([^>]*)>([^<]+)</a>', html
        )
        if len(knoppen) != 1:
            fouten.append(f"{naam}: {len(knoppen)} links naar {INTAKE_HREF}")
            continue
        attrs, label = knoppen[0]
        if "utrecht-button--primary-action" not in attrs:
            fouten.append(f"{naam}: de CTA is geen primaire knop")
        if len(label.strip()) < 10:
            fouten.append(f"{naam}: knoplabel '{label}' zegt te weinig")
    assert not fouten, "\n    " + "\n    ".join(fouten)


def test_de_kop_van_de_cta_hoort_bij_de_sectie():
    # aria-labelledby wijst naar een id dat moet bestaan, anders heeft de
    # sectie geen toegankelijke naam.
    fouten = []
    for naam in CTA_PAGINAS:
        html = _html(naam)
        if html.count('id="intake-heading"') != 1:
            fouten.append(f"{naam}: geen of dubbele id=intake-heading")
    assert not fouten, "\n    " + "\n    ".join(fouten)


def test_het_anker_op_de_hulppagina_bestaat():
    html = _html(ANKER_PAGINA)
    assert html.count(f'id="{ANKER}"') == 1, \
        f"{ANKER_PAGINA} mist id=\"{ANKER}\", de CTA's wijzen dan naar niets"


def test_engelse_cta_meldt_de_taal_van_het_formulier():
    # Het offerteformulier is Nederlands. Een Engelse bezoeker hoort dat te
    # weten voordat hij klikt, en de link krijgt hreflang mee.
    fouten = []
    for s in SECTOREN:
        html = _html(f"en/{s}.html")
        blok = html[html.index('aria-labelledby="intake-heading"'):]
        blok = blok[:blok.index("</section>")]
        if 'hreflang="nl"' not in blok:
            fouten.append(f"en/{s}.html: de CTA-link mist hreflang=nl")
        if "(NL)" not in blok or "in Dutch" not in blok:
            fouten.append(f"en/{s}.html: de CTA zegt niet dat het formulier Nederlands is")
    assert not fouten, "\n    " + "\n    ".join(fouten)


def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL {t.__name__}: {exc}")
    print("\n  ALLES GOED" if not failed else f"\n  {failed} test(s) mislukt")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())
