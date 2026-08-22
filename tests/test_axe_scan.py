#!/usr/bin/env python3
"""Tests voor de WCAG-scan: aggregatie, wegschrijven en statusvertaling.

    python tests/test_axe_scan.py
    pytest tests/test_axe_scan.py

Achtergrond: de scan van 4 augustus 2026 liep tot de jobcap van 60 minuten
(alle runs ervoor deden 21-25 minuten) omdat één site hing en scan_axe.py geen
wall-clock-cap had. De losse Playwright-timeouts dekken de axe-run in
page.evaluate niet. De cap en de zelfherstart hergebruiken de watchdog van
scrape_footer.py; die is daar getest in tests/test_site_timeout.py.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tools.scan_axe as sa  # noqa: E402


def _violation(rule="color-contrast", nodes=3):
    return {"id": rule, "impact": "serious", "sc": "1.4.3",
            "help": "https://x", "nodes": nodes}


def test_aggregate_telt_alleen_geslaagde_scans():
    results = [
        {"status": "ok", "violations": [_violation(nodes=3)]},
        {"status": "ok", "violations": [_violation(nodes=2)]},
        {"status": "timeout"},                       # cap-hit
        {"status": "niet-gerenderd"},                # bot-muur
        {"status": "ok", "violations": []},          # schoon
    ]
    agg = sa.aggregate(results)
    assert agg["color-contrast"]["sites"] == 2
    assert agg["color-contrast"]["nodes"] == 5


def test_aggregate_sorteert_op_aantal_sites():
    results = [
        {"status": "ok", "violations": [_violation("label", 1)]},
        {"status": "ok", "violations": [_violation("image-alt", 1),
                                        _violation("label", 1)]},
        {"status": "ok", "violations": [_violation("label", 1)]},
    ]
    assert list(sa.aggregate(results))[0] == "label"


def test_write_payload_is_atomair_en_leesbaar_terug():
    """De reaper schrijft hiermee weg vlak voor een execv; een half bestand
    zou de hervatte run zijn eerdere resultaten kosten."""
    results = [{"name": "A", "url": "https://a.nl", "status": "ok",
                "violations": [_violation()]}]
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "sub" / "scan.json"
        sa.write_payload(out, results, ["wcag2a"])
        assert not list(out.parent.glob("*.tmp")), "tijdelijk bestand bleef staan"
        back = json.loads(out.read_text())
        assert back["scanned"] == 1
        assert back["results"] == results
        assert back["rule_frequency"]["color-contrast"]["sites"] == 1


def test_niet_gescande_site_telt_nooit_als_schoon():
    """Kernregel: alleen een geslaagde scan mag 'geen fouten gevonden' worden.

    Een cap-hit of hang levert status 'timeout'; die hoort in de overlay als
    'niet-scanbaar' te landen, niet als 'schoon'.
    """
    scan = {"axe_tags": ["wcag2a"], "scanned": 4, "rule_frequency": {}, "results": [
        {"name": "Fout", "url": "https://fout.nl", "status": "ok",
         "violations": [_violation()]},
        {"name": "Schoon", "url": "https://schoon.nl", "status": "ok",
         "violations": []},
        {"name": "Cap", "url": "https://cap.nl", "status": "timeout"},
        {"name": "Muur", "url": "https://muur.nl", "status": "niet-gerenderd"},
    ]}
    with tempfile.TemporaryDirectory() as d:
        inp, out = Path(d) / "scan.json", Path(d) / "overlay.json"
        inp.write_text(json.dumps(scan))
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "build_axe_overlay.py"),
             "--in", str(inp), "--out", str(out)],
            check=True, capture_output=True, cwd=ROOT)
        overlay = json.loads(out.read_text())

    statuses = {s["url"]: s["status"] for s in overlay["sites"].values()}
    assert statuses["https://cap.nl"] == "niet-scanbaar"
    assert statuses["https://muur.nl"] == "niet-scanbaar"
    assert statuses["https://fout.nl"] == "fouten"
    assert statuses["https://schoon.nl"] == "schoon"

    s = overlay["summary"]
    assert s["niet_scanbaar"] == 2
    # Het percentage rekent over gescande sites, niet over het totaal.
    assert s["pct_fouten_van_gescand"] == 50


def test_caps_zijn_gezet():
    assert sa.SCAN_CAP_S > sa.NAVIGATION_TIMEOUT / 1000, \
        "de wall-clock-cap moet ruimer zijn dan de navigatietimeout"
    assert 0 < sa.MAX_SCAN_RESTARTS <= 10
    assert sa.FLUSH_EVERY > 0


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
