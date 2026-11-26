#!/usr/bin/env python3
"""Bepaal of er een nieuwe editie van de LinkedIn-carousel gemaakt moet worden.

    python3 tools/editie_nodig.py                  # leest origin/main
    python3 tools/editie_nodig.py --laatste-editie 2026-11-02   # alleen voor een testrun

Drukt één JSON-regel af met `besluit`:
  maken    de laatste editie is 21 dagen of ouder dan de peildatum van de data,
           de WCAG-scan van de dag na de peildatum staat op de ref, en er is
           nog geen branch voor deze editie
  wachten  het is tijd, maar de WCAG-scan van die week is nog niet binnen
  niets    nog geen 21 dagen, of de branch voor deze editie bestaat al

De cloud-routine "EAA-monitor carousel-herinnering" draait dit elke dinsdag en
woensdag; zie workflows/linkedin_carousel_editie.md.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.carousel_cijfers import STANDAARD_VANAF, laad  # noqa: E402

DAGEN_TUSSEN_EDITIES = 21
EDITIEMAP = re.compile(r"^(\d{4}-\d{2}-\d{2})_eaa-monitor-editie$")
SCAN_COMMIT = "Update WCAG-scan {}"
BRANCH = "carousel-editie-{}"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout


def edities(ref):
    namen = git("ls-tree", "--name-only", f"{ref}:social-posts").split()
    return sorted(m.group(1) for n in namen if (m := EDITIEMAP.match(n)))


def besluit(peildatum, laatste_editie, scan_datums, bestaande_branches):
    """Zuivere beslissing; alle invoer als JJJJ-MM-DD-strings."""
    uit = {"peildatum": peildatum, "laatste_editie": laatste_editie,
           "branch": BRANCH.format(peildatum)}
    if laatste_editie is None:
        dagen = None
    else:
        dagen = (date.fromisoformat(peildatum) - date.fromisoformat(laatste_editie)).days
    uit["dagen"] = dagen
    if dagen is not None and dagen < DAGEN_TUSSEN_EDITIES:
        return {**uit, "besluit": "niets",
                "reden": f"laatste editie is {dagen} dagen ouder dan de peildatum, "
                         f"minder dan {DAGEN_TUSSEN_EDITIES}"}
    # Ook een branch met een voorvoegsel telt (een cloud-sessie pusht soms naar claude/...).
    al = sorted(b for b in bestaande_branches if b.endswith(uit["branch"]))
    if al:
        return {**uit, "besluit": "niets",
                "reden": f"branch {al[0]} bestaat al; de editie staat in een pull request"}
    scan = (date.fromisoformat(peildatum) + timedelta(days=1)).isoformat()
    uit["scan_datum"] = scan
    if scan not in scan_datums:
        return {**uit, "besluit": "wachten",
                "reden": f"commit '{SCAN_COMMIT.format(scan)}' staat nog niet op de ref"}
    return {**uit, "besluit": "maken", "reden": "tijd voor een nieuwe editie"}


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ref", default="origin/main")
    p.add_argument("--laatste-editie",
                   help="doe alsof dit de laatste editie is (JJJJ-MM-DD); alleen voor een testrun")
    args = p.parse_args()

    peildatum = laad(args.ref, STANDAARD_VANAF)["peildatum"]
    alle = edities(args.ref)
    laatste = args.laatste_editie or (alle[-1] if alle else None)
    onderwerpen = git("log", args.ref, "--format=%s", "-200").splitlines()
    scans = {o.removeprefix("Update WCAG-scan ").strip()
             for o in onderwerpen if o.startswith("Update WCAG-scan ")}
    branches = {r.split("refs/heads/", 1)[1]
                for r in git("ls-remote", "--heads", "origin").splitlines()
                if "refs/heads/" in r}
    print(json.dumps(besluit(peildatum, laatste, scans, branches), ensure_ascii=False))


if __name__ == "__main__":
    main()
