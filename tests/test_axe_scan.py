#!/usr/bin/env python3
"""Tests voor de WCAG-scan: aggregatie, wegschrijven en statusvertaling.

    python tests/test_axe_scan.py
    pytest tests/test_axe_scan.py

Achtergrond: de scan van 4 augustus 2026 liep tot de jobcap van 60 minuten
(alle runs ervoor deden 21-25 minuten) omdat één site hing en scan_axe.py geen
wall-clock-cap had. De losse Playwright-timeouts dekken de axe-run in
page.evaluate niet. De cap en de zelfherstart hergebruiken de watchdog van
scrape_footer.py; die is daar getest in tests/test_site_timeout.py.

De scan van 29 september 2026 liep alsnog tot de jobcap, nu van 90 minuten: de
cap dekte wel `scan_site`, maar niet het openen en sluiten van de pagina
eromheen. Na een gewone fout op site 15 hing `page.close()` in de finally, dus
buiten de inmiddels opgeheven deadline. Daarover gaat de laatste test hieronder.
"""

import json
import subprocess
import sys
import tempfile
import threading
import time
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


class _NepPagina:
    """Pagina-mock met precies de aanroepen die scan_site doet."""

    DOM = "() => document.querySelectorAll('*').length"

    def __init__(self, faalt=False, close_hangt=False):
        self.faalt, self.close_hangt = faalt, close_hangt
        self.gesloten = False

    def set_default_timeout(self, ms): pass
    def goto(self, *a, **kw): pass
    def wait_for_timeout(self, ms): pass
    def wait_for_load_state(self, *a, **kw): pass

    def evaluate(self, script, *args):
        if script == self.DOM:
            return 500                      # ruim boven MIN_DOM
        if script.startswith("async (opts)"):
            if self.faalt:
                raise RuntimeError("Page.evaluate: Execution context was "
                                   "destroyed, most likely because of a navigation")
            return {"violations": []}
        return None                         # de axe-injectie zelf

    def close(self):
        if self.close_hangt:
            threading.Event().wait()        # alleen de cap breekt dit af
        self.gesloten = True


class _NepContext:
    def __init__(self, browser): self._browser = browser
    def new_page(self): return self._browser.pw.volgende_pagina()
    def close(self): pass


class _NepBrowser:
    def __init__(self, pw): self.pw = pw
    def new_context(self, **kw): return _NepContext(self)
    def is_connected(self): return True
    def close(self): pass


class _NepPlaywright:
    """Vervangt sync_playwright(): geen chromium, geen netwerk."""

    def __init__(self, gedrag):
        self.gedrag, self.paginas, self.starts = list(gedrag), [], 0
        self.chromium = self

    def launch(self, **kw):
        self.starts += 1
        return _NepBrowser(self)

    def volgende_pagina(self):
        n = len(self.paginas)
        pagina = _NepPagina(**(self.gedrag[n] if n < len(self.gedrag) else {}))
        self.paginas.append(pagina)
        return pagina

    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_hangende_page_close_houdt_de_scan_niet_op():
    """Regressie van 29 september 2026.

    Site 15 (Annadiva.nl) gaf "Execution context was destroyed", en daarna kwam
    er 88 minuten geen regel meer uit de scan: `page.close()` in de finally hing
    op de wedged driver, buiten de per-site-cap. De run werd op de jobcap van 90
    minuten gecanceld, dus `data/axe-results.json` bleef tien dagen oud staan.

    De scan hoort hier door te lopen: de fout belandt als status 'error' en de
    volgende site wordt gewoon gescand, op een verse browser.
    """
    gedrag = [{}, {"faalt": True, "close_hangt": True}, {}]
    pw = _NepPlaywright(gedrag)
    bewaar = (sa.RECOVERY_CAP_S, sa._kill_browser_processes,
              sa.sync_playwright, sys.argv)
    with tempfile.TemporaryDirectory() as d:
        lijst, uit = Path(d) / "sites.json", Path(d) / "scan.json"
        lijst.write_text(json.dumps([
            {"name": "Een", "url": "https://een.nl"},
            {"name": "Hanger", "url": "https://hanger.nl"},
            {"name": "Drie", "url": "https://drie.nl"},
        ]))
        sa.RECOVERY_CAP_S = 1               # anders duurt de test 20 seconden
        sa._kill_browser_processes = lambda: False
        sa.sync_playwright = lambda: pw
        sys.argv = ["scan_axe.py", "--list", str(lijst), "--out", str(uit)]
        t0 = time.time()
        try:
            sa.main()
        finally:
            (sa.RECOVERY_CAP_S, sa._kill_browser_processes,
             sa.sync_playwright, sys.argv) = bewaar
        duur = time.time() - t0
        data = json.loads(uit.read_text())

    assert [r["status"] for r in data["results"]] == ["ok", "error", "ok"], \
        f"onverwachte statussen: {[r['status'] for r in data['results']]}"
    assert duur < 30, f"de scan hing {duur:.0f}s in page.close()"
    assert len(pw.paginas) == 3, "site 3 is nooit geopend"
    assert pw.paginas[2].gesloten, "de laatste pagina is niet netjes gesloten"


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
