#!/usr/bin/env python3
"""
Generator voor de WCAG-audit-pagina (WAT-framework, Layer 3: Tool).

Rendert data/auditbureaus.json naar een server-rendered tabel in
public/wcag-audit.html. Server-rendered, zodat de lijst vindbaar is in
zoekmachines en AI-zoekmachines (GEO).

Deelt de head/header/footer met de artikelgenerator (tools/build_articles.py),
zodat navigatie en stijl overal gelijk zijn.

Gebruik:
    python tools/build_auditbureaus.py

Format van data/auditbureaus.json (lijst van objecten):
    [
      {
        "naam": "Naam bureau",
        "website": "https://www.voorbeeld.nl",
        "specialisatie": "Website-audits, app-audits, advies",
        "talen": ["NL", "EN"]
      }
    ]
De volgorde in het bestand is de volgorde op de pagina.
"""

import html
import json
import sys
from pathlib import Path

# Gedeelde partials hergebruiken uit de artikelgenerator.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_articles import shared_head, site_header, site_footer, BASE_URL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "auditbureaus.json"
OUT_FILE = ROOT / "public" / "wcag-audit.html"

ACTIVE_PATH = "/wcag-audit.html"
URL = f"{BASE_URL}/wcag-audit.html"
TITLE = "WCAG-audit: vind een auditbureau — EAA Monitor"
DESCRIPTION = (
    "Wil je weten of je website voldoet aan de WCAG en de European Accessibility "
    "Act? Een onafhankelijke WCAG-audit brengt het in kaart. Overzicht van "
    "auditbureaus in Nederland."
)


def _talen(value):
    if isinstance(value, list):
        return ", ".join(str(t) for t in value)
    return str(value or "")


def _rows(bureaus):
    rows = []
    for b in bureaus:
        naam = html.escape(str(b.get("naam", "")).strip())
        website = str(b.get("website", "")).strip()
        spec = html.escape(str(b.get("specialisatie", "")).strip())
        talen = html.escape(_talen(b.get("talen")))
        if website:
            naam_cell = (
                f'<a href="{html.escape(website)}" target="_blank" '
                f'rel="noopener noreferrer" class="text-brand hover:text-brand-dark font-semibold">{naam or website}</a>'
            )
        else:
            naam_cell = naam or "—"
        rows.append(
            "        <tr class=\"border-b border-gray-100\">\n"
            f"          <td class=\"py-4 px-4 align-top\">{naam_cell}</td>\n"
            f"          <td class=\"py-4 px-4 align-top text-gray-700\">{spec or '—'}</td>\n"
            f"          <td class=\"py-4 px-4 align-top text-gray-700 whitespace-nowrap\">{talen or '—'}</td>\n"
            "        </tr>"
        )
    return "\n".join(rows)


def _table_or_empty(bureaus):
    if not bureaus:
        return """
      <div class="card p-10 text-center text-gray-600">
        <p>De lijst met auditbureaus wordt binnenkort gevuld.</p>
      </div>"""
    return f"""
      <div class="card overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <caption class="sr-only">Auditbureaus voor een WCAG-audit in Nederland</caption>
            <thead>
              <tr class="bg-gray-50 border-b border-gray-200 text-left">
                <th scope="col" class="py-3 px-4 font-bold text-navy">Auditbureau</th>
                <th scope="col" class="py-3 px-4 font-bold text-navy">Specialisatie</th>
                <th scope="col" class="py-3 px-4 font-bold text-navy">Talen</th>
              </tr>
            </thead>
            <tbody>
{_rows(bureaus)}
            </tbody>
          </table>
        </div>
      </div>"""


def render(bureaus):
    head = shared_head(TITLE, DESCRIPTION, URL)
    return f"""{head}<body class="bg-white">
{site_header(ACTIVE_PATH)}
  <main id="main">

    <section class="bg-navy text-white on-dark">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-20">
        <h1 class="text-4xl md:text-6xl font-extrabold leading-[1.05] tracking-tight max-w-3xl">Vind een WCAG-audit</h1>
        <p class="mt-6 text-lg md:text-xl text-white/70 max-w-2xl leading-relaxed">Een onafhankelijke audit brengt in kaart of je website en app voldoen aan de WCAG en de European Accessibility Act. Hieronder vind je auditbureaus in Nederland.</p>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 -mt-10 relative z-10 pb-4">
      <div class="prose max-w-prose">
        <h2>Waarom een onafhankelijke audit?</h2>
        <p>Een geautomatiseerde tool vindt maar een deel van de toegankelijkheidsproblemen. De barrieres die echte gebruikers tegenkomen, zie je pas met een inhoudelijke audit en met tests door mensen die assistieve technologie gebruiken. Een onafhankelijk bureau heeft geen belang bij de uitkomst en kijkt puur naar wat werkt voor de bezoeker.</p>
      </div>
    </section>

    <section class="max-w-7xl mx-auto px-4 sm:px-6 mt-6" aria-label="Auditbureaus">
      <h2 class="text-2xl md:text-3xl font-extrabold text-navy tracking-tight mb-6">Auditbureaus in Nederland</h2>
{_table_or_empty(bureaus)}
      <p class="mt-4 text-sm text-gray-600">Staat jouw bureau hier nog niet? Deze lijst wordt met de hand samengesteld.</p>
    </section>

  </main>
{site_footer()}</body>
</html>
"""


def main():
    if not DATA_FILE.exists():
        sys.exit(f"Geen databestand gevonden: {DATA_FILE}")
    try:
        bureaus = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"Ongeldige JSON in {DATA_FILE.name}: {exc}")
    if not isinstance(bureaus, list):
        sys.exit(f"{DATA_FILE.name} moet een JSON-lijst zijn.")

    OUT_FILE.write_text(render(bureaus), encoding="utf-8")
    print(f"Geschreven: {OUT_FILE.relative_to(ROOT)} ({len(bureaus)} bureaus)")


if __name__ == "__main__":
    main()
