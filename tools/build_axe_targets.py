#!/usr/bin/env python3
"""Bouwt de scan-doellijst voor tools/scan_axe.py: elke unieke site met een
verklaring (has_statement=True) uit de zes results-bestanden, gededupliceerd op URL.

Gebruik:
    python tools/build_axe_targets.py --out .tmp/verklaring-sites.json
"""
import argparse
import json
from pathlib import Path

FILES = {
    "webshops": "data/results.json",
    "financieel": "data/results-financieel.json",
    "telecom": "data/results-telecom.json",
    "vervoer": "data/results-vervoer.json",
    "media": "data/results-media.json",
    "ebooks": "data/results-ebooks.json",
}


def items(path):
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        for k in ("webshops", "results", "sites", "items"):
            if isinstance(data.get(k), list):
                return data[k]
    return data if isinstance(data, list) else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".tmp/verklaring-sites.json")
    args = ap.parse_args()

    seen = {}
    for sector, path in FILES.items():
        if not Path(path).exists():
            continue
        for it in items(path):
            if it.get("has_statement") is True:
                key = (it.get("url") or "").rstrip("/").lower()
                if key and key not in seen:
                    seen[key] = {"name": it.get("name") or it.get("url"),
                                 "url": it.get("url"), "sector": sector}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(list(seen.values()), ensure_ascii=False, indent=2))
    print(f"{out}: {len(seen)} sites met verklaring")


if __name__ == "__main__":
    main()
