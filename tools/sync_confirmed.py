#!/usr/bin/env python3
"""Onderhoud de bevestigd-groen-lijst na een scrape.

Reconcilieert de confirmed_file van een dataset (bv. data/confirmed.json) met de
verse results.json. Draai dit na finalize/merge (de cron doet dat na de merge-
stap). Shard-veilig: de scrape leest confirmed.json alleen, deze tool schrijft.

Regels per results-entry:
- overgeslagen site (entry met "confirmed": true): met rust laten (datum blijft
  staan, zodat hij na REVERIFY_DAYS vanzelf opnieuw gecheckt wordt).
- echt gescrapt en groen (has_statement + success): toevoegen/verversen met datum
  vandaag.
- echt gescrapt en success + geen verklaring: verwijderen (verklaring weg).
- echt gescrapt met error/timeout: met rust laten (kon niet verifieren, dus de
  bestaande bevestiging niet weggooien om een transiente challenge).

Gebruik:
    python tools/sync_confirmed.py                 # dataset webshops
    python tools/sync_confirmed.py --dataset telecom
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tools.scrape_footer as s  # noqa: E402

_COMMENT = (
    "Bevestigd-groen-lijst: sites met geverifieerde toegankelijkheidsverklaring. "
    "scrape_footer.py slaat deze op de wekelijkse run over zolang 'confirmed' < "
    "REVERIFY_DAYS oud is; daarna herverifieert hij vanzelf. tools/sync_confirmed.py "
    "onderhoudt dit bestand na elke scrape. 'confirmed' = datum laatst echt geverifieerd."
)


def sync_confirmed(ds, today=None):
    """Werk de confirmed_file van een dataset bij op basis van results.json."""
    confirmed_file = ds.get("confirmed_file")
    if not confirmed_file:
        print(f"Dataset {ds['key']} heeft geen confirmed_file; niets te doen.")
        return
    today = today or datetime.now(timezone.utc).date().isoformat()

    existing = s._load_confirmed(ds)  # {genormaliseerde url: entry}
    with open(ds["results_file"], encoding="utf-8") as f:
        results = json.load(f).get("webshops", [])

    added = refreshed = removed = 0
    for r in results:
        nurl = s._normalize_url(r["url"])
        if r.get("confirmed"):
            continue  # overgeslagen: bevestiging niet aanraken
        if r["has_statement"] and r["scrape_status"] == "success":
            refreshed += nurl in existing
            added += nurl not in existing
            existing[nurl] = {
                "name": r.get("name"),
                "url": r["url"],
                "statement_url": r.get("statement_url"),
                "statement_link_text": r.get("statement_link_text"),
                "confirmed": today,
            }
        elif r["scrape_status"] == "success" and not r["has_statement"]:
            if existing.pop(nurl, None) is not None:
                removed += 1
        # error/timeout: laat de bestaande bevestiging staan

    sites = sorted(existing.values(), key=lambda e: (e.get("name") or e["url"]).lower())
    payload = {"_comment": _COMMENT, "sites": sites}
    s._write_atomic(confirmed_file, json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"{confirmed_file.name}: {len(sites)} sites "
          f"(+{added} nieuw, {refreshed} ververst, -{removed} verwijderd)")


def main():
    parser = argparse.ArgumentParser(description="Onderhoud de bevestigd-groen-lijst")
    parser.add_argument("--dataset", choices=list(s.DATASETS), default="webshops")
    args = parser.parse_args()
    sync_confirmed(s.DATASETS[args.dataset])


if __name__ == "__main__":
    main()
