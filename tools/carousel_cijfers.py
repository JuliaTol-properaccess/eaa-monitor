#!/usr/bin/env python3
"""Cijfers voor de driewekelijkse LinkedIn-carousel van de EAA-monitor.

    python3 tools/carousel_cijfers.py                  # leest origin/main, schrijft naar stdout
    python3 tools/carousel_cijfers.py --out cijfers.json
    python3 tools/carousel_cijfers.py --ref werkmap    # leest de bestanden in deze checkout

Leest de zeven history-bestanden en data/axe-results.json en schrijft één JSON
met alles wat de slides en de posttekst nodig hebben.

Percentages zijn over de gecontroleerde sites: met / (met + zonder). Het veld
pct_with in de history-bestanden deelt door het totaal inclusief de sites die
niet te controleren waren, en is daarom niet bruikbaar voor de carousel.

Sectornamen, volgorde en bestandsnamen komen uit DATASETS in
tools/scrape_footer.py, gelezen op dezelfde ref als de data.
"""

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WERKMAP = "werkmap"

# Begin van de wekelijkse reeks; de metingen daarvoor (juni tot augustus)
# hebben geen vaste weekdag.
STANDAARD_VANAF = "2026-09-07"
# Een editie per drie weken: de vorige editie staat drie metingen terug.
METINGEN_PER_EDITIE = 3
# Onder dit aantal sites is één site al 3 tot 10 procentpunt.
KLEIN_ONDER = 30


