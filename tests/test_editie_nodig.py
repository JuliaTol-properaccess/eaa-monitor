#!/usr/bin/env python3
"""Tests voor tools/editie_nodig.py, zonder git.

    python3 tests/test_editie_nodig.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.editie_nodig import besluit  # noqa: E402


def test_te_vroeg():
    b = besluit("2026-12-07", "2026-11-23", {"2026-12-08"}, set())
    assert b["besluit"] == "niets" and b["dagen"] == 14


def test_maken_na_21_dagen():
    b = besluit("2026-12-14", "2026-11-23", {"2026-12-15"}, set())
    assert b["besluit"] == "maken" and b["dagen"] == 21
    assert b["branch"] == "carousel-editie-2026-12-14"


def test_wachten_op_scan():
    b = besluit("2026-12-14", "2026-11-23", {"2026-12-08"}, set())
    assert b["besluit"] == "wachten" and b["scan_datum"] == "2026-12-15"


def test_branch_bestaat_al():
    b = besluit("2026-12-14", "2026-11-23", {"2026-12-15"}, {"carousel-editie-2026-12-14"})
    assert b["besluit"] == "niets"
    b = besluit("2026-12-14", "2026-11-23", {"2026-12-15"}, {"claude/carousel-editie-2026-12-14"})
    assert b["besluit"] == "niets"


def test_nog_geen_editie():
    assert besluit("2026-12-14", None, {"2026-12-15"}, set())["besluit"] == "maken"


if __name__ == "__main__":
    for naam, f in list(globals().items()):
        if naam.startswith("test_"):
            f()
            print("ok", naam)
