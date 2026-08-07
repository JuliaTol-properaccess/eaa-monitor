#!/usr/bin/env python3
"""Tests voor de per-site-cap en de zelfherstart van een shard, zonder netwerk.

    python tests/test_site_timeout.py
    pytest tests/test_site_timeout.py

Achtergrond: de crons van 27 juli en 3 augustus 2026 liepen vast omdat
SiteTimeout van Exception erfde en daardoor werd opgeslokt door de brede
`except Exception` in check_webshop. De cap kwam nooit bij de hoofdlus aan, dus
het browserherstel draaide niet en elke volgende site liep de volle 90s vol.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tools.scrape_footer as sf  # noqa: E402

NOW = "2026-08-07T12:00:00+00:00"


class _HangingPage:
    """Page-mock die de per-site-cap simuleert op het punt waar hij echt vuurt."""

    def goto(self, *a, **kw):
        raise sf.SiteTimeout()


class _CrashingPage:
    """Page-mock die een gewone fout gooit: die hoort wél opgevangen te worden."""

    def goto(self, *a, **kw):
        raise RuntimeError("Target page, context or browser has been closed")


def test_sitetimeout_glipt_door_except_exception():
    """De kern van de regressie: een `except Exception` mag de cap niet slikken."""
    assert not issubclass(sf.SiteTimeout, Exception), \
        "SiteTimeout moet van BaseException erven, anders vangt check_webshop hem"
    assert issubclass(sf.SiteTimeout, BaseException)

    try:
        raise sf.SiteTimeout()
    except Exception:  # noqa: BLE001 - precies het vangnet uit check_webshop
        raise AssertionError("SiteTimeout werd door except Exception opgevangen")
    except sf.SiteTimeout:
        pass


def test_check_webshop_laat_cap_door():
    """check_webshop geeft geen 'error'-resultaat terug bij een cap-hit."""
    try:
        result = sf.check_webshop(_HangingPage(), "https://voorbeeld.nl")
    except sf.SiteTimeout:
        return  # correct: de hoofdlus kan nu herstellen
    raise AssertionError(
        f"cap werd opgeslokt en teruggegeven als {result['scrape_status']!r}")


def test_check_webshop_vangt_gewone_fouten_nog_steeds():
    """Regressie andersom: losse site-fouten mogen de shard niet doden."""
    result = sf.check_webshop(_CrashingPage(), "https://voorbeeld.nl")
    assert result["scrape_status"] == "error"
    assert result["has_statement"] is False


def test_timeout_entry_telt_niet_als_overtreder():
    shop = {"name": "Hanger", "url": "https://hangt.nl", "category": "overig"}
    entry = sf._timeout_entry(shop, NOW, "Onbreekbare hang")
    assert entry["scrape_status"] == "timeout"   # = niet te controleren
    assert entry["has_statement"] is False
    assert entry["url"] == "https://hangt.nl"
    assert entry["category"] == "overig"


def test_resume_argv_stapelt_niet():
    """Bij een tweede hang mogen de vlaggen niet opstapelen."""
    base = ["tools/scrape_footer.py", "--shard", "1", "--num-shards", "12",
            "--out", "results.part-1.json"]

    first = sf._resume_argv(base, 357, 1)
    assert first[:len(base)] == base
    assert first[-2:] == ["--resume-from=357", "--restarts=1"]

    second = sf._resume_argv(first, 512, 2)
    assert second.count("--resume-from=512") == 1
    assert len([a for a in second if a.startswith("--resume-from")]) == 1
    assert len([a for a in second if a.startswith("--restarts")]) == 1
    assert second[-2:] == ["--resume-from=512", "--restarts=2"]

    # Losse-waardevorm hoort net zo goed gestript te worden.
    losse = sf._resume_argv(base + ["--resume-from", "40", "--restarts", "1"], 99, 2)
    assert "40" not in losse and "1" in losse  # "1" is de shard-waarde, die blijft
    assert losse[-2:] == ["--resume-from=99", "--restarts=2"]


def test_restart_budget_is_begrensd():
    assert 0 < sf.MAX_SHARD_RESTARTS <= 10


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