def lees(pad, ref):
    """Inhoud van een repo-bestand, via git show of uit de werkmap."""
    if ref == WERKMAP:
        return (ROOT / pad).read_text(encoding="utf-8")
    return subprocess.run(
        ["git", "show", f"{ref}:{pad}"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout


def sectoren_uit_bron(bron):
    """Haal key, naam, zelfstandig naamwoord en history-bestand uit DATASETS.

    Ontleedt de broncode met ast in plaats van scrape_footer te importeren:
    die module trekt de scraper-afhankelijkheden mee.
    """
    boom = ast.parse(bron)
    for knoop in boom.body:
        if (isinstance(knoop, ast.Assign) and len(knoop.targets) == 1
                and getattr(knoop.targets[0], "id", None) == "DATASETS"):
            break
    else:
        raise ValueError("DATASETS niet gevonden in tools/scrape_footer.py")

    def tekst(waarde):
        if isinstance(waarde, ast.Constant) and isinstance(waarde.value, str):
            return waarde.value
        # DATA_DIR / "history.json"
        if isinstance(waarde, ast.BinOp) and isinstance(waarde.right, ast.Constant):
            return waarde.right.value
        return None

    sectoren = []
    for sleutel, inhoud in zip(knoop.value.keys, knoop.value.values):
        velden = {k.value: tekst(v) for k, v in zip(inhoud.keys, inhoud.values)}
        kop = velden.get("summary_heading") or ""
        naam, _, toezicht = kop.partition(" · ")
        sectoren.append({
            "key": sleutel.value,
            "naam": naam,
            "toezicht": toezicht,
            "noun": velden.get("noun"),
            "history_file": "data/" + velden["history_file"],
        })
    return sectoren


def pct(met, zonder):
    """Hele procenten, ,5 naar boven (round() rondt 62,5 af naar 62)."""
    noemer = met + zonder
    return (200 * met + noemer) // (2 * noemer) if noemer else None


def meting(rij):
    met, zonder = rij["with_statement"], rij["without_statement"]
    return {
        "datum": rij["date"],
        "totaal": rij["total"],
        "met": met,
        "zonder": zonder,
        "niet_te_controleren": rij["errors"],
        "gecontroleerd": met + zonder,
        "pct_met": pct(met, zonder),
    }


def optellen(metingen, datum):
    som = {"met": 0, "zonder": 0, "totaal": 0, "niet_te_controleren": 0}
    for m in metingen:
        for k in som:
            som[k] += m[k]
    return {
        "datum": datum,
        "totaal": som["totaal"],
        "met": som["met"],
        "zonder": som["zonder"],
        "niet_te_controleren": som["niet_te_controleren"],
        "gecontroleerd": som["met"] + som["zonder"],
        "pct_met": pct(som["met"], som["zonder"]),
    }


def verschil(nu, toen):
    if toen is None:
        return None
    return {
        "datum": toen["datum"],
        "met": nu["met"] - toen["met"],
        "pct_punt": (None if nu["pct_met"] is None or toen["pct_met"] is None
                     else nu["pct_met"] - toen["pct_met"]),
        "pct_met_toen": toen["pct_met"],
    }


def bereken(histories, sectoren, axe, vanaf=STANDAARD_VANAF):
    """histories: {key: [history-rijen]}; sectoren: uit sectoren_uit_bron."""
    peildatum = max(r["date"] for k in histories for r in histories[k])

    uit = {"peildatum": peildatum, "lijn_vanaf": vanaf,
           "noemer": "met + zonder (sites die we konden controleren)",
           "sectoren": [], "totaal": None, "wcag_scan": None, "waarschuwingen": []}

    per_datum = {}  # datum -> [metingen], alleen data die in alle sectoren staan
    for s in sectoren:
        rijen = sorted(histories[s["key"]], key=lambda r: r["date"])
        laatste = rijen[-1]
        if laatste["date"] != peildatum:
            uit["waarschuwingen"].append(
                f"{s['key']}: laatste meting {laatste['date']}, peildatum {peildatum}")
        reeks = [meting(r) for r in rijen if r["date"] >= vanaf]
        for m in reeks:
            per_datum.setdefault(m["datum"], []).append(m)
        nu = meting(laatste)
        vorige = (meting(rijen[-1 - METINGEN_PER_EDITIE])
                  if len(rijen) > METINGEN_PER_EDITIE else None)
        uit["sectoren"].append({
            **{k: s[k] for k in ("key", "naam", "toezicht", "noun")},
            **nu,
            "klein": nu["totaal"] < KLEIN_ONDER,
            "vorige_editie": verschil(nu, vorige),
            "eerste_meting": verschil(nu, reeks[0]) if reeks else None,
            "lijn": [{"datum": m["datum"], "pct_met": m["pct_met"], "met": m["met"],
                      "gecontroleerd": m["gecontroleerd"]} for m in reeks],
        })

    aantal = len(sectoren)
    volledige = sorted(d for d, ms in per_datum.items() if len(ms) == aantal)
    onvolledig = sorted(d for d, ms in per_datum.items() if len(ms) != aantal)
    if onvolledig:
        uit["waarschuwingen"].append(
            "niet in alle sectoren gemeten, buiten de totaallijn: " + ", ".join(onvolledig))
    lijn_totaal = [optellen(per_datum[d], d) for d in volledige]
    nu_totaal = optellen([{k: s[k] for k in ("met", "zonder", "totaal", "niet_te_controleren")}
                          for s in uit["sectoren"]], peildatum)
    vorige_totaal = (lijn_totaal[-1 - METINGEN_PER_EDITIE]
                     if len(lijn_totaal) > METINGEN_PER_EDITIE
                     and lijn_totaal[-1]["datum"] == peildatum else None)
    uit["totaal"] = {
        **nu_totaal,
        "vorige_editie": verschil(nu_totaal, vorige_totaal),
        "eerste_meting": verschil(nu_totaal, lijn_totaal[0]) if lijn_totaal else None,
        "lijn": [{"datum": m["datum"], "pct_met": m["pct_met"], "met": m["met"],
                  "gecontroleerd": m["gecontroleerd"]} for m in lijn_totaal],
    }

    sam = axe["summary"]
    uit["wcag_scan"] = {
        "scandatum": axe.get("generated"),
        "total": sam["total"],
        "fouten": sam["fouten"],
        "schoon": sam["schoon"],
        "niet_scanbaar": sam["niet_scanbaar"],
        "pct_fouten_van_gescand": sam["pct_fouten_van_gescand"],
    }
    return uit


def laad(ref, vanaf):
    sectoren = sectoren_uit_bron(lees("tools/scrape_footer.py", ref))
    histories = {s["key"]: json.loads(lees(s["history_file"], ref)) for s in sectoren}
    axe = json.loads(lees("data/axe-results.json", ref))
    uit = bereken(histories, sectoren, axe, vanaf)
    uit["bron"] = {"ref": ref, "bestanden": [s["history_file"] for s in sectoren]
                   + ["data/axe-results.json"]}
    return uit


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ref", default="origin/main",
                   help=f"git-ref om uit te lezen, of '{WERKMAP}' voor de bestanden op schijf")
    p.add_argument("--vanaf", default=STANDAARD_VANAF, help="begin van de lijn (JJJJ-MM-DD)")
    p.add_argument("--out", help="schrijf naar dit bestand in plaats van stdout")
    args = p.parse_args()

    uit = laad(args.ref, args.vanaf)
    tekst = json.dumps(uit, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(tekst, encoding="utf-8")
    else:
        sys.stdout.write(tekst)
    for w in uit["waarschuwingen"]:
        print("let op:", w, file=sys.stderr)


if __name__ == "__main__":
    main()
