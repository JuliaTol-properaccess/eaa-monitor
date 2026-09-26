#!/usr/bin/env python3
"""Tests voor de meta descriptions van alle pagina's in public/.

    python tests/test_meta_descriptions.py
    pytest tests/test_meta_descriptions.py

Achtergrond: op 26 september 2026 stonden 27 van de 43 pagina's boven de 155
tekens, waaronder de homepage met 246. Google kapt zo'n zoekresultaat af, dus de
reden om te klikken viel er vaak net buiten. Deze test houdt dat tegen bij de
volgende pagina die erbij komt.

De test leest de HTML die in git staat. De meetlijsten in public/lijst/ staan
niet in git (de deploy bouwt ze), dus die komen alleen langs als je ze lokaal
hebt gebouwd; de lengte van hun tekst zit in tools/build_lijsten.py.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.build_articles import MAX_META_DESCRIPTION  # noqa: E402

PUBLIC = ROOT / "public"
DESCRIPTION = re.compile(r'<meta name="description" content="(.*?)">', re.S)

# Ruim onder het minimum dat een zinnige omschrijving nodig heeft. Een lege of
# half gevulde description is net zo schadelijk als een te lange: dan kiest
# Google zelf een stuk tekst uit de pagina.
MIN_META_DESCRIPTION = 60


def _paginas():
    return sorted(PUBLIC.rglob("*.html"))


def _description(pad: Path):
    treffers = DESCRIPTION.findall(pad.read_text(encoding="utf-8"))
    return treffers


def test_elke_pagina_heeft_precies_een_description():
    fouten = []
    for pad in _paginas():
        aantal = len(_description(pad))
        if aantal != 1:
            fouten.append(f"{pad.relative_to(ROOT)}: {aantal} description-tags")
    assert not fouten, "\n    " + "\n    ".join(fouten)


def test_geen_description_langer_dan_de_afkapgrens():
    fouten = []
    for pad in _paginas():
        for tekst in _description(pad):
            if len(tekst) > MAX_META_DESCRIPTION:
                fouten.append(
                    f"{pad.relative_to(ROOT)}: {len(tekst)} tekens "
                    f"(max {MAX_META_DESCRIPTION})"
                )
    assert not fouten, "\n    " + "\n    ".join(fouten)


def test_geen_description_te_kort():
    fouten = []
    for pad in _paginas():
        for tekst in _description(pad):
            if len(tekst) < MIN_META_DESCRIPTION:
                fouten.append(
                    f"{pad.relative_to(ROOT)}: {len(tekst)} tekens "
                    f"(minimaal {MIN_META_DESCRIPTION})"
                )
    assert not fouten, "\n    " + "\n    ".join(fouten)


def test_elke_description_is_uniek():
    gezien = {}
    fouten = []
    for pad in _paginas():
        for tekst in _description(pad):
            naam = str(pad.relative_to(ROOT))
            if tekst in gezien:
                fouten.append(f"{naam} heeft dezelfde tekst als {gezien[tekst]}")
            else:
                gezien[tekst] = naam
    assert not fouten, "\n    " + "\n    ".join(fouten)


def test_er_zijn_paginas_gevonden():
    # Een lege glob zou alle tests hierboven groen maken zonder iets te meten.
    assert len(_paginas()) > 30


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
