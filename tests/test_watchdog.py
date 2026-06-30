#!/usr/bin/env python3
"""Deterministische test voor de per-site-watchdog (site_deadline).

Twee lagen worden afzonderlijk getoetst, zonder netwerk of Playwright:
- SIGALRM breekt een gewone (Python/netwerk) hang netjes af met SiteTimeout.
- De kill-watchdog-thread escaleert na KILL_GRACE_S en kilt het chromium-proces,
  voor het geval de hang in de Playwright-driver zit (die SIGALRM niet kan
  breken; zo hing shard 9 op 29 juni 2026 bijna 3 uur).

Gebruik:
    python tests/test_watchdog.py     # print PASS/FAIL, exit 1 bij fout
    pytest tests/test_watchdog.py
"""

import signal
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tools.scrape_footer as sf  # noqa: E402


class _patch:
    """Mini-contextmanager: zet sf-attributen tijdelijk, herstel daarna."""

    def __init__(self, **kw):
        self.kw = kw
        self._old = {}

    def __enter__(self):
        for k, v in self.kw.items():
            self._old[k] = getattr(sf, k)
            setattr(sf, k, v)
        return self

    def __exit__(self, *exc):
        for k, v in self._old.items():
            setattr(sf, k, v)
        return False


def test_sigalrm_breaks_a_plain_hang():
    """Een gewone hang binnen de cap wordt door SIGALRM afgebroken."""
    if not hasattr(signal, "SIGALRM"):
        return  # geen SIGALRM (bv. Windows): laag niet beschikbaar, skip
    t0 = time.monotonic()
    raised = False
    try:
        with sf.site_deadline(1):
            time.sleep(5)
    except sf.SiteTimeout:
        raised = True
    elapsed = time.monotonic() - t0
    assert raised, "SiteTimeout had moeten vuren"
    assert elapsed < 2.5, f"cap vuurde te laat ({elapsed:.1f}s)"


def test_kill_watchdog_escalates_when_sigalrm_cannot():
    """Vuurt SIGALRM niet (seconds=0 -> alarm uit), dan kilt de thread alsnog.

    Simuleert de driver-wedge: we geven seconds=0 zodat signal.alarm(0) geen
    SIGALRM plant, en controleren dat de kill-watchdog na KILL_GRACE_S vuurt.
    """
    fired = threading.Event()
    with _patch(psutil=object(),  # truthy: watchdog-thread wordt bewapend
                KILL_GRACE_S=0.2,
                _kill_browser_processes=lambda: (fired.set(), True)[1]):
        with sf.site_deadline(0):
            time.sleep(0.5)
    assert fired.is_set(), "kill-watchdog had moeten escaleren"


def test_kill_watchdog_cancelled_on_clean_exit():
    """Loopt de site snel klaar, dan kilt de watchdog niets."""
    fired = threading.Event()
    with _patch(psutil=object(),
                KILL_GRACE_S=0.4,
                _kill_browser_processes=lambda: (fired.set(), True)[1]):
        with sf.site_deadline(0):
            pass  # meteen klaar
        time.sleep(0.8)  # ruim voorbij de grace
    assert not fired.is_set(), "watchdog had gecanceld moeten zijn"


def test_kill_is_noop_without_psutil():
    """Zonder psutil valt de kill stil terug (geen crash, geen kill)."""
    with _patch(psutil=None):
        assert sf._kill_browser_processes() is False


def test_reaper_fires_after_double_grace():
    """Breekt niets de hang, dan roept de reaper (on_giveup) na 2x grace aan.

    De echte reaper doet os._exit(0); hier geven we een onschadelijke on_giveup
    mee en controleren dat hij vuurt. seconds=0 zet SIGALRM uit, geen psutil zodat
    de kill-laag niets doet -> alleen de reaper kan de hang nog opvangen.
    """
    fired = threading.Event()
    with _patch(psutil=None, KILL_GRACE_S=0.2):
        with sf.site_deadline(0, on_giveup=fired.set):
            time.sleep(0.7)  # voorbij 2x grace (0.4s)
    assert fired.is_set(), "reaper had moeten vuren"


def test_reaper_cancelled_on_clean_exit():
    """Loopt de site netjes klaar, dan reapt hij niet."""
    fired = threading.Event()
    with _patch(psutil=None, KILL_GRACE_S=0.3):
        with sf.site_deadline(0, on_giveup=fired.set):
            pass  # meteen klaar
        time.sleep(0.9)  # ruim voorbij 2x grace
    assert not fired.is_set(), "reaper had gecanceld moeten zijn"


CASES = [
    test_sigalrm_breaks_a_plain_hang,
    test_kill_watchdog_escalates_when_sigalrm_cannot,
    test_kill_watchdog_cancelled_on_clean_exit,
    test_kill_is_noop_without_psutil,
    test_reaper_fires_after_double_grace,
    test_reaper_cancelled_on_clean_exit,
]


def run():
    ok = True
    for case in CASES:
        try:
            case()
            print(f"  [PASS] {case.__name__}")
        except AssertionError as e:
            ok = False
            print(f"  [FAIL] {case.__name__}: {e}")
    print("\n  " + ("ALLES GOED" if ok else "REGRESSIE GEDETECTEERD"))
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
