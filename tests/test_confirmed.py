#!/usr/bin/env python3
"""Tests voor de bevestigd-groen-lijst (overslaan + sync), zonder netwerk.

    python tests/test_confirmed.py
    pytest tests/test_confirmed.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tools.scrape_footer as sf  # noqa: E402
from tools.sync_confirmed import sync_confirmed  # noqa: E402

NOW = "2026-06-23T12:00:00+00:00"
TODAY = "2026-06-23"


def test_freshness_window():
    assert sf._confirmed_is_fresh("2026-06-23", NOW) is True
    assert sf._confirmed_is_fresh("2026-06-10", NOW) is True          # 13 dagen
    assert sf._confirmed_is_fresh("2026-05-23", NOW) is False         # 31 dagen
    assert sf._confirmed_is_fresh("rommel", NOW) is False


def test_injected_result_shape():
    entry = {"url": "https://x.nl", "statement_url": "https://x.nl/toeg",
             "statement_link_text": "Toegankelijkheidsverklaring", "confirmed": "2026-06-20"}
    r = sf._confirmed_result_for({"name": "X", "url": "https://x.nl", "category": "mode"}, entry)
    assert r["has_statement"] is True
    assert r["scrape_status"] == "success"
    assert r["confirmed"] is True
    assert r["statement_url"] == "https://x.nl/toeg"
    assert r["last_checked"].startswith("2026-06-20")


def _fake_ds(tmp, confirmed_sites, results_webshops):
    cf = Path(tmp) / "confirmed.json"
    rf = Path(tmp) / "results.json"
    cf.write_text(json.dumps({"sites": confirmed_sites}), encoding="utf-8")
    rf.write_text(json.dumps({"webshops": results_webshops}), encoding="utf-8")
    return {"key": "webshops", "confirmed_file": cf, "results_file": rf}


def test_sync_add_refresh_remove_keep():
    with tempfile.TemporaryDirectory() as tmp:
        confirmed = [
            {"name": "Oud-groen", "url": "https://oud.nl", "statement_url": "https://oud.nl/t",
             "statement_link_text": "Toegankelijkheidsverklaring", "confirmed": "2026-05-01"},
            {"name": "Weg-verklaring", "url": "https://weg.nl", "statement_url": "https://weg.nl/t",
             "statement_link_text": "Toegankelijkheidsverklaring", "confirmed": "2026-05-01"},
            {"name": "Challenge", "url": "https://bot.nl", "statement_url": "https://bot.nl/t",
             "statement_link_text": "Toegankelijkheidsverklaring", "confirmed": "2026-05-01"},
        ]
        results = [
            # overgeslagen: niet aanraken (blijft 2026-05-01)
            {"name": "Oud-groen", "url": "https://oud.nl", "category": "mode", "has_statement": True,
             "statement_url": "https://oud.nl/t", "statement_link_text": "x",
             "scrape_status": "success", "error": None, "confirmed": True},
            # echt gescrapt, verklaring weg -> verwijderen
            {"name": "Weg-verklaring", "url": "https://weg.nl", "category": "mode", "has_statement": False,
             "statement_url": None, "statement_link_text": None, "scrape_status": "success", "error": None},
            # echt gescrapt, challenge -> behouden
            {"name": "Challenge", "url": "https://bot.nl", "category": "mode", "has_statement": False,
             "statement_url": None, "statement_link_text": None, "scrape_status": "error", "error": "challenge"},
            # nieuw groen -> toevoegen met vandaag
            {"name": "Nieuw", "url": "https://nieuw.nl", "category": "mode", "has_statement": True,
             "statement_url": "https://nieuw.nl/toegankelijkheidsverklaring", "statement_link_text": "T",
             "scrape_status": "success", "error": None},
        ]
        ds = _fake_ds(tmp, confirmed, results)
        sync_confirmed(ds, today=TODAY)
        out = {e["url"]: e for e in json.loads(Path(ds["confirmed_file"]).read_text())["sites"]}

        assert "https://oud.nl" in out and out["https://oud.nl"]["confirmed"] == "2026-05-01"  # ongemoeid
        assert "https://weg.nl" not in out                                                      # verwijderd
        assert "https://bot.nl" in out and out["https://bot.nl"]["confirmed"] == "2026-05-01"  # behouden
        assert "https://nieuw.nl" in out and out["https://nieuw.nl"]["confirmed"] == TODAY      # toegevoegd


def run():
    tests = [test_freshness_window, test_injected_result_shape,
             test_sync_add_refresh_remove_keep]
    ok = True
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
        except AssertionError as e:
            ok = False
            print(f"  FAIL {t.__name__}: {e}")
    print("\n  " + ("ALLES GOED" if ok else "FOUTEN"))
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
