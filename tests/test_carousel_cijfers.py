#!/usr/bin/env python3
"""Tests voor tools/carousel_cijfers.py.

    python tests/test_carousel_cijfers.py
    pytest tests/test_carousel_cijfers.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.carousel_cijfers import bereken, sectoren_uit_bron  # noqa: E402

BRON = '''
DATASETS = {
    "groot": {
        "history_file": DATA_DIR / "history.json",
        "summary_heading": "E-commerce · ACM-toezicht",
        "noun": "webshops",
    },
    "klein": {
        "history_file": DATA_DIR / "history-klein.json",
        "summary_heading": "Personenvervoer · ILT-toezicht",
        "noun": "vervoerders",
    },
}
'''


def rij(datum, met, zonder, fout):
    return {"date": datum, "total": met + zonder + fout, "with_statement": met,
            "without_statement": zonder, "errors": fout, "pct_with": 0}


DATA = ["2026-08-31", "2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28", "2026-10-05"]
HISTORIES = {
    # 6 metingen; laatste: 30 met, 70 zonder, 900 niet te controleren
    "groot": [rij(d, 20 + 2 * i, 80 - 2 * i, 900) for i, d in enumerate(DATA)],
    "klein": [rij(d, 5 + (i % 2), 11 - (i % 2), 4) for i, d in enumerate(DATA)],
}
AXE = {"generated": "2026-10-06", "summary": {"total": 10, "fouten": 6, "schoon": 3,
                                             "niet_scanbaar": 1, "pct_fouten_van_gescand": 67}}


def uitkomst():
    return bereken(HISTORIES, sectoren_uit_bron(BRON), AXE)


def test_sectoren_uit_bron():
    s = sectoren_uit_bron(BRON)
    assert [x["key"] for x in s] == ["groot", "klein"]
    assert s[0]["naam"] == "E-commerce" and s[0]["toezicht"] == "ACM-toezicht"
    assert s[1]["history_file"] == "data/history-klein.json"


def test_percentage_over_gecontroleerd():
    g = uitkomst()["sectoren"][0]
    assert (g["met"], g["zonder"], g["niet_te_controleren"]) == (30, 70, 900)
    assert g["gecontroleerd"] == 100
    assert g["pct_met"] == 30  # niet 3 (30 van 1000)
    assert g["totaal"] == 1000


def test_vorige_editie_drie_metingen_terug_en_vlag_klein():
    u = uitkomst()
    g, k = u["sectoren"]
    assert u["peildatum"] == "2026-10-05"
    assert g["vorige_editie"]["datum"] == "2026-09-14"
    assert g["vorige_editie"]["pct_punt"] == 30 - 24
    assert not g["klein"] and k["klein"]


def test_lijn_vanaf_7_september():
    u = uitkomst()
    lijn = u["sectoren"][0]["lijn"]
    assert lijn[0]["datum"] == "2026-09-07" and len(lijn) == 5
    t = u["totaal"]
    assert [p["datum"] for p in t["lijn"]] == DATA[1:]
    assert t["met"] == 30 + 6 and t["gecontroleerd"] == 100 + 16
    assert t["pct_met"] == round(100 * 36 / 116)
    assert t["eerste_meting"]["datum"] == "2026-09-07"


def test_afronden_half_naar_boven():
    from tools.carousel_cijfers import pct
    assert pct(5, 3) == 63  # 62,5
    assert pct(1, 2) == 33
    assert pct(0, 0) is None


def test_wcag_scan():
    w = uitkomst()["wcag_scan"]
    assert (w["total"], w["fouten"], w["schoon"], w["niet_scanbaar"]) == (10, 6, 3, 1)
    assert w["scandatum"] == "2026-10-06"


def test_waarschuwing_bij_achterlopende_sector():
    h = {"groot": HISTORIES["groot"], "klein": HISTORIES["klein"][:-1]}
    u = bereken(h, sectoren_uit_bron(BRON), AXE)
    assert any("klein" in w for w in u["waarschuwingen"])


if __name__ == "__main__":
    for naam, f in list(globals().items()):
        if naam.startswith("test_"):
            f()
            print("ok", naam)
