#!/usr/bin/env python3
"""Tests voor tools/maak_carousel.py, zonder Chromium.

    python3 tests/test_maak_carousel.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.maak_carousel import (  # noqa: E402
    SJABLOON, datum_lang, getal, kandidaten, posttekst, vul_sjabloon)


def sector(naam, noun, met, gecontroleerd, pct, klein, punt, toen):
    return {"naam": naam, "noun": noun, "met": met, "gecontroleerd": gecontroleerd,
            "pct_met": pct, "klein": klein,
            "vorige_editie": {"datum": "2026-11-02", "met": 3, "pct_punt": punt,
                              "pct_met_toen": toen}}


def cijfers(punt_groot=0):
    totaal = sector("totaal", "sites", 120, 2000, 6, False, 0, 6)
    totaal.update(totaal=2500, niet_te_controleren=500,
                  lijn=[{"datum": "2026-11-02", "gecontroleerd": 2100},
                        {"datum": "2026-11-23", "gecontroleerd": 2000}])
    return {
        "peildatum": "2026-11-23",
        "totaal": totaal,
        "sectoren": [
            sector("E-commerce", "webshops", 100, 1980, 5, False, punt_groot, 5 - punt_groot),
            sector("Telecom", "telecomaanbieders", 20, 20, 100, True, 10, 90),
        ],
        "wcag_scan": {"scandatum": "2026-11-24", "total": 120, "fouten": 80,
                      "schoon": 30, "niet_scanbaar": 10, "pct_fouten_van_gescand": 73},
        "bron": {"ref": "origin/main", "bestanden": ["data/history.json"]},
    }


def test_datum_en_getal():
    assert datum_lang("2026-11-03") == "3 november 2026"
    assert getal(10271) == "10.271" and getal(42) == "42"


def test_vul_sjabloon_vervangt_alleen_het_blok():
    html = SJABLOON.read_text(encoding="utf-8")
    c = cijfers()
    c["vreemd"] = "</script><b>"
    uit = vul_sjabloon(html, c)
    m = re.search(r'id="cijfers">\n(.*?)\n</script>', uit, re.S)
    assert json.loads(m.group(1))["peildatum"] == "2026-11-23"
    assert "</script><b>" not in m.group(1)
    assert "tools/maak_carousel.py vult dit blok" not in uit
    voor, na = html.split("<!-- CIJFERS-BEGIN -->")[0], html.split("<!-- CIJFERS-EIND -->")[1]
    assert uit.startswith(voor) and uit.endswith(na)


def test_vul_sjabloon_weigert_zonder_blok():
    try:
        vul_sjabloon("<html></html>", cijfers())
    except ValueError:
        return
    raise AssertionError("geen fout zonder CIJFERS-blok")


def test_kandidaten_drempel_en_kleine_groep():
    rustig = kandidaten(cijfers(punt_groot=2))
    assert any(r.startswith("Geen verschil") for r in rustig)
    # telecom gaat +10, maar is klein: geen kandidaat
    assert not any(r.startswith("Telecom:") for r in rustig)
    druk = kandidaten(cijfers(punt_groot=-4))
    assert any(r.startswith("E-commerce: 9% -> 5% (-4 procentpunt") for r in druk)
    assert any("2.100 -> 2.000" in r for r in druk)


def test_posttekst():
    tekst = posttekst(cijfers())
    assert "peildatum: 2026-11-23" in tekst and "status: concept" in tekst
    assert "[WAT VIEL OP: vul zelf in]" in tekst
    assert "120 van de 2.000" in tekst and "webshops 5%" in tekst
    assert "telecomaanbieders" not in tekst.split("## Posttekst")[1].split("<!--")[0]
    assert "80 van de 110" in tekst
    for verboden in ("—", "eerlijk", "Eerlijk"):
        assert verboden not in tekst


if __name__ == "__main__":
    for naam, f in list(globals().items()):
        if naam.startswith("test_"):
            f()
            print("ok", naam)
