#!/usr/bin/env python3
"""Bouwt data/axe-results.json uit een scan-output van tools/scan_axe.py.

Dit is de overlay die monitor.html/app.js client-side op URL koppelt (los van de
footer-scrape, zodat een nieuwe scrape de scanuitslag niet overschrijft). Per site
één status: "fouten", "schoon" of "niet-scanbaar".

Optioneel patcht het ook het kerncijfer in een HTML-pagina tussen de markers
<!--AXE-STAT:START--> en <!--AXE-STAT:END--> (gebakken cijfer voor GEO/no-JS).

Gebruik:
    python tools/build_axe_overlay.py --in .tmp/axe-verklaring-final.json
    python tools/build_axe_overlay.py --in <scan> --patch-html public/monitor.html
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

MONTHS = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
          "augustus", "september", "oktober", "november", "december"]
DETAIL_URL = "https://wcag-scan.nl/"
START = "<!--AXE-STAT:START-->"
END = "<!--AXE-STAT:END-->"


def norm(u):
    return (u or "").rstrip("/").lower()


def dutch_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def stat_sentence(summary, generated, engine, detail_url):
    scanned = summary["fouten"] + summary["schoon"]
    return (
        f'Van de {scanned} sites met een verklaring die we konden scannen, bevat '
        f'<strong>{summary["pct_fouten_van_gescand"]}%</strong> minstens één '
        f'automatisch detecteerbare WCAG-fout. Gemeten met {engine} op '
        f'{dutch_date(generated)}. Automatische checks dekken niet alle WCAG-eisen, '
        f'dus "geen fouten gevonden" betekent niet automatisch volledig toegankelijk. '
        f'Wil je weten wélke fouten een site bevat, gebruik dan '
        f'<a href="{detail_url}" target="_blank" rel="noopener noreferrer" '
        f'class="link">wcag-scan.nl</a>.'
    )


def patch_html(path, sentence):
    p = Path(path)
    html = p.read_text()
    if html.count(START) != 1 or html.count(END) != 1:
        sys.exit(f"FOUT: {path} mist de AXE-STAT-markers precies één keer.")
    new = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        START + sentence + END,
        html,
        count=1,
        flags=re.DOTALL,
    )
    p.write_text(new)
    print(f"{path}: kerncijfer gebakken tussen AXE-STAT-markers.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="scan-output (JSON)")
    ap.add_argument("--out", default="data/axe-results.json")
    ap.add_argument("--detail-url", default=DETAIL_URL)
    ap.add_argument("--patch-html", action="append", default=[],
                    help="HTML-bestand(en) met AXE-STAT-markers om te baken")
    args = ap.parse_args()

    scan = json.loads(Path(args.inp).read_text())
    sites = {}
    cnt = {"fouten": 0, "schoon": 0, "niet-scanbaar": 0}
    for r in scan["results"]:
        if r["status"] == "ok" and r.get("violations"):
            status = "fouten"
        elif r["status"] == "ok":
            status = "schoon"
        else:
            status = "niet-scanbaar"
        cnt[status] += 1
        sites[norm(r["url"])] = {"status": status, "url": r["url"]}

    scanned = cnt["fouten"] + cnt["schoon"]
    generated = datetime.date.today().isoformat()
    engine = "axe-core 4.11.4"
    summary = {
        "total": len(sites),
        "fouten": cnt["fouten"],
        "schoon": cnt["schoon"],
        "niet_scanbaar": cnt["niet-scanbaar"],
        "pct_fouten_van_gescand": round(100 * cnt["fouten"] / scanned) if scanned else 0,
    }
    out = {
        "generated": generated,
        "engine": engine,
        "scope": "WCAG 2.2 A/AA (best-practice uitgesloten)",
        "detail_url": args.detail_url,
        "summary": summary,
        "sites": sites,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"{args.out} geschreven: {summary}")

    if args.patch_html:
        sentence = stat_sentence(summary, generated, engine, args.detail_url)
        for path in args.patch_html:
            patch_html(path, sentence)


if __name__ == "__main__":
    main()
